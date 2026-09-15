# gmail_breif

Daily Gmail triage → Groq (llama-3.3-70b) → Telegram. Runs once a day, costs $0.

## 1. Google Cloud OAuth (Gmail, readonly)

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
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env   # fill in GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
.\.venv\Scripts\python main.py   # first run opens a browser for Google consent, writes token.json
```

Files created at runtime (all gitignored): `token.json`, `seen_ids.json`, `briefing.log`.

## 5. Schedule

### Option A: cron on any Linux box / VPS / Raspberry Pi (07:00 daily)

```
0 7 * * * cd /path/to/gmail_breif && .venv/bin/python main.py >> briefing.log 2>&1
```

### Option B: GitHub Actions (free, no machine needed) — `.github/workflows/briefing.yml`

Run step 4 once locally to produce `token.json`, then add these **repo secrets**
(Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `GROQ_API_KEY` | from step 2 |
| `TELEGRAM_BOT_TOKEN` | from step 3 |
| `TELEGRAM_CHAT_ID` | from step 3 |
| `GMAIL_CREDENTIALS_JSON` | full contents of `credentials.json` |
| `GMAIL_TOKEN_JSON` | full contents of `token.json` |

Cron is `30 1 * * *` UTC = 07:00 IST; edit the `cron:` line for your timezone.
Trigger manually via **Actions → daily-briefing → Run workflow**.

> Vercel isn't a fit: serverless functions have no persistent disk, so `token.json`
> and the seen-ID cache can't survive between runs and the one-time OAuth browser
> flow can't happen there. GitHub Actions gives the same $0 daily cron without that problem.

## Why $0

Gmail API (free quota), Groq free tier, Telegram Bot API (free), GitHub Actions (free minutes).
