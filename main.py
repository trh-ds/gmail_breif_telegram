import logging
import sys
from datetime import date

from dotenv import load_dotenv

load_dotenv()

import gmail_client  # noqa: E402
import notifier  # noqa: E402
import seen_cache  # noqa: E402
import summarizer  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("briefing.log"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def main() -> int:
    try:
        seen = seen_cache.load()
        emails = [e for e in gmail_client.fetch_recent() if e["id"] not in seen]
        header = f"*Briefing {date.today():%a %d %b}*"
        if not emails:
            notifier.send(f"{header}\nInbox is clear.")
            log.info("run ok: 0 new emails")
            return 0
        summary = summarizer.summarize(emails)
        notifier.send(f"{header} ({len(emails)} new)\n\n{summary}")
        seen_cache.save(seen | {e["id"] for e in emails})
        log.info("run ok: %d new emails", len(emails))
        return 0
    except Exception as exc:
        log.exception("run failed")
        try:
            notifier.send(f"Briefing failed: {type(exc).__name__}: {str(exc)[:300]}")
        except Exception:
            log.exception("could not send failure notice")
        return 1


if __name__ == "__main__":
    sys.exit(main())
