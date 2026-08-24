---
type: entity
source_files: [frontend/src/pages/Matches.tsx, frontend/src/pages/Passed.tsx]
status: active
verified: 2026-08-24
tags: [frontend, react, page, matches, passed]
---

# Frontend matches and passed pages

## Purpose

Two related audit/review pages downstream of swiping. `Matches.tsx` (`/matches`) shows listings where both people swiped right (real matches, ready for category ratings/comments) plus a "waiting on a decision" section for one-sided likes. `Passed.tsx` (`/passed`) is the full-transparency audit of everything either person swiped left on, split into disagreements versus mutual passes, plus a third section for Leaderboard-disqualified ("off market") matches with an undo.

## Key exports

- `Matches({ user })` - the sole export of `Matches.tsx`, route `/matches`.
- `matched` / `waiting` (derived in `Matches.tsx`) - `listings.filter(l => l.match_status === "match")` and `=== "pending"` respectively, computed client-side from one `api.matches()` response.
- `Passed({ user })` - the sole export of `Passed.tsx`, route `/passed`.
- `disagreements` / `bothPassed` (derived in `Passed.tsx`) - split from one `api.passed()` response via `l.mismatch` (one person liked, one passed) vs. not (both passed, or one passed and the other hasn't decided).
- `offMarket` (state in `Passed.tsx`) - separately fetched via `api.offMarket()`, rendered in its own "Disqualified matches (off market)" section with an `undoOffMarket(id)` handler that calls `api.setHidden(id, false)`.
- `PassedRow` (internal component, `Passed.tsx` only) - compact one-line-per-listing renderer (thumbnail + address + facts + swipe tags) used for the unbounded "Passed while swiping" list.
- `SwipeTags` (internal component, `Passed.tsx` only) - renders each person's swipe state as a colored pill (`liked`/`passed`/`pending`, via `swipeTag()`); used both above `PassedRow` and above the disagreements grid.
- `NAMES` (internal constant, both files) - `{ elliott: "Elliott", madison: "Madison" }`, duplicated in both files rather than shared.

## Depends on / used by

- [frontend-listing-card](../entities/frontend-listing-card.md)
- [frontend-app-shell](../entities/frontend-app-shell.md) (uses `api`, `Listing`)
- [frontend-misc](../entities/frontend-misc.md) (uses `useCategoryRate`)
- [api-routes](../entities/api-routes.md)

## Notes & gotchas

- **Matches.tsx**: the "waiting on a decision" section renders `ListingCard` with `detailLevel="minimal"` specifically because rating panels don't make sense for a listing that isn't a real match yet - showing "not yet rated" rows or a category panel on a one-sided like would be premature. Each waiting card is preceded by a `swipe-tag pending` pill reading "Waiting on {name}" (via `l.waiting_on`).
- **Passed.tsx**: the "Passed while swiping" section uses the compact `PassedRow` list instead of full `ListingCard` grids on purpose - this list is unbounded (passing happens far more often than matching) and full photo cards didn't scale: the comment in the source notes the page was roughly 17,600px tall with full cards before the change, ~6,900px after switching to `PassedRow`. "Disagreements" stays as a full `ListingCard` grid because it's expected to stay small.
- **Passed.tsx**'s three sections have three different semantics that are easy to conflate: "Disagreements" = mismatch (one liked, one passed), "Passed while swiping" = both passed or one-sided-pass-plus-undecided (no undo, ever - a hard invariant of the swipe model), "Disqualified matches" = a *former match* removed via the Leaderboard's shared, reversible off-market flag (`hidden`), which is a completely different mechanism from a personal swipe and is the one thing on this page that can be undone.
- Neither page paginates or virtualizes - if the "Passed while swiping" list keeps growing, `PassedRow`'s row-based layout is the load-bearing scalability decision, not a stopgap.

## Related concepts

- [blind-swipe-model](../concepts/blind-swipe-model.md)
- [the-two-pivots](../concepts/the-two-pivots.md)
- [identity-and-data-model](../concepts/identity-and-data-model.md)
