"""
Run this only when the main polling step fails (wired into the GitHub
Actions workflow via `if: failure()`). Sends a plain "the agent broke"
email so a bad run doesn't just go silent for days.
"""

import base64
import os
import sys
from email.mime.text import MIMEText

from googleapiclient.discovery import build

from .gmail_auth import get_gmail_credentials


def main():
    recipients_env = os.environ.get("NOTIFY_RECIPIENTS", "")
    from_address = os.environ.get("NOTIFY_FROM_ADDRESS", "")
    run_url = os.environ.get("GITHUB_RUN_URL", "unknown")

    recipients = [r.strip() for r in recipients_env.split(",") if r.strip()]
    if not recipients or not from_address:
        print(
            "NOTIFY_RECIPIENTS / NOTIFY_FROM_ADDRESS not set, skipping failure email.",
            file=sys.stderr,
        )
        return

    creds = get_gmail_credentials()
    service = build("gmail", "v1", credentials=creds)

    body = f"""The apartment agent's scheduled run just failed.

Check the run log here: {run_url}

Common causes: OAuth token expired (needs re-auth), a listing site changed
its email/page format, or a transient network error. If this keeps
happening, take a look before you miss real listings.
"""
    message = MIMEText(body)
    message["to"] = ", ".join(recipients)
    message["from"] = from_address
    message["subject"] = "[Apt Agent] Run failed - check logs"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print("Failure alert email sent.")


if __name__ == "__main__":
    main()
