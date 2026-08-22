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
