/*
 * DOM-extraction script for a StreetEasy saved-search RESULTS page,
 * run via the `browser-use` MCP plugin's `js()` helper against the
 * user's real authenticated browser session (bypasses the PerimeterX
 * wall that blocks anonymous scraping - see DECISIONS.md).
 *
 * Returns RAW cards only (url, addressText, cardText, photo) - deliberately
 * does no field parsing here. Field parsing (price/beds/baths/etc regex)
 * lives in apt_agent/browser_scan_helpers.py instead, so it's testable
 * Python running in this repo's normal environment, not one-off code
 * typed into a browser_exec call each session.
 *
 * NOTE: targets StreetEasy's current markup (a[href*="/building/"] with
 * a building+unit path, climbing to the nearest ancestor containing both
 * "$" and "bed"/"studio" text, then finding a photo <img> by climbing
 * further). If StreetEasy changes their card layout, this selector logic
 * is the first thing to re-check - same caveat as listing_parser.py's
 * email-based extraction.
 */
(() => {
  const seen = new Set();
  const cards = [];
  const links = Array.from(document.querySelectorAll('a[href*="/building/"]'));
  for (const a of links) {
    const path = new URL(a.href).pathname;
    const parts = path.replace('/building/', '').split('/').filter(Boolean);
    if (parts.length < 2) continue;
    const cleanUrl = a.href.split('?')[0];
    if (seen.has(cleanUrl)) continue;

    let node = a, priceContainer = null, hops = 0;
    while (node && hops < 8) {
      if (node.textContent.includes('$') && /bed|studio/i.test(node.textContent)) {
        priceContainer = node;
        break;
      }
      node = node.parentElement;
      hops++;
    }
    if (!priceContainer) continue;

    let imgNode = priceContainer, img = null, hops2 = 0;
    while (imgNode && hops2 < 6) {
      img = imgNode.querySelector('img[src*="streeteasy"], img[src*="zillow"], img[srcset]');
      if (img) break;
      imgNode = imgNode.parentElement;
      hops2++;
    }
    seen.add(cleanUrl);

    cards.push({
      url: cleanUrl,
      addressText: a.textContent.trim(),
      cardText: priceContainer.textContent.replace(/\s+/g, ' ').trim(),
      photo: img ? (img.currentSrc || img.src) : null
    });
  }
  return cards;
})()
