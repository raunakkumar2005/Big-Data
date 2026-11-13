"""Windowed aggregation transformations."""
from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def aggregate_windows(
    posts: DataFrame,
    window_duration: str = "1 minute",
    slide_duration: str | None = None,
) -> DataFrame:
    """Aggregate sentiment counts and average score by keyword and event time."""
    window = F.window("event_time", window_duration, slide_duration) if slide_duration else F.window(
        "event_time", window_duration
    )
    return (
        posts.groupBy(window, "keyword")
        .agg(
            F.sum(F.when(F.col("label") == "positive", 1).otherwise(0)).alias("positive"),
            F.sum(F.when(F.col("label") == "negative", 1).otherwise(0)).alias("negative"),
            F.sum(F.when(F.col("label") == "neutral", 1).otherwise(0)).alias("neutral"),
            F.count("*").alias("total"),
            F.avg("score").alias("average_score"),
        )
        .select(
            "keyword",
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            "positive", "negative", "neutral", "total", "average_score",
        )
    )
