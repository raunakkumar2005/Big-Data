.PHONY: setup check-model up down stream produce-bluesky produce-hn produce-replay dashboard seed-demo test bench

setup:
	python -m pip install -r requirements.txt

check-model:
	python model/check_model.py

up:
	docker compose --profile streaming up -d --build

down:
	docker compose down

stream:
	docker compose run --rm spark-submit

produce-bluesky:
	python producers/bluesky_producer.py

produce-hn:
	python producers/hackernews_producer.py

produce-replay:
	python producers/csv_replay_producer.py

dashboard:
	streamlit run dashboard/app.py

seed-demo:
	python storage/seed_demo.py

test:
	pytest -q

bench:
	python benchmarks/benchmark_pipeline.py
