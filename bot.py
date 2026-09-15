"""Telegram bot: turn a chat instruction into a Gmail draft, send it on confirmation."""
import json
import os
import re

import gmail_client
import notifier
import summarizer

COMPOSE_PROMPT = (
    "You draft emails on behalf of the user. You get their recent inbox (id, from, subject, snippet) "
    "and an instruction. Return ONLY JSON:\n"
    '{"reply_to_id": "<id of the inbox email being replied to, or null for a brand-new email>", '
    '"to": "<recipient address; empty if replying>", "subject": "<subject; empty if replying>", '
    '"body": "<plain-text email body>"}\n'
    "Body: natural, concise, ready to send: greeting, content, sign-off. "
)
REVISE_PROMPT = "Rewrite this email body following the user's instruction. Return ONLY the new plain-text body."
HELP = (
    "Tell me what to send, e.g.\n"
    "- reply to John saying I'll send the invoice by Friday\n"
    "- email alice@x.com about rescheduling Monday's call\n"
    "Then press Send or Discard, or reply to the draft message with changes."
)


def _signature() -> str:
    name = os.environ.get("SENDER_NAME")
    return f"Sign off as {name}." if name else "Sign off without a name unless the instruction gives one."


def _show(draft_id: str, d: dict) -> None:
    text = f"✉️ To: {d['to']}\nSubject: {d['subject']}\n\n{d['body']}\n\nDraft: {draft_id}"
    notifier.send(text, parse_mode=None, reply_markup={"inline_keyboard": [[
        {"text": "Send ✅", "callback_data": f"send:{draft_id}"},
        {"text": "Discard \U0001F5D1", "callback_data": f"discard:{draft_id}"},
    ]]})


def _compose(instruction: str) -> None:
    inbox = gmail_client.fetch_recent("newer_than:7d in:inbox", 30)
    ctx = "\n".join(f"[{e['id']}] from: {e['from']} | subject: {e['subject']} | {e['snippet'][:120]}" for e in inbox)
    raw = summarizer.chat(
        COMPOSE_PROMPT + _signature(), f"INBOX:\n{ctx}\n\nINSTRUCTION: {instruction}", json_mode=True
    )
    out = json.loads(re.sub(r"^```\w*|```$", "", raw, flags=re.M).strip())
    d = {"to": out.get("to") or "", "subject": out.get("subject") or "", "body": out["body"]}
    if out.get("reply_to_id"):
        o = gmail_client.get_message(out["reply_to_id"])
        subj = o["subject"]
        d.update(
            to=o["reply_to"],
            subject=subj if subj.lower().startswith("re:") else f"Re: {subj}",
            thread_id=o["thread_id"],
            in_reply_to=o["message_id"],
            references=o["references"],
        )
    _show(gmail_client.create_draft(d), d)


def _revise(draft_id: str, instruction: str) -> None:
    d = gmail_client.read_draft(draft_id)
    d["body"] = summarizer.chat(REVISE_PROMPT, f"BODY:\n{d['body']}\n\nINSTRUCTION: {instruction}")
    gmail_client.update_draft(draft_id, d)
    _show(draft_id, d)


def _callback(cq: dict) -> None:
    action, draft_id = cq["data"].split(":", 1)
    if action == "send":
        gmail_client.send_draft(draft_id)
        note = "✅ Sent"
    else:
        gmail_client.delete_draft(draft_id)
        note = "\U0001F5D1 Discarded"
    notifier.call("answerCallbackQuery", callback_query_id=cq["id"], text=note)
    m = cq["message"]  # editing without reply_markup drops the buttons
    notifier.call("editMessageText", chat_id=m["chat"]["id"], message_id=m["message_id"], text=f"{m['text']}\n\n{note}")


def handle(update: dict) -> None:
    """Telegram webhook update -> action. Only the configured chat is served."""
    cq, msg = update.get("callback_query"), update.get("message")
    if cq:
        chat_id = cq["message"]["chat"]["id"]
    elif msg and msg.get("text"):
        chat_id = msg["chat"]["id"]
    else:
        return
    if str(chat_id) != os.environ["TELEGRAM_CHAT_ID"]:
        return
    if cq:
        return _callback(cq)
    text = msg["text"].strip()
    if text.startswith("/"):
        return notifier.send(HELP, parse_mode=None)
    m = re.search(r"Draft: (\S+)$", msg.get("reply_to_message", {}).get("text", ""))
    return _revise(m.group(1), text) if m else _compose(text)