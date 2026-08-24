---
type: concept
status: active
verified: 2026-08-24
tags: [identity, data-model, sqlite, security]
---

# Identity and data model

## Summary

Identity in this app is deliberately lightweight: an unsigned cookie names one of exactly two hardcoded users, no passwords, because the worst case of a tampered cookie is a misattributed rating, not a real security exposure. Underneath that, one shared SQLite `ListingStore` file backs every ingestion path and the webapp, with per-user swipe/rating/category-rating tables layered on top of a single `listings` table, plus a shared, reversible hide flag that is explicitly not the same mechanism as a personal swipe.

## Details

**Identity.** `GET`/`POST /api/whoami` ([api-routes](../entities/api-routes.md)) reads/sets a plain `user` cookie holding `"elliott"` or `"madison"`, validated only against `KNOWN_USERS` (defined once in `webapp/ranking.py`, re-exported from `webapp/deps.py` after an earlier duplication bug was consolidated - see [webapp-app-and-deps](../entities/webapp-app-and-deps.md)). `get_current_user()` returns `None` for anything else, and every route except the two whoami routes calls `_require_user()`, returning HTTP 401 without a valid cookie. There are no signed sessions and no password check anywhere in this layer - a deliberate choice given the tiny, known, trusted user set. The frontend's `WhoAmI` page is the one-time picker that sets this cookie (see [frontend-misc](../entities/frontend-misc.md)); a genuine bug during development (cookie silently not sent) came from a `SameSite=Lax` / cross-hostname mismatch, not from the identity model itself - see [dev-tooling-and-hosting](dev-tooling-and-hosting.md).

**Data model.** [store](../entities/store.md)'s `ListingStore` is the single SQLite-backed class every consumer reads and writes through: the deprioritized email pipeline's `main.py`, [browser-import](../entities/browser-import.md) (used by both browser-scan skills), [zillow-email-import](../entities/zillow-email-import.md), and the entire `webapp/` package. Base schema: `listings` (one row per unique URL, the dedup anchor), `listing_reactions` (per-user overall rating + comment, unique per listing+user), `listing_category_ratings` (per-user, per-category 1-5 score, unique per listing+user+category), and `listing_swipes` (per-user left/right direction, unique per listing+user - see [blind-swipe-model](blind-swipe-model.md)). Columns are added over time via a flat list of `ALTER TABLE` migrations rather than schema rewrites, specifically because `listings.db` is committed to the repo and existing rows must survive upgrades.

**Two categorically different removal mechanisms.** `record_swipe()` is personal, one-time, and permanent - the app layer exposes no undo, though a re-swipe does overwrite the DB row. `set_hidden()` is the opposite in every respect: shared (not per-user), reversible, and used for exactly one purpose - the Leaderboard's "off market" disqualify on an already-matched listing, undoable from the Passed view. Conflating these two would be a real design error; they answer different questions ("do I want this at all" vs. "is this still real-world available"). The `interested`/`interested_by`/`interested_at` columns are dead leftovers from the pre-swipe shared-feed design (see [the-two-pivots](the-two-pivots.md)) - left in the schema because SQLite can't cheaply drop columns, not wired to anything.

## Related entities

- [store](../entities/store.md)
- [api-routes](../entities/api-routes.md)
- [webapp-app-and-deps](../entities/webapp-app-and-deps.md)
- [frontend-misc](../entities/frontend-misc.md)

## Sources

CLAUDE.md ("Lightweight identity, no passwords", architecture summary bullets on `listing_reactions`/`listing_category_ratings`/`listing_swipes`/`hidden`); wiki/entities/store.md, wiki/entities/api-routes.md, wiki/entities/webapp-app-and-deps.md.
