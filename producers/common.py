"""Shared producer configuration and Kafka message formatting."""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterator

from dotenv import load_dotenv
import yaml

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if TYPE_CHECKING:
    from kafka import KafkaProducer


def settings() -> dict:
    return yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))


def producer() -> KafkaProducer:
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", settings()["storage"]["kafka_bootstrap_servers"]),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        retries=5,
    )


def post_message(text: str, source: str, keyword: str = "all", true_label: str | int | None = None) -> dict[str, Any]:
    message: dict[str, Any] = {
        "post_id": str(uuid.uuid4()),
        "source": source,
        "text": text,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "keyword": keyword,
    }
    if true_label is not None:
        message["true_label"] = str(true_label)
    return message


def matching_keyword(text: str, keywords: list[str]) -> str | None:
    if not keywords:
        return "all"
    lowered = text.casefold()
    matches = [keyword for keyword in keywords if keyword.casefold() in lowered]
    return matches[0] if matches else None


def send_messages(messages: Callable[[], Iterator[dict[str, Any]]], rate: float | None = None, loop: bool = False) -> None:
    kafka = producer()
    started = time.monotonic()
    sent = 0
    try:
        while True:
            for message in messages():
                kafka.send("social_posts", message)
                sent += 1
                if sent % 100 == 0:
                    logging.info("published %d posts", sent)
                if rate and rate > 0:
                    time.sleep(1 / rate)
            if not loop:
                break
    except KeyboardInterrupt:
        logging.info("stopping producer")
    finally:
        kafka.flush()
        logging.info("published %d posts in %.1fs", sent, time.monotonic() - started)
