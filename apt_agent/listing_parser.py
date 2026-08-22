"""
Fetch and parse individual listing pages for structured fields.

IMPORTANT CAVEAT: StreetEasy/Zillow/RentHop actively discourage automated
scraping of listing pages (rate limits, IP blocks, layout changes without
notice). This module does a light, low-frequency fetch (one request per
NEW listing URL, not repeated polling of the same page) to keep the
footprint minimal. If you start seeing 403s/CAPTCHAs, the safest fallback
is to rely on the fields already present in the alert email itself
(price/address are usually in the email body) rather than fetching the
page - see `extract_from_email_snippet` below for that path.

Selectors below are best-effort based on common patterns and WILL need
adjustment once you see real page HTML - treat this as a starting point,
not a finished scraper.
"""

import re

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

PRICE_RE = re.compile(r"\$([\d,]{3,7})")
BEDS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:bed|bd|br)\b", re.IGNORECASE)
BATHS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:bath|ba)\b", re.IGNORECASE)
AVAIL_RE = re.compile(
    r"(available\s+(?:now|immediately|on)?\s*[:\-]?\s*[A-Za-z0-9,\s]{0,20})",
    re.IGNORECASE,
)


def fetch_listing_page(url: str, timeout: int = 10) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
        return None
    except requests.RequestException:
        return None


def parse_listing_html(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    price_match = PRICE_RE.search(text)
    beds_match = BEDS_RE.search(text)
    baths_match = BATHS_RE.search(text)
    avail_match = AVAIL_RE.search(text)

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    return {
        "url": url,
        "address": title,
        "price": int(price_match.group(1).replace(",", "")) if price_match else None,
        "beds": float(beds_match.group(1)) if beds_match else None,
        "baths": float(baths_match.group(1)) if baths_match else None,
        "available_date": avail_match.group(1).strip() if avail_match else None,
        "source": _source_from_url(url),
    }


def extract_from_email_snippet(snippet_text: str, url: str) -> dict:
    """
    Fallback / primary-lite path: pull the same fields directly from the
    alert email's own text, skipping the page fetch entirely. Use this
    first if you want to minimize scraping footprint.
    """
    price_match = PRICE_RE.search(snippet_text)
    beds_match = BEDS_RE.search(snippet_text)
    baths_match = BATHS_RE.search(snippet_text)
    avail_match = AVAIL_RE.search(snippet_text)

    return {
        "url": url,
        "address": None,  # usually needs the page or a separate regex tuned to email layout
        "price": int(price_match.group(1).replace(",", "")) if price_match else None,
        "beds": float(beds_match.group(1)) if beds_match else None,
        "baths": float(baths_match.group(1)) if baths_match else None,
        "available_date": avail_match.group(1).strip() if avail_match else None,
        "source": _source_from_url(url),
    }


def _source_from_url(url: str) -> str:
    for name in ("streeteasy", "zillow", "renthop", "nakedapartments"):
        if name in url:
            return name
    return "unknown"
