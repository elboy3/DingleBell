# CLAUDE.md - Project Context

Read this before making any product or architecture decision on this
repo. If you're a Claude session picking this up fresh, this file plus
`DECISIONS.md` and `ROADMAP.md` should get you fully oriented in one pass.

## What this is

An automated agent that watches a Gmail inbox for apartment-listing
alert emails (StreetEasy, Zillow, RentHop, NakedApartments), extracts
and filters listings against hard criteria, dedups across sources, and
emails the two end users immediately when a real match appears.

## Who this is for, and why it matters

Built for two people apartment-hunting in Brooklyn on a real deadline -
their current lease ends end of September 2026, and manual searching
hadn't surfaced much. This is not a toy project or a casual
side-experiment: **finding the right apartment on this timeline matters
a lot to them.** Treat reliability and correctness with commensurate
seriousness - a missed alert or a silent failure has a real cost.

## Hard constraints (do not relax without the user confirming)

- Move-in window: **Sep 1 - Oct 3, 2026** (2 wk flex early, 1-2 day flex
  late). Encoded in `config.yaml` -> `search.earliest_move_in` /
  `latest_move_in`.
- Price range, beds/baths minimums: also in `config.yaml`, user-owned,
  don't guess or change these.

## Goal ordering (matters for design decisions)

1. Surface listings they wouldn't have found through manual searching
   (breadth of discovery)
2. Alert as fast as practically reasonable when something good appears
   (latency)

This is explicitly **not** a price-drop tracker or a leisurely
browsing tool - deadline pressure means speed and coverage beat
sophistication.

## Current phase: Phase 1

Ingestion + hard filtering + alerting, no taste/style scoring yet.
**As of the last working session, the explicit instruction was: don't
start Phase 2 (Claude-vision taste scoring against reference photos)
until the user confirms Phase 1 is live and working reliably.** Check
with the user before jumping ahead, even if it seems like a natural
next step.

**Phase 2.5 (interactive SMS agent) has been designed but not built** -
see ROADMAP.md and DECISIONS.md. It's a real scope increase (new
deployment model - always-on/on-demand server, not cron; absorbs
Phase 2's similarity-matching problem as its data foundation) and is
sequenced to come after Phase 2, not instead of it or in parallel.

## Architecture summary (see DECISIONS.md for full reasoning on each)

- **Ingestion via Gmail alert emails**, not direct scraping of
  StreetEasy/Zillow/etc. Avoids anti-bot and ToS problems entirely.
- **Deployed on GitHub Actions, public repo.** Unlimited free minutes;
  secrets (OAuth creds, recipient emails) live only in encrypted GitHub
  Secrets, never committed in plaintext.
- **Variable polling schedule**: every 15 min 7am-11pm ET, every 30 min
  overnight - tuned to when listings actually get posted, not maximal
  frequency. See `.github/workflows/poll.yml` for the cron entries.
- **SQLite (`listings.db`) for dedup**, keyed by URL and by a normalized
  address (catches the same unit cross-posted on multiple sites).
  **This file is deliberately committed back to the repo by the
  workflow after every run** - GitHub Actions runners are ephemeral, so
  without that commit step dedup state would reset every run.
- **Daily heartbeat email** (separate workflow, `heartbeat.yml`) so
  silence never has to be interpreted as "did it break?"
- **Dry-run mode** (`python -m apt_agent.main --dry-run`) pushes one
  fake listing through the full pipeline to confirm OAuth + filters +
  email delivery work, without waiting for a real alert.

## File map

| File | Purpose |
|---|---|
| `apt_agent/gmail_auth.py` | One-time OAuth setup, produces `token.json` |
| `apt_agent/gmail_ingest.py` | Polls Gmail, extracts listing URLs from alert emails |
| `apt_agent/listing_parser.py` | Best-effort fetch/parse of listing pages |
| `apt_agent/filters.py` | Hard filters: price, beds/baths, move-in window |
| `apt_agent/store.py` | SQLite dedup (by URL and normalized address) + stats |
| `apt_agent/notify.py` | Builds and sends alert/heartbeat/test emails via Gmail API |
| `apt_agent/notify_failure.py` | Sends a "run failed" email, wired to `if: failure()` in the workflow |
| `apt_agent/heartbeat.py` | Daily "agent is alive" summary email |
| `apt_agent/main.py` | Orchestrates a normal run or a `--dry-run` test |
| `config.yaml` | User-owned filters and settings (non-secret) |
| `.github/workflows/poll.yml` | Scheduled ingestion/alert workflow |
| `.github/workflows/heartbeat.yml` | Scheduled daily heartbeat workflow |

## Known limitations / open items

- Address normalization for cross-source dedup is best-effort regex,
  not a real address parser - won't catch every variant.
- No delisting detection yet (deliberately deferred).
- No weekly "close calls" digest yet (deliberately deferred).
- `listing_parser.py` field extraction is regex-based against whatever
  HTML the page returns that day - will miss fields on layout changes.
- Scraping listing pages directly (even lightly) carries some risk of
  being blocked over time; if that starts happening, prefer switching
  to `extract_from_email_snippet()` in `listing_parser.py`, which reads
  fields straight out of the alert email instead of fetching the page.

## Working style notes for future sessions

- The user is technical (comfortable with Python, Git, cron, OAuth,
  GitHub Actions) - no need to over-explain basic tooling, but do
  explain non-obvious infra tradeoffs (e.g. GitHub Actions minute
  costs, ephemeral runners) since those aren't things general
  programming knowledge covers.
- Prioritize things that build *confidence the system works* (dry-run
  mode, heartbeats, clear failure alerts) over feature breadth, given
  how much this matters to the user and how tight the timeline is.
- Don't add scope (e.g. Phase 2 taste scoring, delisting detection)
  without the user asking or confirming Phase 1 is solid first.
