import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import briefing  # noqa: E402  (loads .env, configures logging)
import bot  # noqa: E402
import notifier  # noqa: E402

log = logging.getLogger(__name__)


class handler(BaseHTTPRequestHandler):
    def _reply(self, code: int, body: str = "ok") -> None:
        self.send_response(code)
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):  # Vercel cron -> daily briefing
        if self.path.split("?")[0] != "/api/cron":
            return self._reply(404, "not found")
        secret = os.environ.get("CRON_SECRET")
        if secret and self.headers.get("Authorization") != f"Bearer {secret}":
            return self._reply(401, "unauthorized")
        code = briefing.main()
        self._reply(200 if code == 0 else 500, "ok" if code == 0 else "failed")

    def do_POST(self):  # Telegram webhook
        if self.path.split("?")[0] != "/api/telegram":
            return self._reply(404, "not found")
        secret = os.environ.get("CRON_SECRET")
        if not secret or self.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
            return self._reply(401, "unauthorized")
        update = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        try:
            bot.handle(update)
        except Exception as exc:  # always 200, otherwise Telegram redelivers the same update
            log.exception("bot failed")
            notifier.send(f"Bot error: {type(exc).__name__}: {str(exc)[:300]}", parse_mode=None)
        self._reply(200)