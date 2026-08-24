# CLAUDE.md - Project Context

Read this before making any product or architecture decision on this
repo. If you're a Claude session picking this up fresh, this file plus
`DECISIONS.md`, `ROADMAP.md`, and `STATUS.md` should get you fully
oriented in one pass.

## What this is

Two things, in one repo, at different points in their life:

1. **The shared apartment-review web app (`webapp/`) - current focus.**
   A small FastAPI app, now built as a dating-app-style swipe/match
   flow: Elliott and Madison each swipe left/right on Brooklyn listings
   independently and blind to each other (an AI taste-match score is
   computed automatically to help prioritize); a listing becomes a
   match only when **both** swipe right, moving it into a shared Inbox
   for category ratings and comments; a ranked Leaderboard sits
   downstream of that. See "The second pivot" below for why this isn't
   the original shared-feed design. Fed by an interactive browser-driven
   scan (see "Ingestion" below), not a cron job.
2. **The original Gmail-alert pipeline (`apt_agent/`) - deprioritized,
   still running.** Watches a Gmail inbox for StreetEasy/Zillow/etc.
   alert emails and emails the two users when a hard-filtered match
   appears, on a GitHub Actions cron. Left running as-is in case
   Zillow's alert cadence turns out to be worth revisiting later - not
   actively developed, not removed.

**If you're only going to read one section below to understand why
there are two systems here, read "The pivot" below.**

## Who this is for, and why it matters

Built for two people (Elliott + Madison) apartment-hunting in Brooklyn
on a real deadline - their current lease ends end of September 2026,
and manual searching hadn't surfaced much. This is not a toy project
or a casual side-experiment: **finding the right apartment on this
timeline matters a lot to them.** Treat reliability and correctness
with commensurate seriousness.

## Hard constraints (do not relax without the user confirming)

- Move-in window: **Sep 1 - Oct 3, 2026** (2 wk flex early, 1-2 day flex
  late). Encoded in `config.yaml` -> `search.earliest_move_in` /
  `latest_move_in`. Still used as a hard filter (`apt_agent/filters.py`),
  including for the `would_alert` stat browser_import.py reports.
- Price range, beds/baths minimums: also in `config.yaml`, user-owned,
  don't guess or change these.

## The pivot (read this if anything below seems to contradict itself)

Phase 1 (the email pipeline) was built and deployed first, on the
assumption that speed - being first to see a new listing - was the
main thing worth optimizing. Real-world testing (2026-08-20/22) showed
that assumption was wrong on two counts: StreetEasy doesn't actually
send real-time per-listing alerts (only a few thin "recommendations"
digests a day), and the emails are missing photos and most detail
anyway. Separately, it turned out the user's real authenticated
browser session can load StreetEasy's full search-results page
directly (via the `browser-use` MCP plugin), bypassing the anti-bot
wall that blocks anonymous scraping - a much richer data source than
email ever was.

More importantly, the user's actual stated problem turned out not to
be speed at all: *"not re-evaluating the same apartments over and
over, not holding rankings in our heads, and letting both of us react
to listings async... without always having to text back and forth in
real time."* That's a shared-state/collaboration problem, not a
latency problem - hence the pivot to a persistent shared web app
instead of faster/smarter emails. **Goal ordering below has been
updated accordingly - speed is explicitly no longer a priority.** Full
story: `DECISIONS.md` (search "Pivot from email alerts") and
`.claude/plans/well-i-realized-that-goofy-platypus.md`.

## The second pivot: shared feed -> independent swipe/match

The first webapp build had both people rate/comment/hide from one
shared feed together. Real feedback: *"it's actually going to be like
a dating app... we each do this separately... for each of us we never
see the same listing twice."* So the shared feed, its filters, and a
shared "interested" flag were replaced with true per-user independent
swiping (`apt_agent/store.py`'s `listing_swipes` table) - a listing
only becomes a match (both swiped right) and moves to the shared Inbox
once both have decided. A left swipe is personal and permanent (no
undo), but stays visible in a full-transparency Passed view. The
Leaderboard survived this pivot, now scoped to matches instead of the
old shared flag. Full reasoning: `DECISIONS.md` ("Dating-app swipe
model"). The Open Houses feature (a dedicated page for browsing
upcoming open houses across listings) was removed outright rather than
updated for the new model - a specific listing's open-house info still
shows inline on its own card via `open_house_raw`/`open_house_date`.

## Goal ordering (matters for design decisions) - updated post-pivot

1. **Breadth of discovery** - surface listings they wouldn't have found
   through manual searching. Unchanged from Phase 1.
2. **Shared, persistent, asynchronous review** - both people see the
   same ranked set, can react on their own time, nothing needs to be
   re-evaluated once one person has already looked at it. This
   replaced "alert as fast as possible" as goal #2.
3. Speed/real-time alerting is **explicitly not a goal anymore.** Don't
   optimize for it, don't add urgency-driven complexity (real-time
   push, aggressive polling, etc.) without the user asking for it back.

This is explicitly **not** a leisurely browsing tool either, though -
deadline pressure (end of Sep 2026) still means the web app needs to
actually be usable and hosted somewhere both phones can reach, not a
perpetual work-in-progress.

## Current focus: the shared web app, now the swipe/match model

Status as of 2026-08-24: React SPA + JSON API, browser-scan ingestion
formalized as a project skill, AI scoring working via the scanning
session's own vision (no API key needed), category ratings (light/
kitchen/location/vibe/coziness/space) added as the deeper post-match
review mechanism, and the shared feed replaced by the independent
swipe/match model described in "The second pivot" above. **Not yet
hosted anywhere** (no Turso/Fly.io accounts set up yet), and the taste
profile is in progress (user has started sending liked StreetEasy
links). See `STATUS.md`'s "Shared web app pivot" section for the live
checklist of what's left.

**Phase 2.5 (interactive SMS/texting agent), previously designed in
`ROADMAP.md`/`DECISIONS.md`, is superseded by this pivot** - the user
chose a web app over a texting interface. Its design reasoning is left
in `DECISIONS.md` as historical record (don't build it), not as a
pending plan.

## Architecture summary - shared web app (see DECISIONS.md for full reasoning)

- **React + TypeScript SPA (`frontend/`, Vite) talking to a FastAPI
  JSON API (`webapp/`).** Started as server-rendered Jinja2 ("no JS
  build step needed for 2 users") - reversed after the user actually
  used the app and found full-page reloads on every click felt
  "templated," not slick. `webapp/routes/api_*.py` are pure JSON
  endpoints (CORS-enabled for the frontend origin); the old Jinja
  templates/routes were deleted outright, not left dormant. **Two
  processes now, not one** - `poe api` (FastAPI, port 8000) and
  `poe web` (Vite dev server, pinned to port 5175) - or `poe dev` to
  run both.
- **Frontend and backend must be accessed via the same hostname** -
  both `localhost`, never mix with `127.0.0.1`. A real bug (identity
  cookie silently not sent) came from exactly this: different
  hostnames count as cross-*site* for `SameSite=Lax` cookie purposes
  even though both are loopback. See DECISIONS.md.
- **Pages**: Swipe (home - one-at-a-time personal queue, left/right,
  highest AI match first, no filter UI), Inbox (matches - both swiped
  right - where category ratings/comments happen), ListingDetail
  (Google Maps embed - keyless, no API key - StreetEasy CTA, category
  ratings, comments), Leaderboard (four tabs: shared/elliott/madison/
  ai, scoped to matches, with an "off market" disqualify action),
  Passed (full-transparency audit of every listing either person
  swiped left on, plus disqualified matches with an undo), NeedsScan
  (listings missing a photo/address, kept out of the swipe queue),
  WhoAmI.
- **Testing this app's own UI doesn't need the authenticated
  browser-use session** - only StreetEasy scraping does. Use a plain
  headless Playwright browser (`frontend/`'s own `playwright` dev
  dependency) against `localhost:5175`/`localhost:8000` instead - it's
  independent of the user's real browser and its permission prompts,
  so it works even when the user isn't physically present to click
  anything.
- **Two ingestion paths now - StreetEasy needs a browser, Zillow doesn't.**
  StreetEasy: an authenticated browser scan, not a cron job. The
  `browser-use` MCP plugin drives the user's real, already-logged-in
  Brave/Chrome session to load StreetEasy's saved-search results page
  directly - this bypasses the PerimeterX wall that blocks anonymous
  scraping, because it's a real user's own browser loading a page
  they're entitled to see, not automated evasion. Formalized as
  `.claude/skills/scan-streeteasy/SKILL.md` + `apt_agent/browser_scan/
  extract.js` (DOM extraction, JS) + `apt_agent/browser_scan_helpers.py`
  (field parsing, Python) + `apt_agent/browser_import.py` (persists
  into `listings.db`, dedups, never sends email). This only works
  interactively (drives a live local browser) - run whenever someone
  asks, not on a schedule.

  Zillow: `apt_agent/zillow_email_import.py`, fully unattended, on the
  existing GitHub Actions poll cron. Zillow's `rental-instant-updates@
  mail.zillow.com` sender fires within minutes of a new listing (unlike
  StreetEasy's thin digests) with full structured data in the plain-text
  body (price/beds/baths/address/agent) plus a real photo on
  `photos.zillowstatic.com` - the same public, no-auth CDN the browser
  scan already uses - so this needs no page fetch at all. Each
  listing's Zillow property ID (zpid), decoded from the "View this
  listing" link's click-tracking `target=` param, builds a stable
  canonical URL (`zillow.com/homedetails/{zpid}_zpid/`) without ever
  resolving a redirect. Bundled "Other rentals you might like" entries
  in the same email get imported too (free breadth). AI scoring is left
  NULL here - there's no live session watching a cron run to judge a
  photo itself; run `poe rescore` to backfill via the API-key fallback
  path if you want these scored.
- **Pacing matters even with a real authenticated session.** A tight
  loop of 13 rapid sequential page loads tripped PerimeterX; a single
  organic load didn't. Mitigated with `PAGE_PACING_SECONDS = 20` and
  `MAX_PAGES_PER_SESSION = 5` in `browser_scan_helpers.py` - resuming a
  scan across sessions is safe regardless, since `already_seen()` skips
  anything already imported.
- **One shared `ListingStore` (`apt_agent/store.py`), three consumers**:
  the email pipeline's `main.py`, `browser_import.py`, and `webapp/`.
  Extended (not replaced) with `listing_reactions` (per-user rating +
  comment), `listing_category_ratings` (per-user, per-category 1-5
  score - the overall rating follows their average), `listing_swipes`
  (per-user left/right, permanent, drives `match_status` in
  `webapp/feed_logic.py`), a shared `hidden`/`hidden_by`/`hidden_at`/
  `hidden_reason` flag (now used for exactly one thing - the
  Leaderboard's reversible "off market" disqualify on an already-
  matched listing, not for pre-match rejection), `ai_score`/
  `ai_reasoning`/`ai_profile_version`, and `open_house_raw`/
  `open_house_date`. (`interested`/`interested_by`/`interested_at`
  columns are unused leftovers from a superseded design - see "The
  second pivot" - left in place since SQLite can't cheaply drop
  columns; don't wire anything up to them.)
- **AI taste-match scoring: the scanning session scores it directly,
  no API key required.** The Claude Code session doing the interactive
  browser scan already has vision and is already looking at the
  results page - it judges each new listing's photo (via a page
  screenshot) against `taste_profile.md` and sets `ai_score`/
  `ai_reasoning` directly in the JSON handed to `browser_import.py`
  (see `.claude/skills/scan-streeteasy/SKILL.md` step 7). No Anthropic
  API call needed for this, the primary path. `webapp/scoring.py`
  (Claude-vision-via-API-key) is kept only as a **secondary, optional
  fallback** for listings that arrive without a pre-computed score -
  every failure mode there (no photo, fetch failure, API error, bad
  response) returns `(None, None)` and never blocks ingestion, matching
  `filters.py`'s "unknown field, don't block on it" pattern.
  `webapp/rescore.py` is a manual backfill command using that fallback
  path, for un-scored or stale-profile listings.
- **Filtering out and ranking down are two different, deliberately
  separate mechanisms.** A personal swipe-left (permanent, no undo,
  independent per person - see "The second pivot") is how a listing
  leaves consideration *before* a match. Once matched, ranking uses
  min-of-both-ratings (deliberately MIN not average, so one person's
  dislike isn't smoothed over) or AI score - a live, non-destructive
  sort, never a hide. The only *shared*, reversible removal is the
  Leaderboard's "off market" disqualify, for a match that's no longer
  real-world available.
- **Lightweight identity, no passwords.** `/whoami` sets an unsigned
  cookie for "elliott" or "madison" - a tampered cookie's worst case is
  a misattributed rating, not a security problem, for exactly 2 known
  users.
- **Planned hosting (not done yet): Fly.io + Turso (libSQL).** Turso's
  Python client is designed as a near-drop-in for `sqlite3`, so
  `store.py`'s connection logic would change in one place, in remote
  mode (no embedded-replica sync complexity needed at this traffic
  level). See the plan doc for the concrete setup steps.

## Architecture summary - email pipeline (deprioritized, left running)

- **Ingestion via Gmail alert emails**, not direct scraping. Avoids
  anti-bot/ToS problems for this specific pipeline (the browser-scan
  approach above is a different, deliberate exception - see its
  reasoning in `DECISIONS.md`, it's not a contradiction).
- **Deployed on GitHub Actions, public repo, variable-frequency cron**
  (`.github/workflows/poll.yml`, `heartbeat.yml`) - unchanged since
  Phase 1, still running.
- **Gmail query deliberately avoids `in:inbox`/`is:unread`** - this
  account has a pre-existing filter that auto-archives StreetEasy mail
  (missing it entirely under `in:inbox`), and `is:unread` is fragile
  against a human opening an alert email. Relies on `newer_than:1d` +
  `ListingStore.already_seen()` instead. See `config.yaml`'s inline
  comment and `DECISIONS.md`.
- **Listing detail comes from the email snippet, not a page fetch** -
  StreetEasy/Zillow 403 on direct page fetches. `extract_from_email_snippet()`
  in `listing_parser.py`.
- **Daily heartbeat + dry-run mode** unchanged from Phase 1.

## File map

### Shared web app (current focus)
| File | Purpose |
|---|---|
| `webapp/app.py` | FastAPI app instance, CORS, mounts all API routers |
| `webapp/deps.py` | `get_store()`, `get_current_user()` - `KNOWN_USERS` itself lives in `ranking.py`, re-exported here |
| `webapp/config.py` | Thin wrapper around `apt_agent.main.load_config()` |
| `webapp/ranking.py` | `KNOWN_USERS`, `compute_rating_summary()` - shared min-of-both-ratings logic |
| `webapp/feed_logic.py` | `enrich()`, `match_status()`, `swipe_queue_for_user()`, `filter_listings()`/`sort_listings()` (Leaderboard only) |
| `webapp/categories.py` | The six rating categories (light/kitchen/location/vibe/coziness/space) |
| `webapp/scoring.py` | Claude vision taste-match scoring, graceful degradation (secondary/fallback path) |
| `webapp/rescore.py` | `python -m webapp.rescore` - manual backfill for stale/missing AI scores |
| `webapp/routes/api_listings.py` | `/swipe-queue`, `/inbox`, `/passed`, `/off-market`, `/needs-scan`, `/listings` (Leaderboard only), `/listings/{id}`, and the comment/hidden/swipe/category-rating actions |
| `webapp/routes/api_identity.py` | `GET`/`POST /api/whoami` - cookie-based identity |
| `frontend/src/App.tsx` | React Router setup, identity gate |
| `frontend/src/api.ts` | Fetch client - **must point at `localhost:8000`, not `127.0.0.1:8000`** (cookie hostname match) |
| `frontend/src/pages/*.tsx` | Swipe (home), Inbox, ListingDetail, Leaderboard, Passed, NeedsScan, WhoAmI |
| `frontend/src/components/*.tsx` | `ListingCard` (detailLevel/swipeDecide/linkExternally/onDisqualify props), `Stars`, `NavBar` |
| `frontend/src/hooks/useCategoryRate.ts` | Shared category-rating-then-reload handler, used by every list/detail page |
| `frontend/src/categories.ts` | Mirrors `webapp/categories.py`'s category list (kept in sync by hand) |
| `frontend/vite.config.ts` | Dev server pinned to port 5175 (not the 5173 default - avoids colliding with other local projects) |
| `apt_agent/browser_scan/extract.js` | DOM-extraction script, run via `browser-use`'s `js()` |
| `apt_agent/browser_scan_helpers.py` | Field parsing, batch dedup, pacing/page-cap constants |
| `apt_agent/browser_import.py` | Persists a scan's output into `listings.db`, wires in AI scoring |
| `.claude/skills/scan-streeteasy/SKILL.md` | The actual session procedure for running a scan |
| `taste_profile.md` | Exists, **preliminary draft** - 3 liked examples, no disliked ones yet |

### Email pipeline (deprioritized, still running)
| File | Purpose |
|---|---|
| `apt_agent/gmail_auth.py` | One-time OAuth setup, produces `token.json` |
| `apt_agent/gmail_ingest.py` | Polls Gmail, extracts listing URLs + snippets from alert emails |
| `apt_agent/listing_parser.py` | Email-snippet field extraction (page-fetch path unused, kept for reference) |
| `apt_agent/main.py` | Orchestrates a normal run or a `--dry-run` test |
| `apt_agent/notify.py` | Builds and sends alert/heartbeat/test emails via Gmail API |
| `apt_agent/notify_failure.py` | Sends a "run failed" email, wired to `if: failure()` in the workflow |
| `apt_agent/heartbeat.py` | Daily "agent is alive" summary email |
| `apt_agent/check_setup.py` | `python -m apt_agent.check_setup` - verifies real local setup state |
| `.github/workflows/poll.yml`, `heartbeat.yml` | Scheduled workflows |

### Shared
| File | Purpose |
|---|---|
| `apt_agent/store.py` | The one `ListingStore` - schema, dedup, reactions, hide, AI score, all three consumers |
| `apt_agent/filters.py` | Hard filters: price, beds/baths, move-in window |
| `config.yaml` | User-owned filters/settings (non-secret) + `scoring:` section |
| `listings.db` | Committed to the repo (still true post-pivot for the email side; the webapp will move to Turso once hosted) |
| `pyproject.toml` | `[tool.ruff]`, `[tool.poe.tasks]` - see "Dev tooling" below |
| `requirements.txt` | Runtime deps (what GitHub Actions and the planned Dockerfile install) |
| `requirements-dev.txt` | `ruff`, `ty`, `poethepoet` - not installed by CI |

## Dev tooling

- **`ruff`** for formatting + linting (`pyproject.toml`'s `[tool.ruff]`,
  a simple ruleset: `E`/`F`/`I`/`UP`/`B`). **`ty`** (Astral's type
  checker, mypy-equivalent) for type checking - no special config
  needed. **`poethepoet`** (`poe`) as the task runner, tasks in
  `pyproject.toml`'s `[tool.poe.tasks]`:
  - `poe install` - `uv pip install -r requirements.txt -r requirements-dev.txt`
  - `poe fmt` / `poe fmt-check` - rewrite / verify-only
  - `poe lint` / `poe lint-fix`
  - `poe typecheck`
  - `poe check` - the full verify-only sequence (fmt-check + lint + typecheck), CI/pre-commit style
  - `poe api` - `uvicorn webapp.app:app --reload --port 8000`
  - `poe web` - `npm --prefix frontend run dev` (Vite, port 5175)
  - `poe dev` - both together
  - `poe rescore` - `python -m webapp.rescore`
- **`uv` for local env/installs** (light adoption - `requirements.txt`/
  `requirements-dev.txt` stay the source of truth, GitHub Actions and
  the planned Dockerfile stay on plain `pip`, not touched). `uv` works
  against the existing `.venv` without needing to recreate it.
- **Frontend**: plain `npm`/`npx` in `frontend/` - `npx tsc --noEmit`
  for type-checking, no separate lint step configured yet.
- Run `poe check` (backend) before considering any Python change done;
  `npx tsc --noEmit` (in `frontend/`) before considering any TS change
  done.

## Known limitations / open items

**Shared web app:**
- The optional `webapp/scoring.py` API-key fallback path has never been
  run against the real Claude API (no `ANTHROPIC_API_KEY` was available
  while building it) - its graceful-degradation path is proven, the
  real API call isn't. Doesn't block anything: the primary scoring
  path (the scanning session itself) doesn't depend on it.
- `taste_profile.md` exists but is a **preliminary draft, liked
  examples only** (3 favorites, no disliked examples yet) - scores from
  it are rough signal, not confident judgment. Ask for disliked
  examples to sharpen it.
- Not hosted anywhere yet - no Turso or Fly.io accounts set up.
- Zillow's real alert-email/page links are wrapped in click-tracking
  redirects the current extraction won't resolve - not fixed since
  there's no real Zillow saved-search sample to match against yet.

**Email pipeline (lower priority, but still true):**
- Address normalization for cross-source dedup is best-effort regex.
- `listing_parser.py` field extraction is regex-based, will miss
  fields on layout changes.
- No delisting detection, no weekly digest (deferred, `ROADMAP.md`
  Phase 3 - may end up as webapp features instead if picked back up).

## Working style notes for future sessions

- The user is technical (Python, Git, cron, OAuth, GitHub Actions,
  and now FastAPI/uv/ruff/ty) - no need to over-explain basic tooling,
  but do explain non-obvious infra tradeoffs.
- Prioritize things that build *confidence the system works* (tested
  end-to-end, not just "should work") over feature breadth, given how
  much this matters to the user and how tight the timeline is.
- **Real-world testing surfaced multiple genuine bugs this project,
  repeatedly** (OAuth scope, unbounded Gmail query, page-fetch 403s,
  invented version pins in `requirements.txt`, an ambiguous type
  signature `ty` caught) - test end-to-end against real data/APIs
  before declaring something done, don't assume it works from reading
  the code.
- Don't add scope beyond what's asked or explicitly agreed in a
  planning conversation - the shared-web-app pivot itself is the
  precedent for how scope changes should happen: driven by the user's
  own stated problem, discussed and confirmed before building, not
  assumed.
