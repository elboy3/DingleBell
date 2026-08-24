# DECISIONS.md - Decision Log

Append-only. Each entry: what was decided, and why, so future sessions
don't relitigate settled tradeoffs. If a decision needs to change,
add a new entry noting the change and why - don't edit history.

---

### Ingest via Gmail alerts, not direct scraping
StreetEasy/Zillow/etc. actively fight scrapers (rotating markup, IP
bans, ToS issues). Letting their own saved-search email alerts do
discovery, then reading those emails via Gmail API, avoids the fight
entirely and is far more robust than maintaining scrapers against
sites that change layout without notice.

### Cast a wider net than the user's manual search
The user's manual searching wasn't surfacing much. Rather than mirror
their exact filters, the agent's saved-search alerts and hard filters
are intentionally looser (wider price band, +1 neighborhood ring) -
breadth of discovery was explicitly prioritized over precision.

### Public GitHub repo for deployment, not private
Private repos get 2,000 free Actions minutes/month; at the polling
frequency needed here that's burned through fast (rough math: even a
flat 5-min interval for 6 weeks is ~20,000 runs/month). Public repos
get unlimited free minutes. The repo's code has no sensitive content -
all real secrets (OAuth creds, recipient emails) live in encrypted
GitHub Secrets, never in tracked files - so public costs nothing in
practice and solves the minutes problem completely.

### Variable-frequency polling schedule, not flat interval
Considered flat 5-min polling first, but reasoned that (a) most new
listings post during broker business hours with an evening bump, not
overnight, and (b) the real bottleneck is usually each *listing site's*
own alert-email cadence (instant vs. daily digest), not our polling
interval. Landed on: every 15 min 7am-11pm ET, every 30 min overnight.
Cuts total runs roughly 3x vs. flat 5-min with no meaningful loss of
speed in practice.

### listings.db is committed back to the repo, not gitignored
GitHub Actions runners are ephemeral - nothing persists between runs
unless explicitly saved somewhere. Without committing the SQLite file
back after each run, dedup state would reset every single run, and
the same listings would get re-alerted repeatedly. Considered
alternatives (actions/cache, external DB) but a direct git commit is
simplest and sufficient at this scale (single low-frequency writer,
small file, low conflict risk).

### Dedup by both URL and normalized address
Started with URL-only dedup, but the same physical unit routinely gets
cross-posted on StreetEasy, Zillow, and RentHop with different URLs -
URL-only dedup would trigger duplicate alerts for the same apartment.
Added a best-effort address-normalization layer (lowercase, strip
noise words/punctuation) as a second dedup check before sending an
alert. Not perfect (doesn't unify "St" vs "Street" etc.) but catches
the common case.

### Daily heartbeat added deliberately, weekly digest deferred
Given how much this matters to the user, silence needed to stop being
ambiguous between "nothing new" and "something's broken." A daily
heartbeat email (stats: listings seen / alerts sent in the last 24h)
solves that cheaply. A weekly "close calls" digest (near-miss filtered
listings) was considered but deferred - it adds value but not
confidence-that-it-works, which was the priority at the time.

### Dry-run mode added before waiting on Phase 1 confirmation
The user explicitly wanted to confirm Phase 1 works before moving to
Phase 2. A `--dry-run` flag that pushes one fake listing through the
full pipeline (skipping Gmail entirely) lets that confirmation happen
immediately rather than waiting for a real alert email to arrive
naturally.

### Phase 2 (taste scoring) deliberately not started
User's instruction: stick with Phase 1 until it's confirmed working.
Don't build Phase 2 features (Claude vision scoring against reference
photos) preemptively, even if it seems like a natural next step -
check with the user first.

### Interactive texting agent scoped as "Phase 2.5," designed but deferred
User asked about a texting-based agent they could query conversationally
("anything in Boerum Hill that looks like the Fort Greene one?") instead
of (or alongside) one-way email alerts. This is a genuine scope increase,
not a small add-on - flagged explicitly rather than quietly folded into
Phase 1 or 2:

- **It can't run on the existing GitHub Actions cron infrastructure.**
  Cron is a scheduled batch job; an interactive agent has to listen for
  and respond to incoming texts in near-real-time, which needs an
  always-on or on-demand server (webhook endpoint), a different
  deployment model entirely.
- **It absorbs Phase 2's hard problem rather than sitting alongside it.**
  The interesting part of "like the Fort Greene one" isn't the SMS
  transport, it's the visual/style similarity comparison - which is
  exactly what Phase 2's taste-profile work already exists to solve.
  Sequencing this after Phase 2 means building a conversational UI on
  top of working intelligence, rather than building both at once.

Given that, this was deliberately scoped down to a "simple v1" rather
than a full build, with these specific simplifications and why:

- **Serverless webhook, not an always-on VPS.** Twilio only calls the
  endpoint when a text actually arrives - a few times a day at this
  usage level - so paying for an idle always-on box doesn't fit. A
  serverless function (Lambda/Fly.io/Render) that spins up per-request
  is the better cost/complexity fit.
- **No vector DB or embeddings pipeline for similarity search.** At the
  realistic volume here (dozens to low hundreds of listings over 6
  weeks), building a real embeddings/similarity-index pipeline is
  disproportionate. Handing Claude the target listing's description
  plus a handful of candidate descriptions directly, and asking it to
  compare in one call, is simpler to build and likely at least as
  accurate at this scale.
- **One shared conversation thread, not per-person sessions.** Both
  users text the same number about the same shared search - a single
  running conversation history is sufficient and avoids the complexity
  of multi-user session management for no real benefit here.
- **One Claude call per incoming text, not a classifier pipeline.**
  Rather than a separate intent-classification step before routing to
  a handler, a single call (given conversation history + recent
  listings as context) both decides what the message needs and drafts
  the reply. Fewer moving parts, one point of failure instead of two.
- **Descriptions generated for every listing seen, not just alerted
  ones.** This is the one non-negotiable piece: similarity queries
  can't work retroactively, so the per-listing Claude-vision
  description has to be generated at ingestion time for the full set
  of listings the pipeline sees - not added later once someone asks
  about a listing that was never described.

Status: designed, not built. Depends on Phase 2's taste-profile
foundation existing first.

### Switched from page-fetch to email-snippet parsing on day one of deploy
`listing_parser.fetch_listing_page()` hit real 403s from both StreetEasy
and Zillow immediately during initial deploy testing (2026-08-19), not
"eventually" as the original caveat anticipated. Worse than a missed
listing: `main.py` was silently dropping every URL that failed to fetch
before it ever reached `store.save()`, so the daily heartbeat's "seen"
count would read 0 too - indistinguishable from "no new listings
posted," a real silent-failure risk.

Fixed by switching `run_once()` to `extract_from_email_snippet()`
(already written, previously unused) instead of fetching the listing
page at all. `gmail_ingest.py` now extracts a per-listing text snippet
alongside each URL (climbing from the `<a>` tag to a parent element
with enough text, since a single alert email holds many listings and a
global regex over the whole email would bleed one listing's price into
another's). Address extraction still returns `None` from the snippet
path (deliberately not guessed at without real sample HTML - a wrong
guess causing a false-positive address-dedup collision is worse than
no address). Net effect: weaker cross-source dedup on listings with no
extractable address, stronger overall reliability - acceptable given
goal #1 (breadth of discovery) outweighs a possible duplicate alert.

### Pivot from email alerts to a shared web app, deprioritizing speed
Real-world testing (2026-08-20/22) showed StreetEasy doesn't actually
send real-time per-listing alerts - only a few thin "recommendations"
digests a day, missing photos and full detail. The user's actual
problem turned out not to be speed at all: it's not re-evaluating the
same apartments repeatedly, not holding rankings in their heads, and
letting two people react asynchronously with a persisted, shared
result. Pivoted to a small web app (`webapp/`) on top of the existing
`apt_agent/store.py` persistence layer: shared feed, per-user 1-5
star ratings + comments, a shared (not per-user) hide/unhide flag, an
AI taste-match score computed automatically at ingest time, and a
deterministic open-house view - no in-app LLM/chat interface, since
that was explicitly declined for now. The existing Gmail/cron pipeline
is left running as-is, deprioritized rather than removed, in case
Zillow's alert cadence turns out to be genuinely better later. Full
design: `.claude/plans/well-i-realized-that-goofy-platypus.md`.

### Browser-authenticated scan replaces anonymous scraping for full census
Using the `browser-use` MCP plugin to drive the user's real, already
logged-in Brave/Chrome session, StreetEasy's saved-search RESULTS page
loads successfully - the PerimeterX wall that blocks anonymous
scraping doesn't trigger against a genuine authenticated session. This
gives real structured data (address, neighborhood, price, beds/baths,
sqft, a real CDN-hosted photo, open-house timing) with far more detail
than any alert email ever had, without violating the original
scraping-avoidance reasoning above - this isn't defeating a bot
defense, it's a real user's own browser loading a page they're
entitled to see.

Real constraint found while building this: a tight loop of 13 rapid
sequential page-to-page navigations tripped PerimeterX on page 2, even
with the authenticated session - a single organic page load did not.
Mitigated with a deliberate pace between navigations
(`PAGE_PACING_SECONDS = 20`) and a per-session page cap
(`MAX_PAGES_PER_SESSION = 5`) in `apt_agent/browser_scan_helpers.py` -
resuming a scan across multiple sessions is safe regardless, since
`ListingStore.already_seen()` skips anything already imported.

This only works interactively (it drives a live local browser), so it
can't run on the old GitHub Actions cron - formalized instead as a
project skill (`.claude/skills/scan-streeteasy/SKILL.md`) run whenever
someone asks, which is the correct cadence now that speed isn't the
goal.

### Added ruff/ty/poethepoet, light uv adoption
User asked for formatting/linting and Astral's type checker (`ty`,
their newer mypy equivalent) on top of the growing `webapp/` codebase.
Added `ruff` (format + a simple `E`/`F`/`I`/`UP`/`B` lint ruleset) and
`ty` (no special config needed), both configured in a new
`pyproject.toml`. Added `poethepoet` as the task runner rather than a
plain `Makefile` - tasks live in `pyproject.toml` (already exists for
ruff/ty config) rather than a separate file, and it's genuinely
Python-native rather than a general-purpose tool bolted on.

Every `ruff check` finding was fixed by hand, not suppressed - 2
genuinely unused imports/variables, ambiguous single-letter `l` loop
variables renamed to `listing` across the webapp routes, two overlong
lines wrapped/split. `ty` caught one real type mismatch:
`ListingStore.set_ai_score` declared `reasoning: str` but
`score_listing()` can return `str | None` - loosened the signature to
match, since `ai_reasoning` is a nullable column anyway.

Separately adopted `uv` for local env/installs (light adoption only -
`requirements.txt`/`requirements-dev.txt` stay the source of truth,
GitHub Actions and the planned Fly.io Dockerfile stay on plain `pip`,
not touched). `uv`'s stricter dependency resolver immediately caught a
real bug: `requirements.txt` had invented, never-verified version pins
for `anthropic`/`fastapi`/`uvicorn`/`jinja2`/`python-multipart` (e.g.
`anthropic==0.40.0` when `1.0.0` - a major version - was what was
actually installed and tested against). Re-pinned to match reality.

### AI scoring: the interactive session scores directly, no API key required
Original design called the Anthropic API (via `ANTHROPIC_API_KEY`) from
inside `browser_import.py` to score each listing. User pointed out the
obvious thing this missed: a Claude Code session doing the interactive
browser scan already has vision and is already looking at the results
page - there's no need for a *separate* API-key-based call to have
Claude judge a photo it's already looking at.

Restructured `import_listings()` to prefer a pre-computed `ai_score`/
`ai_reasoning` on each raw listing dict (set by the scanning session
itself, per `.claude/skills/scan-streeteasy/SKILL.md`'s step 7 - score
against `taste_profile.md` using a page screenshot, no API call). The
`ANTHROPIC_API_KEY` + `webapp/scoring.py` path is kept as a secondary
fallback only, for listings that don't already carry a score - not
required, not the primary path. This removes an entire external
credential from the critical path for something that only ever needed
to happen during an already-interactive Claude session anyway.

### Photo galleries: extract image URLs directly, don't fight the lightbox UI
While building `taste_profile.md` from real StreetEasy listing pages,
clicking through the photo lightbox (next-arrow, thumbnails) via
`click_at_xy()` never advanced the photo - tried correcting for
viewport/screenshot coordinate scaling, activating the tab, keyboard
arrow-key events, none worked. Root cause unclear (screenshot-based
click dispatch may not reliably trigger the lightbox's own event
handlers).

Rather than keep debugging UI interaction, extracted photo URLs
directly from the DOM (`document.querySelectorAll('img')`, filtered to
`zillowstatic` CDN URLs, deduped) and downloaded each with `curl` into
the scratchpad, then viewed them with the `Read` tool - `.webp` works
directly, no conversion needed. More reliable than UI navigation
anyway: one pass gets every photo already loaded into the DOM, not
just whichever one the lightbox happens to be showing. Photos don't
all render in the DOM until the page settles or you scroll - if fewer
URLs come back than the page's own "X of N" count, scroll through the
page first and re-run the extraction.

Same underlying technique the scan-streeteasy skill's scoring step
already uses (screenshotting a page rather than clicking into
anything) - reuse this directly if a future session needs a specific
listing's full photo set, not just its search-results thumbnail.

### Rebuilt webapp/ as a React SPA + JSON API, replacing server-rendered Jinja
User's own real usage surfaced the actual problem: full-page reloads on
every star click/hide felt "templated," not the slick, instant-feedback
interaction a real app should have - plus a genuine bug (`min_score=""`
crashed the Jinja route with a raw FastAPI validation error rendered as
JSON in the page). This reverses the original "Jinja2, no build step"
decision - a real tradeoff, not free: now two processes (Vite dev
server + FastAPI) instead of one, a build step, a JSON API layer where
there wasn't one. Worth it for what was actually being asked for.

`webapp/` is now a pure JSON API (routes/api_*.py) with CORS enabled
for the frontend origin; `frontend/` is a Vite + React + TypeScript app
consuming it. Old Jinja templates/static/routes deleted outright, not
left dormant - two competing UIs in one repo would confuse the next
session more than the diff of deleting them helps anyone.

**Real bug found integrating the two**: the identity cookie silently
never got sent on API calls even though the POST that set it succeeded
(200 `{"ok": true}`). Root cause: frontend served from `localhost:5175`,
backend from `127.0.0.1:8000` - different hostnames count as
cross-*site* for cookie purposes even though both are loopback, and
`SameSite=Lax` (the correct setting here, not a bug) only sends cookies
on top-level navigation across sites, not on background `fetch()`
calls. Fixed by pointing the frontend's API client at `localhost:8000`
instead of `127.0.0.1:8000` - same hostname, different port, which *is*
same-site. Caught via a headless Playwright script hitting the API
directly and inspecting the actual `Set-Cookie`/cookie-jar behavior,
not by guessing.

**Testing note**: browser-use (the authenticated-scan tool) needs a
literal click on a Chrome permission popup, which blocks unattended
testing when the user isn't physically present. The app's own UI
doesn't need that authenticated session at all, though - it only talks
to the local FastAPI API - so a plain headless Playwright browser
(`npm install -D playwright`, its own independent Chromium, zero
relation to the user's real browser or its permissions) is the right
tool for testing this app's own UI. Don't reach for browser-use to test
things that don't need StreetEasy's authenticated session.

### Airbnb-inspired visual redesign
The React rewrite's first pass used generic/templated-looking styling
("still looks very jinja"). Rather than invent a look from scratch, we
picked a well-known app with a design language that fits the domain
(browsing photo-forward real-estate listings) and deliberately mimicked
its patterns: coral accent (`#ff385c`), warm neutral grays, large
rounded corners, Nunito font, square photo-forward cards with info
living in the card body instead of as photo overlays, a heart icon for
favorite/hide instead of a text button, and a responsive CSS grid
instead of a single stacked column. This was a user-directed choice
(picked Airbnb from a short list of options) rather than an invented
style, on the reasoning that copying a proven, well-tested design
system beats guessing at "good design" from first principles.

Implementation note: the address/URL fallback text in listing cards
needs `overflow-wrap: anywhere` - long unbroken strings (URLs, in
listings scanned before `address` parsing succeeded) will otherwise
overflow the card's fixed width instead of wrapping, since flex items
don't wrap unbreakable text by default. Found via an actual Playwright
screenshot of the rendered feed, not by reading the CSS.

### Dating-app swipe model: independent per-person swiping, matches gate review
The single shared feed (rate/comment/hide together) got reworked twice
in one session. First pass: a shared "interested" flag and one shared
swipe queue both people triage together. User feedback: that's not
actually what was wanted - "it's actually going to be like a dating
app... we each do this separately... for each of us we never see the
same listing twice." The real model: Elliott and Madison each get their
own private swipe queue and decide left/right independently, blind to
what the other does. A listing only becomes a match - and moves to a
shared Inbox for category-rating/comment review - when **both** swipe
right. A miss (either swipes left) is gone from *that person's* queue
forever, no undo, but stays visible in a full-transparency Passed view
(tagged per-person: liked/passed/hasn't swiped yet) so nothing silently
disappears.

Implementation: a new `listing_swipes` table (`listing_id, user,
direction, swiped_at`, unique per listing+user) replaces the earlier
shared `interested` boolean - `match_status()` in `webapp/feed_logic.py`
derives pending/match/miss from the two recorded swipes, computed at
request time, not stored. The `interested`/`interested_by`/
`interested_at` columns from the superseded first pass were left in
the schema unused rather than dropped - SQLite can't cheaply drop
columns, and three unused nullable columns cost nothing. The existing
shared `hidden`/`hidden_reason` flag was *not* replaced - it's kept for
exactly one purpose now, the Leaderboard's reversible "off market"
disqualify action on an already-matched listing, which is a genuinely
different, shared, reversible decision from a personal, permanent
pre-match swipe.

The Leaderboard survives downstream of the Inbox (ranked matches,
Elliott/Madison/AI/Shared tabs), confirmed explicitly rather than
assumed, since it would have been easy to guess the Inbox replaced it.

### Cleanup pass: 3 parallel review agents (bugs / dead code / refactors)
After the swipe/match rework, ran three parallel agents against the
whole repo - one hunting real bugs, one hunting unused code/bad naming,
one hunting worthwhile refactors - each told to verify findings (grep
for actual callers, trace code paths) rather than speculate, and to
weigh refactor suggestions against this file's own "don't over-abstract"
philosophy rather than default to more abstraction. Real findings fixed:

- **Bug**: the category-rating average used Python's round-half-to-even
  (`round(2.5) == 2`), silently understating a rating that drives
  Leaderboard sort order. Fixed to round half up.
- **Bug**: `/api/open-houses` was never updated for the swipe/match
  model - a permanently-swiped-left listing could still show up there.
  Rather than patch it, removed the Open Houses feature outright
  (route, page, nav link, `FAVORITE_THRESHOLD`) - it was a dedicated
  cross-listing browsing page nobody asked to keep; a listing's own
  open-house info still shows inline on its card via `open_house_raw`.
- **Dead code**: `ListingStore.swiped_listing_ids_for_user` (never
  wired in), the entire filter/sort surface in `feed_logic.py`/
  `api_listings.py` left over from the deleted grid-browse Feed page
  (`neighborhood`/`price_min`/`price_max`/`available_before`/
  `needs_review`/`min_score`, `_available_on_or_before`, the plain
  `"ai"`/`"ours"` sort branch), the `/listings/{id}/rating` POST route
  and its frontend client method (superseded by category-rating's
  averaging), and several CSS classes (`.comment-preview`,
  `.filters-toggle`/`.more-filters`, `.empty a`, and `.controls` once
  Open Houses' filter checkbox - its last user - was removed too).
- **Landmine**: `KNOWN_USERS` was independently defined in both
  `webapp/deps.py` and `webapp/ranking.py` with the same name/value -
  a third user added to one and not the other would've silently broken
  things. Consolidated to `ranking.py`, re-exported from `deps.py`.
- **Refactor**: extracted `frontend/src/hooks/useCategoryRate.ts` - the
  save-then-reload handler was copy-pasted verbatim across 6 page
  files. Added a small `_enriched_listings()` helper in
  `api_listings.py` for the same reason on the backend side.
- **Docs**: `CLAUDE.md` had drifted significantly out of date (still
  described the deleted Feed/Hidden pages and `/api/hidden`/
  `/api/neighborhoods` endpoints, didn't mention the swipe/match model
  at all) - given it's the "read this first" file, this was treated as
  the highest-priority fix, not a nice-to-have. Also caught
  `taste_profile.md` incorrectly still listed as "doesn't exist yet"
  when it had already been written earlier in this same session.
- **Explicitly rejected**: a generic SQL-upsert helper for `store.py`'s
  four `INSERT...ON CONFLICT...DO UPDATE` methods (four different
  tables/conflict keys - more moving parts than four grep-able
  statements), and splitting `ListingCard.tsx` (still readable at three
  orthogonal prop dimensions; revisit only if a fifth swipe-only UI
  element gets added).

### Zillow instant-update emails: a second, fully-automated ingestion path
The user found that Zillow (unlike StreetEasy) has a `rental-instant-
updates@mail.zillow.com` sender that fires within minutes of a new
listing, individually, not as a thin digest - the exact "speed" problem
the original email pipeline never actually got from StreetEasy. Turned
out to be far richer than expected: the plain-text body already has
structured price/beds/baths/sqft/address/agent as free text, and the
HTML body has a real photo on `photos.zillowstatic.com` - the same
public, no-auth CDN the browser-scan already relies on - plus each
listing's Zillow property ID (zpid), decodable straight out of the
"View this listing" link's click-tracking `target=` query param
without ever following the redirect or fetching a page. That's enough
to build a canonical `zillow.com/homedetails/{zpid}_zpid/` URL with
zero browser interaction.

Two non-obvious extraction details, found by inspecting a real saved
email rather than guessing: (1) the photo isn't an `<img src>` - it's a
`background=` attribute on a `<td>`/`<th>` (an email-HTML convention
with an Outlook VML fallback), so photo-to-listing correlation has to
scope by each listing's own `<table role="group" aria-label="property">`,
not by climbing the DOM from the link. (2) the anchor's href is itself
the click-tracking wrapper, so the zpid must be decoded from the
(percent-encoded) `target=` param via `urllib.parse`, not
substring-matched against the raw href text.

New `apt_agent/zillow_email_import.py`, reusing `browser_import.
import_listings()` rather than duplicating its dedup/backfill logic.
Bundled "Other rentals you might like" listings in the same email get
imported too (free breadth, same full data). Since this needs no
interactive session at all (pure Gmail API + regex), it runs
unattended on the existing GitHub Actions poll cron - the first fully
automated ingestion path in this project, unlike the StreetEasy browser
scan which can only ever be interactive. AI scoring is deliberately
left NULL for these (no live session watching an unattended cron run
to judge a photo itself) rather than wiring up the untested API-key
fallback path just for this - a user decision, not an assumption.

Verified for real against the live inbox before considering this done
(not just "should work from reading the code," per this project's
established norm): 42 new listings imported on the first real run, 41
of 42 with complete photo+address data, the 1 gap falling gracefully
into the existing Needs Scan queue exactly as designed.

**Found and fixed a real silent-drop bug in `_BLOCK_RE` (2026-08-24),**
while investigating whether "all new Brooklyn listings" actually make
it into the app. Two real email variants failed to parse entirely,
discovered by pulling and testing actual captured emails (not
guessed): (1) a "just listed" email's own *featured* listing - the
literal reason the email was sent - had no trailing "| Pets"-style
amenity tag on its bed/bath/sqft line, which the regex required
unconditionally; bundled "you might also like" entries in the same
email happened to all have one, so this wasn't a rare edge case, it
specifically dropped the primary listing type this pipeline exists to
catch. (2) A "New Rental Match" digest template's price line has extra
trailing text (`$4,325/mo | Total monthly price` instead of
`$4,325/mo`), breaking the match immediately. Both are now optional in
the regex. Backfilling the full mailbox history through the fixed
parser recovered **42 genuinely new listings** that had been silently
dropped since the pipeline went live - confirms this wasn't a
theoretical fix. (A third thing found while testing wasn't a bug: two
sample "New Rental Match" emails whose only listing was a
building/complex page with no individual zpid, e.g. "One Blue Slip" -
correctly excluded already, same reasoning as the SRP scan's
building-aggregator filtering and the existing "premium ad in a
different city" exclusion - not every parse failure was a bug.)

**Also confirmed the underlying Zillow saved search itself is
genuinely broad**, not scoped to just the 7 `config.yaml`
neighborhoods - it's named **"Most of Brooklyn"** (visible in each
alert email's subject/body), and real captured addresses span
Greenpoint, Park Slope/Gowanus, Bushwick, Bed-Stuy/Crown Heights,
DUMBO/Downtown Brooklyn, and Red Hook, well outside the 7 configured
neighborhoods. So "new Brooklyn listings go in automatically" was
already true in *scope* - the gap was purely the parsing bug above,
not a narrower-than-expected search.

### Zillow historical backfill: a real anti-bot trip, and a scan skill built around it
The automated email import only catches new listings going forward -
it can't retroactively see whatever was already on the market before
it existed, since Zillow doesn't resend old alerts. Backfilling that
needs the same authenticated-browser technique as the StreetEasy scan.

Two things learned by actually trying it, not by guessing:

1. **Zillow's search-results list is virtualized and only renders
   ~5 cards into the DOM at a time when the map panel is visible** -
   scripted `scrollTop` changes and synthetic CDP wheel events didn't
   reliably force it to render more in initial testing. Toggling
   `isMapVisible: false` in the URL's `searchQueryState` switches to a
   full-width list layout that renders ~11-18 cards up front with zero
   scrolling needed - the difference between "workable per-page
   extraction" and "not."
2. **Zillow's anti-bot wall tripped faster than StreetEasy's did** - 5
   page loads only ~3 seconds apart (testing per-neighborhood
   pagination) hit "Access to this page has been denied," versus
   StreetEasy's wall tripping on page 2 of a 13-load rapid loop. Same
   mitigation applies: pace at `PAGE_PACING_SECONDS` (20s), cap at
   `MAX_PAGES_PER_SESSION` - reused directly from
   `apt_agent/browser_scan_helpers.py` rather than re-tuned per-site,
   since both walls behave the same way (fast loop trips it, paced
   loop reportedly doesn't - not yet re-verified end-to-end with real
   pacing, since the trip happened before pacing was applied).
   Deliberately did **not** try opening a new tab or a fresh browser
   identity to route around the block once hit - the whole reason this
   technique is legitimate is that it's the user's own authenticated
   browser loading a page they're entitled to see, not automated
   evasion, and deliberately spinning up a new identity specifically to
   dodge a block would cross into evasion. Just waited and left it for
   a future session with correct pacing from the start.

**Found and fixed the actual root cause of a "wrong photo" bug
(2026-08-24)**, prompted by the user noticing the app sometimes shows
what looks like Zillow's *last* photo instead of the first. Confirmed
for real, not guessed: every search-card renders exactly 3
`<img src*="zillowstatic">` tags, always in this order - **[last
photo, first/primary photo, second photo]** - an infinite-loop
carousel's prev/current/next peek slides. `extract.js`'s
`card.querySelector('img[src*="zillowstatic"]')` (first DOM match)
therefore grabbed the *last* photo 100% of the time (8/8 real listings
checked, cross-verified against each listing's own
`carouselPhotosComposable.photoData` order) - a systematic,
deterministic bug in the old DOM-scraping technique, not a rare Zillow
inconsistency. Fixed by taking the second matching `<img>` instead of
the first. The current primary technique (`__NEXT_DATA__`/`imgSrc`)
was separately checked across 20 real listings and was never affected
- `imgSrc` matched `photoData[0]` every time - so this bug was already
fully retired by the technique switch; fixing `extract.js` closes the
loop for its fallback role. Backfill-corrected 56 already-imported
listings whose `photo_url` was confirmed wrong, using `__NEXT_DATA__`
data already captured this session (no new page loads needed) - 18
older rows that were never re-surfaced by a later rescan remain
uncorrected; fixing those needs an individual page visit each, not
worth the anti-bot budget right now for a photo-only issue.

Formalized as `.claude/skills/scan-zillow/SKILL.md` +
`apt_agent/zillow_scan/extract.js` + `apt_agent/zillow_scan_helpers.py`
(card-text parsing regex validated offline against 5 real captured
samples before ever touching the module, same "verify against real data"
discipline as everything else here) - explicitly scoped as a backfill-only
tool, not the day-to-day Zillow path, to avoid confusion with
`zillow_email_import.py`.

**Since run for real, multiple times, with correct pacing - and a third
thing learned that the above two didn't catch:**

3. **Zillow's pagination silently drops the search filter state.**
   Navigating to `{page}_p/` with a hand-built `searchQueryState` (no
   `regionSelection`/resolved `mapBounds`) doesn't reliably paginate -
   sometimes it re-serves page 1's results, and sometimes (confirmed
   scanning Brooklyn Heights) it redirects to a canonicalized URL with
   the `searchQueryState` query param dropped entirely, silently
   reverting to Zillow's default *unfiltered* listing set (title's "N
   Rentals" count jumped from 41 to 51 - the filtered vs. unfiltered
   count for the same neighborhood). Mitigated by treating anything
   past page 1 as untrusted for price/beds/baths and re-filtering it in
   Python against `config.yaml`'s bounds before import (5 of Brooklyn
   Heights' page-2 cards were below `price_min` and got dropped this
   way) - not by trying to fix the pagination itself, which isn't worth
   the anti-bot-pacing cost for a plateau that nets only a few
   genuinely-new listings per extra page. **Practical conclusion: budget
   each paced session as roughly one page per neighborhood, spread
   across more neighborhoods, rather than paginating deep into one.**
   First real multi-neighborhood run (2026-08-24, one session, 5 paced
   page loads total - the `MAX_PAGES_PER_SESSION` cap): Brooklyn
   Heights (14 new), Cobble Hill (14 new), Clinton Hill (5 new, only 6
   cards rendered that pass - worth a follow-up), Prospect Heights (14
   new).

4. **The neighborhood-slug guess isn't always right, and a wrong guess
   fails silently (no error, just the wrong neighborhood's data).**
   `williamsburg-brooklyn-ny` resolves to a different, adjacent
   neighborhood ("East Williamsburg") - the correct slug is
   `williamsburg-new-york-ny`. Caught only by checking `page_info()`'s
   title against the intended neighborhood before extracting, exactly
   as the skill instructs - a reminder that this check isn't optional
   even for neighborhoods that seem unambiguous.
5. **The Clinton Hill query specifically plateaus at 6 rendered cards**,
   confirmed by retrying it in a later session (same 6 URLs both times,
   out of 33 total) - not a one-off virtualization glitch like the
   general 5-card map-visible issue above, since `isMapVisible: false`
   was already set both times. Unresolved; a different technique
   (scrolling, a different sort order, or the map-visible layout after
   all) would need to be tried, not just a re-run.
6. **A real anti-bot block recurred** (2026-08-24, second session of
   that day): "Access to this page has been denied" on a Fort Greene
   request, after 4 paced (20s-apart) page loads across Williamsburg/
   Boerum Hill/Clinton Hill that session. Pacing alone doesn't
   guarantee immunity every time - stopped immediately, did not retry
   or open a fresh browser identity, left it for a future session, per
   the same non-negotiable rule as every previous block this project
   has hit. The user was able to clear the block themselves (they can
   see the real browser this drives) - resumed once they confirmed it,
   same legitimate-access reasoning as always since it's still their
   own authenticated session, not a fresh identity spun up to dodge it.

7. **Found a much better extraction source: Zillow's own `__NEXT_DATA__`
   script tag already embeds the full, structured search-results JSON**
   (`props.pageProps.searchPageState.cat1.searchResults.listResults`) -
   the same data the page's React app hydrates from, present on every
   search-results page load regardless of `isMapVisible`. This is a
   strict upgrade over DOM-scraping `article.property-card` text:
   - **Structured fields**, not squished text needing a fragile regex -
     `address`/`unformattedPrice`/`beds`/`baths`/`availabilityDate`/
     `brokerName` come pre-parsed, and `availabilityDate` (a real move-in
     date) wasn't extractable from the DOM cards at all before this.
   - **No hydration-timing race** - it's in the server-rendered HTML at
     initial load, not populated by client-side JS after the fact, which
     likely explains the 6-18 card count variance the DOM approach saw
     (see point 3) - a same-session Clinton Hill re-test with this
     technique is the first real check of that theory.
   - **Each result already carries up to 10-30 photo keys**
     (`carouselPhotosComposable.photoData`, combined with
     `carouselPhotosComposable.baseUrl`'s `{photoKey}` template) - the
     *entire* photo gallery, not just one thumbnail. This directly
     reopens the multi-photo feature the user asked about earlier this
     project and was told to drop (2026-08-24) because getting all
     photos seemed to need a separate per-listing page visit - it
     doesn't, it's already sitting in data this scan loads anyway. Not
     built yet, flagged back to the user, needs their go-ahead given
     they explicitly deprioritized it once already.
   - **Still capped at roughly one page's worth of results per load**
     (18 for the first Fort Greene check, against a
     `categoryTotals.cat1.totalResultCount` of 29) - this technique
     fixes data *quality* and *reliability* per page, not the
     underlying "how do we see the rest of a large neighborhood"
     problem by itself. `mapResults` (which might hold every pin
     regardless of list pagination) was empty even with
     `isMapVisible: true` - appears to populate via a later
     client-side XHR that `wait_for_load()` doesn't wait for, not from
     the initial payload - unresolved, would need active
     waiting/polling to test further.
   - **Confirmed the hydration-timing-race hypothesis directly**: a
     same-day, same-query Clinton Hill re-test using `__NEXT_DATA__`
     returned **26 results, versus 6 from DOM-scraping the exact same
     query earlier that day** - the "6-card plateau" was never a hard
     cap, it was `extract.js` reading the DOM before the client had
     finished hydrating the full first page. `__NEXT_DATA__` is
     server-rendered at initial load, so it doesn't have this problem.
     `scan-zillow/SKILL.md` should be updated to make `__NEXT_DATA__`
     parsing the primary extraction technique, with `extract.js`/DOM
     scraping demoted to a fallback if `__NEXT_DATA__` is ever absent
     or restructured.
   - **Hit another real anti-bot block** on Williamsburg
     (2026-08-24, third session of the day) after only 3 successful
     page loads that session (2x Fort Greene + Clinton Hill) - stopped
     immediately again, same rule as every prior block. Blocks appear
     to cluster around the 3rd-5th paced load regardless of technique
     used to read the page afterward - the anti-bot wall is reacting to
     navigation frequency, not to how the page is parsed once loaded,
     which makes sense since parsing happens entirely client-side after
     the page has already been served.
   - Real listResults entries include some **"relaxed"/building-
     aggregator cards** (a lat/long string standing in for `zpid`, a
     relative `/b/...` or `/apartments/...` URL, no price/beds/baths) -
     these are building-level pages, not individual units, and don't
     fit the per-listing swipe model - filtered out during import
     rather than treated as `needs_backfill`.

8. **Tested price-band splitting as a way to push a neighborhood's
   coverage toward 100% (2026-08-24) - negative result, not a partial
   win.** Narrowing Boerum Hill's price filter from $5000-10000 (47
   total) to $5000-6500 (21 total, per `categoryTotals`) still only
   returned 13 results, and **all 13 were listings already captured**
   by the earlier broad-range scan. The batch Zillow hands back isn't
   "everything under some size cap" - it looks like a fixed-size
   top-slice of the `sort: days` (newest-first) ordering, largely
   independent of how narrow the price filter is, so narrowing price
   mostly just re-confirms the same recent listings with a smaller
   denominator attached rather than surfacing different ones. **Don't
   reach for price-slicing as the fix without re-verifying this** - it
   didn't work in this one real test.
   **Also tested changing sort order** (`sort: {"value": "priceD"}`
   instead of `"days"`) on a later, unblocked retry - also negative.
   All 12 individual listings returned were already-known ones; zero
   new. Combined with the price-band result, this points at a specific
   mechanism: **Zillow appears to select a fixed subset of the pool for
   an exact filtered query first, then sort *that* subset** by whatever
   `sort` value was requested - changing sort just reorders the same
   ~16-18 already-selected listings, it doesn't change which ones get
   selected. Neither lever can get past that selection step.

   **Also tested the user's own observation that scrolling reveals
   more** (2026-08-24) - found and scrolled the actual scrollable
   element (`#search-page-list-container`, not `window`/`document.body`,
   which never scrolls at all on this page) with real scroll-position
   changes and dispatched `scroll` events, in both `isMapVisible: true`
   and `false`, waiting after each step. Card count stayed fixed (18)
   all the way to the true bottom of the container, where the DOM shows
   the page footer, not a loading spinner. No pagination controls exist
   in the DOM either. Conclusion: for this page/query, there is no
   client-side lazy-load or "next page" UI to trigger - the batch is
   fixed at initial load, independent of user interaction.

   **Net result after three real tests (price-band split, sort-order
   change, scroll): no working lever found to push a single query
   toward 100%.** All three came back negative, and the price/sort
   results both point at the same root cause (a fixed pre-sort subset
   selection this project has no visibility into or control over). The
   only thing that has actually produced new listings across sessions
   is **re-running the same query after real time has passed** -
   genuine market turnover changes which listings fall into that fixed
   selection, which is different from any of the three techniques
   above. Coverage now looks like it improves gradually over calendar
   time via repeated scans, not through a cleverer single query.
9. **A third real anti-bot block** (2026-08-24, fourth session of the
   day) hit on only the *second* paced load of that session (the sort-
   order test) - faster than prior blocks, which had taken 3-5 loads.
   Suggests the wall may be sensitive to cumulative same-day activity
   across sessions, not just a fresh per-session counter - worth
   spacing scan sessions further apart across a day, not just pacing
   within one. Stopped immediately, no retry, same rule as always.
