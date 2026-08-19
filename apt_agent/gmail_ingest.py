"""Poll Gmail for new listing-alert emails and extract listing URLs."""
import base64
import re
from googleapiclient.discovery import build
from bs4 import BeautifulSoup

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
            decoded = base64.urlsafe_b64decode(body_data + "===").decode(
                "utf-8", errors="ignore"
            )
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
    urls = set()

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        for pattern in _COMPILED_PATTERNS:
            if pattern.match(a["href"]):
                urls.add(a["href"].split("?")[0])  # strip tracking params

    # fallback: raw regex over the text too, in case links aren't <a> tags
    for pattern in _COMPILED_PATTERNS:
        for match in pattern.findall(html):
            urls.add(match.split("?")[0])

    return sorted(urls)


def fetch_new_alert_urls(query: str, mark_as_read: bool = True) -> list[str]:
    """
    Query Gmail for unread alert emails matching `query`, extract listing
    URLs from all of them, and (optionally) mark those emails as read so
    we don't reprocess them next poll.
    """
    service = _get_service()
    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=50)
        .execute()
    )
    message_ids = [m["id"] for m in results.get("messages", [])]

    all_urls = []
    for msg_id in message_ids:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_id, format="full")
            .execute()
        )
        body = _decode_body(msg["payload"])
        all_urls.extend(extract_listing_urls(body))

        if mark_as_read:
            service.users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()

    # dedup while preserving order
    seen = set()
    deduped = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped
