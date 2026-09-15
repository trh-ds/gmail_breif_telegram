import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        secret = os.environ.get("CRON_SECRET")
        if secret and self.headers.get("Authorization") != f"Bearer {secret}":
            self.send_response(401)
            self.end_headers()
            return
        code = main.main()
        self.send_response(200 if code == 0 else 500)
        self.end_headers()
        self.wfile.write(b"ok" if code == 0 else b"failed")
