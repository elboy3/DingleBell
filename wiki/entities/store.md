---
type: entity
source_files: [apt_agent/store.py]
status: active
verified: 2026-08-24
tags: [sqlite, data-model, dedup, storage]
---

# ListingStore (shared data layer)

`apt_agent/store.py` is the single `ListingStore` class - the one SQLite-backed
store for every listing seen by either ingestion path (email pipeline or
browser scan), plus per-user reactions/ratings, per-user swipes, and shared
hide/AI-score state. It is the most central, most-referenced file in the
repo: the email pipeline's `main.py`, `browser_import.py`, and the entire
`webapp/` package all read and write through this one class. It also exports
a module-level `normalize_address()` helper used for cross-source dedup.

## Schema/migrations

Base schema (`SCHEMA`, applied via `executescript` on every `ListingStore.__init__`) creates four tables:

- **`listings`** - one row per unique URL (`url TEXT UNIQUE NOT NULL`). Core
  columns: `address`, `normalized_address` (indexed), `price`, `beds`,
  `baths`, `available_date`, `source`, `first_seen`, `alerted`.
- **`listing_reactions`** - per-user rating/comment, `UNIQUE(listing_id, user)` -
  one row per (listing, user) pair, upserted via `ON CONFLICT`.
- **`listing_category_ratings`** - per-user, per-category 1-5 score,
  `UNIQUE(listing_id, user, category)`.
- **`listing_swipes`** - per-user left/right decision, `UNIQUE(listing_id, user)` -
  drives the swipe/match model (see [blind-swipe-model](../concepts/blind-swipe-model.md)).

Indexes: `idx_normalized_address`, `idx_first_seen`, `idx_listing_reactions_listing`,
`idx_listing_category_ratings_listing`, `idx_listing_swipes_listing`.

Beyond the base schema, `_MIGRATIONS` is a flat list of `(column, sql_type)`
pairs applied as `ALTER TABLE listings ADD COLUMN ...` for any column not
already present (checked via `PRAGMA table_info`). This list-based approach
exists specifically because `listings.db` is committed to the repo - existing
databases need incremental `ALTER TABLE`, not a `CREATE TABLE` rewrite.
Migrated columns include `neighborhood`, `sqft`, `listing_agent`, `photo_url`,
`open_house_raw`, `open_house_date`, the AI-scoring columns (`ai_score`,
`ai_reasoning`, `ai_scored_at`, `ai_profile_version`), the shared hide flag
(`hidden`, `hidden_by`, `hidden_at`, `hidden_reason` - reason is currently
only ever `"off_market"`), and `interested`/`interested_by`/`interested_at`.

The `interested*` columns are explicitly **dead**: leftovers from an earlier
shared-swipe-queue design, superseded by the per-user `listing_swipes` table.
Left in place (not dropped) because SQLite can't cheaply drop columns -
nothing in the current codebase reads or writes them. See [the-two-pivots](../concepts/the-two-pivots.md).

## Write API

- `save(listing: dict, alerted: bool) -> int` - `INSERT OR IGNORE` keyed on
  URL uniqueness; if the URL already exists the insert is a no-op and the
  method looks up and returns the existing row's id instead. Also computes
  and stores `normalized_address` at write time. Optional fields
  (`neighborhood`, `sqft`, `listing_agent`, `photo_url`, `open_house_raw`,
  `open_house_date`) are only ever populated by a browser-sourced scan, never
  the email pipeline.
- `backfill_listing(url: str, fields: dict) -> bool` - fills in currently-empty
  columns on an already-saved listing from a fresh scan of the same URL;
  never overwrites a column that already has a value. Used to resume
  scanning listings first saved without a photo/address (paired with
  `needs_backfill_listings()` below). Also recomputes `normalized_address` if
  `address` was empty and is now being filled in.
- `set_rating(listing_id, user, rating)` / `set_comment(listing_id, user, comment)` -
  upsert into `listing_reactions` via `ON CONFLICT(listing_id, user)`.
- `set_category_rating(listing_id, user, category, score)` - upsert into
  `listing_category_ratings` via `ON CONFLICT(listing_id, user, category)`.
- `set_hidden(listing_id, hidden, by, reason="off_market")` - **shared, not
  per-user** - a deliberate joint decision, made only from the Leaderboard to
  disqualify an already-matched listing (e.g. it went off-market), reversible
  via the Passed view's undo. This is explicitly *not* how a pre-match "no" is
  recorded - see `record_swipe` below.
- `record_swipe(listing_id, user, direction)` - personal, one-time,
  permanent per the docstring: a listing swiped in either direction never
  reappears in that user's own swipe queue again. Upserted via
  `ON CONFLICT(listing_id, user)` (so a re-swipe overwrites direction/time,
  but the app layer never exposes an undo for this). Whether the listing
  becomes a match depends only on what the *other* person independently
  does (see `feed_logic.match_status` in [feed-logic-and-ranking](feed-logic-and-ranking.md)).
- `set_ai_score(listing_id, score, reasoning, profile_version)` - updates
  `ai_score`, `ai_reasoning`, `ai_scored_at`, `ai_profile_version`.

## Query/read API

- `already_seen(url) -> bool` - exact URL lookup, the cheap first dedup layer.
- `already_alerted_for_address(address) -> bool` - normalized-address lookup
  restricted to `alerted = 1` rows; used by the email pipeline to avoid
  re-alerting on a listing already alerted under a different URL/source.
- `all_swipes_for_listing(listing_id) -> dict[user, direction]`.
- `get_category_ratings_for_listing(listing_id) -> dict[user, dict[category, score]]`.
- `get_reactions_for_listing(listing_id) -> dict[user, {rating, comment, updated_at}]`.
- `needs_backfill_listings() -> list[dict]` - listings missing `photo_url` or
  `address`, ordered newest-first; candidates for the next browser scan to
  revisit rather than re-scraping everything from scratch.
- `all_listings(include_hidden=False) -> list[dict]` - full listing rows,
  ordered by `first_seen DESC`; excludes `hidden = 1` rows unless requested.
- `stats_since(since)` / `stats_last_24h()` - counts of `{seen, alerted}` for
  the heartbeat email.

## Dedup logic

Two independent layers, per the module docstring:

1. **Exact URL match** - the `UNIQUE NOT NULL` constraint on `listings.url`,
   enforced at insert time via `INSERT OR IGNORE` in `save()`. Cheap, exact,
   catches re-imports of the identical link.
2. **Normalized-address match** - catches the same physical unit
   cross-posted under different URLs across sites (StreetEasy + Zillow +
   RentHop commonly all carry the same listing). Implemented by
   `normalize_address()`:
   - Lowercases the input.
   - Expands street-suffix abbreviations first (`st`→`street`, `ave`→`avenue`,
     `blvd`→`boulevard`, `dr`→`drive`, `rd`→`road`, `pl`→`place`, `ln`→`lane`,
     `ct`→`court`) so `"29 Joralemon St"` and `"29 Joralemon Street"` collapse
     identically - done *before* noise-word stripping deliberately.
   - Strips noise words/phrases that appear in titles but don't identify the
     physical unit: `apt`, `apartment`, `unit`, `for rent`, `rental`, `ny`,
     `new york`, `brooklyn`, `no fee`/`noFee`, `#`.
   - Strips all remaining non-alphanumeric characters.
   - Returns `None` for empty/`None` input.

   The result is stored in `listings.normalized_address` (indexed) at write
   time. The docstring is explicit that this is **best-effort, not perfect** -
   unit-numbering-style differences and typos can still slip through - but it
   catches the common cross-posting case cheaply. `already_alerted_for_address`
   is the only read path that currently queries on this column directly (the
   webapp's own dedup/display logic works off the row set returned by
   `all_listings`).

## Depends on / used by

- [email-pipeline](email-pipeline.md)
- [browser-import](browser-import.md)
- [webapp-app-and-deps](webapp-app-and-deps.md)
- [feed-logic-and-ranking](feed-logic-and-ranking.md)
- [api-routes](api-routes.md)
- [scoring](scoring.md)
- [zillow-email-import](zillow-email-import.md)
- [browser-scan-streeteasy](browser-scan-streeteasy.md)
- [browser-scan-zillow](browser-scan-zillow.md)
- [check-setup](check-setup.md)

## Notes & gotchas

- `save()` returning an existing row's id on a duplicate URL means callers
  can always treat the return value as "the listing's id," whether newly
  inserted or already present - they don't need to branch on which happened.
- `backfill_listing` only fills columns that are currently falsy on the
  existing row (`not row[col]`) - it will never clobber a previously-scraped
  value with a new one, even if the new scan disagrees.
- `set_hidden` and `record_swipe` are deliberately different mechanisms for
  removing a listing from consideration: swiping left is personal/permanent/
  pre-match, hiding is shared/reversible/post-match-only. See
  [blind-swipe-model](../concepts/blind-swipe-model.md) and [identity-and-data-model](../concepts/identity-and-data-model.md).
- `interested`/`interested_by`/`interested_at` columns exist in the schema
  but are dead - do not wire anything up to them, they're a pre-pivot
  artifact kept only because SQLite can't cheaply drop columns.
- Every write method opens its own connection via the `_conn()` context
  manager (commit-on-success, always closes) - there is no shared/long-lived
  connection or explicit transaction spanning multiple calls.

## Related concepts

- [the-two-pivots](../concepts/the-two-pivots.md)
- [blind-swipe-model](../concepts/blind-swipe-model.md)
- [identity-and-data-model](../concepts/identity-and-data-model.md)
- [ai-taste-scoring](../concepts/ai-taste-scoring.md)
