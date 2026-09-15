import os

import requests


def send(text: str) -> None:
    r = requests.post(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
        json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:4096], "parse_mode": "Markdown"},
        timeout=30,
    )
    r.raise_for_status()
