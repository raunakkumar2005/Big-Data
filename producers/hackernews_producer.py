"""Poll Hacker News public API for stories and comments."""
from __future__ import annotations

import time

import requests

from common import matching_keyword, post_message, producer, settings


def main() -> None:
    config = settings()
    keywords = config["app"]["keywords"]
    base = "https://hacker-news.firebaseio.com/v0"
    kafka = producer()
    seen: set[int] = set()
    try:
        while True:
            ids = requests.get(f"{base}/newstories.json", timeout=15).json()[:100]
            for item_id in ids:
                if item_id in seen:
                    continue
                seen.add(item_id)
                item = requests.get(f"{base}/item/{item_id}.json", timeout=15).json() or {}
                text = item.get("title") or item.get("text") or ""
                keyword = matching_keyword(text, keywords)
                if text and keyword is not None:
                    kafka.send("social_posts", post_message(text, "hackernews", keyword))
            time.sleep(config["sources"]["hackernews_poll_seconds"])
    except KeyboardInterrupt:
        pass
    finally:
        kafka.flush()


if __name__ == "__main__":
    main()
