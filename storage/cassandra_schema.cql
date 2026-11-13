CREATE KEYSPACE IF NOT EXISTS sentiment
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS sentiment.posts (
    keyword text,
    day date,
    event_time timestamp,
    post_id text,
    source text,
    text text,
    created_at text,
    label text,
    score double,
    true_label text,
    PRIMARY KEY ((keyword, day), event_time, post_id)
) WITH CLUSTERING ORDER BY (event_time DESC);

CREATE TABLE IF NOT EXISTS sentiment.window_counts (
    keyword text,
    window_start timestamp,
    window_end timestamp,
    positive bigint,
    negative bigint,
    neutral bigint,
    total bigint,
    average_score double,
    PRIMARY KEY (keyword, window_start)
) WITH CLUSTERING ORDER BY (window_start DESC);

CREATE TABLE IF NOT EXISTS sentiment.replay_quality (
    keyword text PRIMARY KEY,
    evaluated bigint,
    correct bigint,
    accuracy double,
    updated_at timestamp
);
