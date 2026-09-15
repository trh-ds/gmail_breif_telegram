import os

import requests


def call(method: str, **payload) -> dict:
    r = requests.post(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}",
        json={k: v for k, v in payload.items() if v is not None},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def send(text: str, parse_mode: str | None = "Markdown", **kw) -> None:
    call("sendMessage", chat_id=os.environ["TELEGRAM_CHAT_ID"], text=text[:4096], parse_mode=parse_mode, **kw)