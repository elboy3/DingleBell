---
type: entity
source_files: [apt_agent/zillow_scan_helpers.py, apt_agent/zillow_scan/extract.js, apt_agent/zillow_scan/extract_next_data.js, .claude/skills/scan-zillow/SKILL.md]
status: active
verified: 2026-08-24
tags: [ingestion, browser-scan, zillow, anti-bot, backfill, next-data]
---

# Browser-scan ingestion: Zillow (historical backfill)

## Purpose

A backfill-only tool for Zillow listings that existed *before* the automated `zillow_email_import.py` pipeline was set up - that pipeline already catches every new Zillow listing going forward, unattended, on the GitHub Actions cron, so this scan only matters for the pre-existing historical backlog. Like the StreetEasy scan, it drives the user's real authenticated browser session via the `browser-use` MCP plugin (same "legitimate access, not evasion" reasoning) and only works interactively, one neighborhood per session. Two extraction techniques exist: the original DOM-scraping approach (`extract.js`) and a since-discovered, now-primary technique that reads Zillow's own `__NEXT_DATA__` JSON blob (`extract_next_data.js`) - the latter is both more complete and fixed a confirmed photo-ordering bug in the former.

## Key exports

- `apt_agent/zillow_scan/extract_next_data.js` - **primary extraction technique**. Reads the `__NEXT_DATA__` script tag's `props.pageProps.searchPageState.cat1.searchResults.listResults` - the same structured JSON Zillow's own React app hydrates from (address, `unformattedPrice`, beds, baths, sqft, `availabilityDate`, `brokerName`, `imgSrc`, and full `carouselPhotosComposable.photoData` photo-key list). Server-rendered at initial load, so it has no client-hydration timing race. Returns `null` if the tag is missing/restructured, signaling a fallback to `extract.js`.
- `apt_agent/zillow_scan/extract.js` - **fallback only**. DOM-scrapes `article.property-card` text/photo. Fixed to take the *second* matching `img[src*="zillowstatic"]`, not the first (see photo-order bug below).
- `parse_next_data_result(raw) -> dict | None` (`zillow_scan_helpers.py`) - structures one `__NEXT_DATA__` result; returns `None` for "relaxed"/building-aggregator entries (lat/long standing in for `zpid`, a `/b/...` or `/apartments/...` URL, no price/beds/baths) which don't fit the per-listing swipe model.
- `parse_next_data_page(raw_results) -> list[dict]` - maps `parse_next_data_result` over one load's results, dropping the `None`s.
- `parse_card(raw_card) -> dict` - fallback parser for `extract.js`'s DOM-text cards, regex-based (`_CARD_RE`) against real captured card text (handles no-space runs like `"3 bds2 ba"`); returns a bare `url`/`photo`/`source` dict (never fails) if the text doesn't match, letting `browser_import.py` treat it as `needs_backfill`.
- `parse_page_json(raw_cards) -> list[dict]` - maps `parse_card` over one page (superseded by `parse_next_data_page`, kept as documented fallback).
- Reuses `PAGE_PACING_SECONDS`, `MAX_PAGES_PER_SESSION`, and `dedupe_within_batch()` directly from `apt_agent/browser_scan_helpers.py` rather than duplicating them - deliberate, since both sites' anti-bot walls behave the same way.
- **Skill procedure** (`.claude/skills/scan-zillow/SKILL.md`): pick one neighborhood per session; build a Zillow search URL with a `searchQueryState` encoding `config.yaml`'s price/beds/baths bounds (deliberately no move-in-date filter, casting a wider net); sanity-check the page title actually matches the intended neighborhood (slug guesses aren't always right); for each load up to `MAX_PAGES_PER_SESSION`, run `extract_next_data.js` first (falling back to `extract.js` only if it returns `null`), screenshot if scoring, sleep `PAGE_PACING_SECONDS`, and stop immediately on any block-page signal; then `parse_next_data_page` -> `dedupe_within_batch` -> `matches_config_bounds` per listing (to catch anything that snuck past Zillow's own filter); tag each listing's `neighborhood` manually (the JSON doesn't reliably say which of the 7 target neighborhoods it's in); score against `taste_profile.md` the same no-API-key way as the StreetEasy skill; write to scratchpad and run `python -m apt_agent.browser_import`; update `STATUS.md`'s coverage table (captured vs. Zillow-reported total per neighborhood) rather than relying on a vague "done" feeling.

## Depends on / used by

- [browser-scan-streeteasy.md](browser-scan-streeteasy.md)
- [browser-import.md](browser-import.md)
- [store.md](store.md)
- [shared-config.md](shared-config.md)
- [scoring.md](scoring.md)

## Notes & gotchas

- **The photo-order bug (confirmed 2026-08-24, not guessed).** Every Zillow search-card renders exactly 3 `<img src*="zillowstatic">` tags, always in this order: **[last photo, first/primary photo, second photo]** - an infinite-loop carousel's prev/current/next peek slides. `extract.js`'s original `card.querySelector(...)` (first DOM match) therefore grabbed the *last* photo 100% of the time (8/8 real listings checked, cross-verified against each listing's own `carouselPhotosComposable.photoData` order) - a systematic, deterministic bug, not a rare inconsistency. Fixed by taking the second matching `<img>` instead of the first. The `__NEXT_DATA__` technique (`imgSrc`) was separately checked across 20 real listings and was never affected - it matched `photoData[0]` every time - so switching techniques had already fully retired this bug; the `extract.js` fix just closes the loop for its now-fallback role. 56 already-imported rows with confirmed-wrong `photo_url` were backfill-corrected using `__NEXT_DATA__` data already captured that session (no new page loads needed); 18 older rows never resurfaced by a later rescan remain uncorrected - low priority, photo-only issue.
- **Why `__NEXT_DATA__` became primary**: a same-day, same-query Clinton Hill re-test returned 26 results via `__NEXT_DATA__` versus only 6 via DOM-scraping earlier that day. The "6-card plateau" was never a hard rendering cap - `extract.js`'s `wait_for_load()` was returning before the client-side card list finished hydrating, a timing race. `__NEXT_DATA__` is server-rendered into the initial HTML, so it doesn't have that problem.
- **Anti-bot wall trips faster on Zillow than StreetEasy**: 5 page loads only ~3 seconds apart tripped a block during this skill's initial build (versus StreetEasy's wall tripping on page 2 of a 13-load rapid loop). Blocks have recurred multiple times since, sometimes as early as the 2nd-4th paced load in a session even with correct 20s pacing - pacing reduces the odds, it does not guarantee immunity. On any block: stop immediately, do not retry in the same session, and do **not** open a new tab or fresh browser identity to route around it - that would cross from legitimate access into evasion, which is the whole reason this technique is allowed at all. Just wait; the user has been able to clear a block themselves by observing the real browser.
- **Zillow's own pagination silently drops filter state.** Navigating to a `{page}_p/` URL with a hand-built `searchQueryState` sometimes re-serves page 1, and sometimes redirects to a canonicalized URL with the `searchQueryState` param dropped entirely, reverting to Zillow's default *unfiltered* result set (confirmed: a Brooklyn Heights title's count jumped from 41 to 51 rentals). Mitigation is `matches_config_bounds()` re-filtering anything past page 1 in Python, not trying to fix pagination itself.
- **No lever found to push a single scan toward 100% coverage** - three separate techniques were tested and all came back negative: narrowing the price band (Boerum Hill $5000-10000 -> $5000-6500 returned only already-known listings), changing sort order (`days` -> `priceD`, zero new listings), and scrolling the actual scrollable container (`#search-page-list-container`, tested in both map-visible states - card count never increased, no pagination controls exist in the DOM). All three point at the same root cause: Zillow appears to select a fixed subset of a neighborhood's pool for an exact filtered query *before* sorting/serving it - nothing tested changes which listings land in that subset. The only thing that has actually surfaced new listings across real sessions is time passing between scans (market turnover). Practical conclusion: budget one load per neighborhood per session, spread across more neighborhoods, and treat coverage as improving gradually over calendar time via repeated re-scans, not a smarter single query.
- The neighborhood-slug guess (`{name}-brooklyn-ny`) isn't always right and a wrong guess fails silently with no error - `williamsburg-brooklyn-ny` resolves to a different neighborhood ("East Williamsburg"); the correct slug is `williamsburg-new-york-ny`. The skill's page-title sanity check exists specifically to catch this.
- Even the `__NEXT_DATA__` technique is still capped at roughly one page's worth of results per load (matched `categoryTotals.cat1.totalResultCount`'s first page in testing) - it fixes data quality/reliability per load, not the underlying "how do we see a large neighborhood's full pool" problem.

## Related concepts

- [zillow-ingestion-evolution.md](../concepts/zillow-ingestion-evolution.md)
- [two-ingestion-paths.md](../concepts/two-ingestion-paths.md)
- [ai-taste-scoring.md](../concepts/ai-taste-scoring.md)
