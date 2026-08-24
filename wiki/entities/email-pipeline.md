---
type: entity
source_files: [apt_agent/main.py, apt_agent/gmail_auth.py, apt_agent/gmail_ingest.py, apt_agent/listing_parser.py]
status: deprioritized
verified: 2026-08-24
tags: [email-pipeline, gmail, ingestion, phase-1, deprioritized]
---

# Email pipeline (Phase 1 - Gmail alert ingestion)

The original ingestion path for this project: poll a Gmail inbox for StreetEasy/Zillow/RentHop/NakedApartments listing-alert emails, extract listing URLs and a nearby text snippet, apply hard filters, dedup, and email the two users when something passes. Built and deployed first on the assumption that speed (being first to see a new listing) was the thing worth optimizing. Real-world testing (2026-08-20/22) showed that assumption was wrong - StreetEasy doesn't send true real-time per-listing alerts (only thin daily "recommendations" digests), and the emails are missing photos and most detail anyway. **Explicitly deprioritized**: still running on the existing GitHub Actions cron, but not actively developed, superseded by the authenticated browser-scan (StreetEasy) and `zillow_email_import.py` (Zillow) ingestion paths. Left running rather than removed in case Zillow's alert cadence turns out worth revisiting later.

## Key exports

- `main.load_config(path="config.yaml")` - loads `config.yaml`, then overlays `NOTIFY_RECIPIENTS`/`NOTIFY_FROM_ADDRESS` env vars so secrets don't sit in the public repo's plaintext config.
- `main.process_listing(listing, cfg, store)` - runs hard filters, cross-source address dedup, saves to the store, sends an alert email if it passes; returns whether an alert was sent.
- `main.run_once(cfg)` - the normal per-poll flow: fetch new alert emails, skip already-seen URLs, extract fields from the email snippet, process each listing.
- `main.run_dry_run(cfg)` - pushes one hardcoded fake listing through `send_alert()` only, bypassing Gmail and filters entirely, to confirm OAuth/email delivery end-to-end.
- `main.main()` - CLI entry point (`python -m apt_agent.main [--dry-run]`), the thing the GitHub Actions cron actually invokes.
- `gmail_auth.get_gmail_credentials()` - loads/refreshes `token.json`, or runs the interactive OAuth flow against `credentials.json` if no valid token exists.
- `gmail_ingest.fetch_new_alert_urls(query, mark_as_read=True)` - queries Gmail, extracts `(url, snippet)` pairs from every matching message, dedups across messages, optionally clears the `UNREAD` label.
- `gmail_ingest.extract_listings_with_snippets(html)` - pulls listing-detail URLs out of an alert email body via known per-source URL patterns, pairing each with nearby text (climbing up the DOM from the anchor, or a raw-text window as a fallback for non-`<a>` links).
- `listing_parser.extract_from_email_snippet(snippet_text, url)` - regex-based price/beds/baths/availability extraction from the alert email's own text; the actual field source used by `main.run_once()`.
- `listing_parser.fetch_listing_page(url)` / `parse_listing_html(html, url)` - a page-fetch alternative to the snippet path, present but **unused** by `main.py` since StreetEasy/Zillow 403 on direct anonymous fetches.

## Depends on / used by

- [store](../entities/store.md)
- [shared-config](../entities/shared-config.md)
- [notifications](../entities/notifications.md)
- [github-workflows](../entities/github-workflows.md)
- [check-setup](../entities/check-setup.md)

## Notes & gotchas

- `--dry-run` sends one fake listing through the full alert-email path unconditionally (ignores filters) - the way to confirm OAuth + filters + email delivery work before waiting on a real alert.
- The Gmail query in `config.yaml` deliberately avoids `in:inbox` (this account has a pre-existing filter that auto-archives StreetEasy mail, so `in:inbox` would miss it entirely) and avoids `is:unread` (fragile if a human opens an alert email first). Relies on `newer_than:1d` + `store.already_seen()` for correctness instead - see `gmail_ingest.fetch_new_alert_urls`'s `mark_as_read` behavior and `config.yaml`'s inline comment.
- Listing detail comes from the **email snippet**, not a page fetch - `listing_parser.fetch_listing_page`/`parse_listing_html` exist but are dead code in the real flow, kept only as reference/fallback documentation, because StreetEasy/Zillow return 403 on direct anonymous fetches.
- `gmail_auth.SCOPES` requests `gmail.readonly`, `gmail.send`, and `gmail.modify` - the `modify` scope specifically exists to clear `UNREAD` off processed alert emails so they aren't reprocessed; a real bug (missing this scope) was found and fixed during initial deployment (see `STATUS.md` log, 2026-08-19/20).
- `gmail_ingest`'s URL-extraction regexes are hardcoded per-source (`LISTING_URL_PATTERNS`) and will silently miss any source or URL-shape not already listed there.
- `listing_parser.extract_from_email_snippet` never fills `address` (usually needs the page or a source-specific regex tuned to that email's layout) - a known, accepted gap, not a bug to chase given the pipeline's deprioritized status.
- All regex-based field extraction (price/beds/baths/availability) is best-effort and will silently return `None` on any layout it wasn't tuned against - `filters.py` treats unknown/`None` fields as "let it through," so this pipeline biases toward false positives, not false negatives, on parse failure.

## Related concepts

- [the-two-pivots](../concepts/the-two-pivots.md)
- [two-ingestion-paths](../concepts/two-ingestion-paths.md)
- [zillow-ingestion-evolution](../concepts/zillow-ingestion-evolution.md)
