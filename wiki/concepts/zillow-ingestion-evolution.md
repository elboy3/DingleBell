---
type: concept
status: active
verified: 2026-08-24
tags: [zillow, ingestion, history, anti-bot, next-data]
---

# Zillow ingestion evolution

## Summary

Within this project's Zillow browser-scan backfill tool ([browser-scan-zillow](../entities/browser-scan-zillow.md)), the extraction technique improved through a specific, verified sequence: DOM-scraping first, then discovering Zillow's own `__NEXT_DATA__` JSON blob was far more complete and reliable, then finding and fixing a confirmed deterministic photo-ordering bug in the old DOM approach, then three separate real experiments to push a single scan toward 100% coverage - all three came back negative. The real, hard-won conclusion is that periodic re-scans over calendar time, not a cleverer query, is the only thing that has actually added coverage.

## Details

**DOM-scraping first.** `extract.js` originally scraped `article.property-card` text and grabbed the first matching `<img src*="zillowstatic">` tag as the photo.

**`__NEXT_DATA__` discovered as strictly better.** Zillow's search-results pages embed the full structured result set - address, `unformattedPrice`, beds, baths, sqft, a real `availabilityDate`, `brokerName`, and up to 10-30 photo keys per listing (`carouselPhotosComposable.photoData`) - in a `__NEXT_DATA__` script tag, server-rendered at initial load. `extract_next_data.js` reads this directly and is now the primary technique; `extract.js` is demoted to a fallback used only if the tag is missing or restructured. This wasn't just a data-quality upgrade: a same-day, same-query Clinton Hill re-test returned 26 results via `__NEXT_DATA__` versus only 6 via DOM-scraping earlier that day, confirming the old "6-card plateau" was never a hard rendering cap - it was `extract.js` reading the DOM before the client finished hydrating the full first page, a timing race `__NEXT_DATA__` doesn't have.

**The confirmed "wrong photo" bug.** Every Zillow search-card renders exactly 3 `<img src*="zillowstatic">` tags, always in carousel peek-ahead order **[last photo, first/primary photo, second photo]**. `extract.js`'s original `querySelector` (first DOM match) therefore grabbed the *last* photo 100% of the time - confirmed 8/8 real listings checked against each listing's own `carouselPhotosComposable.photoData` order, a systematic bug, not a rare inconsistency. Fixed by taking the second matching `<img>` instead of the first. The `__NEXT_DATA__` technique's `imgSrc` field was separately checked across 20 listings and was never affected (matched `photoData[0]` every time), so the technique switch had already fully retired this bug for the primary path; fixing `extract.js` only closed the loop for its fallback role. 56 already-imported rows with confirmed-wrong `photo_url` were backfill-corrected using data already captured that session; 18 older rows never resurfaced by a later rescan remain uncorrected (low priority, photo-only).

**Three real, negative experiments toward 100% coverage.** All conducted and reported honestly as failures, not partial wins: (1) price-band splitting - narrowing Boerum Hill's filter from $5000-10000 (47 total) to $5000-6500 (21 total) still returned only already-known listings; (2) sort-order change (`days` -> `priceD`) - zero new listings, all 12 already known; (3) scrolling the actual scrollable container (`#search-page-list-container`, tested in both map-visible states, all the way to the true bottom) - card count never increased, no pagination controls exist in the DOM either. All three point at one root cause: Zillow appears to select a **fixed subset of a neighborhood's pool for an exact filtered query, before sorting/serving it** - nothing tested changes which listings land in that subset.

**The real conclusion.** The only thing that has actually surfaced new listings across real sessions is time passing between scans (market turnover changing what falls into that fixed subset). Practical policy, recorded in `STATUS.md`'s coverage table: budget roughly one page load per neighborhood per session, spread across more neighborhoods rather than paginating deep into one, and treat coverage as improving gradually over calendar time via repeated re-scans - not a smarter single query. Zillow's own reported "N Rentals" totals are themselves unstable between checks, so that column is an approximate denominator, not a precise one. This whole backfill effort only matters for the historical backlog anyway - `zillow_email_import.py` already catches every new Zillow listing automatically going forward with no coverage-gap risk at all (see [two-ingestion-paths](two-ingestion-paths.md)).

## Related entities

- [browser-scan-zillow](../entities/browser-scan-zillow.md)
- [browser-import](../entities/browser-import.md)
- [zillow-email-import](../entities/zillow-email-import.md)
- [store](../entities/store.md)

## Sources

DECISIONS.md ("Zillow historical backfill: a real anti-bot trip, and a scan skill built around it", points 7-9); STATUS.md ("Zillow historical backfill" checklist item, coverage table); wiki/entities/browser-scan-zillow.md.
