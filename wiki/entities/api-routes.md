---
type: entity
source_files: [webapp/routes/api_identity.py, webapp/routes/api_listings.py]
status: active
verified: 2026-08-24
tags: [fastapi, rest-api, swipe-match, leaderboard]
---

# API routes

## Purpose

The full set of JSON HTTP routes the React frontend consumes: cookie-based identity get/set, the per-user swipe queue, the Matches view (real matches plus a viewer's own pending likes), the Leaderboard, single-listing detail, the Passed/off-market/needs-scan audit views, and the mutation endpoints (comment, off-market hide, swipe, category-rating).

## Key exports

- `GET /api/whoami` - current user from the identity cookie, or `null`
- `POST /api/whoami` - sets the identity cookie (`{"user": "elliott" | "madison"}`)
- `GET /api/listings` - Leaderboard only; `sort=leaderboard_shared|leaderboard_ai|leaderboard_{user}`, `only_matched` flag
- `GET /api/listings/{listing_id}` - single enriched listing, 404 if not found
- `POST /api/listings/{listing_id}/comment` - sets this user's comment
- `POST /api/listings/{listing_id}/hidden` - shared, reversible off-market disqualify (Leaderboard only, not pre-match rejection)
- `POST /api/listings/{listing_id}/swipe` - personal, permanent left/right swipe (`direction` must be `"left"` or `"right"`)
- `POST /api/listings/{listing_id}/category-rating` - sets a 1-5 per-category score; recomputes this user's overall star rating as a round-half-up average
- `GET /api/swipe-queue` - this user's personal undecided queue, highest AI score first
- `GET /api/matches` - real matches plus, for this viewer only, their own pending right-swipes still awaiting the partner
- `GET /api/passed` - every non-hidden listing with at least one recorded left swipe (both-passed, mismatch, or partial pass)
- `GET /api/off-market` - matches disqualified via `hidden`/`hidden_reason == "off_market"`
- `GET /api/needs-scan` - listings missing a photo or address

## Depends on / used by

- [store](../entities/store.md)
- [feed-logic-and-ranking](../entities/feed-logic-and-ranking.md)
- [webapp-app-and-deps](../entities/webapp-app-and-deps.md)
- [frontend-swipe-page](../entities/frontend-swipe-page.md)
- [frontend-matches-and-passed](../entities/frontend-matches-and-passed.md)
- [frontend-listing-detail-and-leaderboard](../entities/frontend-listing-detail-and-leaderboard.md)

## Notes & gotchas

- Every route except the two `/whoami` routes calls `_require_user(request)`, which raises HTTP 401 if there's no valid identity cookie - the frontend must `POST /api/whoami` before anything else here will work.
- `swipe` is personal and permanent - there is no undo route. A left swipe removes that listing from that user's own queue forever, but it remains visible via `/api/passed` for full transparency.
- `hidden` (off-market) is a categorically different, *shared*, *reversible* action, used only post-match to disqualify a listing that's no longer really available - undoable from the Passed view. It is never used for pre-match rejection; that's what `swipe` is for.
- `category-rating` recomputes the overall star rating as `int(avg + 0.5)` - deliberately round-half-up, not Python's built-in `round()` (round-half-to-even) - a real prior bug silently understated ratings that drive Leaderboard sort order.
- `/api/matches` contains no blind-judgment logic itself; it delegates entirely to `feed_logic.matches_for_user()`/`waiting_on()`. Correctness of "never leak a partner's opinion on an undecided listing" lives entirely in `feed_logic.py`, not here.
- `/api/listings` is Leaderboard-only now - the old grid-browse Feed page's filter params (`neighborhood`, `price_min`/`price_max`, `available_before`, `needs_review`, `min_score`) were removed as dead code along with that page, not left dormant.
- `_enriched_listings(store, *, include_hidden)` is a small shared helper (`store.all_listings()` + `enrich()`) factored out because the same two-line pattern was repeated across nearly every route in this file.

## Related concepts

- [blind-swipe-model](../concepts/blind-swipe-model.md)
- [identity-and-data-model](../concepts/identity-and-data-model.md)
