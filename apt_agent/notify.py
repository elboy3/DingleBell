"""Send alert emails via the Gmail API (reuses the same OAuth creds as ingestion)."""
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build

from .gmail_auth import get_gmail_credentials


def _build_message(listing: dict, recipients: list[str], from_address: str, subject_prefix: str) -> dict:
    source = listing.get("source", "unknown")

    if source == "heartbeat":
        subject = f"{subject_prefix} Daily check-in - agent is alive"
        body = f"""{listing['address']}

This is an automatic daily heartbeat, not a real listing - just
confirming the agent ran successfully in the last 24h. If you stop
getting these, something's broken (check the GitHub Actions log).

---
Sent automatically by your apartment agent.
"""
    elif source == "dry-run":
        subject = f"{subject_prefix} TEST alert - pipeline check"
        body = f"""This is a test email, not a real listing.

If you're reading this, OAuth + filters + email delivery are all
working end-to-end. Nothing to act on here.

---
Sent automatically by your apartment agent.
"""
    else:
        price = f"${listing['price']:,}" if listing.get("price") else "price unknown"
        beds = listing.get("beds", "?")
        baths = listing.get("baths", "?")
        avail = listing.get("available_date") or "unknown"

        subject = f"{subject_prefix} New listing - {price} ({source})"
        body = f"""New apartment alert!

Price: {price}
Beds / Baths: {beds} / {baths}
Available: {avail}
Source: {source}

Link: {listing['url']}

---
Sent automatically by your apartment agent.
"""

    message = MIMEText(body)
    message["to"] = ", ".join(recipients)
    message["from"] = from_address
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_alert(listing: dict, notify_cfg: dict):
    creds = get_gmail_credentials()
    service = build("gmail", "v1", credentials=creds)

    message = _build_message(
        listing,
        notify_cfg["recipients"],
        notify_cfg["from_address"],
        notify_cfg["subject_prefix"],
    )
    service.users().messages().send(userId="me", body=message).execute()
