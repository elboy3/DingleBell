/*
 * DOM-extraction script for a Zillow rental search-results page, run via
 * the `browser-use` MCP plugin's `js()` helper against the user's real
 * authenticated browser session (same reasoning as
 * apt_agent/browser_scan/extract.js for StreetEasy - a real user's own
 * browser loading a page they're entitled to see, not automated evasion).
 *
 * Returns RAW cards only (url, cardText, photo) - field parsing lives in
 * apt_agent/zillow_scan_helpers.py instead, for the same reason as the
 * StreetEasy version: testable Python, not one-off browser_exec code.
 *
 * Superseded by extract_next_data.js as the primary extraction technique
 * (see that file and DECISIONS.md) - kept only as a fallback if Zillow's
 * __NEXT_DATA__ tag is ever missing or restructured.
 *
 * NOTE: targets Zillow's current markup (`article.property-card`, a
 * homedetails link, and a photo `<img src>` inside the card). Already
 * includes the zpid and full address slug directly in the URL, unlike
 * the click-tracked links in Zillow's alert emails - no target= decoding
 * needed here. If Zillow changes their card layout, this selector logic
 * is the first thing to re-check.
 *
 * PHOTO ORDER - confirmed for real (2026-08-24), not guessed: each card
 * renders exactly 3 `<img src*="zillowstatic">` tags, always in this
 * order: [last photo, first/primary photo, second photo] - an
 * infinite-loop carousel's prev/current/next peek slides. The *first*
 * DOM match is therefore always the *last* photo, 100% of the time (8/8
 * real listings checked) - not a rare Zillow inconsistency. This
 * silently gave every listing imported via this script (before
 * extract_next_data.js existed) its LAST photo instead of its first;
 * confirmed several real rows in listings.db had exactly this bug. Fixed
 * by taking the second matching `<img>`, not the first.
 */
(() => {
  const cards = Array.from(document.querySelectorAll('article.property-card'));
  const seen = new Set();
  const out = [];
  for (const card of cards) {
    const a = card.querySelector('a[href*="/homedetails/"]');
    if (!a) continue;
    const url = a.href.split('?')[0];
    if (seen.has(url)) continue;
    seen.add(url);
    const imgs = card.querySelectorAll('img[src*="zillowstatic"]');
    const img = imgs.length > 1 ? imgs[1] : imgs[0];
    out.push({
      url,
      cardText: card.textContent.replace(/\s+/g, ' ').trim(),
      photo: img ? (img.currentSrc || img.src) : null,
    });
  }
  return out;
})()
