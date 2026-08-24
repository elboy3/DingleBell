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
    """Maps parse_card over everything extract.js returned for one page."""
    return [parse_card(c) for c in raw_cards]
