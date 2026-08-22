"""Poll Gmail for new listing-alert emails and extract listing URLs."""

import base64
import re

from bs4 import BeautifulSoup
from googleapiclient.discovery import build

from .gmail_auth import get_gmail_credentials

# Known listing-detail URL patterns per source. We only keep links that
# look like an actual unit/listing page, not nav/footer/unsubscribe links.
LISTING_URL_PATTERNS = [
    r"https?://(?:www\.)?streeteasy\.com/(?:building|rental)/[^\s\"'<>]+",
    r"https?://(?:www\.)?zillow\.com/homedetails/[^\s\"'<>]+",
    r"https?://(?:www\.)?renthop\.com/listings/[^\s\"'<>]+",
    r"https?://(?:www\.)?nakedapartments\.com/[a-z0-9\-]+/listing/[^\s\"'<>]+",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in LISTING_URL_PATTERNS]


def _get_service():
    creds = get_gmail_credentials()
    return build("gmail", "v1", credentials=creds)


def _decode_body(payload) -> str:
    """Walk a Gmail message payload and return concatenated HTML/text body."""
    parts_to_check = [payload] + payload.get("parts", [])
    html_chunks = []
    for part in parts_to_check:
        body_data = part.get("body", {}).get("data")
        mime_type = part.get("mimeType", "")
        if body_data and ("html" in mime_type or "plain" in mime_type):
            decoded = base64.urlsafe_b64decode(body_data + "===").decode("utf-8", errors="ignore")
            html_chunks.append(decoded)
        # recurse into nested multipart
        if "parts" in part:
            for sub in part["parts"]:
                sub_data = sub.get("body", {}).get("data")
                if sub_data:
                    decoded = base64.urlsafe_b64decode(sub_data + "===").decode(
                        "utf-8", errors="ignore"
                    )
                    html_chunks.append(decoded)
    return "\n".join(html_chunks)


def extract_listing_urls(html: str) -> list[str]:
    """Pull unique listing-detail URLs out of an alert email body."""
    return [url for url, _snippet in extract_listings_with_snippets(html)]


def extract_listings_with_snippets(html: str) -> list[tuple[str, str]]:
    """
    Pull unique listing-detail URLs out of an alert email body, each paired
    with a nearby text snippet - used by
    `listing_parser.extract_from_email_snippet()` to pull price/beds/baths
    straight from the alert email instead of fetching the listing page
    (StreetEasy/Zillow 403 on direct page fetches - see CLAUDE.md known
    limitations). Snippet-per-URL (not one global blob) matters because a
    single alert email usually contains many listings.
    """
    found = {}  # url -> snippet, insertion order preserved (dict, py3.7+)

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        for pattern in _COMPILED_PATTERNS:
            if pattern.match(a["href"]):
                url = a["href"].split("?")[0]  # strip tracking params
                if url in found:
                    break
                # The anchor's own text is often just "View listing" or an
                # image - climb up to a parent (the listing "card") until
                # we find enough text to plausibly contain price/beds/baths.
                node, snippet, hops = a, a.get_text(" ", strip=True), 0
                while len(snippet) < 20 and node.parent is not None and hops < 4:
                    node = node.parent
                    snippet = node.get_text(" ", strip=True)
                    hops += 1
                found[url] = snippet
                break

    # fallback: raw regex over the text too, in case links aren't <a> tags -
    # grab a window of surrounding text since there's no element to climb.
    for pattern in _COMPILED_PATTERNS:
        for match in pattern.finditer(html):
            url = match.group(0).split("?")[0]
            if url in found:
                continue
            start, end = max(0, match.start() - 300), min(len(html), match.end() + 300)
            found[url] = BeautifulSoup(html[start:end], "html.parser").get_text(" ", strip=True)

    return list(found.items())


def fetch_new_alert_urls(query: str, mark_as_read: bool = True) -> list[tuple[str, str]]:
    """
    Query Gmail for unread alert emails matching `query`, extract
    (listing URL, nearby text snippet) pairs from all of them, and
    (optionally) mark those emails as read so we don't reprocess them
    next poll.
    """
    service = _get_service()
    results = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
    message_ids = [m["id"] for m in results.get("messages", [])]

    all_listings = []
    for msg_id in message_ids:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        body = _decode_body(msg["payload"])
        all_listings.extend(extract_listings_with_snippets(body))

        if mark_as_read:
            service.users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()

    # dedup while preserving order (same URL could appear in >1 email)
    seen = set()
    deduped = []
    for url, snippet in all_listings:
        if url not in seen:
            seen.add(url)
            deduped.append((url, snippet))
    return deduped
