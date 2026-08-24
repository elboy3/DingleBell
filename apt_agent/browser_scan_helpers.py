"""
Pure-Python helpers for the browser-scan ingestion workflow (see
.claude/skills/scan-streeteasy/SKILL.md for the actual session-driven
scan procedure, and apt_agent/browser_scan/extract.js for the paired
DOM-extraction script that produces the raw cards these functions
parse).

Kept separate from extract.js deliberately: DOM extraction has to run
inside the browser session (via the `browser-use` MCP plugin's js()
helper), but turning that raw text into price/beds/baths/etc is
ordinary text parsing that belongs in this repo, versioned and
reusable, not re-derived ad hoc in a browser_exec call each session.
"""

import re
from datetime import date, datetime

from dateutil import parser as dateparser

# PerimeterX tripped on page 2 of a 13-page rapid-fire scan during this
# feature's initial build, even with a real authenticated session -
# a single organic page load didn't trigger it, a tight loop did. These
# constants are the mitigation: pace navigations, and cap how much one
# session attempts (resuming later is safe - browser_import.py dedups
# by url via ListingStore.already_seen()).
PAGE_PACING_SECONDS = 20
MAX_PAGES_PER_SESSION = 5

_PRICE_RE = re.compile(r"\$([\d,]+)\s*base rent")
_BEDS_RE = re.compile(r"(Studio|\d+(?:\.\d+)?)\s*beds?", re.IGNORECASE)
_BATHS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*baths?", re.IGNORECASE)
_SQFT_RE = re.compile(r"([\d,]+)\s*ft")
_AGENT_RE = re.compile(r"Listing by (.+)$")
_NEIGHBORHOOD_RE = re.compile(r"\bin\s+([A-Za-z .\-]+?)$")
_OPEN_HOUSE_RE = re.compile(r"Open:\s*([A-Za-z]+ \d{1,2}(?:\s*\([^)]*\))?)")


def _parse_open_house_date(raw: str) -> str | None:
    """Best-effort: pull just the date portion (e.g. "Aug 23") out of a
    raw open-house string and resolve it to an ISO date, assuming the
    nearest future occurrence (StreetEasy never shows a past open
    house). Returns None if unparseable - never blocks ingestion on
    this, same pattern as filters.py's own date handling."""
    date_part = raw.split("(")[0].strip()
    try:
        parsed = dateparser.parse(date_part, default=datetime.now()).date()
    except (ValueError, OverflowError):
        return None
    if parsed < date.today():
        parsed = parsed.replace(year=parsed.year + 1)
    return parsed.isoformat()


def parse_card(raw_card: dict) -> dict:
    """Turns one raw card (url, addressText, cardText, photo - the shape
    extract.js produces) into a structured listing dict ready for
    browser_import.import_listings()."""
    text = raw_card["cardText"]
    addr = raw_card["addressText"]
    prefix = text.split(addr)[0] if addr in text else ""

    neighborhood_m = _NEIGHBORHOOD_RE.search(prefix.strip())
    price_m = _PRICE_RE.search(text)
    beds_m = _BEDS_RE.search(text)
    baths_m = _BATHS_RE.search(text)
    sqft_m = _SQFT_RE.search(text)
    agent_m = _AGENT_RE.search(text)
    open_house_m = _OPEN_HOUSE_RE.search(text)

    beds = None
    if beds_m:
        beds = 0.0 if beds_m.group(1).lower() == "studio" else float(beds_m.group(1))

    open_house_raw = open_house_m.group(0) if open_house_m else None

    return {
        "url": raw_card["url"],
        "address": addr,
        "neighborhood": neighborhood_m.group(1).strip() if neighborhood_m else None,
        "price": int(price_m.group(1).replace(",", "")) if price_m else None,
        "beds": beds,
        "baths": float(baths_m.group(1)) if baths_m else None,
        "sqft": int(sqft_m.group(1).replace(",", "")) if sqft_m else None,
        "listing_agent": agent_m.group(1).strip() if agent_m else None,
        "photo": raw_card.get("photo"),
        "open_house_raw": open_house_raw,
        "open_house_date": _parse_open_house_date(open_house_m.group(1)) if open_house_m else None,
        "source": "streeteasy-browser-scan",
    }


def parse_page_json(raw_cards: list[dict]) -> list[dict]:
    """Maps parse_card over everything extract.js returned for one page."""
    return [parse_card(c) for c in raw_cards]


def matches_config_bounds(listing: dict, cfg: dict) -> bool:
    """True if listing's price/beds/baths (any that are present) fall
    within config.yaml's search: bounds. A listing with a field left
    unset (None) is never rejected on that field - unknown, don't block
    on it, same pattern as filters.py.

    Exists because Zillow's own pagination has been observed to
    silently drop the price/beds/baths filter state past page 1 -
    sometimes redirecting to a canonicalized URL with no
    searchQueryState at all, serving its *unfiltered* default result
    set instead (see DECISIONS.md, "Zillow's pagination silently drops
    the search filter state"). Anything past a scan's first page should
    be treated as untrusted and re-checked against this before import,
    rather than assumed to already respect the search config."""
    search_cfg = cfg["search"]
    price, beds, baths = listing.get("price"), listing.get("beds"), listing.get("baths")
    if price is not None and not (search_cfg["price_min"] <= price <= search_cfg["price_max"]):
        return False
    if beds is not None and beds < search_cfg["beds_min"]:
        return False
    if baths is not None and baths < search_cfg["baths_min"]:
        return False
    return True


def dedupe_within_batch(listings: list[dict]) -> list[dict]:
    """Same listing can appear on more than one page within a single
    scan session (StreetEasy's own sort can shift results as you
    paginate) - keep first occurrence, preserve order."""
    seen = set()
    deduped = []
    for listing in listings:
        if listing["url"] in seen:
            continue
        seen.add(listing["url"])
        deduped.append(listing)
    return deduped
