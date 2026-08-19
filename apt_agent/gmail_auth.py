"""
Run this once to authorize the agent against your Gmail account.

Setup steps (do this before running):
1. Go to https://console.cloud.google.com/ -> create a project (or reuse one).
2. Enable the "Gmail API" for that project.
3. Create OAuth credentials: APIs & Services -> Credentials -> Create Credentials
   -> OAuth client ID -> Application type: Desktop app.
4. Download the JSON, save it as `credentials.json` in this project's root dir.
5. Run: python -m apt_agent.gmail_auth
   -> a browser window opens, log in with the Gmail account that receives
      your StreetEasy/Zillow/RentHop alerts, approve access.
6. This creates `token.json` - the agent reuses this on future runs, no
   need to re-auth unless you revoke access.

Scopes requested:
  - gmail.readonly  (read alert emails)
  - gmail.send      (optional, only needed if you want the agent itself
                      to send the alert emails from this same Gmail account
                      instead of a separate SMTP/SES sender)
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_gmail_credentials() -> Credentials:
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found. See module docstring for setup steps."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


if __name__ == "__main__":
    get_gmail_credentials()
    print("Auth complete. token.json written - agent is ready to run.")
