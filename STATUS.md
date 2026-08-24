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
- [x] [CLAUDE] `webapp/` (FastAPI JSON API) + `frontend/` (React/TS SPA,
      Vite) - feed with sort (AI score/our ratings/leaderboard) and
      filters (neighborhood, price range, move-in date, "needs my
      review"/"needs both"), listing detail (Google Maps embed, back
      link, rating/comment/hide), `/open-houses`, `/hidden`,
      `/leaderboard`, lightweight cookie identity, mobile-responsive
      nav/filters - tested end-to-end via headless Playwright against
      the real `listings.db`. Rebuilt from an initial Jinja2
      server-rendered version after real usage showed full-page
      reloads felt "templated" - see DECISIONS.md.
- [x] [CLAUDE] Formalized the browser-scan workflow: `extract.js` +
      `browser_scan_helpers.py` (with the pacing/page-cap fix for the
      PerimeterX trip found while building this) + a project skill
      (`.claude/skills/scan-streeteasy/SKILL.md`)
- [x] [CLAUDE] AI scoring: primary path is the Claude Code session doing
      the scan scoring each listing itself (vision + a page screenshot,
      no API key) per `.claude/skills/scan-streeteasy/SKILL.md` step 7.
      `webapp/scoring.py`/`webapp/rescore.py` (Anthropic-API-key-based)
      kept only as an optional secondary fallback, not required.
- [x] [CLAUDE] Dev tooling: `ruff` (format + lint), `ty` (Astral's type
      checker), `poethepoet` (task runner - `poe check`/`fmt`/`lint`/
      `typecheck`/`api`/`web`/`dev`/`rescore`/`install`), light `uv`
      adoption for local env/installs (`requirements.txt` stays the
      source of truth, GitHub Actions untouched), Playwright (headless
      browser testing for the app's own UI, independent of the
      authenticated browser-use session). Fixed real bugs found via
      testing: invented version pins in `requirements.txt`, an empty
      `min_score=""` crashing the feed, a cross-hostname SameSite
      cookie bug (frontend/backend must both use `localhost`, not mix
      with `127.0.0.1`).
- [x] [CLAUDE] Reworked the shared feed into the current model: each
      person swipes left/right independently (`listing_swipes` table),
      a match (both swiped right) moves a listing into a shared Inbox
      for category ratings (light/kitchen/location/vibe/coziness/
      space) and comments, and the Leaderboard is scoped to matches.
      Superseded pages/routes (`Feed`, `Hidden`, `/api/hidden` GET,
      `/api/neighborhoods`) removed rather than left dormant. Open
      Houses (a dedicated cross-listing browsing page) removed outright
      - a listing's own open-house info still shows on its card.
      Cleanup pass after: fixed a category-rating rounding bug
      (round-half-up instead of Python's round-half-to-even), removed
      other dead code/CSS, consolidated a duplicated `KNOWN_USERS`
      constant, and brought `CLAUDE.md` back in sync with the current
      pages/routes. See `DECISIONS.md`.
- [x] [CLAUDE] `apt_agent/zillow_email_import.py` - a second, fully
      automated ingestion path. Zillow's `rental-instant-updates@
      mail.zillow.com` sender fires per-listing within minutes (found by
      the user); the email body alone has full structured data plus a
      real photo (no page fetch needed at all), so this runs unattended
      on the existing GitHub Actions poll cron - verified for real
      against the live inbox, 42 listings imported on the first run.
      AI scoring deliberately left NULL for these (no live session to
      judge a photo in an unattended run). See `DECISIONS.md`.
- [ ] [CLAUDE] Zillow historical backfill - **built, not yet run for
      real**. `.claude/skills/scan-zillow/SKILL.md` +
      `apt_agent/zillow_scan/extract.js` + `apt_agent/zillow_scan_helpers.py`
      exist and the card-parsing regex is verified against real captured
      samples, but an actual scan attempt tripped Zillow's anti-bot wall
      (5 rapid page loads, ~3s apart) before the skill's pacing was ever
      applied - see `DECISIONS.md`. Next session should retry with real
      20s-apart pacing, one `config.yaml` neighborhood at a time (now 7,
      Williamsburg added). Not urgent - `zillow_email_import.py` already
      covers everything going forward, this is only the pre-existing
      backlog.

Needs you (all [MANUAL] - real accounts/credentials/content only you can provide):
- [ ] [MANUAL] Send reference photos or StreetEasy links (liked + disliked)
      so a taste profile can be written to `taste_profile.md` - in
      progress, see log below
- [ ] [MANUAL] `turso auth login` + create a database (`apt-listings`) -
      get `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN`
- [ ] [MANUAL] `fly auth login`, `fly launch`, `fly secrets set` (Turso
      creds), `fly deploy`
- [ ] [MANUAL] Run the one-time migration script into Turso, confirm the
      live URL works from both phones
- (no longer needed for the primary scoring path) ~~Provide an
  `ANTHROPIC_API_KEY`~~ - the scanning session scores listings itself now,
  see the AI scoring line above. Still relevant only if you want the
  optional API-key fallback path too.

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
- **2026-08-22 (later)**: User used the app for real (rated + commented
  on a real listing within minutes) and gave direct feedback: no back
  button, no photos/map embedded, and "still looks very templated
  jinja." Rebuilt `webapp/` from server-rendered Jinja into a React/TS
  SPA (`frontend/`) + JSON API, added a Google Maps embed (keyless,
  no API key), a leaderboard, location/price/move-in-date filters, and
  a "needs my review"/"needs both" segmentation - all per explicit
  request. AI scoring no longer needs `ANTHROPIC_API_KEY` at all for
  the primary path (the scanning session scores listings itself, see
  DECISIONS.md) - removed as a stated blocker. Found and fixed two
  real bugs via testing: an empty `min_score` crashing the feed, and a
  cross-hostname `SameSite` cookie bug that silently broke login
  (frontend/backend must both be accessed via `localhost`, never mixed
  with `127.0.0.1`). Also found and fixed real mobile-viewport overflow
  issues (nav bar, filter bar) via a Playwright mobile-width test.
  Tested throughout via a fresh headless Playwright browser rather than
  the authenticated browser-use session, since this app's own UI needs
  no StreetEasy authentication - notable because the user stepped away
  mid-session and browser-use's Chrome permission prompt can't be
  clicked unattended, but this app's testing wasn't blocked by that.
