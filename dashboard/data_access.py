"""Backend-neutral dashboard queries."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import csv
from datetime import datetime, timedelta, timezone


logger = logging.getLogger(__name__)


def read_demo_data() -> tuple[list[dict], list[dict], bool]:
    """Read the bundled scored sample without requiring a service."""
    path = Path(__file__).resolve().parents[1] / "data" / "sample" / "demo_posts_scored.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    now = datetime.now(timezone.utc)
    posts = []
    for index, row in enumerate(rows):
        posts.append(
            {
                "post_id": f"demo-{index}",
                "text": row.get("text", ""),
                "score": row.get("score"),
                "label": row.get("pred_label", "neutral"),
                "source": "bundled demo",
                "keyword": "all",
                "created_at": now - timedelta(minutes=len(rows) - index),
            }
        )
    return posts, [], True


def read_data(hours: int = 24) -> tuple[list[dict], list[dict], bool]:
    backend = os.getenv("DATA_BACKEND", "cassandra").lower()
    if backend in {"demo", "local", "sample"}:
        return read_demo_data()
    if backend == "mongodb":
        from pymongo import MongoClient

        uri = os.getenv("MONGODB_URI")
        if not uri:
            return [], [], False
        collection = MongoClient(uri)[os.getenv("MONGODB_DATABASE", "sentiment_tracker")][os.getenv("MONGODB_COLLECTION", "aggregates")]
        doc = collection.find_one({"_id": "latest"}) or collection.find_one({"_id": "demo"}) or {}
        return doc.get("posts", []), doc.get("aggregates", []), bool(doc.get("pre_recorded"))
    from cassandra.cluster import Cluster

    host = os.getenv("CASSANDRA_HOST", "localhost")
    port = int(os.getenv("CASSANDRA_PORT", "9042"))
    cluster = Cluster([host], port=port)
    try:
        session = cluster.connect("sentiment")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        posts = [row._asdict() for row in session.execute("SELECT * FROM posts LIMIT 200")]
        aggregates = [row._asdict() for row in session.execute("SELECT * FROM window_counts LIMIT 500")]
        return posts, aggregates, False
    except Exception as exc:
        logger.exception("Unable to read Cassandra at %s:%s: %s", host, port, exc)
        raise RuntimeError(f"Dashboard cannot connect to Cassandra at {host}:{port}") from exc
    finally:
        cluster.shutdown()
