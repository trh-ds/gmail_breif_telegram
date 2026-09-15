# gmail_breif

Daily Gmail triage → Groq → Telegram, plus a Telegram bot that drafts and sends email for you. Costs $0.

## 1. Google Cloud OAuth (Gmail)

1. https://console.cloud.google.com → New project.
2. **APIs & Services → Library** → enable **Gmail API**.
3. **OAuth consent screen** → External → add your Gmail as a *test user*.
4. **Credentials → Create credentials → OAuth client ID → Desktop app** → download JSON → save as `credentials.json` in this folder.

## 2. Groq API key (free tier)

https://console.groq.com/keys → Create API Key.

## 3. Telegram bot + chat ID

1. Message **@BotFather** → `/newbot` → copy the token.
2. Message **@userinfobot** → it replies with your numeric chat ID.
3. Open your new bot and press **Start** (bots can't message you first).

## 4. Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\pip install .
Copy-Item .env.example .env   # fill in GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
.\.venv\Scripts\python briefing.py   # first run opens a browser for Google consent, writes token.json
```

Files created at runtime (all gitignored): `token.json`, `seen_ids.json`, `briefing.log`.

## 5. Schedule

### Option A: cron on any Linux box / VPS / Raspberry Pi (07:00 daily)

```
0 7 * * * cd /path/to/gmail_breif && .venv/bin/python briefing.py >> briefing.log 2>&1
```

### Option B: Vercel (free Hobby plan, no machine needed)

Run step 4 once locally so `token.json` exists, then:

```powershell
npx vercel login
npx vercel link --yes
# add each var below with:  echo VALUE | npx vercel env add NAME production   (or via the dashboard)
npx vercel --prod --yes
```

| Variable | Value |
|---|---|
| `GROQ_API_KEY` | from step 2 |
| `TELEGRAM_BOT_TOKEN` | from step 3 |
| `TELEGRAM_CHAT_ID` | from step 3 |
| `GMAIL_TOKEN_JSON` | full contents of `token.json` (one line) |
| `SEEN_CACHE_PATH` | `/tmp/seen_ids.json` |
| `LOG_PATH` | `/tmp/briefing.log` |
| `CRON_SECRET` | any random string (Vercel sends it as `Authorization: Bearer ...`) |

Note: on Windows, PowerShell's pipe appends a newline — Vercel rejects `CRON_SECRET` with trailing whitespace.
Use the dashboard or `cmd /c "npx vercel env add NAME production < value.txt"`.

`vercel.json` schedules `GET /api/cron` at `30 1 * * *` UTC (07:00 IST) — edit for your timezone.
Hobby plan runs crons once per day and may fire anywhere within that hour.
`pyproject.toml` holds the deps (Vercel's Python runtime uses `uv`) and the `api.cron:handler` entrypoint.

Test now: `curl -H "Authorization: Bearer <CRON_SECRET>" https://<your-app>.vercel.app/api/cron`
Logs: **Project → Logs** on vercel.com.

`credentials.json` is only needed locally for the one-time consent; Vercel never sees it.
## 6. Telegram bot: draft & send email

After deploying, register the webhook once (uses the same `CRON_SECRET`):

```powershell
Invoke-RestMethod -Method Post "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" -Body @{ url = "https://<your-app>.vercel.app/api/telegram"; secret_token = "<CRON_SECRET>"; allowed_updates = '["message","callback_query"]' }
```

Then just message the bot:

- `reply to Priya saying the deck will be ready Thursday` → finds the email in your last 7 days, drafts a threaded reply
- `email alice@x.com about moving Monday's call to 3pm` → drafts a new email
- Reply to the draft message with `shorter` / `more formal` / anything → revised draft
- **Send ✅** sends it from your Gmail; **Discard 🗑** deletes the draft

Drafts are real Gmail drafts, so you can also edit/send them from the Gmail app. Only your `TELEGRAM_CHAT_ID` is served.
Scopes: `gmail.readonly` + `gmail.compose` (drafts + send; the bot can't delete or modify existing mail).
Optional `SENDER_NAME` env var controls the sign-off.
## Why $0

Gmail API (free quota), Groq free tier, Telegram Bot API (free), Vercel Hobby (free).

