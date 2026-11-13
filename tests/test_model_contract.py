import json
from pathlib import Path

import pytest

pytest.importorskip("pyspark")

from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession


def test_model_contract():
    root = Path(__file__).parents[1]
    model_path = root / "model" / "sentiment_pipeline_model"
    if not (model_path / "stages").exists():
        pytest.fail("supplied PipelineModel stages are missing")
    spark = SparkSession.builder.master("local[2]").appName("model-contract-test").getOrCreate()
    try:
        expected = json.loads((root / "model" / "metrics.json").read_text())["environment"]["spark"]
        assert spark.version.split(".")[:2] == expected.split(".")[:2]
        model = PipelineModel.load(str(model_path))
        output = model.transform(spark.createDataFrame([("I love it",)], ["text"]))
        assert {"prediction", "probability"} <= set(output.columns)
    finally:
        spark.stop()
