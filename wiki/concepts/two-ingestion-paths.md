---
type: concept
status: active
verified: 2026-08-24
tags: [ingestion, streeteasy, zillow, architecture]
---

# Two ingestion paths (StreetEasy vs. Zillow)

## Summary

StreetEasy and Zillow need fundamentally different ingestion techniques. StreetEasy has no real per-listing alert emails at all, so it depends entirely on an interactive, authenticated browser scan. Zillow has two paths: a fully automated, unattended email pipeline ([zillow-email-import](../entities/zillow-email-import.md)) that is the primary, day-to-day path, plus a browser scan ([browser-scan-zillow](../entities/browser-scan-zillow.md)) that exists only to backfill listings that predated the email pipeline. Every listing's `source` column tags which of these four paths produced it.

## Details

**StreetEasy - browser scan only.** StreetEasy's saved-search alerts turned out to be thin daily "recommendations" digests, not real-time per-listing alerts, and even those emails lack photos and detail (see [the-two-pivots](the-two-pivots.md)). There is no automated-email alternative for StreetEasy in this project. [browser-scan-streeteasy](../entities/browser-scan-streeteasy.md) is therefore the only ingestion path for it: an interactive session drives the user's real, already-logged-in browser via the `browser-use` MCP plugin to load the saved-search results page directly, bypassing the PerimeterX wall that blocks anonymous scraping (legitimate access, not evasion, since it's the user's own browser loading a page they're entitled to see). Because it drives a live local browser, it can only ever run interactively - never on the GitHub Actions cron - so it's formalized as a project skill (`.claude/skills/scan-streeteasy/SKILL.md`) run whenever someone asks.

**Zillow - two paths, one primary, one backfill-only.** Zillow is different: it has a real `rental-instant-updates@mail.zillow.com` sender that fires within minutes of a new listing, individually, with full structured data (price/beds/baths/sqft/address/agent) already in the plain-text body and a real photo in the HTML body - no page fetch, redirect-following, or browser needed at all. [zillow-email-import](../entities/zillow-email-import.md) (`apt_agent/zillow_email_import.py`) exploits this and runs unattended on the existing GitHub Actions poll cron - it is the **primary, active, day-to-day** Zillow ingestion path, and the first fully automated ingestion path in the whole project. But it only catches listings going forward from when it was set up; it can't retroactively see whatever was already on the market before then, since Zillow doesn't resend old alerts. [browser-scan-zillow](../entities/browser-scan-zillow.md) fills that gap - explicitly scoped as **backfill-only**, not a competing day-to-day path, to avoid confusion with the email importer. See [zillow-ingestion-evolution](zillow-ingestion-evolution.md) for how its extraction technique matured and why 100% backfill coverage isn't achievable.

**The `source` tagging convention.** Every row in `listings.source` records which path produced it: `streeteasy` / `streeteasy-browser-scan` (from the browser scan skill, distinguishing it from the deprioritized email pipeline's own StreetEasy alerts), `zillow-email` (from `zillow_email_import.py`), and `zillow-browser-scan` (from the Zillow backfill scan). Both browser-scan skills explicitly set this field themselves rather than relying on [browser-import](../entities/browser-import.md)'s default. All four paths write into the single shared `ListingStore` (see [store](../entities/store.md)), so `already_seen()`-based URL dedup is what makes re-running any of them, or running them in any order, safe.

## Related entities

- [email-pipeline](../entities/email-pipeline.md)
- [zillow-email-import](../entities/zillow-email-import.md)
- [browser-scan-streeteasy](../entities/browser-scan-streeteasy.md)
- [browser-scan-zillow](../entities/browser-scan-zillow.md)
- [browser-import](../entities/browser-import.md)
- [store](../entities/store.md)

## Sources

CLAUDE.md ("Two ingestion paths now - StreetEasy needs a browser, Zillow doesn't"); DECISIONS.md ("Zillow instant-update emails: a second, fully-automated ingestion path"); wiki/entities/zillow-email-import.md, wiki/entities/browser-scan-zillow.md, wiki/entities/browser-import.md.
