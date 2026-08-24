---
type: entity
source_files: [webapp/feed_logic.py, webapp/ranking.py, webapp/categories.py]
status: active
verified: 2026-08-24
tags: [swipe-match, ranking, blind-judgment, backend]
---

# Feed logic and ranking

## Purpose

The core business logic of the dating-app-style swipe/match model: deriving a listing's match status from the two independent per-user swipes, computing the shared "our rating" from per-user star ratings, enriching raw listing rows with everything the frontend needs to render, and producing the three per-user views (swipe queue, matches, leaderboard) with the correct visibility rules for each. This is where the project's most safety-critical invariant - a user must never see their partner's opinion on something the user hasn't decided on yet - is actually implemented and enforced.

## Key exports

- `enrich(listings, store)` - attaches `reactions`, rating summary (`ratings`/`both_rating`/`label`), `category_ratings`, `needs_backfill`, `swipes`, `match_status`, `mismatch` to each listing dict; called by nearly every route
- `match_status(swipes)` - `"pending"` until both `KNOWN_USERS` have swiped, then `"match"` (both right) or `"miss"` (otherwise)
- `is_mismatch(swipes)` - true only when both have swiped and disagreed (one right, one left)
- `waiting_on(swipes, user)` - returns the partner's name if `user` swiped right and is the *only* one who's swiped so far, else `None`; the per-viewer-safe primitive everything blind-judgment-related is built on
- `matches_for_user(listings, user)` - real matches, plus (for this viewer only) their own pending right-swipes still awaiting the partner's decision
- `swipe_queue_for_user(listings, user)` - this user's undecided, complete listings, shuffled then sorted highest-AI-score-first
- `filter_listings(listings, *, include_incomplete=False, only_matched=False)` - Leaderboard-only filtering
- `sort_listings(listings, sort)` - `leaderboard_shared` / `leaderboard_ai` / `leaderboard_{user}`, assigns `rank` via `_ranked()`
- `compute_rating_summary(reactions)` (`ranking.py`) - MIN (not average) of both users' star ratings once both have rated
- `KNOWN_USERS` (`ranking.py`) - `["elliott", "madison"]`, the canonical definition re-exported by `deps.py`
- `CATEGORIES` / `CATEGORY_KEYS` (`categories.py`) - the six rating categories: light, kitchen, location, vibe, coziness, space

## Depends on / used by

- [store](../entities/store.md)
- [api-routes](../entities/api-routes.md)
- [webapp-app-and-deps](../entities/webapp-app-and-deps.md)
- [frontend-listing-card](../entities/frontend-listing-card.md)

## Notes & gotchas

- **`waiting_on()` / `matches_for_user()` are the most subtle and important logic in the backend.** `waiting_on()` only returns non-`None` when `swipes` has exactly one entry *and* that entry belongs to the requesting `user` *and* it's `"right"` - by construction this can only ever describe the viewer's own pending like, never the partner's. `matches_for_user()` then only appends the `"pending"` case when `waiting_on()` returns non-`None` for that specific viewer; the mirror case (partner already liked it, viewer hasn't swiped) is simply never added to the result - it stays fully invisible until the viewer swipes themselves. There is no shared/global "someone liked this" flag anywhere in this module.
- `is_mismatch()` is safe to reveal unconditionally (once true, both people have already swiped, so there's no remaining blind-judgment risk) - contrast this with `waiting_on()`, which is unsafe to reveal to the wrong viewer and is guarded accordingly.
- `compute_rating_summary()` combines ratings with **MIN, not average**, deliberately: the goal is a place both people like, so one low rating should pull the combined score down rather than get smoothed over by the other's high rating.
- `swipe_queue_for_user()` shuffles the undecided list *before* sorting by AI score, because most listings have no `ai_score` (scoring is deliberately deprioritized) - without the shuffle, Python's stable sort would leave every unscored listing in DB insertion order, which clusters by neighborhood (scans import one neighborhood at a time), producing a queue that shows one neighborhood after another instead of a mixed order.
- `sort_listings()` is now called only from the Leaderboard's four tabs - the old grid-browse Feed page's neighborhood/price/date filter surface was removed as dead code in an earlier cleanup pass, not kept dormant.
- `CATEGORY_KEYS` in `categories.py` is hand-mirrored in `frontend/src/categories.ts` - not generated, kept in sync manually since there are only six entries and two users.

## Related concepts

- [blind-swipe-model](../concepts/blind-swipe-model.md)
- [the-two-pivots](../concepts/the-two-pivots.md)
- [identity-and-data-model](../concepts/identity-and-data-model.md)
