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
 * NOTE: targets Zillow's current markup (`article.property-card`, a
 * homedetails link, and a photo `<img src>` inside the card). Already
 * includes the zpid and full address slug directly in the URL, unlike
 * the click-tracked links in Zillow's alert emails - no target= decoding
 * needed here. If Zillow changes their card layout, this selector logic
 * is the first thing to re-check.
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
    const img = card.querySelector('img[src*="zillowstatic"]');
    out.push({
      url,
      cardText: card.textContent.replace(/\s+/g, ' ').trim(),
      photo: img ? (img.currentSrc || img.src) : null,
    });
  }
  return out;
})()
