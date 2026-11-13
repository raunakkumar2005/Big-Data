# Live Public Sentiment Tracker

A laptop-friendly Big Data Analytics project using Kafka, Spark Structured Streaming, Spark MLlib inference, Cassandra, and Streamlit. The supplied Spark `PipelineModel` is loaded for inference only; this repository never trains a model or downloads training data.

## Architecture

```text
Bluesky Jetstream / Hacker News / CSV replay
                 -> Kafka social_posts
                 -> Spark Structured Streaming + supplied PipelineModel
                 -> Cassandra posts + window_counts
                 -> Streamlit dashboard
                 -> optional MongoDB Atlas sync for public deployment
```

## Supplied model

The model is a binary Logistic Regression PipelineModel saved with Spark 3.5.3. All preprocessing is inside the pipeline. A configurable probability uncertainty band labels posts `neutral`; it is not a trained neutral class.

See [model/metrics.md](model/metrics.md), [model/model_card.md](model/model_card.md), and the Model page in the dashboard for the supplied metrics and plots. The model was trained on 2009 Sentiment140 tweets with emoticon-derived labels, so Bluesky and Hacker News text is out of domain.

## Setup

1. Copy `.env.example` to `.env`.
2. Install Python 3.10+ and run `make setup`.
3. Check the supplied model with `make check-model`.
4. Start the complete local stack with `docker compose --profile streaming up -d --build` (or `make up`). Kafka topic and Cassandra schema initialization run automatically.
5. Set `KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9094` in `.env`, then run `make produce-replay` (or a public producer).
6. Open `http://localhost:8501`.

The dashboard also works without the streaming stack. If Cassandra is unavailable it
automatically opens the bundled scored sample; to select it explicitly, set
`DATA_BACKEND=demo`. The Live page includes topic inference for rows without a
keyword, search, source/sentiment/time-window filters, negative-sentiment alerts,
conversation insights, and CSV export. No API key or extra data service is required
for the demo mode.

The streaming container is available through the Compose `streaming` profile. Inspect it with `docker compose logs -f spark-submit`; stop everything with `docker compose down`.

## Tests and benchmarks

Run `make test` for offline producer and Spark aggregation/model-contract tests. `make bench` writes a machine-specific harness report to `benchmarks/results.md`; end-to-end throughput and Cassandra latency require the running stack and must be measured on the target machine.

## Public demo

Run `storage/sync_to_hosted.py` with `MONGODB_URI` configured, then deploy the dashboard and the `model/` artifacts to Streamlit Community Cloud. Set `DATA_BACKEND=mongodb` and the connection string in Streamlit secrets. Run `make seed-demo` to publish clearly pre-recorded demo data. Free-tier limits change, so check the current provider limits before deployment.

### Streamlit Community Cloud

1. Push this project to a GitHub repository without committing `.env` or any MongoDB URI.
2. Create an app with `dashboard/app.py` as the entry point.
3. Add these secrets in the app settings:

   ```toml
   DATA_BACKEND = "mongodb"
   MONGODB_URI = "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/"
   MONGODB_DATABASE = "sentiment_tracker"
   MONGODB_COLLECTION = "aggregates"
   ```

4. Run `python storage/seed_demo.py` locally with the same URI, or sync live data with
   `python storage/sync_to_hosted.py`, before opening the public app.

The dashboard uses the bundled scored sample only when explicitly configured with
`DATA_BACKEND=demo`; hosted deployment should use MongoDB Atlas. The URI shown in
older local configuration must be rotated before publishing because it has been exposed.

## Limitations

The model is trained on 2009 tweets and emoticon-derived labels. Live sources differ in language, slang, topic, and style. Neutral is an uncertainty band, not a learned class. Replay accuracy is measured on held-out labelled tweets and should not be presented as live-source accuracy. Public raw posts may contain strong language; profanity masking is enabled in the dashboard by default.
