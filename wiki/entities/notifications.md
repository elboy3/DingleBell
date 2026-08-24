---
type: entity
source_files: [apt_agent/notify.py, apt_agent/notify_failure.py, apt_agent/heartbeat.py]
status: deprioritized
verified: 2026-08-24
tags: [email-pipeline, gmail, notifications, phase-1, deprioritized]
---

# Notifications (alert / failure / heartbeat emails)

The outbound-email side of the deprioritized Phase 1 email pipeline: sends the actual "new listing" alert emails, a daily "agent is alive" heartbeat, and a "run failed" email when the scheduled poll breaks. All three reuse the same Gmail API OAuth credentials as ingestion (`gmail_auth.get_gmail_credentials()`) rather than a separate SMTP/SES sender. Deprioritized along with the rest of the email pipeline it belongs to - still running on the existing cron, not actively developed, superseded in spirit by the shared web app's own UI (matches/ratings are now seen in-app, not via email).

## Key exports

- `notify.send_alert(listing, notify_cfg)` - builds and sends one email via the Gmail API; the single send path shared by real listing alerts, the dry-run test, and the heartbeat (dispatched on `listing["source"]`).
- `notify._build_message(listing, recipients, from_address, subject_prefix)` - constructs the `MIMEText` message, branching on `source in {"heartbeat", "dry-run", <anything else>}` to pick subject/body content.
- `notify_failure.main()` - `python -m apt_agent.notify_failure` (CLI) - reads `NOTIFY_RECIPIENTS`/`NOTIFY_FROM_ADDRESS`/`GITHUB_RUN_URL` from env, sends a plain "the agent broke, check this run" email.
- `heartbeat.build_heartbeat_listing(stats)` - shapes `store.stats_last_24h()` output into a fake "listing" dict so it can flow through `send_alert()`'s existing machinery.
- `heartbeat.main()` - `python -m apt_agent.heartbeat` (CLI) - loads config, pulls 24h stats from the store, sends the heartbeat email.

## Depends on / used by

- [email-pipeline](../entities/email-pipeline.md)
- [store](../entities/store.md)
- [shared-config](../entities/shared-config.md)
- [github-workflows](../entities/github-workflows.md)

## Notes & gotchas

- `notify.send_alert` is intentionally the *only* email-sending function in the pipeline - heartbeat and dry-run both go through it by constructing a listing-shaped dict with a special `source` value (`"heartbeat"`, `"dry-run"`), rather than each having their own send logic. Adding a new "kind" of notification means adding another `source` branch in `_build_message`, not a new sender.
- `notify_failure.main()` is invoked only via the GitHub Actions workflow's `if: failure()` step (see `github-workflows`), not called from anywhere in the normal Python flow - it reads its config purely from environment variables (no `config.yaml` load), and silently no-ops (prints to stderr, returns) if `NOTIFY_RECIPIENTS`/`NOTIFY_FROM_ADDRESS` aren't set, rather than raising.
- The heartbeat exists specifically so silence is never ambiguous between "nothing new today" and "the agent broke quietly" - it fires daily regardless of whether any listings were seen.
- All three modules reuse `gmail_auth.get_gmail_credentials()`, so a revoked/expired OAuth token breaks alerting, heartbeat, *and* the failure-notification email simultaneously - there's no independent channel to report an auth failure if auth itself is what's broken.

## Related concepts

- [the-two-pivots](../concepts/the-two-pivots.md)
- [two-ingestion-paths](../concepts/two-ingestion-paths.md)
