---
type: entity
source_files: [frontend/src/components/ListingCard.tsx]
status: active
verified: 2026-08-24
tags: [frontend, react, component, listing-card]
---

# Frontend listing card

## Purpose

The single reusable card component that renders a listing everywhere in the app - Swipe, Matches, Passed, Leaderboard, ListingDetail, and NeedsScan all render the same `ListingCard`, differentiated only by props. It's the largest frontend file (240 lines) and the most cross-referenced component in the SPA, covering photo/drag-swipe gesture, price/facts, AI score pill, overall rating readout, the editable per-category rating panel, and the various page-specific action rows (swipe buttons, disqualify link, details link).

## Key exports

- `ListingCard({ listing, user, onCategoryRate, detailLevel, linkExternally, swipeDecide, onSwipe, onDisqualify })` - the sole export.
- `detailLevel?: "minimal" | "summary" | "full"` (default `"summary"`) - `"minimal"` (Swipe page) shows photo/price/facts/AI score only, no ratings or category panel, to keep the fast yes/no decision uncluttered; `"summary"` (Matches/Passed/Leaderboard/NeedsScan default) adds the two people's overall `RatingReadout` rows but no category panel/comments; `"full"` (ListingDetail only) adds the editable category-rating panel (the *only* place ratings are set).
- `linkExternally?: boolean` - on the card's own detail page, the title should open the real StreetEasy/Zillow listing rather than link back to the page it's already on; also suppresses the redundant "Details / comment →" footer link.
- `swipeDecide?: boolean` - Swipe page only: renders big Pass/Interested buttons plus a bidirectional pointer-drag gesture (`onPointerDown`/`onPointerMove`/`commitDrag`) that commits a swipe once dragged past `SWIPE_THRESHOLD` (90px), rotating/translating the photo and fading in PASS/YES stamp overlays as feedback.
- `onSwipe?: (id, direction) => void` - called by both the drag gesture and the explicit buttons when `swipeDecide` is set.
- `onDisqualify?: (id) => void` - Leaderboard only: renders the "Off market / disqualify" link.
- `onCategoryRate: (id, category, score) => void` - required prop, wired to the `category-panel`'s `Stars` inputs when `detailLevel === "full"`.
- `RatingReadout` (internal, not exported) - renders "not yet rated" or a filled star + numeric value for one person's overall rating.
- `NEW_WINDOW_MS` / `SWIPE_THRESHOLD` (internal constants) - "new" badge window (3 days from `first_seen`) and drag-commit distance (90px).

## Depends on / used by

- [frontend-app-shell](../entities/frontend-app-shell.md)
- [frontend-swipe-page](../entities/frontend-swipe-page.md)
- [frontend-matches-and-passed](../entities/frontend-matches-and-passed.md)
- [frontend-listing-detail-and-leaderboard](../entities/frontend-listing-detail-and-leaderboard.md)
- [frontend-misc](../entities/frontend-misc.md)
- [api-routes](../entities/api-routes.md)

## Notes & gotchas

- No listing card anywhere renders an "unhide"/"undo" affordance for a personal swipe - swiping is deliberately permanent and personal (no undo), unlike the old shared-hide model this app replaced. The only reversible action the card supports is `onDisqualify` (Leaderboard's shared off-market flag), which is a categorically different mechanism.
- `detailLevel` is the single prop that controls almost all of the card's visual complexity - when adding a new page that reuses this component, picking the right `detailLevel` (rather than adding new one-off props) is the established pattern.
- The category-rating panel (`detailLevel === "full"`) is the *only* place `onCategoryRate` actually fires from a user action - it's still a required prop on every other `detailLevel` because the component always accepts it, even though it's unused there.
- The drag gesture uses Pointer Events (`onPointerDown/Move/Up/Cancel`) with `setPointerCapture`, not separate mouse/touch handlers - works uniformly across mouse and touch.
- `swipeDecide` and `linkExternally` are usually set together (Swipe page, ListingDetail's own swipe affordance) since a card mid-decision shouldn't link back to its own internal detail page.
- The AI score pill's color threshold (`score-high` >=70, `score-mid` >=40, else `score-low`) and the `ai_reasoning` caption are suppressed at `detailLevel="minimal"` even though the score pill itself still shows - the score is a fast-glance signal on Swipe, the reasoning text is not.

## Related concepts

- [blind-swipe-model](../concepts/blind-swipe-model.md)
- [ai-taste-scoring](../concepts/ai-taste-scoring.md)
