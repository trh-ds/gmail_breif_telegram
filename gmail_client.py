import base64
import json
import os
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",  # drafts + send only, no delete/modify of mail
]
TOKEN_FILE = "token.json"
HEADERS = ["From", "To", "Subject", "Message-ID", "Reply-To", "In-Reply-To", "References"]


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


def _svc():
    return build("gmail", "v1", credentials=_creds(), cache_discovery=False)


def _parse(msg: dict) -> dict:
    h = {x["name"].lower(): x["value"] for x in msg["payload"].get("headers", [])}
    return {
        "id": msg["id"],
        "thread_id": msg["threadId"],
        "snippet": msg.get("snippet", ""),
        "from": h.get("from", ""),
        "to": h.get("to", ""),
        "subject": h.get("subject", "(no subject)"),
        "message_id": h.get("message-id", ""),
        "reply_to": h.get("reply-to") or h.get("from", ""),
        "in_reply_to": h.get("in-reply-to", ""),
        "references": h.get("references", ""),
    }


def fetch_recent(query: str = "newer_than:1d in:inbox", limit: int = 100) -> list[dict]:
    """Metadata for matching inbox mail. Sequential on purpose: batching 40 gets trips Gmail's 429 rate limit."""
    svc = _svc()
    ids = svc.users().messages().list(userId="me", q=query, maxResults=limit).execute().get("messages", [])
    return [
        _parse(
            svc.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=HEADERS)
            .execute(num_retries=3)
        )
        for m in ids
    ]

def get_message(msg_id: str) -> dict:
    return _parse(
        _svc().users().messages().get(userId="me", id=msg_id, format="metadata", metadataHeaders=HEADERS).execute(num_retries=3)
    )


def _raw(d: dict) -> dict:
    """{to, subject, body, thread_id?, in_reply_to?, references?} -> Gmail draft body."""
    m = EmailMessage()
    m["To"], m["Subject"] = d["to"], d["subject"]
    if d.get("in_reply_to"):
        m["In-Reply-To"] = d["in_reply_to"]
        refs = d.get("references", "")
        m["References"] = refs if d["in_reply_to"] in refs else f"{refs} {d['in_reply_to']}".strip()
    m.set_content(d["body"])
    msg = {"raw": base64.urlsafe_b64encode(m.as_bytes()).decode()}
    if d.get("thread_id"):
        msg["threadId"] = d["thread_id"]
    return {"message": msg}


def create_draft(d: dict) -> str:
    return _svc().users().drafts().create(userId="me", body=_raw(d)).execute()["id"]


def update_draft(draft_id: str, d: dict) -> None:
    _svc().users().drafts().update(userId="me", id=draft_id, body=_raw(d)).execute()


def read_draft(draft_id: str) -> dict:
    msg = _svc().users().drafts().get(userId="me", id=draft_id, format="full").execute()["message"]
    d = _parse(msg)
    d["body"] = base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode()
    return d


def send_draft(draft_id: str) -> None:
    _svc().users().drafts().send(userId="me", body={"id": draft_id}).execute()


def delete_draft(draft_id: str) -> None:
    _svc().users().drafts().delete(userId="me", id=draft_id).execute()