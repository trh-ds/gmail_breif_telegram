"""Google Calendar events + Google Tasks (to-dos in the default list, targets in "Weekly Targets")."""
import os
from datetime import datetime, timedelta  # noqa: F401  (timedelta re-exported for callers)
from zoneinfo import ZoneInfo

from google_auth import service

TZ_NAME = os.environ.get("TZ_NAME", "Asia/Kolkata")
TZ = ZoneInfo(TZ_NAME)
TODOS, TARGETS = "@default", "Weekly Targets"


def now() -> datetime:
    return datetime.now(TZ)


def _dt(s: str) -> dict:
    return {"dateTime": s if len(s) > 16 else f"{s}:00", "timeZone": TZ_NAME}  # "YYYY-MM-DDTHH:MM" local


# --- calendar ---
def events(start: datetime, end: datetime) -> list[dict]:
    r = service("calendar", "v3").events().list(
        calendarId="primary", timeMin=start.isoformat(), timeMax=end.isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=100,
    ).execute()
    return [{
        "id": e["id"],
        "title": e.get("summary", "(untitled)"),
        "start": e["start"].get("dateTime", e["start"].get("date")),
        "end": e["end"].get("dateTime", e["end"].get("date")),
        "reminded": e.get("extendedProperties", {}).get("private", {}).get("reminded"),
    } for e in r.get("items", [])]


def add_event(title: str, start: str, end: str) -> str:
    body = {"summary": title, "start": _dt(start), "end": _dt(end)}
    return service("calendar", "v3").events().insert(calendarId="primary", body=body).execute()["id"]


def update_event(event_id: str, title: str | None = None, start: str | None = None, end: str | None = None) -> None:
    body = {k: v for k, v in {"summary": title, "start": start and _dt(start), "end": end and _dt(end)}.items() if v}
    service("calendar", "v3").events().patch(calendarId="primary", eventId=event_id, body=body).execute()


def delete_event(event_id: str) -> None:
    service("calendar", "v3").events().delete(calendarId="primary", eventId=event_id).execute()


def mark_reminded(event_id: str) -> None:
    body = {"extendedProperties": {"private": {"reminded": "1"}}}
    service("calendar", "v3").events().patch(calendarId="primary", eventId=event_id, body=body).execute()


# --- tasks ---
def _list_id(name: str) -> str:
    if name == TODOS:
        return name
    svc = service("tasks", "v1")
    for tl in svc.tasklists().list().execute().get("items", []):
        if tl["title"] == name:
            return tl["id"]
    return svc.tasklists().insert(body={"title": name}).execute()["id"]


def tasks(name: str) -> list[dict]:
    r = service("tasks", "v1").tasks().list(tasklist=_list_id(name), showCompleted=False, maxResults=100).execute()
    return [{"id": t["id"], "title": t.get("title", ""), "due": (t.get("due") or "")[:10]} for t in r.get("items", [])]


def add_task(name: str, title: str, due: str | None = None) -> None:
    body = {"title": title}
    if due:
        body["due"] = f"{due}T00:00:00.000Z"
    service("tasks", "v1").tasks().insert(tasklist=_list_id(name), body=body).execute()


def complete_task(name: str, task_id: str) -> None:
    service("tasks", "v1").tasks().patch(tasklist=_list_id(name), task=task_id, body={"status": "completed"}).execute()