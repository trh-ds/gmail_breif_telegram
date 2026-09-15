import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",  # drafts + send only, no delete/modify of mail
    "https://www.googleapis.com/auth/calendar.events",  # events only, not calendar settings
    "https://www.googleapis.com/auth/tasks",
]
TOKEN_FILE = "token.json"


def creds() -> Credentials:
    c = None
    if os.environ.get("GMAIL_TOKEN_JSON"):  # hosted: token passed via env, never written to disk
        c = Credentials.from_authorized_user_info(json.loads(os.environ["GMAIL_TOKEN_JSON"]), SCOPES)
        if c.expired and c.refresh_token:
            c.refresh(Request())
        return c
    if os.path.exists(TOKEN_FILE):
        c = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if c and c.expired and c.refresh_token:
        c.refresh(Request())
    elif not c or not c.valid:
        flow = InstalledAppFlow.from_client_secrets_file(os.environ["GMAIL_CREDENTIALS_PATH"], SCOPES)
        c = flow.run_local_server(port=0)  # one-time interactive auth
    with open(TOKEN_FILE, "w") as f:
        f.write(c.to_json())
    return c


def service(name: str, version: str):
    return build(name, version, credentials=creds(), cache_discovery=False)