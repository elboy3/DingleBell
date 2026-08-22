# CLAUDE.md - Project Context

Read this before making any product or architecture decision on this
repo. If you're a Claude session picking this up fresh, this file plus
`DECISIONS.md`, `ROADMAP.md`, and `STATUS.md` should get you fully
oriented in one pass.

## What this is

Two things, in one repo, at different points in their life:

1. **The shared apartment-review web app (`webapp/`) - current focus.**
   A small FastAPI app where the two end users browse a shared,
   persistent, ranked feed of Brooklyn apartment listings: rate them
   individually (1-5 stars), leave comments, jointly hide ones they're
   done with, see upcoming open houses, and see an AI taste-match score
   computed automatically for each listing. Fed by an interactive
   browser-driven scan (see "Ingestion" below), not a cron job.
2. **The original Gmail-alert pipeline (`apt_agent/`) - deprioritized,
   still running.** Watches a Gmail inbox for StreetEasy/Zillow/etc.
   alert emails and emails the two users when a hard-filtered match
   appears, on a GitHub Actions cron. Left running as-is in case
   Zillow's alert cadence turns out to be worth revisiting later - not
   actively developed, not removed.

**If you're only going to read one section below to understand why
there are two systems here, read "The pivot" below.**

## Who this is for, and why it matters

Built for two people (Elliott + Madison) apartment-hunting in Brooklyn
on a real deadline - their current lease ends end of September 2026,
and manual searching hadn't surfaced much. This is not a toy project
or a casual side-experiment: **finding the right apartment on this
timeline matters a lot to them.** Treat reliability and correctness
with commensurate seriousness.

## Hard constraints (do not relax without the user confirming)

- Move-in window: **Sep 1 - Oct 3, 2026** (2 wk flex early, 1-2 day flex
  late). Encoded in `config.yaml` -> `search.earliest_move_in` /
  `latest_move_in`. Still used as a hard filter (`apt_agent/filters.py`),
  including for the `would_alert` stat browser_import.py reports.
- Price range, beds/baths minimums: also in `config.yaml`, user-owned,
  don't guess or change these.

## The pivot (read this if anything below seems to contradict itself)

Phase 1 (the email pipeline) was built and deployed first, on the
assumption that speed - being first to see a new listing - was the
main thing worth optimizing. Real-world testing (2026-08-20/22) showed
that assumption was wrong on two counts: StreetEasy doesn't actually
send real-time per-listing alerts (only a few thin "recommendations"
digests a day), and the emails are missing photos and most detail
anyway. Separately, it turned out the user's real authenticated
browser session can load StreetEasy's full search-results page
directly (via the `browser-use` MCP plugin), bypassing the anti-bot
wall that blocks anonymous scraping - a much richer data source than
email ever was.

More importantly, the user's actual stated problem turned out not to
be speed at all: *"not re-evaluating the same apartments over and
over, not holding rankings in our heads, and letting both of us react
to listings async... without always having to text back and forth in
real time."* That's a shared-state/collaboration problem, not a
latency problem - hence the pivot to a persistent shared web app
instead of faster/smarter emails. **Goal ordering below has been
updated accordingly - speed is explicitly no longer a priority.** Full
story: `DECISIONS.md` (search "Pivot from email alerts") and
`.claude/plans/well-i-realized-that-goofy-platypus.md`.

## Goal ordering (matters for design decisions) - updated post-pivot

1. **Breadth of discovery** - surface listings they wouldn't have found
   through manual searching. Unchanged from Phase 1.
2. **Shared, persistent, asynchronous review** - both people see the
   same ranked set, can react on their own time, nothing needs to be
   re-evaluated once one person has already looked at it. This
   replaced "alert as fast as possible" as goal #2.
3. Speed/real-time alerting is **explicitly not a goal anymore.** Don't
   optimize for it, don't add urgency-driven complexity (real-time
   push, aggressive polling, etc.) without the user asking for it back.

This is explicitly **not** a leisurely browsing tool either, though -
deadline pressure (end of Sep 2026) still means the web app needs to
actually be usable and hosted somewhere both phones can reach, not a
perpetual work-in-progress.

## Current focus: the shared web app pivot

Status as of 2026-08-22: schema extended, `webapp/` built and verified
locally end-to-end (feed/rating/comment/hide/open-houses/identity), the
browser-scan ingestion workflow formalized as a project skill, and AI
scoring working via the scanning session's own vision (no API key
needed - see "The pivot within the pivot" below). **Not yet hosted
anywhere** (no Turso/Fly.io accounts set up yet), and the taste profile
is in progress (user has started sending liked StreetEasy links).
See `STATUS.md`'s "Shared web app pivot" section for the live
checklist of what's left.

**Phase 2.5 (interactive SMS/texting agent), previously designed in
`ROADMAP.md`/`DECISIONS.md`, is superseded by this pivot** - the user
chose a web app over a texting interface. Its design reasoning is left
in `DECISIONS.md` as historical record (don't build it), not as a
pending plan.

## Architecture summary - shared web app (see DECISIONS.md for full reasoning)

- **FastAPI + Jinja2 server-rendered templates, no JS build step**
  (`webapp/`) - the interactions are small CRUD actions for 2 known
  users on a small dataset; no SPA framework needed. htmx is a
  documented future upgrade if plain-form page reloads feel clunky,
  not built yet.
- **Ingestion via an authenticated browser scan, not a cron job.**
  The `browser-use` MCP plugin drives the user's real, already-logged-in
  Brave/Chrome session to load StreetEasy's saved-search results page
  directly - this bypasses the PerimeterX wall that blocks anonymous
  scraping, because it's a real user's own browser loading a page
  they're entitled to see, not automated evasion. Formalized as
  `.claude/skills/scan-streeteasy/SKILL.md` + `apt_agent/browser_scan/
  extract.js` (DOM extraction, JS) + `apt_agent/browser_scan_helpers.py`
  (field parsing, Python) + `apt_agent/browser_import.py` (persists
  into `listings.db`, dedups, never sends email). This only works
  interactively (drives a live local browser) - run whenever someone
  asks, not on a schedule.
- **Pacing matters even with a real authenticated session.** A tight
  loop of 13 rapid sequential page loads tripped PerimeterX; a single
  organic load didn't. Mitigated with `PAGE_PACING_SECONDS = 20` and
  `MAX_PAGES_PER_SESSION = 5` in `browser_scan_helpers.py` - resuming a
  scan across sessions is safe regardless, since `already_seen()` skips
  anything already imported.
- **One shared `ListingStore` (`apt_agent/store.py`), three consumers**:
  the email pipeline's `main.py`, `browser_import.py`, and `webapp/`.
  Extended (not replaced) with `listing_reactions` (per-user rating +
  comment), a shared `hidden`/`hidden_by`/`hidden_at` flag (a joint,
  reversible decision - not per-user, unlike rating), `ai_score`/
  `ai_reasoning`/`ai_profile_version`, and `open_house_raw`/
  `open_house_date`.
- **AI taste-match scoring: the scanning session scores it directly,
  no API key required.** The Claude Code session doing the interactive
  browser scan already has vision and is already looking at the
  results page - it judges each new listing's photo (via a page
  screenshot) against `taste_profile.md` and sets `ai_score`/
  `ai_reasoning` directly in the JSON handed to `browser_import.py`
  (see `.claude/skills/scan-streeteasy/SKILL.md` step 7). No Anthropic
  API call needed for this, the primary path. `webapp/scoring.py`
  (Claude-vision-via-API-key) is kept only as a **secondary, optional
  fallback** for listings that arrive without a pre-computed score -
  every failure mode there (no photo, fetch failure, API error, bad
  response) returns `(None, None)` and never blocks ingestion, matching
  `filters.py`'s "unknown field, don't block on it" pattern.
  `webapp/rescore.py` is a manual backfill command using that fallback
  path, for un-scored or stale-profile listings.
- **Ranking is two separate, non-destructive mechanisms** - explicit
  shared hide (reversible via `/hidden`) for "we're done with this
  one," and a live, adjustable sort/filter (AI score, or min-of-both
  -ratings - deliberately MIN not average, so one person's dislike
  isn't smoothed over) for "declutter the view." Neither one silently
  discards data.
- **Lightweight identity, no passwords.** `/whoami` sets an unsigned
  cookie for "elliott" or "madison" - a tampered cookie's worst case is
  a misattributed rating, not a security problem, for exactly 2 known
  users.
- **Planned hosting (not done yet): Fly.io + Turso (libSQL).** Turso's
  Python client is designed as a near-drop-in for `sqlite3`, so
  `store.py`'s connection logic would change in one place, in remote
  mode (no embedded-replica sync complexity needed at this traffic
  level). See the plan doc for the concrete setup steps.

## Architecture summary - email pipeline (deprioritized, left running)

- **Ingestion via Gmail alert emails**, not direct scraping. Avoids
  anti-bot/ToS problems for this specific pipeline (the browser-scan
  approach above is a different, deliberate exception - see its
  reasoning in `DECISIONS.md`, it's not a contradiction).
- **Deployed on GitHub Actions, public repo, variable-frequency cron**
  (`.github/workflows/poll.yml`, `heartbeat.yml`) - unchanged since
  Phase 1, still running.
- **Gmail query deliberately avoids `in:inbox`/`is:unread`** - this
  account has a pre-existing filter that auto-archives StreetEasy mail
  (missing it entirely under `in:inbox`), and `is:unread` is fragile
  against a human opening an alert email. Relies on `newer_than:1d` +
  `ListingStore.already_seen()` instead. See `config.yaml`'s inline
  comment and `DECISIONS.md`.
- **Listing detail comes from the email snippet, not a page fetch** -
  StreetEasy/Zillow 403 on direct page fetches. `extract_from_email_snippet()`
  in `listing_parser.py`.
- **Daily heartbeat + dry-run mode** unchanged from Phase 1.

## File map

### Shared web app (current focus)
| File | Purpose |
|---|---|
| `webapp/app.py` | FastAPI app instance, mounts all routers |
| `webapp/deps.py` | `get_store()`, `get_current_user()`, `KNOWN_USERS` |
| `webapp/config.py` | Thin wrapper around `apt_agent.main.load_config()` |
| `webapp/ranking.py` | `compute_rating_summary()` - shared min-of-both-ratings logic |
| `webapp/scoring.py` | Claude vision taste-match scoring, graceful degradation |
| `webapp/rescore.py` | `python -m webapp.rescore` - manual backfill for stale/missing AI scores |
| `webapp/routes/feed.py` | `GET /` - sortable/filterable shared feed |
| `webapp/routes/listing.py` | Listing detail + rating/comment/hidden POST actions |
| `webapp/routes/hidden.py` | `GET /hidden` - review + unhide |
| `webapp/routes/open_houses.py` | `GET /open-houses` - deterministic upcoming-open-house view |
| `webapp/routes/identity.py` | `GET`/`POST /whoami` - cookie-based identity |
| `webapp/templates/`, `webapp/static/` | Jinja2 templates + plain CSS, no build step |
| `apt_agent/browser_scan/extract.js` | DOM-extraction script, run via `browser-use`'s `js()` |
| `apt_agent/browser_scan_helpers.py` | Field parsing, batch dedup, pacing/page-cap constants |
| `apt_agent/browser_import.py` | Persists a scan's output into `listings.db`, wires in AI scoring |
| `.claude/skills/scan-streeteasy/SKILL.md` | The actual session procedure for running a scan |
| `taste_profile.md` | **Doesn't exist yet** - written from user's reference photos |

### Email pipeline (deprioritized, still running)
| File | Purpose |
|---|---|
| `apt_agent/gmail_auth.py` | One-time OAuth setup, produces `token.json` |
| `apt_agent/gmail_ingest.py` | Polls Gmail, extracts listing URLs + snippets from alert emails |
| `apt_agent/listing_parser.py` | Email-snippet field extraction (page-fetch path unused, kept for reference) |
| `apt_agent/main.py` | Orchestrates a normal run or a `--dry-run` test |
| `apt_agent/notify.py` | Builds and sends alert/heartbeat/test emails via Gmail API |
| `apt_agent/notify_failure.py` | Sends a "run failed" email, wired to `if: failure()` in the workflow |
| `apt_agent/heartbeat.py` | Daily "agent is alive" summary email |
| `apt_agent/check_setup.py` | `python -m apt_agent.check_setup` - verifies real local setup state |
| `.github/workflows/poll.yml`, `heartbeat.yml` | Scheduled workflows |

### Shared
| File | Purpose |
|---|---|
| `apt_agent/store.py` | The one `ListingStore` - schema, dedup, reactions, hide, AI score, all three consumers |
| `apt_agent/filters.py` | Hard filters: price, beds/baths, move-in window |
| `config.yaml` | User-owned filters/settings (non-secret) + `scoring:` section |
| `listings.db` | Committed to the repo (still true post-pivot for the email side; the webapp will move to Turso once hosted) |
| `pyproject.toml` | `[tool.ruff]`, `[tool.poe.tasks]` - see "Dev tooling" below |
| `requirements.txt` | Runtime deps (what GitHub Actions and the planned Dockerfile install) |
| `requirements-dev.txt` | `ruff`, `ty`, `poethepoet` - not installed by CI |

## Dev tooling

- **`ruff`** for formatting + linting (`pyproject.toml`'s `[tool.ruff]`,
  a simple ruleset: `E`/`F`/`I`/`UP`/`B`). **`ty`** (Astral's type
  checker, mypy-equivalent) for type checking - no special config
  needed. **`poethepoet`** (`poe`) as the task runner, tasks in
  `pyproject.toml`'s `[tool.poe.tasks]`:
  - `poe install` - `uv pip install -r requirements.txt -r requirements-dev.txt`
  - `poe fmt` / `poe fmt-check` - rewrite / verify-only
  - `poe lint` / `poe lint-fix`
  - `poe typecheck`
  - `poe check` - the full verify-only sequence (fmt-check + lint + typecheck), CI/pre-commit style
  - `poe run` - `uvicorn webapp.app:app --reload`
  - `poe rescore` - `python -m webapp.rescore`
- **`uv` for local env/installs** (light adoption - `requirements.txt`/
  `requirements-dev.txt` stay the source of truth, GitHub Actions and
  the planned Dockerfile stay on plain `pip`, not touched). `uv` works
  against the existing `.venv` without needing to recreate it.
- Run `poe check` before considering any Python change done.

## Known limitations / open items

**Shared web app:**
- The optional `webapp/scoring.py` API-key fallback path has never been
  run against the real Claude API (no `ANTHROPIC_API_KEY` was available
  while building it) - its graceful-degradation path is proven, the
  real API call isn't. Doesn't block anything: the primary scoring
  path (the scanning session itself) doesn't depend on it.
- `taste_profile.md` doesn't exist yet - needs reference photos.
- Not hosted anywhere yet - no Turso or Fly.io accounts set up.
- Zillow's real alert-email/page links are wrapped in click-tracking
  redirects the current extraction won't resolve - not fixed since
  there's no real Zillow saved-search sample to match against yet.

**Email pipeline (lower priority, but still true):**
- Address normalization for cross-source dedup is best-effort regex.
- `listing_parser.py` field extraction is regex-based, will miss
  fields on layout changes.
- No delisting detection, no weekly digest (deferred, `ROADMAP.md`
  Phase 3 - may end up as webapp features instead if picked back up).

## Working style notes for future sessions

- The user is technical (Python, Git, cron, OAuth, GitHub Actions,
  and now FastAPI/uv/ruff/ty) - no need to over-explain basic tooling,
  but do explain non-obvious infra tradeoffs.
- Prioritize things that build *confidence the system works* (tested
  end-to-end, not just "should work") over feature breadth, given how
  much this matters to the user and how tight the timeline is.
- **Real-world testing surfaced multiple genuine bugs this project,
  repeatedly** (OAuth scope, unbounded Gmail query, page-fetch 403s,
  invented version pins in `requirements.txt`, an ambiguous type
  signature `ty` caught) - test end-to-end against real data/APIs
  before declaring something done, don't assume it works from reading
  the code.
- Don't add scope beyond what's asked or explicitly agreed in a
  planning conversation - the shared-web-app pivot itself is the
  precedent for how scope changes should happen: driven by the user's
  own stated problem, discussed and confirmed before building, not
  assumed.
