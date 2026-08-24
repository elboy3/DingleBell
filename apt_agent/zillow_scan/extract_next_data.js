/*
 * Primary DOM-extraction script for a Zillow rental search-results page,
 * run via the `browser-use` MCP plugin's `js()` helper against the user's
 * real authenticated browser session (same reasoning as
 * apt_agent/browser_scan/extract.js for StreetEasy - a real user's own
 * browser loading a page they're entitled to see, not automated evasion).
 *
 * Unlike extract.js (DOM-scraping `article.property-card` text), this
 * reads Zillow's own `__NEXT_DATA__` script tag, which embeds the same
 * structured JSON the page's React app hydrates from
 * (props.pageProps.searchPageState.cat1.searchResults.listResults).
 * Confirmed for real (2026-08-24) to be both more complete and more
 * reliable than DOM-scraping: a same-query Clinton Hill re-test got 26
 * results this way versus only 6 from extract.js earlier the same day -
 * extract.js's `wait_for_load()` was returning before the client-side
 * card list finished hydrating, a timing race, not a hard rendering cap.
 * __NEXT_DATA__ is server-rendered into the initial HTML, so it doesn't
 * have that problem.
 *
 * Field parsing lives in apt_agent/zillow_scan_helpers.py's
 * parse_next_data_result(), same "testable Python, not one-off
 * browser_exec code" reasoning as extract.js/zillow_scan_helpers.py.
 *
 * Returns RAW results only, still capped at roughly one page's worth per
 * load (matches categoryTotals.cat1.totalResultCount's first page, not
 * the full neighborhood total) - this fixes data quality/reliability per
 * page, not the "how do we see the rest of a large neighborhood"
 * problem. A neighborhood with more listings than one load captures
 * needs a future session's re-scan to catch more, same as before.
 *
 * Falls back to null if the __NEXT_DATA__ tag is missing/restructured -
 * check for that and fall back to extract.js's DOM-scraping approach if
 * so, rather than assuming this always works.
 */
(() => {
  const el = document.getElementById('__NEXT_DATA__');
  if (!el) return null;
  let data;
  try {
    data = JSON.parse(el.textContent);
  } catch (e) {
    return null;
  }
  const sr = data?.props?.pageProps?.searchPageState?.cat1?.searchResults;
  const listResults = sr?.listResults;
  if (!listResults) return null;
  return listResults.map((r) => ({
    zpid: r.zpid,
    url: r.detailUrl,
    address: r.address,
    price: r.unformattedPrice ?? null,
    beds: r.beds ?? null,
    baths: r.baths ?? null,
    sqft: r.hdpData?.homeInfo?.livingArea ?? null,
    availabilityDate: r.availabilityDate ?? null,
    brokerName: r.brokerName ?? null,
    photo: r.imgSrc ?? null,
    photoKeys:
      r.carouselPhotosComposable?.photoData?.map((p) => p.photoKey) ?? [],
    photoBaseUrl: r.carouselPhotosComposable?.baseUrl ?? null,
  }));
})()
