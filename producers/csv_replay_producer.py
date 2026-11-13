"""Replay labelled sample posts through Kafka."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import matching_keyword, post_message, send_messages, settings


def messages(path: Path, keywords: list[str]):
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            keyword = matching_keyword(row["text"], keywords)
            if keyword is not None:
                yield post_message(row["text"], "replay", keyword, row.get("label"))


def main() -> None:
    config = settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=Path(__file__).parents[1] / "data" / "sample" / "replay_sample.csv")
    parser.add_argument("--rate", type=float, default=config["replay"]["posts_per_second"])
    parser.add_argument("--loop", action="store_true", default=config["replay"]["loop"])
    args = parser.parse_args()
    send_messages(lambda: messages(args.path, config["app"]["keywords"]), args.rate, args.loop)


if __name__ == "__main__":
    main()
