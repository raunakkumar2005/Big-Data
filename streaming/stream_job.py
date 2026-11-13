"""Kafka -> Spark ML -> Cassandra Structured Streaming job."""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

from aggregation import aggregate_windows
from scoring import score_posts, select_classified_columns


ROOT = Path(__file__).resolve().parents[1]


def load_settings() -> dict:
    return yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))


def require_spark_line(spark_version: str) -> None:
    metrics = json.loads((ROOT / "model" / "metrics.json").read_text(encoding="utf-8"))
    expected = metrics["environment"]["spark"].split(".")[:2]
    actual = spark_version.split(".")[:2]
    if actual != expected:
        raise RuntimeError(f"Spark version mismatch: model requires {'.'.join(expected)}.x, runtime is {spark_version}")


def write_cassandra(batch, batch_id: int, table: str, keyspace: str) -> None:
    (
        batch.coalesce(4)
        .write.format("org.apache.spark.sql.cassandra")
        .options(
            keyspace=keyspace,
            table=table,
            **{
                "spark.cassandra.output.concurrent.writes": "2",
                "spark.cassandra.output.batch.size.rows": "50",
            },
        )
        .mode("append")
        .save()
    )


def main() -> None:
    settings = load_settings()
    cassandra_host = os.getenv("CASSANDRA_HOST", settings["storage"]["cassandra_host"])
    cassandra_port = os.getenv("CASSANDRA_PORT", str(settings["storage"]["cassandra_port"]))
    spark = (
        SparkSession.builder.appName("live-public-sentiment-tracker")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")
        .config("spark.cassandra.connection.host", cassandra_host)
        .config("spark.cassandra.connection.port", cassandra_port)
        .getOrCreate()
    )
    require_spark_line(spark.version)
    schema = StructType([
        StructField("post_id", StringType(), False),
        StructField("source", StringType(), False),
        StructField("text", StringType(), False),
        StructField("created_at", StringType(), False),
        StructField("keyword", StringType(), False),
        StructField("true_label", StringType(), True),
    ])
    kafka = settings["storage"]["kafka_bootstrap_servers"]
    raw = spark.readStream.format("kafka").option("kafka.bootstrap.servers", kafka).option(
        "subscribe", settings["storage"]["kafka_topic"]
    ).option("startingOffsets", "latest").load()
    posts = raw.select(F.from_json(F.col("value").cast("string"), schema).alias("post")).select("post.*")
    posts = posts.withColumn("event_time", F.to_timestamp("created_at")).withWatermark(
        "event_time", settings["streaming"]["watermark"]
    )
    model = PipelineModel.load(str(ROOT / "model" / "sentiment_pipeline_model"))
    classified = score_posts(posts, model, settings["app"]["neutral_margin"]).withColumn(
        "day", F.to_date("event_time")
    )
    classified = select_classified_columns(classified)
    aggregates = aggregate_windows(classified, "1 minute")
    checkpoint = settings["streaming"]["checkpoint_dir"]
    classified.writeStream.foreachBatch(
        lambda batch, batch_id: write_cassandra(batch, batch_id, "posts", settings["storage"]["cassandra_keyspace"])
    ).option("checkpointLocation", checkpoint + "/posts").start()
    aggregates.writeStream.foreachBatch(
        lambda batch, batch_id: write_cassandra(batch, batch_id, "window_counts", settings["storage"]["cassandra_keyspace"])
    ).outputMode("update").option("checkpointLocation", checkpoint + "/aggregates").start()
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
