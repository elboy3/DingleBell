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
      **2026-08-24: found and fixed a real silent-drop bug** in the
      email-parsing regex - a "just listed" email's own featured
      listing (not just bundled recommendations) was dropped whenever
      it lacked a trailing "| Pets"-style amenity tag, and a "New
      Rental Match" digest template's price line format broke matching
      entirely. Backfilling the full mailbox with the fix recovered 42
      previously-missed listings. Also confirmed the underlying Zillow
      saved search is named **"Most of Brooklyn"** and genuinely spans
      far beyond the 7 `config.yaml` neighborhoods (Greenpoint, Park
      Slope, Bushwick, Bed-Stuy, DUMBO, Red Hook all seen in real
      captured emails) - so new-listing coverage going forward is
      broad by scope, and was only limited by the now-fixed parsing
      bug. See `DECISIONS.md`.
- [ ] [CLAUDE] Zillow historical backfill - **in progress, all 7
      `config.yaml` neighborhoods now have at least one paced pass**
      (148 total listings in `listings.db`, up from 87 across this and
      the prior session). **Hit a real anti-bot block** requesting Fort
      Greene again, even with correct 20s pacing, after 4 paced loads
      that session (title: "Access to this page has been denied") -
      stopped immediately per the established rule, didn't retry or
      open a fresh browser identity. Confirmed *again* (see
      `DECISIONS.md`) that Zillow's own pagination silently drops the
      price/beds/baths filter state past page 1 - each neighborhood
      pass is realistically "page 1 only," spread across neighborhoods
      rather than paginating deep into one. StreetEasy backfill
      deprioritized per user preference (2026-08-24: "I'm okay with
      actually using all zillow, it has everything streeteasy has for
      the most part") - not pursuing a `scan-streeteasy` pass unless
      asked. Not urgent day-to-day either way - `zillow_email_import.py`
      already covers everything going forward unattended; this is only
      the pre-existing backlog.

      **Coverage tracking (captured / Zillow's own reported total for
      that filtered search, as of 2026-08-24, updated after each
      session) - this table is the concrete answer to "how do we know
      when we've gotten everything":**

      | Neighborhood | Captured | Reported total | Coverage | Notes |
      |---|---|---|---|---|
      | Williamsburg | 27 | 221 | ~12% | up from 7 (~3%) in one re-scan with the new technique; still by far the biggest gap |
      | Brooklyn Heights | 22 | 41 | ~54% | |
      | Clinton Hill | 19 | 33 | ~58% | jumped from 6 (~18%) once switched to the `__NEXT_DATA__` extraction technique - the old "plateau" was a DOM-hydration-timing bug, not a hard cap, see DECISIONS.md |
      | Fort Greene | 18 | ~29-49 (fluctuates, see note) | ~40-60% | |
      | Prospect Heights | 17 | 35 | ~49% | |
      | Cobble Hill | 15 | 34 | ~44% | this re-scan mostly re-confirmed existing data (10 of 11 backfilled, only 1 new) - may be close to what one paced load can see for this neighborhood |
      | Boerum Hill | 11 | 47 | ~23% | |

      All 7 neighborhoods have now been scanned at least once with the
      `__NEXT_DATA__` technique (2026-08-24) - re-running the same
      neighborhood again mostly backfills better data on existing rows
      at this point (Cobble Hill: 10 of 11 results were already known).

      **Tested and ruled out three separate techniques for pushing a
      neighborhood toward 100%** (see DECISIONS.md for full detail on
      each): price-band splitting (narrowing Boerum Hill's pool from 47
      to 21 still returned only already-known listings), sort-order
      changes (price-descending instead of newest-first - also zero
      new listings), and scrolling (tested properly on the real
      scrollable list container in both map views - never loaded more
      cards, no pagination controls exist either). All three came back
      negative in the same way, pointing at one root cause: Zillow
      appears to select a **fixed subset of a neighborhood's pool for
      an exact filtered query before sorting/serving it** - nothing
      tested changes which listings land in that subset.

      **Final conclusion: there is no known lever that reliably pushes
      a single scan toward 100%.** The only thing that has actually
      added new listings across this project's real sessions is time
      passing between scans (market turnover changes what falls into
      that fixed subset) - the practical path forward is periodic
      re-scans of each neighborhood over the coming weeks, not a
      smarter single query.

      **2026-08-24: found and fixed a real "wrong photo" bug** - the
      old DOM-scraping technique (`extract.js`) always grabbed a
      listing's *last* photo instead of its first (Zillow's card DOM
      renders exactly 3 images in [last, first, second] order for a
      peek-ahead carousel; the first DOM match is always the last
      photo). The current `__NEXT_DATA__` technique was unaffected.
      Fixed `extract.js` for its fallback role, and backfill-corrected
      56 already-imported listings using data already captured this
      session - 18 older rows remain uncorrected (never resurfaced by
      a later rescan), low priority since it's a photo-only issue. See
      `DECISIONS.md`.

      Zillow's own reported total for the same neighborhood/filter isn't
      perfectly stable between checks (Fort Greene showed "89 Rentals" on
      one load and "49 Rentals" on another, while the underlying
      `categoryTotals.cat1.totalResultCount` said 29) - live market
      turnover plus at least one inconsistent count Zillow itself
      exposes, not a bug in our tracking. Treat the "reported total"
      column as an approximate denominator, not a precise one.

      **Extraction technique upgraded mid-backlog (2026-08-24)**: Zillow's
      search-results pages embed the full structured result set (address,
      price, beds, baths, real availability date, up to ~10-30 photo
      keys per listing) in a `__NEXT_DATA__` script tag - reading that
      JSON directly is now the primary technique (better data, and fixes
      a real hydration-timing bug that was capping some neighborhoods at
      far fewer cards than the DOM would eventually render). DOM-scraping
      `extract.js` is demoted to a fallback. `scan-zillow/SKILL.md` needs
      a rewrite to reflect this as the default procedure, not yet done.

      **Two-part completion model** (this is the real answer, not just
      the table): (1) *Going forward*, this is already effectively
      solved - `zillow_email_import.py` catches every new Zillow listing
      automatically within minutes, no browser/coverage-gap risk at all.
      (2) *The historical backlog* (everything that existed before that
      pipeline started) is what the table above tracks, and it has a
      real technical ceiling - Zillow's page rendering and anti-bot
      posture mean literal 100% isn't achievable through this technique.
      Realistic target: get the 6 non-Williamsburg neighborhoods to
      ~90%+ coverage (achievable in a handful more paced sessions,
      especially if the price-slicing or hydration-timing fix in
      `scan-zillow/SKILL.md` pans out), and treat Williamsburg as a
      standing, never-quite-100% background effort given its size - new
      Williamsburg listings still get caught automatically either way.
      Update this table after each scan session so progress is visible
      rather than a vague "done" feeling.

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
