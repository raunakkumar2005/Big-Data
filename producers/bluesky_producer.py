"""Consume public Bluesky Jetstream posts without authentication."""
from __future__ import annotations

import json
import time

import websocket

from common import matching_keyword, post_message, producer, settings


def main() -> None:
    config = settings()
    keywords = config["app"]["keywords"]
    endpoint = config["sources"]["bluesky_endpoint"]
    kafka = producer()
    backoff = 1
    try:
        while True:
            try:
                socket = websocket.create_connection(endpoint, timeout=30)
                backoff = 1
                for raw in socket:
                    event = json.loads(raw)
                    record = event.get("commit", {}).get("record", {})
                    text = record.get("text", "")
                    langs = record.get("langs", [])
                    if text and (not langs or "en" in langs):
                        keyword = matching_keyword(text, keywords)
                        if keyword is not None:
                            kafka.send("social_posts", post_message(text, "bluesky", keyword))
            except (OSError, websocket.WebSocketException) as exc:
                print(f"Bluesky connection failed: {exc}; retrying in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
    except KeyboardInterrupt:
        pass
    finally:
        kafka.flush()


if __name__ == "__main__":
    main()
