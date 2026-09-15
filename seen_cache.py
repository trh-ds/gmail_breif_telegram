import json
import os

# ponytail: on Vercel this lands in /tmp and may not survive between runs; newer_than:1d + once-a-day cron makes that harmless
CACHE_FILE = os.environ.get("SEEN_CACHE_PATH", "seen_ids.json")


def load() -> set[str]:
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE) as f:
        return set(json.load(f))


def save(ids: set[str]) -> None:
    # ponytail: keeps only the last 2000 ids; plenty for a 24h window
    with open(CACHE_FILE, "w") as f:
        json.dump(sorted(ids)[-2000:], f)


if __name__ == "__main__":
    import tempfile
    CACHE_FILE = os.path.join(tempfile.mkdtemp(), "seen.json")
    assert load() == set()
    save({"b", "a"})
    assert load() == {"a", "b"}
    print("seen_cache ok")

