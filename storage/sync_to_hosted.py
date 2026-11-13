"""Copy recent Cassandra data to MongoDB when configured."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from cassandra.cluster import Cluster
from pymongo import MongoClient


def main() -> None:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI is required to sync hosted data")
    cassandra = Cluster([os.getenv("CASSANDRA_HOST", "localhost")]).connect("sentiment")
    mongo = MongoClient(uri)[os.getenv("MONGODB_DATABASE", "sentiment_tracker")]
    aggregates = list(cassandra.execute("SELECT * FROM window_counts LIMIT 500"))
    posts = list(cassandra.execute("SELECT * FROM posts LIMIT 200"))
    collection = mongo[os.getenv("MONGODB_COLLECTION", "aggregates")]
    collection.replace_one({"_id": "latest"}, {
        "_id": "latest", "aggregates": [row._asdict() for row in aggregates],
        "posts": [row._asdict() for row in posts],
        "synced_at": datetime.now(timezone.utc),
    }, upsert=True)
    print(f"synced {len(posts)} posts and {len(aggregates)} aggregates")


if __name__ == "__main__":
    main()
