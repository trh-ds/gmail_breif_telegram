"""Self-check with all external calls mocked. Run: .venv/Scripts/python test_bot.py"""
import base64
import json
import os

os.environ.update(TELEGRAM_CHAT_ID="1", TELEGRAM_BOT_TOKEN="x")
import bot  # noqa: E402
import gmail_client  # noqa: E402
import notifier  # noqa: E402
import summarizer  # noqa: E402

# MIME: reply headers + threading
raw = gmail_client._raw({"to": "j@x.com", "subject": "Re: Hi", "body": "yo", "thread_id": "t1",
                         "in_reply_to": "<a@x>", "references": "<z@x>"})
mime = base64.urlsafe_b64decode(raw["message"]["raw"]).decode()
assert raw["message"]["threadId"] == "t1" and "In-Reply-To: <a@x>" in mime and "References: <z@x> <a@x>" in mime

calls = []
notifier.call = lambda method, **p: calls.append((method, p)) or {}
gmail_client.fetch_recent = lambda q, n: [{"id": "m1", "from": "John <j@x.com>", "subject": "Invoice", "snippet": "pls"}]
gmail_client.get_message = lambda i: {"reply_to": "j@x.com", "subject": "Invoice", "thread_id": "t1",
                                      "message_id": "<a@x>", "references": ""}
created = {}
gmail_client.create_draft = lambda d: created.update(d) or "r1"
summarizer.chat = lambda s, u, json_mode=False: (
    json.dumps({"reply_to_id": "m1", "to": "", "subject": "", "body": "Hi John, Friday."}) if json_mode else "Revised"
)

# compose a reply
bot.handle({"message": {"chat": {"id": 1}, "text": "reply to john, friday"}})
assert created["to"] == "j@x.com" and created["subject"] == "Re: Invoice" and created["in_reply_to"] == "<a@x>"
assert calls[-1][0] == "sendMessage" and "Draft: r1" in calls[-1][1]["text"] and calls[-1][1]["reply_markup"]

# revise by replying to the draft message
gmail_client.read_draft = lambda i: {"to": "j@x.com", "subject": "Re: Invoice", "body": "old", "thread_id": "t1",
                                     "in_reply_to": "<a@x>", "references": "<a@x>"}
updated = {}
gmail_client.update_draft = lambda i, d: updated.update(d)
bot.handle({"message": {"chat": {"id": 1}, "text": "shorter", "reply_to_message": {"text": "x\n\nDraft: r1"}}})
assert updated["body"] == "Revised"

# confirm -> send
sent = []
gmail_client.send_draft = sent.append
bot.handle({"callback_query": {"id": "c", "data": "send:r1",
                               "message": {"chat": {"id": 1}, "message_id": 5, "text": "d"}}})
assert sent == ["r1"] and calls[-1][0] == "editMessageText" and "Sent" in calls[-1][1]["text"]

# foreign chat ignored
calls.clear()
bot.handle({"message": {"chat": {"id": 999}, "text": "hack"}})
assert calls == []
print("bot ok")