# ROADMAP.md

High-level phases/features. For concrete next actions and who does
them, see `STATUS.md`. For why each choice was made, see `DECISIONS.md`.

## Phase 1 - Gmail alert ingestion  [DEPRIORITIZED - still running, not actively developed]

Built, deployed, and confirmed working (with known gaps accepted) before
the pivot below. Left running on GitHub Actions cron in case Zillow's
alert cadence turns out to be worth revisiting later - not being built
on further right now.

- [x] Gmail ingestion of alert emails (StreetEasy/Zillow/RentHop/NakedApartments)
- [x] Email-snippet field extraction (page-fetch path abandoned - 403s)
- [x] Hard filters: price, beds/baths, move-in window (Sep 1 - Oct 3)
- [x] SQLite dedup by URL + by normalized address (cross-source)
- [x] Email alerts via Gmail API, GitHub Actions deployment, variable-frequency schedule
- [x] Failure alert email + daily heartbeat + dry-run mode
- [x] User confirmed end-to-end working (2026-08-20, with known gaps accepted)
- [ ] (parked) Zillow/RentHop/NakedApartments saved searches never finished
- [ ] (parked) Delisting detection, weekly "close calls" digest

## Shared web app pivot  [IN PROGRESS - started 2026-08-22]

**Supersedes the Phase 2 (taste-scored emails) and Phase 2.5 (texting
agent) plans below** - real-world testing showed speed was never the
actual problem; the user's problem is shared, persistent, asynchronous
review by two people. See `DECISIONS.md` ("Pivot from email alerts to
a shared web app") and `.claude/plans/well-i-realized-that-goofy-platypus.md`
for the full reasoning.

- [x] Schema: per-user ratings/comments, shared hide flag, AI score
      fields, open-house fields (extends the existing `ListingStore`,
      shared with the email pipeline)
- [x] `webapp/` - FastAPI + Jinja2 shared feed, rating/comment/hide,
      open-houses view, hidden-listings review, lightweight identity -
      built and tested locally end-to-end
- [x] Browser-authenticated scan ingestion (bypasses the anti-scraping
      wall that blocks anonymous requests) - formalized as a project
      skill with a pacing fix for a real PerimeterX trip found while
      building it
- [x] AI taste-match scoring: primary path is the scanning Claude Code
      session scoring each listing itself (vision + a page screenshot,
      no API key needed) - an Anthropic-API-key-based fallback exists
      but is optional, not required
- [ ] Reference photos or StreetEasy links -> written taste profile
      (`taste_profile.md`) - **needs the user, in progress**
- [ ] Host it: Turso (db) + Fly.io (app) - **needs the user's accounts**
- [ ] Dev tooling: ruff (format+lint), ty (types), poethepoet (task
      runner), light `uv` adoption - done, see `CLAUDE.md` "Dev tooling"

## Phase 2 - Taste/style scoring in email alerts  [SUPERSEDED - see pivot above]

Original plan: score each new listing's photos against a taste profile
and include it in the alert email. The AI-scoring *mechanism* was kept
and reused in the pivot above, but the *delivery* (email) was replaced
by the shared web app's feed. Left here as historical record, not a
pending plan - don't build an email-delivered version of this.

## Phase 2.5 - Interactive texting agent  [SUPERSEDED - see pivot above]

Original plan: a Twilio-based SMS agent for conversational queries
("anything in Boerum Hill that looks like the Fort Greene one?"). The
user chose a web app over a texting interface instead. Full original
design reasoning kept in `DECISIONS.md` as historical record (in case
a chat/NL interface gets revisited later - the user explicitly declined
building one into the web app "for now," not permanently) - don't build
this as designed here.

## Phase 3 - Nice-to-haves  [NOT STARTED - may end up as webapp features instead]

These predate the pivot and were scoped for the email pipeline. Worth
re-evaluating each as a webapp feature (e.g. a button/field on the
shared feed) rather than an email addition, if picked back up.

- [ ] Auto-drafted inquiry message ("still available? can we see it Thurs?")
- [ ] Days-on-market tracking as a negotiation-leverage signal
- [ ] Delisting detection
- [ ] Weekly close-calls digest (or: a webapp view of near-misses)
- [ ] Commute-time enrichment via Maps API
- [ ] Rent-stabilization lookup against NYC public data
