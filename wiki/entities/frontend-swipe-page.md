---
type: entity
source_files: [frontend/src/pages/Swipe.tsx]
status: active
verified: 2026-08-24
tags: [frontend, react, page, swipe]
---

# Frontend swipe page

## Purpose

The app's home page (`/`) - a one-at-a-time personal queue where a user swipes left/right on listings, independently and blind to their partner, with a live comment draft and a map preview alongside the card. This is the primary, highest-traffic page in the dating-app-style model described in `CLAUDE.md`'s "second pivot."

## Key exports

- `Swipe({ user })` - the sole export, rendered at route `/`.
- `load()` (internal) - fetches `api.swipeQueue()` into `queue` state and resets the session's `decided` counter to 0.
- `current` (derived) - always `queue?.[0] ?? null`, i.e. the first item in the queue is "on screen."
- `decide(id)` (internal) - optimistically removes the decided listing from local `queue` state and increments the `decided` counter, called immediately (not after the API round-trip) so the UI advances instantly.
- `onSwipe(id, direction)` (internal) - calls `decide(id)` first, then fires `api.swipe()` and (if there's an unsaved comment draft) `api.setComment()` in parallel via `Promise.all`.
- `saveComment()` (internal) - explicit "Save comment" button handler, independent of the swipe action.
- `OTHER_USER` (internal constant) - `{ elliott: "madison", madison: "elliott" }`, used to look up and display the partner's existing comment on the current listing (their swipe decision itself is never shown - only their comment, if any).

## Depends on / used by

- [frontend-listing-card](../entities/frontend-listing-card.md)
- [frontend-app-shell](../entities/frontend-app-shell.md) (uses `api`, `mapEmbedUrl`, `Listing`)
- [frontend-misc](../entities/frontend-misc.md) (uses `useCategoryRate`, though the callback is a no-op here)
- [api-routes](../entities/api-routes.md)

## Notes & gotchas

- The current listing's id is reflected into the URL as a query param (`/?id=123`) via `useSearchParams`, purely for reference (sharing/debugging) - it deliberately does **not** drive which listing loads. This is intentional: letting the URL param control the queue would risk leaking which listing is "next" across navigation/sharing in a way that could break the blind-swipe guarantee, so the queue is entirely server-driven state instead.
- The queue itself is shuffled server-side, not by this component - explains why listing order looks mixed rather than neighborhood-clustered when browsing.
- `onCategoryRate` here is wired via `useCategoryRate(() => {})` - a no-op reload - because `ListingCard` always requires the prop even at `detailLevel="minimal"`, where the category panel never actually renders, so there's nothing to reload.
- The `ListingCard` on this page is always rendered with `detailLevel="minimal"`, `swipeDecide`, and `linkExternally` together: minimal to keep the decision fast/uncluttered, `swipeDecide` for the drag/button gesture, `linkExternally` so the title opens the real StreetEasy/Zillow page rather than this app's own (redundant, since you're already deciding) detail page.
- The partner's comment (if any) is shown, but never their swipe decision - preserving blind independent swiping while still letting async notes come through.
- The empty state distinguishes "nothing decided this session yet" ("Nothing new to decide on right now") from "just finished a batch" ("That's everything for now - nice work"), based on whether local `decided` count is > 0, and links out to Matches and Needs Scan.

## Related concepts

- [blind-swipe-model](../concepts/blind-swipe-model.md)
- [the-two-pivots](../concepts/the-two-pivots.md)
