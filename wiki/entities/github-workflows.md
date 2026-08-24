---
type: entity
source_files: [.github/workflows/poll.yml, .github/workflows/heartbeat.yml]
status: active
verified: 2026-08-24
tags: [github-actions, cron, email-pipeline, zillow, automation]
---

# GitHub Actions workflows

## Purpose

The two scheduled workflows that run the project's fully-automated (non-browser) ingestion and health-check paths on a public GitHub repo. `poll.yml` runs the original Gmail-alert email pipeline plus the newer, fully-automated Zillow instant-update email import on a variable-frequency cron; `heartbeat.yml` sends a once-daily "agent is alive" confirmation email. Both are unchanged in shape since Phase 1 of the project and still running, even though the email pipeline itself is deprioritized relative to the browser-scan paths.

## Key exports

- `poll.yml` - triggers: cron every 15 min during ET daytime/evening (7am-11pm, `*/15 11-23,0-2 UTC`) and every 30 min overnight (`*/30 3-10 UTC`), plus a manual `workflow_dispatch` with a `dry_run` input. Steps: checkout, install `requirements.txt`, reconstruct `credentials.json`/`token.json` from repo secrets, run `python -m apt_agent.main` (the email-alert pipeline, optionally `--dry-run`), then run `python -m apt_agent.zillow_email_import` (skipped on dry-run) to pull Zillow's per-listing instant-update emails straight into `listings.db` for the swipe app, then commit `listings.db` back to the repo if it changed, then (on any step failure) run `python -m apt_agent.notify_failure`.
- `heartbeat.yml` - triggers: cron once daily at 12:00 UTC (8am ET), plus manual `workflow_dispatch`. Steps: checkout, install deps, reconstruct Gmail OAuth files, run `python -m apt_agent.heartbeat`.

## Depends on / used by

- [email-pipeline.md](email-pipeline.md)
- [zillow-email-import.md](zillow-email-import.md)
- [notifications.md](notifications.md)
- [store.md](store.md)

## Notes & gotchas

- `poll.yml` only triggers on `schedule`/`workflow_dispatch`, deliberately not on normal `push` - the workflow's own DB-commit step pushes to the repo, and reacting to pushes would create a recursive trigger loop.
- The DB-commit step (`git add listings.db` -> commit -> `git pull --rebase` -> `push`) is what makes cross-run dedup persistence work at all: GitHub Actions runners are ephemeral, so without committing `listings.db` back after every run, dedup state would reset each run and the same listings would get re-alerted repeatedly (see DECISIONS.md, "listings.db is committed back to the repo").
- Cron times are UTC-only (GitHub Actions cron has no timezone support) - the inline comments do the ET->UTC conversion by hand and explicitly note NY is UTC-4 (EDT) through early November, covering the whole 6-week move-in window with no DST-adjustment step needed.
- The 15-min/30-min split (rather than a flat interval) is a deliberate cost/signal tradeoff: most new listings post during broker business hours plus an evening bump, and the real bottleneck is each site's own alert-email cadence, not the polling interval itself - this cuts total runs roughly 3x vs. flat 5-min polling with no meaningful loss of real-world speed (see DECISIONS.md, "Variable-frequency polling schedule").
- The repo being **public** (not private) is why this cron budget is affordable at all: private repos get only 2,000 free Actions minutes/month, which a 15-min interval for 6 weeks would burn through fast (~20,000 runs/month); public repos get unlimited free minutes, and the repo has no sensitive content since all real secrets (OAuth creds, recipient emails) live in encrypted GitHub Secrets, never in tracked files.
- The Zillow email-import step is the **first fully automated ingestion path** in this project - unlike both browser-scan skills, it needs no interactive session or live browser at all (pure Gmail API + regex), which is exactly why it's the one ingestion method that could be added to this cron in the first place.
- `poll.yml`'s failure-notification step (`notify_failure`) is wired to `if: failure()` specifically so a broken run doesn't fail silently - consistent with the project's broader "silence must not be ambiguous between 'nothing new' and 'something's broken'" reasoning behind the heartbeat email existing at all.

## Related concepts

- [two-ingestion-paths.md](../concepts/two-ingestion-paths.md)
- [zillow-ingestion-evolution.md](../concepts/zillow-ingestion-evolution.md)
