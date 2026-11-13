"""Pure scoring helpers for the supplied Spark PipelineModel."""
from __future__ import annotations

from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def score_posts(posts: DataFrame, model: PipelineModel, margin: float) -> DataFrame:
    """Score text using the model's complete preprocessing pipeline."""
    if not 0 <= margin < 0.5:
        raise ValueError("neutral margin must be in [0, 0.5)")
    scored = model.transform(posts.select(*posts.columns))
    return (
        scored.withColumn("score", vector_to_array("probability")[1])
        .withColumn(
            "label",
            F.when(F.abs(F.col("score") - F.lit(0.5)) < F.lit(margin), "neutral")
            .when(F.col("score") >= F.lit(0.5), "positive")
            .otherwise("negative"),
        )
    )


def select_classified_columns(scored: DataFrame) -> DataFrame:
    """Keep only the stable post contract before persistence."""
    columns = [
        "post_id", "source", "text", "created_at", "keyword",
        "true_label", "score", "label", "event_time", "day",
    ]
    return scored.select(*[name for name in columns if name in scored.columns])
