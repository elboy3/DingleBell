"""
Pure-Python helpers for the Zillow search-results browser-scan workflow
(see .claude/skills/scan-zillow/SKILL.md for the session procedure, and
apt_agent/zillow_scan/extract.js for the paired DOM-extraction script).

This is for backfilling listings that existed *before* the automated
apt_agent/zillow_email_import.py pipeline was set up - that pipeline
covers everything going forward on its own, unattended. This scan is
for the historical backlog only, and (unlike the email import) needs a
live authenticated browser, same as the StreetEasy scan.

Kept separate from apt_agent/browser_scan_helpers.py (StreetEasy) since
the card markup and field layout genuinely differ, but the pacing
constants (PAGE_PACING_SECONDS, MAX_PAGES_PER_SESSION) and
dedupe_within_batch() there are fully generic - reuse those directly
rather than duplicating them here. Both sites' anti-bot walls have
shown the same behavior (a tight rapid-fire loop trips a block within
the first few pages; a paced, organic-looking loop doesn't), so
there's no reason to tune pacing per-site until real evidence says
otherwise.
"""

import re

# A search-result card's text has no whitespace between some adjacent
# fields (e.g. "3 bds2 ba", "1 bd1 ba") - real examples pulled from a
# live page, not guessed - so this can't rely on consistent spacing.
_CARD_RE = re.compile(
    r"\$([\d,]+)/mo.*?"
    r"(Studio|\d+) bds?"
    r"(\d+(?:\.\d+)?) ba"
    r"(?:--|([\d,]+)) sqft"
    r"[A-Za-z ]*? for rent"
    r"(.+?),\s*Brooklyn,\s*NY\s*(\d{5})"
    r"(?:LISTING BY: ([^0-9]+?))?"
    r"(?:More|\d+\s*(?:hour|day|minute)s?\s*ago)",
    re.IGNORECASE,
)


def parse_card(raw_card: dict) -> dict:
    """Turns one raw card (url, cardText, photo - the shape extract.js
    produces) into a structured listing dict ready for
    browser_import.import_listings(). If the card text doesn't match
    the expected shape (e.g. a "premium"/ad placement with different
    markup), returns just url/photo/source - browser_import treats a
    listing with no address/photo as needs_backfill rather than failing,
    same graceful-degradation pattern as everywhere else in this repo."""
    m = _CARD_RE.search(raw_card["cardText"])
    if not m:
        return {
            "url": raw_card["url"],
            "photo": raw_card.get("photo"),
            "source": "zillow-browser-scan",
        }

    price, beds, baths, sqft, street, zip_code, agent = m.groups()
    beds_val = 0.0 if beds.lower() == "studio" else float(beds)

    return {
        "url": raw_card["url"],
        "address": f"{street.strip()}, Brooklyn, NY {zip_code}",
        "price": int(price.replace(",", "")),
        "beds": beds_val,
        "baths": float(baths),
        "sqft": int(sqft.replace(",", "")) if sqft else None,
        "listing_agent": agent.strip() if agent else None,
        "photo": raw_card.get("photo"),
        "source": "zillow-browser-scan",
    }


def parse_page_json(raw_cards: list[dict]) -> list[dict]:
    """Maps parse_card over everything extract.js returned for one page.
    Superseded by parse_next_data_page() below as the primary technique
    (see that function's docstring) - kept as a documented fallback if
    Zillow's __NEXT_DATA__ tag is ever missing or restructured."""
    return [parse_card(c) for c in raw_cards]


def parse_next_data_result(raw: dict) -> dict | None:
    """Turns one raw __NEXT_DATA__ listResults entry (the shape
    apt_agent/zillow_scan/extract_next_data.js produces) into a
    structured listing dict ready for browser_import.import_listings().

    Confirmed for real (2026-08-24) to be both more complete and more
    reliable than parse_card()/extract.js's DOM-text regex parsing - see
    that function's docstring and DECISIONS.md ("Found a much better
    extraction source"). Does not set `neighborhood` - the raw JSON
    doesn't reliably say which of this project's 7 target neighborhoods
    a listing belongs to (addressZipcode covers multiple, overlapping
    neighborhoods), so the calling session should tag it based on which
    neighborhood search it just ran, same as it already does for
    parse_card() output.

    Returns None for "relaxed"/building-aggregator entries mixed into
    Zillow's own results (a lat/long string standing in for zpid, a
    relative /b/... or /apartments/... URL, no price/beds/baths) - these
    are building-level pages, not individual units, and don't fit the
    per-listing swipe model, so they're dropped rather than imported as
    an unresolvable needs_backfill row."""
    if raw.get("price") is None:
        return None

    broker = raw.get("brokerName")
    if broker and broker.lower().startswith("listing by:"):
        broker = broker.split(":", 1)[1].strip()

    return {
        "url": raw["url"],
        "address": raw.get("address"),
        "price": raw["price"],
        "beds": raw.get("beds"),
        "baths": raw.get("baths"),
        "sqft": raw.get("sqft"),
        "listing_agent": broker,
        "photo": raw.get("photo"),
        "available_date": raw.get("availabilityDate"),
        "source": "zillow-browser-scan",
    }


def parse_next_data_page(raw_results: list[dict]) -> list[dict]:
    """Maps parse_next_data_result over everything
    extract_next_data.js returned for one page, dropping building-
    aggregator entries (see that function's docstring)."""
    return [r for raw in raw_results if (r := parse_next_data_result(raw)) is not None]
