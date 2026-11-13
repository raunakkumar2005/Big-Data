"""Seed the optional hosted MongoDB backend with pre-recorded sample data."""
from __future__ import annotations

import csv
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pymongo import MongoClient


def main() -> None:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI is required to seed the demo")
    path = Path(__file__).parents[1] / "data" / "sample" / "demo_posts_scored.csv"
    now = datetime.now(timezone.utc)
    client = MongoClient(uri)
    collection = client[os.getenv("MONGODB_DATABASE", "sentiment_tracker")][os.getenv("MONGODB_COLLECTION", "aggregates")]
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    posts = []
    for index, row in enumerate(rows):
        created_at = now - timedelta(seconds=(len(rows) - index) * 86400 / max(len(rows), 1))
        posts.append({**row, "created_at": created_at, "source": "replay", "keyword": "all"})
    collection.replace_one({"_id": "demo"}, {"_id": "demo", "pre_recorded": True, "posts": random.sample(posts, min(200, len(posts)))}, upsert=True)
    print(f"seeded {len(posts)} pre-recorded posts")


if __name__ == "__main__":
    main()
