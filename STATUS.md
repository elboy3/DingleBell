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

## Phase 1 - Ingestion, filtering, alerting

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
- [ ] [MANUAL] Run `pip install -r requirements.txt` in your real environment
- [ ] [MANUAL] Run `python -m apt_agent.gmail_auth`, approve in browser
- [ ] [MANUAL] Set up saved-search alerts on StreetEasy/Zillow/RentHop/NakedApartments -> the same inbox, set to "instant" not "daily digest"
- [x] [CLAUDE-ASSISTED] Edit `config.yaml` price range / beds/baths minimums (tell Claude the numbers, it makes the edit)
- [x] [MANUAL] Create a new **public** GitHub repo, push this code
- [ ] [MANUAL] Add the 4 repo secrets (`GMAIL_CREDENTIALS_JSON`, `GMAIL_TOKEN_JSON`, `NOTIFY_RECIPIENTS`, `NOTIFY_FROM_ADDRESS`)
- [ ] [MANUAL] Trigger a dry-run via Actions tab -> "Run workflow", confirm the TEST email arrives
- [ ] [MANUAL] Trigger the heartbeat workflow manually, confirm the "agent is alive" email arrives
- [ ] [MANUAL] Let it run 1-2 days on real alerts

### Confirm (blocker before Phase 2)
- [ ] [MANUAL] You confirm it's been working reliably end-to-end

---

## Phase 2 - Taste/style scoring [NOT STARTED - blocked on Phase 1 confirmation]

- [ ] [MANUAL] Send reference photos of apartments you both liked/disliked
- [ ] [CLAUDE] Derive a written taste profile from those photos
- [ ] [CLAUDE] Wire a scoring step into the pipeline (Claude vision vs. profile)
- [ ] [CLAUDE] Include score + one-line reasoning in alert emails
- [ ] [MANUAL] Review real scored alerts, give feedback to refine the profile

---

## Phase 2.5 - Interactive texting agent [DESIGNED, NOT STARTED - sequenced after Phase 2]

- [ ] [MANUAL] Sign up for Twilio, buy a phone number
- [ ] [CLAUDE] Build the webhook server (FastAPI or similar)
- [ ] [MANUAL] Deploy to chosen serverless platform, connect Twilio webhook URL
- [ ] [CLAUDE] Build per-listing Claude-vision description generation at ingestion time
- [ ] [CLAUDE] Build similarity-query handling (direct comparison, no vector DB)
- [ ] [CLAUDE] Build preference-notes logging from casual texted feedback
- [ ] [MANUAL] Test via real texts, iterate on tone/behavior

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
