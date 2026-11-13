# Sentiment model card

- **Task:** binary sentiment (negative / positive) on short English social-media text, plus a low-confidence "neutral" band.
- **Training data:** Sentiment140 (600,931 de-duplicated tweets, 2009). Live posts from other sources differ in style and topic, so expect lower accuracy there.
- **Model:** Spark ML PipelineModel: SQL cleaning -> regex tokenizer -> stop-words (negations kept) -> bigrams -> CountVectorizer -> IDF -> Logistic Regression.
- **Test accuracy / F1 / AUC:** 0.776 / 0.7759 / 0.8458
- **Spark version used to save it:** 3.5.3 (load it with the same 3.5.x line).

## Input and output

- Input: a DataFrame with a string column `text` (no `label` needed).
- Output columns: `prediction` (0.0 = negative, 1.0 = positive), `probability` (vector `[P(negative), P(positive)]`), `rawPrediction`, plus intermediate columns (`clean_text`, `tokens`, ...).
- Neutral band: label a post `neutral` when `|P(positive) - 0.5| < 0.1` (configurable; see `neutral_band.json` for the coverage/accuracy trade-off).

## Usage

```python
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

model = PipelineModel.load("model/sentiment_pipeline_model")
scored = (model.transform(posts.select("text"))
          .withColumn("score", vector_to_array("probability")[1]))
scored = scored.withColumn(
    "label",
    F.when(F.abs(F.col("score") - 0.5) < 0.1, "neutral")
     .when(F.col("score") >= 0.5, "positive")
     .otherwise("negative"))
```

## Limitations

- Trained on 2009 tweets; slang, emojis, sarcasm, non-English text and technical vocabulary (for example Hacker News) are weak spots.
- Labels in Sentiment140 come from emoticons, so they are noisy; roughly 80% accuracy is typical for this dataset.
- The neutral band reflects model uncertainty, not a real neutral class.
- Sample files contain raw tweets and may include strong language.
