import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_FILE = "token.json"


def _creds() -> Credentials:
    creds = None
    if os.environ.get("GMAIL_TOKEN_JSON"):  # hosted: token passed via env, never written to disk
        creds = Credentials.from_authorized_user_info(json.loads(os.environ["GMAIL_TOKEN_JSON"]), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(os.environ["GMAIL_CREDENTIALS_PATH"], SCOPES)
        creds = flow.run_local_server(port=0)  # one-time interactive auth
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    return creds


def fetch_recent() -> list[dict]:
    """Return [{id, from, subject, snippet}] for inbox mail from the last 24h."""
    svc = build("gmail", "v1", credentials=_creds(), cache_discovery=False)
    resp = svc.users().messages().list(userId="me", q="newer_than:1d in:inbox", maxResults=100).execute()
    out = []
    for m in resp.get("messages", []):
        msg = svc.users().messages().get(
            userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        out.append({
            "id": m["id"],
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", "(no subject)"),
            "snippet": msg.get("snippet", ""),
        })
    return out
