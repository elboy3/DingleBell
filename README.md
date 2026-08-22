# Apartment Agent - Phase 1 (Gmail alert ingestion)

Watches a Gmail inbox for StreetEasy / Zillow / RentHop / NakedApartments
alert emails, extracts listing links, filters on price/beds/availability
window, and emails you + your girlfriend the moment a match clears.

No taste/style scoring yet - that's Phase 2, added on top of this once
it's running.

**Where things stand / what's next:** see `STATUS.md` for the full
running checklist, organized by phase, tagged **[MANUAL]** (only you
can do it) vs **[CLAUDE]** (a Claude session can do it directly). To
check your *actual* current local setup state at any point, run:

```
python -m apt_agent.check_setup
```

This verifies real state on disk (credentials present? config still
has placeholder emails? git remote configured?) rather than relying on
memory. It can't check GitHub Secrets or your alert-site subscriptions
though - no way to verify those from your local machine.

## 1. One-time setup

1. **Create the alert-receiving inbox.** Use an existing Gmail or make a
   fresh one just for this. Go to each site and set up saved-search email
   alerts pointed at it, with filters *wider* than your real target (the
   agent narrows things down - a wider net catches more good options).

2. **Google Cloud OAuth credentials:**
   - https://console.cloud.google.com/ -> new project
   - Enable "Gmail API"
   - Credentials -> Create Credentials -> OAuth client ID -> Desktop app
   - Download JSON, save as `credentials.json` in this folder

3. **Install deps:**
   ```
   uv venv && uv pip install -r requirements.txt -r requirements-dev.txt
   # or: poe install (once the venv exists and poethepoet is installed)
   ```

4. **Authorize:**
   ```
   python -m apt_agent.gmail_auth
   ```
   Browser opens, log into the alert-receiving Gmail, approve. This
   writes `token.json`, reused on future runs.

5. **Edit `config.yaml`:**
   - `search.price_min` / `price_max` - your real range
   - `search.earliest_move_in` / `latest_move_in` - already set to your
     Sep 1 - Oct 3 window, adjust if it changes
   - `notify.recipients` - your two email addresses
   - `notify.from_address` - must be the same address you authorized in
     step 4 (Gmail API send only works as the authorized account)

## 2. Run it once manually to test

```
python -m apt_agent.main
```

Check the console output - it'll tell you what got fetched, filtered,
or alerted on. First run may show 0 if there are no unread alert emails
yet; go trigger one from StreetEasy to confirm the pipeline works
end-to-end.

## 3. Deploy: GitHub Actions (public repo, free, every 5 min)

This runs the agent on GitHub's schedule instead of your own machine -
no laptop needs to stay on. Public repo = unlimited free minutes; your
actual secrets (OAuth creds, email addresses) never live in the repo
itself, only in encrypted GitHub Secrets.

**Steps:**

1. Create a new **public** GitHub repo, push this project to it.
   `.gitignore` already excludes `credentials.json` and `token.json` -
   double check `git status` before your first commit that neither
   shows up as untracked-and-about-to-be-added.

2. Go to the repo -> Settings -> Secrets and variables -> Actions ->
   "New repository secret." Add these four:

   | Secret name | Value |
   |---|---|
   | `GMAIL_CREDENTIALS_JSON` | paste the full contents of your local `credentials.json` |
   | `GMAIL_TOKEN_JSON` | paste the full contents of your local `token.json` (created in step 4 above) |
   | `NOTIFY_RECIPIENTS` | `you@example.com,cricket@example.com` |
   | `NOTIFY_FROM_ADDRESS` | the Gmail address you authorized (must match) |

3. That's it - `.github/workflows/poll.yml` is already set up to run
   every 5 minutes, reconstruct those two JSON files from secrets at
   runtime, and run the agent. Go to the repo's **Actions** tab to watch
   it run, and use "Run workflow" there to trigger a manual test
   immediately instead of waiting for the next 5-min tick.

4. **Important: switch your OAuth consent screen to "Production" status**
   in Google Cloud Console (APIs & Services -> OAuth consent screen).
   Apps left in "Testing" status get their refresh token revoked after
   7 days - your agent would silently die a week in. Production status
   is fine for personal/unverified use, it just shows a one-time
   "unverified app" click-through the first time (which you already
   passed during the `gmail_auth.py` step).

5. If a run fails (bad token, site layout change, etc.), you'll get an
   automatic "run failed" email via `notify_failure.py` - GitHub itself
   won't tell you, so this is the only safety net. Check the Actions
   tab logs to debug.

6. **You'll also get a daily heartbeat email** (`heartbeat.yml`, runs
   once/day at 8am ET) confirming the agent is alive and summarizing
   the last 24h - so silence never has to mean "did it break?"

7. **Before waiting on a real listing, confirm the whole pipeline works**
   by triggering a dry run: go to the Actions tab -> "Apartment Agent
   Poll" -> "Run workflow", or locally: `python -m apt_agent.main --dry-run`.
   This pushes one fake listing through filters/dedup/email and should
   land a clearly-marked TEST email in your inbox within a minute or two.

**Why every 5 min, not faster:** GitHub's own docs note scheduled
workflows are best-effort - tighter schedules (every 1-3 min) get
silently delayed or dropped under platform load.

**Polling schedule design:** the workflow uses variable frequency
instead of one flat interval:
- **7am-11pm ET: every 15 min** - most new listings post during broker
  business hours, plus an evening bump as people list after showings
- **11pm-7am ET: every 30 min** - very little new inventory posts
  overnight, so there's no real benefit to polling faster then

This is expressed as three separate `cron:` entries in `poll.yml`
(GitHub cron is UTC-only, so the comments there show the ET->UTC
conversion). It's already tuned for your Aug 19-early Oct window and
doesn't need adjusting unless the window shifts into November DST.

**The bigger latency lever, before touching polling frequency at all:**
go check each site's own alert settings (StreetEasy, Zillow, etc.) and
confirm saved searches are set to "instant"/"immediate" rather than a
daily digest. If any of them batch their own emails once a day, that's
a far bigger delay than anything in this polling schedule - fix that
first.

### Alternative: run locally instead

If you'd rather test on your own machine first before deploying:

```
*/5 * * * * cd /path/to/apt_agent && /usr/bin/python3 -m apt_agent.main >> agent.log 2>&1
```

## Known limitations (by design, for Phase 1)

- **Listing page fetches are best-effort.** StreetEasy/Zillow actively
  discourage scraping - if you start seeing failed fetches, that's
  expected. The email alert itself often already has price/beds info in
  the snippet (`extract_from_email_snippet` in `listing_parser.py` is a
  fallback path you can wire in instead of fetching the page).
- **Field extraction is regex-based**, not a real HTML parser tuned to
  each site's current markup. It'll miss fields on some listings. Good
  enough to filter obvious mismatches; not perfect.
- **Address dedup is best-effort.** Catches common cross-posting cases
  (St/Street, Ave/Avenue unified) but isn't a real address parser -
  unusual formatting can still slip through as a "new" listing.
- **No taste/style filtering yet.** Everything that passes hard filters
  gets emailed. Once you send over reference photos, Phase 2 adds a
  Claude-scored ranking on top of this same pipeline.
- **No de-listing detection.** If a unit gets rented, you won't get a
  "no longer available" notice - deferred to Phase 3.

See `CLAUDE.md` for full project context, `DECISIONS.md` for why each
architecture choice was made, and `ROADMAP.md` for what's done vs. planned.

## Next up (Phase 2 - not started)

Send me photos of apartments you both liked/disliked -> I turn that into
a taste profile -> wire a `score_listing()` step into `main.py` that
runs Claude vision against each new listing's photos before sending the
alert, and includes a one-line "why this one" in the email.

**Per explicit instruction: don't start this until Phase 1 is confirmed
working reliably in production.**
