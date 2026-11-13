"""Validate and smoke-test the supplied Spark PipelineModel."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    metrics = json.loads((ROOT / "model" / "metrics.json").read_text(encoding="utf-8"))
    expected = metrics["environment"]["spark"]
    model_path = ROOT / "model" / "sentiment_pipeline_model"
    if not (model_path / "metadata").exists() or not (model_path / "stages").exists():
        print(f"FAIL: supplied PipelineModel is incomplete: {model_path}", file=sys.stderr)
        return 1

    spark = (
        SparkSession.builder.master("local[2]")
        .appName("sentiment-model-check")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    try:
        actual = spark.version
        if actual.split(".")[:2] != expected.split(".")[:2]:
            print(f"FAIL: Spark {actual} does not match required {expected} 3.5.x line", file=sys.stderr)
            return 1
        model = PipelineModel.load(str(model_path))
        posts = spark.createDataFrame(
            [("I absolutely love this!",), ("This is awful and disappointing.",), ("The package arrived today.",)],
            ["text"],
        )
        output = model.transform(posts)
        required = {"prediction", "probability"}
        missing = required.difference(output.columns)
        if missing:
            print(f"FAIL: model output missing columns: {sorted(missing)}", file=sys.stderr)
            return 1
        print(f"PASS: Spark {actual}; model contract and {output.count()} smoke rows verified")
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    raise SystemExit(main())
