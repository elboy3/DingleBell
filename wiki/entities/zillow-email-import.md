---
type: entity
source_files: [apt_agent/zillow_email_import.py]
status: active
verified: 2026-08-24
tags: [zillow, ingestion, gmail, active, automated]
---

# Zillow email import (active, automated Zillow ingestion)

A newer, currently **active** and fully automated Zillow-specific ingestion path - separate from and unrelated to the deprioritized Phase 1 Gmail pipeline, despite also using Gmail as its transport. Imports individual rental listings straight from Zillow's `rental-instant-updates@mail.zillow.com` "just listed"/instant-update alert emails, with no browser scan and no interactive session required. Discovered because Zillow's alert sender fires within minutes of a new listing (unlike StreetEasy's thin digests), and each email's plain-text body already has full structured data (price/beds/baths/sqft/address/agent) plus a real listing photo in its HTML body - so no page fetch, redirect-following, or anti-bot workaround is needed at all. Runs unattended on the existing GitHub Actions poll cron.

## Key exports

- `zillow_email_import.main()` - `python -m apt_agent.zillow_email_import` (CLI) - loads config, fetches matching emails, parses them, imports via `browser_import.import_listings()`, prints stats.
- `zillow_email_import.fetch_listings_from_inbox()` - queries Gmail for `QUERY` (`from:rental-instant-updates@mail.zillow.com newer_than:1d`), pulls each matching message's plain-text and HTML bodies, parses every one.
- `zillow_email_import.parse_zillow_email(text, html)` - turns one instant-update email into a list of raw listing dicts (the featured "just listed" property plus every bundled "Other rentals you might like" entry), dropping any block whose link doesn't resolve to a real `zpid` (paid "premium property" placements).
- `zillow_email_import._zpid_from_tracking_url(url)` - decodes the real Zillow property ID out of the `target=` query param of a `click.mail.zillow.com` tracking link, without following the redirect - used to build a stable canonical URL (`zillow.com/homedetails/{zpid}_zpid/`).
- `zillow_email_import._photo_for_zpid(soup, zpid)` - finds a listing's photo by scoping to its enclosing `<table role="group" aria-label="property">` and reading a `background=` attribute (an email-HTML convention), rather than climbing from the link itself.
- `zillow_email_import._BLOCK_RE` - the regex matching one listing block ("For rent[. NEW.]" + price + beds/baths/sqft + address + optional agent + tracking link) shared by both the featured listing and bundled recommendations.

## Depends on / used by

- [browser-import](../entities/browser-import.md)
- [store](../entities/store.md)
- [shared-config](../entities/shared-config.md)
- [github-workflows](../entities/github-workflows.md)

## Notes & gotchas

- **AI scoring is deliberately left `NULL` here** - unlike the browser-scan path, there's no live session watching a cron run to judge a listing photo. Run `poe rescore` (`webapp/rescore.py`, the API-key-fallback scorer) afterward to backfill scores if wanted.
- `_BLOCK_RE`'s two trailing optional groups (extra text after the price like `"| Total monthly price"`, and the bed/bath/sqft line's trailing `"| Pets"`-style amenity tag) were made optional only after a real 2026-08-24 bug: without that, a "just listed" email's own **featured** listing (the literal reason the email was sent) was silently dropped whenever it lacked a trailing amenity tag - not a rare edge case, since bundled "you might also like" entries in the same email happened to always have one, masking the bug. Fixing it and re-running against the full mailbox recovered 42 previously-missed listings.
- A listing agent and a resolvable `zpid` are both optional/best-effort in the regex - paid "premium property" placements (observed pointing at a different city than the actual saved search) have neither and get filtered out downstream by the `if not zpid: continue` check in `parse_zillow_email`.
- The visible email link is always a `click.mail.zillow.com` tracker, never a direct Zillow URL - `_zpid_from_tracking_url` must decode the percent-encoded `target=` param rather than substring-matching the raw href, which contains `"zpid_target%2F..."` not `"zpid_target/..."`.
- `_photo_for_zpid` scopes by the enclosing property `<table>`, not by climbing from the `<a>` tag itself, because the photo lives elsewhere in the same table, not as a sibling/descendant of the link.
- This module is the primary, day-to-day active Zillow ingestion path going forward; `apt_agent/zillow_scan/` (browser-driven Zillow SRP scanning) is a separate, backfill-only path for historical listings that predate this email pipeline - see `zillow-ingestion-evolution`.

## Related concepts

- [zillow-ingestion-evolution](../concepts/zillow-ingestion-evolution.md)
- [two-ingestion-paths](../concepts/two-ingestion-paths.md)
- [ai-taste-scoring](../concepts/ai-taste-scoring.md)
