---
type: entity
source_files: [config.yaml, apt_agent/filters.py]
status: active
verified: 2026-08-24
tags: [config, filters, shared-seam, ingestion]
---

# Shared config (config.yaml + filters.py)

`config.yaml` is the repo's user-owned, non-secret settings file, and
`apt_agent/filters.py` implements the hard price/beds/baths/move-in-window
filter that reads from it. **`config.yaml` is not apt_agent-owned** - despite
living conceptually with the ingestion code, it is a shared seam between the
ingestion side and the webapp side: `webapp/config.py` is a thin wrapper
around `apt_agent.main.load_config()`, so the same file backs both the email
pipeline's filtering and the webapp's `scoring:` section (taste-match config).
Any change here can affect both halves of the repo.

## Purpose

`config.yaml` centralizes everything a human might reasonably want to tune
without touching code: the hard move-in-date window and price/beds/baths
minimums that gate what counts as a candidate listing at all, the Gmail
query/polling cadence for the email pipeline, notification recipients/from-
address, the SQLite db path, and the AI taste-scoring profile path/version.
`filters.py` is the one function (`passes_filters`) that turns the `search:`
section into a pass/fail decision per listing, used to hard-filter the email
pipeline's candidates before anything else happens.

## Key exports

**`config.yaml` sections:**

- `search:` - `earliest_move_in`/`latest_move_in` (hard move-in window,
  currently `2026-09-01`–`2026-10-03`, 1-2 wk flex early/1-2 day flex late per
  inline comment), `price_min`/`price_max` (5000-10000), `beds_min`/`baths_min`
  (both 1), `neighborhoods` (a list of seven Brooklyn neighborhoods -
  explicitly a filter for the **email pipeline only**, not the webapp's
  browser-scan ingestion, which instead uses whatever StreetEasy search is
  currently open in the browser), `no_fee_only`/`pets_required` (both false).
- `gmail:` - `label_or_query` (deliberately avoids `in:inbox`/`is:unread` -
  see Notes below) and `poll_interval_seconds` (180).
- `notify:` - `recipients`, `from_address`, `subject_prefix` - placeholders in
  the repo; overridden at runtime by `NOTIFY_RECIPIENTS`/`NOTIFY_FROM_ADDRESS`
  env vars (from GitHub Secrets) in the deployed GitHub Actions environment so
  real addresses never sit in the public repo.
- `storage:` - `db_path` (`"listings.db"`).
- `scoring:` - `profile_path` (`"taste_profile.md"`) and `profile_version`
  (currently `"v1-liked-only-2026-08-22"`, bumped manually whenever
  `taste_profile.md`'s content meaningfully changes) - config for the
  webapp's AI taste-match scoring, per [ai-taste-scoring](../concepts/ai-taste-scoring.md). Both the profile
  file and `ANTHROPIC_API_KEY` must be present for scoring to run at all;
  otherwise `browser_import.py` just skips it silently - ingestion never
  blocks on scoring being unset up.

**`filters.py`:**

- `passes_filters(listing: dict, cfg: dict) -> tuple[bool, str]` - returns
  `(passes, reason_if_not)`. Checks, in order: price within
  `[price_min, price_max]` (skipped if `price` is `None`), `beds >= beds_min`
  (skipped if `None`), `baths >= baths_min` (skipped if `None`), then
  availability via `_check_availability`.
- `_check_availability(avail_str, search_cfg) -> tuple[bool, str]` - treats
  `None`/empty as passing (unknown, don't filter, let a human eyeball it);
  treats `"now"`/`"immediately"` (case-insensitive substring) as always
  passing; otherwise fuzzy-parses a date via `dateutil.parser` and checks it
  falls within `[earliest_move_in, latest_move_in]`; an unparseable date also
  passes rather than filtering (flag for review instead of silently
  dropping).

## Depends on / used by

- [email-pipeline](email-pipeline.md)
- [webapp-app-and-deps](webapp-app-and-deps.md)
- [browser-import](browser-import.md)
- [check-setup](check-setup.md)
- [scoring](scoring.md)

## Notes & gotchas

- Every numeric/date filter in `passes_filters` is "unknown field, don't
  block on it" - a missing price/beds/baths/availability never causes a
  false-negative filter; only an explicitly out-of-range *known* value does.
  This same permissive pattern is echoed in `webapp/scoring.py`'s graceful
  degradation.
- The `gmail.label_or_query` deliberately skips `in:inbox` (this account has
  a pre-existing filter that auto-archives StreetEasy mail, so `in:inbox`
  would miss it entirely) and skips `is:unread` (fragile against a human
  opening the alert email first). Dedup responsibility is pushed onto
  `ListingStore.already_seen()` (URL-based) instead, bounded by
  `newer_than:1d` so years of backlog mail never gets treated as new.
- `search.neighborhoods` only constrains the **email pipeline** - the
  browser-scan path (StreetEasy/Zillow scans) is bounded by whatever saved
  search is open in the browser, not by this config. Don't assume changing
  this list affects browser-scan results.
- The hard move-in window and price/beds/baths minimums are explicitly
  user-owned per `CLAUDE.md` - don't guess at or change these values without
  the user confirming.
- `notify.recipients`/`from_address` in the committed file are placeholders,
  not the real deployed values - the real values live in GitHub Secrets.

## Related concepts

- [two-ingestion-paths](../concepts/two-ingestion-paths.md)
- [the-two-pivots](../concepts/the-two-pivots.md)
- [dev-tooling-and-hosting](../concepts/dev-tooling-and-hosting.md)
