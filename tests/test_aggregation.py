import pytest

pytest.importorskip("pyspark")

from pyspark.sql import SparkSession

from streaming.aggregation import aggregate_windows


@pytest.fixture(scope="module")
def spark():
    session = SparkSession.builder.master("local[2]").appName("aggregation-test").getOrCreate()
    yield session
    session.stop()


def test_aggregation_counts(spark):
    rows = [
        ("2026-01-01 00:00:01", "all", "positive", 0.9),
        ("2026-01-01 00:00:05", "all", "negative", 0.1),
        ("2026-01-01 00:00:10", "all", "neutral", 0.5),
    ]
    frame = spark.createDataFrame(rows, ["event_time", "keyword", "label", "score"]).withColumn(
        "event_time", __import__("pyspark").sql.functions.to_timestamp("event_time")
    )
    result = aggregate_windows(frame).collect()
    assert result[0].total == 3
    assert (result[0].positive, result[0].negative, result[0].neutral) == (1, 1, 1)
