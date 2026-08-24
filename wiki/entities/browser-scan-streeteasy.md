---
type: entity
source_files: [apt_agent/browser_scan_helpers.py, apt_agent/browser_scan/extract.js, .claude/skills/scan-streeteasy/SKILL.md]
status: active
verified: 2026-08-24
tags: [ingestion, browser-scan, streeteasy, anti-bot, ai-scoring]
---

# Browser-scan ingestion: StreetEasy

## Purpose

The primary, currently-active way new StreetEasy listings get into `listings.db`. Because StreetEasy has no real per-listing email alerts (only thin daily "recommendations" digests, missing photos/detail) and blocks anonymous scraping with a PerimeterX anti-bot wall, this pipeline instead drives the user's own real, already-logged-in browser session (via the `browser-use` MCP plugin) to load the saved-search results page directly. That's legitimate access - a real user's browser loading a page they're entitled to see - not automated evasion of the wall. It only works interactively (a live local browser), so it runs as a project skill invoked whenever someone asks ("scan StreetEasy"), never on a schedule. `extract.js` does raw DOM extraction inside the browser session; `browser_scan_helpers.py` does the actual field parsing as ordinary, testable Python back in the repo.

## Key exports

- `apt_agent/browser_scan/extract.js` - runs via `browser-use`'s `js()` helper inside the authenticated session; finds StreetEasy building/unit links, climbs the DOM to the nearest ancestor containing both `$` and `bed`/`studio` text, and returns raw cards (`url`, `addressText`, `cardText`, `photo`) with zero field parsing.
- `PAGE_PACING_SECONDS = 20`, `MAX_PAGES_PER_SESSION = 5` (`browser_scan_helpers.py`) - anti-bot mitigation constants, shared/reused (not duplicated) by the Zillow scan too.
- `parse_card(raw_card) -> dict` - regex-parses one raw card's `cardText` into price/beds/baths/sqft/neighborhood/agent/open-house fields.
- `parse_page_json(raw_cards) -> list[dict]` - maps `parse_card` over one page's raw cards.
- `_parse_open_house_date(raw) -> str | None` - resolves a raw open-house string (e.g. "Aug 23") to an ISO date, assuming the nearest future occurrence; returns `None` rather than blocking ingestion if unparseable.
- `matches_config_bounds(listing, cfg) -> bool` - re-checks a listing's price/beds/baths against `config.yaml`'s search bounds, treating any unset field as non-blocking; exists because Zillow's pagination (not StreetEasy's) has been seen to silently drop filter state, and this helper is shared/reused there.
- `dedupe_within_batch(listings) -> list[dict]` - dedups by URL within one scan session, keeping first occurrence (StreetEasy's own sort can shift results mid-pagination).
- **Skill procedure** (`.claude/skills/scan-streeteasy/SKILL.md`): confirm the saved-search URL and check `needs_backfill_listings()` first; for each page up to `MAX_PAGES_PER_SESSION` (or until a page returns zero cards), navigate, wait for load, run `extract.js`, optionally screenshot (if `taste_profile.md` exists), sleep `PAGE_PACING_SECONDS` before the next page, and stop immediately (no retry) if a page looks like a block page; then run `parse_page_json` + `dedupe_within_batch`; then score each new listing directly against `taste_profile.md` using the scanning session's own vision on the page screenshot (no API call); write the final JSON to the scratchpad and run `python -m apt_agent.browser_import <path>`; report page coverage and import stats back to the user.

## Depends on / used by

- [browser-import.md](browser-import.md)
- [store.md](store.md)
- [shared-config.md](shared-config.md)
- [scoring.md](scoring.md)

## Notes & gotchas

- **Anti-bot trip is confirmed, not theoretical**: a tight loop of 13 rapid sequential page-to-page navigations tripped PerimeterX on page 2 during this feature's initial build, even against a real authenticated session - a single organic page load did not. `PAGE_PACING_SECONDS`/`MAX_PAGES_PER_SESSION` exist specifically to avoid re-triggering that; the skill explicitly says "do not skip" the pacing sleep.
- Resuming a scan across multiple sessions is always safe regardless of the page cap, since `ListingStore.already_seen()` skips anything already imported - the skill leans on this rather than tracking progress between runs itself.
- If a page's title looks like a block page ("Access to this page has been denied" or similar), the skill's instruction is to stop immediately and not retry in the same session - same non-negotiable rule DECISIONS.md documents recurring elsewhere in this project (see [browser-scan-zillow.md](browser-scan-zillow.md)).
- AI scoring here needs **no Anthropic API key** - the Claude Code session running the scan already has vision and is already looking at the results-page screenshot, so it judges each new listing's photo against `taste_profile.md` directly and sets `ai_score`/`ai_reasoning` in the JSON handed to `browser_import.py`. `webapp/scoring.py`'s API-key path is a secondary fallback only, used for listings that arrive unscored.
- Photo galleries: clicking through StreetEasy's photo lightbox via synthetic clicks never worked reliably (tried coordinate correction, tab activation, keyboard events) - the working approach, if a listing's full photo set is ever needed beyond the search-card thumbnail, is extracting `<img>` URLs directly from the DOM and downloading/viewing them, not driving the lightbox UI.
- `extract.js`'s card-finding logic (climbing from a building/unit link to find a `$`+bed/studio ancestor, then climbing further for a photo `<img>`) is markup-dependent - if StreetEasy changes its card layout, this selector logic is the first thing to re-check, same caveat as the email pipeline's snippet parsing.
- Field parsing is deliberately kept out of `extract.js` and lives in `browser_scan_helpers.py` instead, purely so it's versioned, testable Python rather than one-off code typed into a `browser_exec` call each session.

## Related concepts

- [zillow-ingestion-evolution.md](../concepts/zillow-ingestion-evolution.md)
- [two-ingestion-paths.md](../concepts/two-ingestion-paths.md)
- [ai-taste-scoring.md](../concepts/ai-taste-scoring.md)
