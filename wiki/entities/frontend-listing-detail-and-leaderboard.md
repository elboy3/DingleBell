---
type: entity
source_files: [frontend/src/pages/ListingDetail.tsx, frontend/src/pages/Leaderboard.tsx]
status: active
verified: 2026-08-24
tags: [frontend, react, page, listing-detail, leaderboard]
---

# Frontend listing detail and leaderboard pages

## Purpose

`ListingDetail.tsx` (`/listings/:id`) is the deep-dive page for a single listing - full category-rating breakdown table, comments from both users, a map, and a StreetEasy/Zillow CTA link; it's also where a listing can still be swiped on if the current user hasn't decided yet. `Leaderboard.tsx` (`/leaderboard`) is the ranked, tabbed view of matched listings only (shared/elliott/madison/AI sort), with an off-market disqualify action.

## Key exports

- `ListingDetail({ user })` - the sole export of `ListingDetail.tsx`.
- `load()` (internal, `ListingDetail.tsx`) - fetches `api.listing(Number(id))`, re-runs whenever the route's `:id` param changes.
- `onSwipe(listingId, direction)` (internal, `ListingDetail.tsx`) - calls `api.swipe` then reloads; only reachable if `swipeDecide={!listing.swipes[user]}` is true, i.e. this user hasn't swiped on this specific listing yet.
- `saveComment()` (internal, `ListingDetail.tsx`) - same pattern as Swipe.tsx's comment form.
- `Leaderboard({ user })` - the sole export of `Leaderboard.tsx`.
- `TABS` (constant, `Leaderboard.tsx`) - four tabs, each a `{ key, label, empty }`: `leaderboard_shared` (min-of-both ranking), `leaderboard_elliott`, `leaderboard_madison`, `leaderboard_ai` (AI taste-match score ranking) - `key` values are passed straight through as the `sort` query param to `api.listings()`.
- `load(sort)` (internal, `Leaderboard.tsx`) - calls `api.listings({ sort, only_matched: "true" })` - **always** scoped to matches only, regardless of tab.
- `onDisqualify(id)` (internal, `Leaderboard.tsx`) - calls `api.setHidden(id, true, "off_market")`, then reloads the current tab.

## Depends on / used by

- [frontend-listing-card](../entities/frontend-listing-card.md)
- [frontend-app-shell](../entities/frontend-app-shell.md) (uses `api`, `mapEmbedUrl`, `CATEGORIES`, `Listing`)
- [frontend-misc](../entities/frontend-misc.md) (uses `useCategoryRate`, `CATEGORIES`)
- [api-routes](../entities/api-routes.md)
- [feed-logic-and-ranking](../entities/feed-logic-and-ranking.md)

## Notes & gotchas

- `ListingDetail.tsx` renders `ListingCard` with `detailLevel="full"` - the only place in the app the category-rating panel is actually editable - plus `linkExternally` (title opens the real listing, not this page) and conditionally `swipeDecide={!listing.swipes[user]}`, so a listing that arrived here without this user having swiped on it yet can still be swiped from the detail page itself.
- The category-ratings breakdown table on `ListingDetail.tsx` only renders at all if at least one of `listing.category_ratings.elliott` or `.madison` is truthy - an unrated listing shows no table, not an empty one.
- `Leaderboard.tsx` hardcodes `only_matched: "true"` in every `load()` call - there is no way to view the Leaderboard for non-matched listings from this page; that's a deliberate scope restriction per `CLAUDE.md` ("the Leaderboard survived this pivot, now scoped to matches instead of the old shared flag").
- The four Leaderboard tabs map directly to backend `sort` values (`leaderboard_shared`/`leaderboard_elliott`/`leaderboard_madison`/`leaderboard_ai`) - adding a new sort mode means adding both a `TABS` entry here and the corresponding case in the backend's sort logic.
- `onDisqualify` is the one path in the whole frontend that flips the shared `hidden` flag to `true` (`Passed.tsx`'s `undoOffMarket` is the only path that flips it back to `false`) - everywhere else in the UI, `hidden` doesn't apply because pre-match rejection is a personal swipe, not a shared hide.

## Related concepts

- [blind-swipe-model](../concepts/blind-swipe-model.md)
- [ai-taste-scoring](../concepts/ai-taste-scoring.md)
- [identity-and-data-model](../concepts/identity-and-data-model.md)
