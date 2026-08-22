# Apartment Hunt

A shared web app for two people to browse, rate, comment on, and hide
Brooklyn apartment listings together, asynchronously, from their own
phones - with an AI taste-match score computed for each listing. Fed by
an interactive browser scan of StreetEasy's real search results (not
email alerts, not a cron job).

There's a second, older piece in this repo too: a Gmail-alert email
pipeline (`apt_agent/`) that's still running on a GitHub Actions cron,
but deprioritized - see "Why two systems?" below. **If you're setting
this up fresh, skip straight to the web app section; you don't need
the email pipeline unless you specifically want it.**

See `CLAUDE.md` for full project context, `DECISIONS.md` for why each
choice was made, `ROADMAP.md` for what's done vs. planned, and
`STATUS.md` for the live, concrete checklist of what's left (tagged
**[MANUAL]** - only you can do it - vs **[CLAUDE]** - a Claude session
can do it directly).

## Why two systems?

The email pipeline was built first, on the assumption that speed -
seeing a new listing first - was what mattered. Real-world testing
showed that was wrong: StreetEasy doesn't send true real-time alerts,
and the actual problem was never speed - it was giving two people a
shared, persistent, ranked view they can react to on their own time,
without re-evaluating the same listings or holding rankings in their
heads. Full story in `DECISIONS.md`. The email pipeline is left
running (it might be worth revisiting for Zillow specifically later)
but isn't being built on further.

## The web app

### 1. Set up locally

```
uv venv
uv pip install -r requirements.txt -r requirements-dev.txt
# or, once poethepoet is installed: poe install
```

```
poe run          # uvicorn webapp.app:app --reload, http://127.0.0.1:8000
```

Visit `/whoami`, pick "Elliott" or "Madison" (no password - see
`CLAUDE.md` for why that's fine at this scale), and you're in. This
runs against the same `listings.db` the email pipeline uses/updates -
no separate setup needed to see real data locally.

### 2. Populate the feed

There's no cron for this - it's an interactive, session-driven scan
that only works because it drives your real, already-logged-in Brave/
Chrome browser (see `DECISIONS.md` for why that bypasses the anti-bot
wall that blocks anonymous scraping). To run one, open a Claude Code
session in this repo and ask it to scan StreetEasy (it'll pick up
`.claude/skills/scan-streeteasy/SKILL.md`), or run it yourself whenever
you want a fresh batch - every few days, or before a weekend of
apartment hunting, is a reasonable cadence now that speed isn't the
goal.

Behind the scenes this ends in `python -m apt_agent.browser_import
<scanned-listings.json>`, which dedups against everything already in
`listings.db` and never sends an email - it's a pure data-in operation.

### 3. AI taste-match scoring

Each newly-imported listing gets scored automatically **if** both of
these exist:

- `taste_profile.md` at the repo root (written from reference photos -
  send some liked/disliked apartment photos to a Claude session to
  generate this; doesn't exist yet as of this writing)
- an `ANTHROPIC_API_KEY` environment variable

If either is missing, ingestion still works fine - scoring is just
skipped (see `webapp/scoring.py`'s graceful-degradation design). Once
both exist, backfill anything scored before or scored against a
now-stale profile version with:

```
poe rescore       # python -m webapp.rescore
```

### 4. Hosting (not done yet)

Planned: Turso (hosted SQLite-compatible db) + Fly.io (the app itself).
Not set up yet - needs a Turso account/database and a Fly.io account,
both of which only you can create. See `STATUS.md`'s "Shared web app
pivot" section for the exact remaining steps, and the plan doc
(`.claude/plans/well-i-realized-that-goofy-platypus.md`) for the full
setup commands.

### Dev tooling

```
poe check       # ruff format --check + ruff check + ty check - verify only
poe fmt         # ruff format . - actually rewrites
poe lint-fix    # ruff check --fix .
```

## The email pipeline (legacy, still running - see "Why two systems?" above)

Watches a Gmail inbox for StreetEasy/Zillow/RentHop/NakedApartments
alert emails, filters on price/beds/availability window, and emails
you + your girlfriend when a match clears. No taste/style scoring in
this path (that idea was superseded by the web app's AI scoring above).

To check its *actual* current local setup state at any point:

```
python -m apt_agent.check_setup
```

This verifies real state on disk (credentials present? config still
has placeholder emails? git remote configured?) rather than relying on
memory. It can't check GitHub Secrets or your alert-site subscriptions
though - no way to verify those from your local machine.

### One-time setup

1. **Create the alert-receiving inbox.** Use an existing Gmail or make a
   fresh one just for this. Go to each site and set up saved-search email
   alerts pointed at it, with filters *wider* than your real target (the
   agent narrows things down - a wider net catches more good options).

2. **Google Cloud OAuth credentials:**
   - https://console.cloud.google.com/ -> new project
   - Enable "Gmail API"
   - Credentials -> Create Credentials -> OAuth client ID -> Desktop app
   - Download JSON, save as `credentials.json` in this folder

3. **Authorize:**
   ```
   python -m apt_agent.gmail_auth
   ```
   Browser opens, log into the alert-receiving Gmail, approve. This
   writes `token.json`, reused on future runs.

4. **Edit `config.yaml`:**
   - `search.price_min` / `price_max` - your real range
   - `search.earliest_move_in` / `latest_move_in` - already set to your
     Sep 1 - Oct 3 window, adjust if it changes
   - `notify.recipients` - your two email addresses
   - `notify.from_address` - must be the same address you authorized in
     step 3 (Gmail API send only works as the authorized account)

### Run it once manually to test

```
python -m apt_agent.main
```

Check the console output - it'll tell you what got fetched, filtered,
or alerted on.

### Deploy: GitHub Actions (public repo, free)

This runs the agent on GitHub's schedule instead of your own machine -
no laptop needs to stay on. Public repo = unlimited free minutes; your
actual secrets (OAuth creds, email addresses) never live in the repo
itself, only in encrypted GitHub Secrets. Already deployed and running
- these steps are for reference/reconstruction, not first-time setup.

**Steps:**

1. Push this project to a **public** GitHub repo. `.gitignore` already
   excludes `credentials.json` and `token.json`.

2. Repo -> Settings -> Secrets and variables -> Actions -> "New
   repository secret." Add: `GMAIL_CREDENTIALS_JSON`, `GMAIL_TOKEN_JSON`,
   `NOTIFY_RECIPIENTS`, `NOTIFY_FROM_ADDRESS`.

3. `.github/workflows/poll.yml` runs on a variable-frequency schedule
   (every 15 min 7am-11pm ET, every 30 min overnight) and reconstructs
   the two JSON secrets at runtime. `.github/workflows/heartbeat.yml`
   sends a daily "agent is alive" summary.

4. **OAuth consent screen must be "Production" status** (Google Cloud
   Console -> APIs & Services -> OAuth consent screen) - apps left in
   "Testing" get their refresh token revoked after 7 days.

5. If a run fails, `notify_failure.py` sends an automatic "run failed"
   email - GitHub itself won't tell you otherwise.

### Known limitations (by design)

- **Field extraction is regex-based** against the alert email snippet
  (page fetches 403 on both StreetEasy and Zillow) - will miss fields
  on some listings.
- **Address dedup is best-effort** - catches common cross-posting
  cases, not a real address parser.
- **No taste/style filtering, no delisting detection, no weekly
  digest** - all deferred; may resurface as web app features instead
  of email additions if picked back up (see `ROADMAP.md` Phase 3).
