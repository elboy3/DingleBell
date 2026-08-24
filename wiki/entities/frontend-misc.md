---
type: entity
source_files: [frontend/src/pages/NeedsScan.tsx, frontend/src/pages/WhoAmI.tsx, frontend/src/components/NavBar.tsx, frontend/src/components/Stars.tsx, frontend/src/hooks/useCategoryRate.ts, frontend/src/categories.ts]
status: active
verified: 2026-08-24
tags: [frontend, react, page, component, hook, misc]
---

# Frontend misc pages, components, hooks

## Purpose

The smaller supporting pieces that don't warrant their own page: two small pages (`NeedsScan` - listings missing a photo/address that are kept out of the swipe queue; `WhoAmI` - the identity picker), two small shared components (`NavBar`, `Stars`), one shared hook (`useCategoryRate`), and one shared constant list (`categories.ts`) that every category-rating UI depends on.

## Key exports

- `NeedsScan({ user })` (`NeedsScan.tsx`) - route `/needs-scan`, fetches `api.needsScan()` and renders a plain `feed-grid` of default (`detailLevel="summary"`) `ListingCard`s.
- `WhoAmI({ onSet })` (`WhoAmI.tsx`) - route `/whoami`; two buttons ("I'm Elliott" / "I'm Madison") each call `api.setWhoami(user)`, then `onSet(user)` (lifts the choice up to `App.tsx`'s state), then `navigate("/")`.
- `NavBar({ user })` (`NavBar.tsx`) - top nav with links to all five main routes (Swipe/Matches/Passed/Leaderboard/Needs Scan) plus a capitalized "who you are" pill shown only when `user` is set; rendered unconditionally by `App.tsx` (even pre-identity, though its route links are gated by the redirect).
- `Stars({ value, editable, onChange })` (`Stars.tsx`) - five-star selector/readout; renders filled (`★`) vs. empty (`☆`) stars, clickable only when `editable` is true, otherwise `disabled` with a `readonly` class. Used both by `ListingCard`'s category panel (editable) and anywhere a plain rating readout is needed.
- `useCategoryRate(reload)` (`useCategoryRate.ts`) - the sole export; returns an `(id, category, score) => Promise<void>` closure that calls `api.setCategoryRating` then invokes the caller-supplied `reload` callback. Every page that shows a `ListingCard` wires this identically, differing only in what `reload` does (re-fetch that page's own list, or a no-op on Swipe where the panel never shows).
- `CATEGORIES` (`categories.ts`) - the six fixed rating categories: light, kitchen, location, vibe, coziness, space, each `{ key, label }`.

## Depends on / used by

- [frontend-listing-card](../entities/frontend-listing-card.md)
- [frontend-app-shell](../entities/frontend-app-shell.md) (uses `api`, `Listing`)
- [api-routes](../entities/api-routes.md)

## Notes & gotchas

- `categories.ts` is a deliberate hand-maintained mirror of the backend's `webapp/categories.py` - the comment in the source explicitly notes this is a small fixed list, "not worth codegen." Any change to the category list must be made in both places by hand.
- `NeedsScan.tsx` is one of the few pages that renders `ListingCard` with no special props at all (no `swipeDecide`, `linkExternally`, or a non-default `detailLevel`) - it's just a plain review grid, since these listings are explicitly excluded from the swipe queue until a scan backfills their photo/address.
- `WhoAmI`'s identity model is intentionally lightweight - no password, an unsigned cookie set via `api.setWhoami`; per `CLAUDE.md`, a tampered cookie's worst case is a misattributed rating for exactly 2 known users, not a security concern worth hardening.
- `useCategoryRate` is a thin convenience wrapper, not a data-fetching hook (no internal state) - it exists purely to avoid repeating the "save then reload" pattern across every page that embeds a `ListingCard`.
- `Stars`'s "readonly" rendering (used for the overall rating readout elsewhere, via `ListingCard`'s own `RatingReadout`, not `Stars` itself) should not be confused with `Stars`'s own `editable=false` mode - `ListingCard` actually uses a separate inline `RatingReadout` for the two-person overall rating display and only uses `Stars` for the editable per-category panel.

## Related concepts

- [identity-and-data-model](../concepts/identity-and-data-model.md)
- [blind-swipe-model](../concepts/blind-swipe-model.md)
