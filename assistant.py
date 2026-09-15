"""One Groq call turns a chat message into to-do / target / calendar changes (or an email hand-off)."""
import json
import re
from datetime import timedelta

import calendar_client as cal
import notifier
import summarizer

SYSTEM = (
    "You are the user's personal assistant on Telegram with access to their Google Tasks "
    "(TODOS = to-do list, TARGETS = goals for this week) and Google Calendar (EVENTS, next 7 days).\n"
    "Reply with ONLY a JSON object. Fields, all optional except text:\n"
    '"text": plain-text message for the user, concise, "- " bullets; when you plan a day, list the schedule\n'
    '"email": the user\'s instruction verbatim when they want an email drafted/replied/sent (do nothing else then)\n'
    '"add_todos": [{"title": str, "due": "YYYY-MM-DD" or null}]\n'
    '"complete_todos": [todo id]\n'
    '"add_targets": [{"title": str}]\n'
    '"complete_targets": [target id]\n'
    '"add_events": [{"title": str, "start": "YYYY-MM-DDTHH:MM", "end": "YYYY-MM-DDTHH:MM"}] (local time)\n'
    '"update_events": [{"id": str, "title"?: str, "start"?: str, "end"?: str}]\n'
    '"delete_events": [event id]\n'
    "Planning a day (\"plan my day\", \"schedule ...\"): you MUST put every block into add_events (skip breaks and "
    "meals), fitted around existing EVENTS, realistic durations, 08:00-22:00 unless told otherwise; text lists the "
    "same blocks. Questions about schedule/todos/targets: answer from context, change nothing. Never invent ids."
)


def _context() -> str:
    n = cal.now()
    todos = "\n".join(f"- [{t['id']}] {t['title']}" + (f" (due {t['due']})" if t["due"] else "") for t in cal.tasks(cal.TODOS))
    targets = "\n".join(f"- [{t['id']}] {t['title']}" for t in cal.tasks(cal.TARGETS))
    evs = "\n".join(f"- [{e['id']}] {e['start']} -> {e['end']} {e['title']}" for e in cal.events(n, n + timedelta(days=7)))
    return (f"NOW: {n:%A %Y-%m-%d %H:%M} ({cal.TZ_NAME})\n\nTODOS:\n{todos or '(none)'}\n\n"
            f"TARGETS:\n{targets or '(none)'}\n\nEVENTS:\n{evs or '(none)'}")


def handle(text: str) -> str | None:
    """Apply the assistant's actions and message the user. Returns an email instruction if that's what was asked."""
    raw = summarizer.chat(SYSTEM, f"{_context()}\n\nMESSAGE: {text}", json_mode=True)
    out = json.loads(re.sub(r"^```\w*|```$", "", raw, flags=re.M).strip())
    if out.get("email"):
        return out["email"]
    for t in out.get("add_todos") or []:
        cal.add_task(cal.TODOS, t["title"], t.get("due"))
    for i in out.get("complete_todos") or []:
        cal.complete_task(cal.TODOS, i)
    for t in out.get("add_targets") or []:
        cal.add_task(cal.TARGETS, t["title"])
    for i in out.get("complete_targets") or []:
        cal.complete_task(cal.TARGETS, i)
    for e in out.get("add_events") or []:
        cal.add_event(e["title"], e["start"], e["end"])
    for e in out.get("update_events") or []:
        cal.update_event(e["id"], e.get("title"), e.get("start"), e.get("end"))
    for i in out.get("delete_events") or []:
        cal.delete_event(i)
    notifier.send(out.get("text") or "Done.", parse_mode=None)
    return None


def remind(lead_minutes: int = 15) -> int:
    """Telegram a reminder for each timed event starting within lead_minutes; each event reminded once."""
    n = cal.now()
    sent = 0
    for e in cal.events(n, n + timedelta(minutes=lead_minutes)):
        if e["reminded"] or len(e["start"]) <= 10:  # all-day events carry no time
            continue
        start = cal.datetime.fromisoformat(e["start"]).astimezone(cal.TZ)
        if not n <= start <= n + timedelta(minutes=lead_minutes):
            continue  # list() also returns events already in progress
        mins = max(1, int((start - n).total_seconds() // 60))
        notifier.send(f"⏰ In {mins} min: {e['title']} ({start:%H:%M})", parse_mode=None)
        cal.mark_reminded(e["id"])
        sent += 1
    return sent


def agenda() -> str:
    """Today's events + open to-dos + targets, for the morning briefing (Telegram Markdown-escaped)."""
    esc = lambda s: re.sub(r"([_*\[`])", r"\\\1", s)  # noqa: E731
    n = cal.now()
    day_end = n.replace(hour=23, minute=59, second=59)
    evs = [f"- {e['start'][11:16] or 'all day'} {esc(e['title'])}" for e in cal.events(n.replace(hour=0, minute=0), day_end)]
    todos = [f"- {esc(t['title'])}" + (f" (due {t['due']})" if t["due"] else "") for t in cal.tasks(cal.TODOS)]
    targets = [f"- {esc(t['title'])}" for t in cal.tasks(cal.TARGETS)]
    return "\n".join(
        ["*Today*"] + (evs or ["- nothing scheduled"]) +
        ["", "*To-do*"] + (todos or ["- empty"]) +
        ["", "*Weekly targets*"] + (targets or ["- none set"])
    )