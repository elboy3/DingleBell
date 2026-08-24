# Wiki index

Every page in this wiki, one line each, grouped by area. See
[README.md](README.md) for how this wiki is structured and how to keep it
updated. See [log.md](log.md) for the history of wiki-authoring operations.

Pages tagged **[deprioritized]** describe systems that still run but are not
the primary/active path - don't build new work against them without reading
[the-two-pivots](concepts/the-two-pivots.md) first.

## Shared data layer

- [ListingStore](entities/store.md) - the single `ListingStore` SQLite class: schema, write/read API, and dedup logic shared by every ingestion path and the webapp.
- [Shared config](entities/shared-config.md) - `config.yaml` + `filters.py`, the shared, non-secret settings/hard-filter seam read by both `apt_agent` and `webapp`.

## Ingestion: email pipeline (Phase 1) - [deprioritized]

- [Email pipeline](entities/email-pipeline.md) **[deprioritized]** - the original Gmail-alert ingestion (poll → extract → filter → notify); still running, superseded by browser-scan and Zillow email import.
- [Notifications](entities/notifications.md) **[deprioritized]** - outbound alert/heartbeat/failure emails for the Phase 1 pipeline.
- [check_setup](entities/check-setup.md) **[deprioritized]** - diagnostic script validating local setup against the Phase 1 deploy checklist.

## Ingestion: browser-scan and Zillow email

- [Zillow email import](entities/zillow-email-import.md) - active, fully-automated Zillow ingestion straight from Zillow's own instant-update alert emails, no browser needed.
- [Browser-scan: StreetEasy](entities/browser-scan-streeteasy.md) - the primary StreetEasy ingestion path, driving the user's real authenticated browser to bypass PerimeterX since no real alert emails exist.
- [Browser-scan: Zillow (backfill)](entities/browser-scan-zillow.md) - backfill-only Zillow browser scan for pre-existing listings; documents the DOM-scraping → `__NEXT_DATA__` technique evolution and the last-photo bug fix.
- [Browser-scan import](entities/browser-import.md) - the shared persistence step both browser-scan skills call to dedup and save results into `listings.db`.
- [GitHub Actions workflows](entities/github-workflows.md) - the two scheduled workflows (`poll.yml`, `heartbeat.yml`) running the automated ingestion/health-check paths.

## Webapp backend

- [App bootstrap and shared deps](entities/webapp-app-and-deps.md) - FastAPI bootstrap, CORS, the shared `ListingStore` singleton, and cookie-based current-user resolution.
- [Feed logic and ranking](entities/feed-logic-and-ranking.md) - match-status derivation, the per-viewer-safe "waiting on a decision" logic, and MIN-based rating combination - where the blind-judgment invariant is enforced.
- [AI scoring fallback and taste profile](entities/scoring.md) - the secondary/fallback Claude-vision scoring path, the manual rescore backfill command, and the taste profile it scores against.
- [API routes](entities/api-routes.md) - every JSON HTTP route the frontend calls (swipe queue, matches, leaderboard, listing detail, passed/off-market/needs-scan, mutations).

## Frontend

- [Frontend app shell](entities/frontend-app-shell.md) - React Router/identity-gate bootstrap, the shared API client, shared types, global CSS, and the shared map-embed helper.
- [Frontend listing card](entities/frontend-listing-card.md) - the one reusable `ListingCard` component rendered on every page in the app.
- [Frontend swipe page](entities/frontend-swipe-page.md) - the home page's personal, blind, one-at-a-time swipe queue.
- [Frontend matches and passed pages](entities/frontend-matches-and-passed.md) - Matches ("Matched"/"Waiting on a decision") and Passed ("Disagreements"/"Passed while swiping"/"Off market") audit pages.
- [Frontend listing detail and leaderboard](entities/frontend-listing-detail-and-leaderboard.md) - the single-listing deep-dive page and the four-tab ranked Leaderboard.
- [Frontend misc](entities/frontend-misc.md) - NeedsScan, WhoAmI, NavBar, Stars, `useCategoryRate`, and the shared category list.

## Concepts

- [The two pivots](concepts/the-two-pivots.md) - why the project moved from email alerts to browser-scanning, then from a shared feed to blind independent swiping.
- [Blind swipe model](concepts/blind-swipe-model.md) - the core swipe/match mechanic and its one non-negotiable invariant: never reveal a partner's opinion before you've decided yourself.
- [AI taste-match scoring](concepts/ai-taste-scoring.md) - the primary (scan-session vision) vs. secondary (API-key fallback) scoring paths and the still-preliminary taste profile.
- [Zillow ingestion evolution](concepts/zillow-ingestion-evolution.md) - the DOM-scraping → `__NEXT_DATA__` story, the confirmed photo-order bug, and three failed experiments to reach 100% coverage.
- [Two ingestion paths](concepts/two-ingestion-paths.md) - why StreetEasy needs a browser while Zillow has both an automated email path and a backfill-only scan.
- [Identity and data model](concepts/identity-and-data-model.md) - the unsigned two-user cookie identity and the shared SQLite schema underneath everything.
- [Dev tooling, verification, and hosting](concepts/dev-tooling-and-hosting.md) - no test suite exists; how verification actually works, plus dev tooling and not-yet-done hosting plans.
