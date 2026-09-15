import os

import requests

SYSTEM_PROMPT = (
    "You triage a personal inbox. Sort every email into exactly one bucket:\n"
    "RED = needs a reply today, YELLOW = FYI, GREEN = low priority / promo / newsletter.\n"
    "Output format, nothing else, no preamble:\n"
    "*RED*\n- <sender>: <max 12 words>\n*YELLOW*\n- ...\n*GREEN*\n- ...\n"
    "One line per email, max 12 words per line. Omit a bucket heading if it is empty."
)


def chat(system: str, user: str, json_mode: bool = False) -> str:
    payload = {
        "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        "temperature": 0.2,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def summarize(emails: list[dict]) -> str:
    body = "\n\n".join(
        f"From: {e['from']}\nSubject: {e['subject']}\nSnippet: {e['snippet']}" for e in emails
    )
    return chat(SYSTEM_PROMPT, body)