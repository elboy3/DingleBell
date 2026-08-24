"""
Imports individual Zillow rental listings straight from "just listed"/
instant-update alert emails - no browser scan needed at all.

Zillow's `rental-instant-updates@mail.zillow.com` sender fires within
minutes of a new listing going up (unlike StreetEasy, which only sends
thin digest recommendations - see DECISIONS.md "Pivot from email
alerts"). Each email's plain-text body already has full structured
data (price/beds/baths/sqft/address/agent) as free text, and its HTML
body has a real listing photo on `photos.zillowstatic.com` - the same
CDN the browser-scan already pulls from, no auth needed. Each listing's
Zillow property ID (zpid) is embedded in its "View this listing" link's
click-tracking `target=` param, which is enough to build a stable
canonical URL (`zillow.com/homedetails/{zpid}_zpid/`) without ever
following a redirect or fetching a page - the exact 403-on-anonymous-
fetch problem this whole project has otherwise had to work around.

Each email's "Other rentals you might like" section (same full data
per listing) is imported too - free extra breadth (goal #1 in
CLAUDE.md), no extra emails needed.

    python -m apt_agent.zillow_email_import

Unlike the browser-scan skill, this needs no interactive session and
no live human vision for AI scoring - it's plain Gmail API + regex, so
it can run unattended on the existing GitHub Actions poll cron. That
also means there's no live session to score a photo itself: ai_score
is left NULL here. Run `poe rescore` (webapp/rescore.py, the
API-key-fallback scorer) afterward if you want these scored.
"""

import base64
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from googleapiclient.discovery import build

from .browser_import import import_listings
from .gmail_auth import get_gmail_credentials
from .main import load_config
from .store import ListingStore

QUERY = "from:rental-instant-updates@mail.zillow.com newer_than:1d"

# Matches one listing block in the plain-text body - both the featured
# "just listed" property ("For rent. NEW.") and each "Other rentals you
# might like" entry ("For rent") share this shape. Listing agent and a
# resolvable zpid are both optional - paid "premium property" placements
# (seen in the wild pointing at a different city than the saved search)
# have neither, and get filtered out downstream for lacking a zpid.
_BLOCK_RE = re.compile(
    r"For rent\.?\s*(?:NEW\.)?\s*\n+"
    r"\$([\d,]+)/mo\s*\n+"
    r"(Studio|\d+(?:\.\d+)?) bd \| (\d+(?:\.\d+)?) ba \| (?:--|([\d,]+)) sqft \| \w+\s*\n+"
    r"([^\n]+)\s*\n+"
    r"(?:Listing by: ([^\n]+)\s*\n+)?"
    r"View this listing -\s*\n+"
    r"(\S+)",
    re.IGNORECASE,
)


def _zpid_from_tracking_url(url: str) -> str | None:
    """The visible link is a click.mail.zillow.com tracker; the real
    destination (and the zpid within it) lives in its `target=` query
    param - decodable directly, no need to follow the redirect."""
    target = parse_qs(urlparse(url).query).get("target", [None])[0]
    if not target:
        return None
    m = re.search(r"zpid_target/(\d+)_zpid", target)
    return m.group(1) if m else None


def _photo_for_zpid(soup: BeautifulSoup, zpid: str) -> str | None:
    """Each listing sits in its own `<table role="group"
    aria-label="property">` - the photo is a `background=` attribute
    (an email-HTML convention, not a normal <img src>) on some tag
    inside that same table, not a sibling/descendant of the link
    itself, so scope by table rather than climbing from the <a>.
    The anchor's href is itself a click-tracking URL whose `target=`
    query value is percent-encoded, so the zpid has to be decoded via
    _zpid_from_tracking_url rather than substring-matched on the raw
    href (which contains "zpid_target%2F...", not "zpid_target/...")."""
    link = soup.find("a", href=lambda h: h and _zpid_from_tracking_url(h) == zpid)
    if not link:
        return None
    table = link.find_parent("table", attrs={"role": "group", "aria-label": "property"})
    if not table:
        return None
    bg_tag = table.find(
        lambda tag: tag.has_attr("background") and "zillowstatic" in tag["background"]
    )
    return bg_tag["background"] if bg_tag else None


def parse_zillow_email(text: str, html: str) -> list[dict]:
    """Turns one instant-update email into a list of raw listing dicts
    ready for browser_import.import_listings() - the featured listing
    plus every bundled "you might like" one, minus any block whose link
    doesn't resolve to a real zpid (paid placements)."""
    soup = BeautifulSoup(html, "html.parser")
    listings = []
    for m in _BLOCK_RE.finditer(text):
        price, beds, baths, sqft, address, agent, tracking_url = m.groups()
        zpid = _zpid_from_tracking_url(tracking_url)
        if not zpid:
            continue
        beds_val = 0.0 if beds.lower() == "studio" else float(beds)
        listings.append(
            {
                "url": f"https://www.zillow.com/homedetails/{zpid}_zpid/",
                "address": address.strip(),
                "price": int(price.replace(",", "")),
                "beds": beds_val,
                "baths": float(baths),
                "sqft": int(sqft.replace(",", "")) if sqft else None,
                "listing_agent": agent.strip() if agent else None,
                "photo": _photo_for_zpid(soup, zpid),
                "source": "zillow-email",
            }
        )
    return listings


def _get_body(payload: dict, mime_type: str) -> str | None:
    if payload.get("mimeType") == mime_type and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"] + "===").decode(
            "utf-8", errors="ignore"
        )
    for part in payload.get("parts", []):
        found = _get_body(part, mime_type)
        if found:
            return found
    return None


def fetch_listings_from_inbox() -> list[dict]:
    service = build("gmail", "v1", credentials=get_gmail_credentials())
    results = service.users().messages().list(userId="me", q=QUERY, maxResults=100).execute()
    listings = []
    for message in results.get("messages", []):
        full = (
            service.users().messages().get(userId="me", id=message["id"], format="full").execute()
        )
        text = _get_body(full["payload"], "text/plain")
        html = _get_body(full["payload"], "text/html")
        if text and html:
            listings.extend(parse_zillow_email(text, html))
    return listings


def main():
    cfg = load_config()
    store = ListingStore(cfg["storage"]["db_path"])
    listings = fetch_listings_from_inbox()
    stats = import_listings(listings, cfg, store)
    print(f"Imported: {stats}")


if __name__ == "__main__":
    main()
