---
type: entity
source_files: [frontend/src/App.tsx, frontend/src/main.tsx, frontend/src/api.ts, frontend/src/types.ts, frontend/src/index.css, frontend/src/mapEmbed.ts]
status: active
verified: 2026-08-24
tags: [frontend, react, routing, api-client, css]
---

# Frontend app shell

## Purpose

The scaffolding every page and component sits inside: React Router setup and the identity gate (`App.tsx`), the app's entry point (`main.tsx`), the single fetch client every page uses to talk to the FastAPI backend (`api.ts`), the shared TypeScript shape of a listing (`types.ts`), the global Airbnb-inspired stylesheet (`index.css`), and one small shared geo-URL helper (`mapEmbed.ts`) used by both `Swipe.tsx` and `ListingDetail.tsx`.

## Key exports

- `App` (`App.tsx`, default export) - loads identity via `api.whoami()` on mount (`user` state starts `undefined` while loading, `null` if unset), renders `NavBar`, and wraps `react-router-dom`'s `BrowserRouter`/`Routes`. If no user is set, every route redirects to `/whoami`; otherwise it wires up `/` (Swipe), `/matches`, `/listings/:id`, `/passed`, `/leaderboard`, `/needs-scan`.
- `main.tsx` - `createRoot(...).render(<StrictMode><App /></StrictMode>)`, standard Vite entry, imports `index.css` globally.
- `api` object (`api.ts`) - one method per backend endpoint: `whoami`/`setWhoami`, `listings(params)` (Leaderboard only, supports `sort`/`only_matched` query params), `listing(id)`, `setComment`, `setHidden` (used for off-market disqualify/undo), `swipe`, `setCategoryRating`, `needsScan`, `swipeQueue`, `matches`, `passed`, `offMarket`.
- `request<T>(path, options)` (internal, not exported) - shared fetch wrapper: always sets `credentials: "include"` and `Content-Type: application/json`, throws on non-2xx.
- `API_BASE` (internal constant) - hardcoded to `http://localhost:8000/api`.
- `Listing` interface (`types.ts`) - the canonical listing shape shared across every page/component: includes `swipes: Record<string,string>`, `match_status: "pending"|"match"|"miss"`, `mismatch: boolean`, `waiting_on?: string|null`, `reactions`, `ratings`, `both_rating`, `label`, `rank?`, `needs_backfill`, `category_ratings`.
- `Reaction` interface (`types.ts`) - `{ rating, comment, updated_at }` per-user reaction shape.
- `mapEmbedUrl(address, neighborhood)` (`mapEmbed.ts`) - builds a keyless Google Maps embed URL (`z=15`, appends `" Brooklyn, NY"`), shared so the zoom/query logic is tuned in exactly one place.
- `index.css` - global design tokens (`--accent: #ff385c`, `--radius: 20px`, etc.) plus every class used by pages/components: `.feed-grid`, `.listing-card`, `.detail-layout`, `.swipe-tags`/`.swipe-tag.pending`, `.passed-row-list`/`.passed-row`, `.tab-row`, `.category-panel`, `.whoami-page`, responsive breakpoints at 720px and 480px.

## Depends on / used by

- [api-routes](../entities/api-routes.md)
- [frontend-listing-card](../entities/frontend-listing-card.md)
- [frontend-swipe-page](../entities/frontend-swipe-page.md)
- [frontend-matches-and-passed](../entities/frontend-matches-and-passed.md)
- [frontend-listing-detail-and-leaderboard](../entities/frontend-listing-detail-and-leaderboard.md)
- [frontend-misc](../entities/frontend-misc.md)

## Notes & gotchas

- `API_BASE` is hardcoded to `http://localhost:8000` (not `127.0.0.1`) - the frontend must also be loaded via `localhost` (not `127.0.0.1`), because the identity cookie is `SameSite=Lax` and the two loopback hostnames count as cross-*site* for cookie purposes even though they resolve to the same machine. This was a real bug (see `CLAUDE.md`).
- The identity gate in `App.tsx` uses three states for `user` (`undefined`/loading, `null`/unset, `string`/known) - `undefined` renders a loading paragraph and must not be conflated with `null`, or the app would flash the whoami redirect on every load.
- `mapEmbedUrl` is easy to overlook - it's a tiny 8-line file with no page of its own, but it's genuinely shared infrastructure (both `Swipe.tsx` and `ListingDetail.tsx` import it) rather than page-specific logic.
- `index.css`'s header comment documents the whole visual language as a deliberate Airbnb-style mimicry (coral accent, warm neutral grays, photo-forward cards, info below the photo not overlaid, heart-icon-style actions) - a specific user request, not an arbitrary choice.
- `types.ts`'s `Listing.rank` is optional (`rank?`) because it's only populated by the Leaderboard's sorted response, not every endpoint.

## Related concepts

- [identity-and-data-model](../concepts/identity-and-data-model.md)
- [dev-tooling-and-hosting](../concepts/dev-tooling-and-hosting.md)
