# STATUS.md - Live Checklist

This is the operational, keep-it-updated companion to `ROADMAP.md`
(which tracks features/phases at a higher level). This file tracks
concrete next actions, tagged by who does them.

**Legend:**
- **[MANUAL]** - only you can do this (clicking through a console,
  deciding real values, texting, physically waiting on something). A
  Claude session can guide/explain but can't execute it.
- **[CLAUDE]** - a Claude session with code/file/computer access can do
  this directly (writing code, editing config values you've specified,
  running local tests, updating this checklist).
- **[CLAUDE-ASSISTED]** - Claude can do the mechanical part, but needs
  a decision or real value from you first (e.g. editing config.yaml
  once you've told Claude the actual price range).

Check items off as they're done. Add a dated note under a phase if
something changes (blocked, skipped, revisited) - keep it a real log,
not just a static checklist.

---

## Phase 1 - Ingestion, filtering, alerting  [DEPRIORITIZED - still running, see pivot below]

### Build (done, via Claude sessions)
- [x] [CLAUDE] Scaffold repo structure and all core modules
- [x] [CLAUDE] Hard filters, URL dedup, address dedup, notify, heartbeat, dry-run logic
- [x] [CLAUDE] GitHub Actions workflows (poll.yml + heartbeat.yml)
- [x] [CLAUDE] Smoke-tested dedup logic and email-building logic locally
- [x] [CLAUDE] Fixed St/Street normalization bug found during testing

### Deploy (your turn now)
- [x] [MANUAL] Create Google Cloud project, enable Gmail API
- [x] [MANUAL] Create OAuth Desktop credentials, download `credentials.json`
- [x] [MANUAL] Switch OAuth consent screen to Production status (avoids 7-day token expiry)
- [x] [MANUAL] Run `pip install -r requirements.txt` in your real environment
- [x] [MANUAL] Run `python -m apt_agent.gmail_auth`, approve in browser
- [MANUAL] Set up saved-search alerts on StreetEasy/Zillow/RentHop/NakedApartments -> the same inbox, set to "instant" not "daily digest"
  - [x] StreetEasy
  - [ ] Zillow
  - [ ] RentHop
  - [ ] NakedApartments
- [x] [CLAUDE-ASSISTED] Edit `config.yaml` price range / beds/baths minimums (tell Claude the numbers, it makes the edit)
- [x] [MANUAL] Create a new **public** GitHub repo, push this code
- [x] [MANUAL] Add the 4 repo secrets (`GMAIL_CREDENTIALS_JSON`, `GMAIL_TOKEN_JSON`, `NOTIFY_RECIPIENTS`, `NOTIFY_FROM_ADDRESS`)
- [x] [MANUAL] Trigger a dry-run via Actions tab -> "Run workflow", confirm the TEST email arrives
- [x] [MANUAL] Trigger the heartbeat workflow manually, confirm the "agent is alive" email arrives
- [ ] [MANUAL] Let it run 1-2 days on real alerts

### Confirm (blocker before Phase 2)
- [x] [MANUAL] You confirm it's been working reliably end-to-end
  - **2026-08-20**: Confirmed by user with known gaps explicitly accepted
    rather than resolved: Zillow/RentHop/NakedApartments saved searches
    not yet set up, no hard neighborhood filter (site-level trust only),
    address never makes it into the alert email, and no genuine
    saved-search-match alert email seen yet (only a generic
    recommendations digest). Revisit these if real-world alerts turn out
    noisy or off-target.

---

## Phase 2 / 2.5 - SUPERSEDED by the shared web app pivot (2026-08-22)

Real-world testing showed StreetEasy doesn't send true real-time alerts and
the emails are thin on detail - speed was never the actual bottleneck worth
solving. Pivoted to a shared web app instead of taste-scored emails or a
texting agent. See the new section below, `DECISIONS.md`, and
`.claude/plans/well-i-realized-that-goofy-platypus.md` for the full story.
The old Gmail/cron pipeline (Phase 1 above) is left running, deprioritized
- not removed, in case Zillow's alert cadence is worth revisiting later.

---

## Shared web app pivot [IN PROGRESS - started 2026-08-22]

Built and verified locally (all via Claude sessions):
- [x] [CLAUDE] Schema: `listing_reactions` table (per-user rating/comment),
      shared `hidden`/`hidden_by`/`hidden_at`, `ai_score`/`ai_reasoning`/
      `ai_profile_version`, `open_house_raw`/`open_house_date`
- [x] [CLAUDE] `webapp/` - FastAPI + Jinja2 app: feed (sort by AI score or
      by min-of-both-ratings), listing detail + rating/comment/hide,
      `/open-houses`, `/hidden`, lightweight cookie identity - tested
      end-to-end locally against the real `listings.db`
- [x] [CLAUDE] Formalized the browser-scan workflow: `extract.js` +
      `browser_scan_helpers.py` (with the pacing/page-cap fix for the
      PerimeterX trip found while building this) + a project skill
      (`.claude/skills/scan-streeteasy/SKILL.md`)
- [x] [CLAUDE] AI scoring pipeline (`webapp/scoring.py`, `webapp/rescore.py`)
      wired into `browser_import.py`, graceful no-op when no taste profile
      / API key is configured - **not yet tested against the real Claude
      API**, since no `ANTHROPIC_API_KEY` is available in this environment
- [x] [CLAUDE] Dev tooling: `ruff` (format + lint), `ty` (Astral's type
      checker), `poethepoet` (task runner - `poe check`/`fmt`/`lint`/
      `typecheck`/`run`/`rescore`/`install`), light `uv` adoption for
      local env/installs (`requirements.txt` stays the source of truth,
      GitHub Actions untouched). Fixed a real bug `uv`'s stricter
      resolver caught: `requirements.txt` had invented version pins for
      several deps, not what was actually installed/tested.

Needs you (all [MANUAL] - real accounts/credentials/content only you can provide):
- [ ] [MANUAL] Send reference photos (liked + disliked) so a taste profile
      can be written to `taste_profile.md`
- [ ] [MANUAL] Provide an `ANTHROPIC_API_KEY` (for local testing now, and
      as a Fly.io secret once hosted) so AI scoring can actually be verified
      end-to-end for the first time
- [ ] [MANUAL] `turso auth login` + create a database (`apt-listings`) -
      get `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN`
- [ ] [MANUAL] `fly auth login`, `fly launch`, `fly secrets set` (Turso
      creds + `ANTHROPIC_API_KEY`), `fly deploy`
- [ ] [MANUAL] Run the one-time migration script into Turso, confirm the
      live URL works from both phones

---

## Phase 3 - Nice-to-haves [NOT STARTED]

- [ ] [CLAUDE] Auto-drafted inquiry message ("still available? can we see it Thurs?")
- [ ] [CLAUDE] Days-on-market tracking
- [ ] [CLAUDE] Delisting detection
- [ ] [CLAUDE] Weekly close-calls digest
- [ ] [CLAUDE-ASSISTED] Commute-time enrichment via Maps API (needs your API key)
- [ ] [CLAUDE] Rent-stabilization lookup against NYC public data

---

## Log

- **2026-08-19**: Phase 1 built and smoke-tested. Phase 2.5 (texting agent)
  designed and documented, not started. Currently at "your turn to deploy"
  step of Phase 1.
- **2026-08-19/20**: Deployed through most of Phase 1's checklist (Google
  Cloud project, OAuth, config.yaml, public repo, GitHub Secrets, dry-run
  + heartbeat both confirmed via real emails). Found and fixed two real
  bugs surfaced by real-world testing, not hypothetical: (1) OAuth scope
  missing `gmail.modify`, needed to mark alert emails as read - token
  redone locally + secret updated; (2) Gmail query had no date bound, so
  it was pulling years of unread StreetEasy/Zillow backlog on this
  existing personal account in as if new, at risk of false-positive
  alerts since filters.py treats unknown fields as "let it through" -
  added `newer_than:1d`. Also switched ingestion from page-fetch (403s
  immediately on both StreetEasy and Zillow) to email-snippet parsing.
  See DECISIONS.md for full reasoning. No bogus alerts were ever sent -
  verified `listings.db` is empty. Zillow's real alert-email links turned
  out to be wrapped in click-tracking redirects the URL regex won't
  match - not fixed yet since Zillow saved search isn't set up yet and
  we don't have a real sample to match against; revisit when doing Zillow.
  StreetEasy saved-search alert is live; still waiting on a genuine new
  listing email to confirm one real end-to-end match before trusting the
  "let it run 1-2 days" step.
- **2026-08-22**: Discovered the email pipeline's actual alert cadence is
  thin (a few "recommendations" digests/day, no real-time per-listing
  alerts) and separately discovered (via the `browser-use` MCP plugin) that
  the user's authenticated browser session can load StreetEasy's full
  search-results page directly, bypassing the anti-scraping wall entirely.
  Pivoted: the real problem was never speed, it's giving two people a
  shared, persistent, ranked view they can react to asynchronously. Built
  and locally verified `webapp/` (shared feed/ratings/comments/hide/open
  houses) + the browser-scan ingestion path + an AI scoring pipeline
  (untested against the real API - no key available in this environment).
  Old email pipeline left running, deprioritized. Next real blockers are
  all [MANUAL]: reference photos for the taste profile, an Anthropic API
  key, and Turso/Fly.io account setup for hosting. Full design in
  `.claude/plans/well-i-realized-that-goofy-platypus.md`.
