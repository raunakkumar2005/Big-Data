"""Live sentiment dashboard."""
from __future__ import annotations

import logging
import re
from collections import Counter

import pandas as pd
import streamlit as st

from data_access import read_data, read_demo_data
from model_page import render as render_model

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None


PROFANITY = {"fuck", "fucking", "shit", "bitch", "damn"}
logger = logging.getLogger(__name__)

DEFAULT_TOPICS = {
    "Technology": ("python", "software", "app", "technology", "ai", "computer", "phone"),
    "Work": ("work", "job", "office", "meeting", "boss", "email", "career"),
    "Travel": ("travel", "vacation", "flight", "trip", "holiday", "airport"),
    "Entertainment": ("movie", "music", "game", "tv", "book", "concert"),
    "Food": ("food", "lunch", "dinner", "restaurant", "coffee", "meal"),
    "Sports": ("football", "soccer", "cricket", "sports", "game", "team", "match"),
    "Shopping": ("buy", "sale", "price", "order", "shopping", "product"),
}


def mask(text: str) -> str:
    return re.sub(r"\b\w+\b", lambda match: "*" * len(match.group()) if match.group().casefold() in PROFANITY else match.group(), text)


def configure_page() -> None:
    st.set_page_config(
        page_title="Pulse | Live sentiment",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        .eyebrow {
            color: #22d3ee; font-size: 0.78rem; font-weight: 700;
            letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 0.4rem;
        }
        .hero {
            background: linear-gradient(135deg, #10243b 0%, #172554 100%);
            border: 1px solid #24476b; border-radius: 18px; padding: 1.5rem 1.75rem;
            margin-bottom: 1.25rem;
        }
        .hero h1 { color: #f8fafc; margin: 0; font-size: 2.25rem; }
        .hero p { color: #cbd5e1; margin: 0.6rem 0 0; max-width: 760px; font-size: 1.05rem; }
        .live-dot {
            display: inline-block; width: 9px; height: 9px; border-radius: 50%;
            background: #34d399; box-shadow: 0 0 0 4px #34d39933; margin-right: 0.45rem;
        }
        .section-label {
            color: #64748b; font-size: 0.75rem; font-weight: 700;
            letter-spacing: 0.12em; text-transform: uppercase; margin: 1.5rem 0 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def prepare_frames(posts: list[dict], aggregates: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    posts_df = pd.DataFrame(posts)
    aggregates_df = pd.DataFrame(aggregates)
    if not posts_df.empty:
        event_values = posts_df.get("event_time", posts_df.get("created_at"))
        posts_df["event_time"] = pd.to_datetime(event_values, errors="coerce", utc=True)
        posts_df["score"] = pd.to_numeric(posts_df.get("score"), errors="coerce")
        posts_df["label"] = posts_df.get("label", pd.Series(index=posts_df.index, dtype=str)).fillna("unknown").astype(str).str.casefold()
        posts_df["topic"] = posts_df.apply(infer_topic, axis=1)
        posts_df = posts_df.sort_values("event_time", ascending=False, na_position="last")
    if not aggregates_df.empty:
        aggregates_df["window_start"] = pd.to_datetime(
            aggregates_df.get("window_start"), errors="coerce", utc=True
        )
        for column in ("positive", "negative", "neutral", "total", "average_score"):
            if column in aggregates_df:
                aggregates_df[column] = pd.to_numeric(aggregates_df[column], errors="coerce")
        aggregates_df = aggregates_df.sort_values("window_start", ascending=True, na_position="last")
    return posts_df, aggregates_df


def infer_topic(row: pd.Series) -> str:
    keyword = str(row.get("keyword") or "").strip()
    if keyword and keyword.casefold() not in {"all", "none", "nan"}:
        return keyword.title()
    text = str(row.get("text") or "").casefold()
    for topic, terms in DEFAULT_TOPICS.items():
        if any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms):
            return topic
    return "General"


def render_kpis(posts_df: pd.DataFrame, aggregates_df: pd.DataFrame) -> None:
    if posts_df.empty and not aggregates_df.empty and "total" in aggregates_df:
        total = int(aggregates_df["total"].sum())
        positive = int(aggregates_df["positive"].sum())
        negative = int(aggregates_df["negative"].sum())
        neutral = int(aggregates_df["neutral"].sum())
    else:
        total = len(posts_df)
        labels = posts_df["label"].fillna("").str.casefold() if "label" in posts_df else pd.Series(dtype=str)
        positive = int((labels == "positive").sum())
        negative = int((labels == "negative").sum())
        neutral = int((labels == "neutral").sum())
    average_score = posts_df["score"].mean() if "score" in posts_df else None
    score_text = f"{average_score:.2f}" if pd.notna(average_score) else "—"
    columns = st.columns(5)
    columns[0].metric("Conversation volume", f"{total:,}", "events processed")
    columns[1].metric("Positive", f"{positive:,}", f"{positive / total:.0%}" if total else "—")
    columns[2].metric("Negative", f"{negative:,}", f"{negative / total:.0%}" if total else "—")
    columns[3].metric("Neutral", f"{neutral:,}", f"{neutral / total:.0%}" if total else "—")
    columns[4].metric("Average score", score_text, "model confidence")


def filter_data(
    posts_df: pd.DataFrame,
    aggregates_df: pd.DataFrame,
    category: str,
    search_term: str,
    sentiments: list[str] | None = None,
    sources: list[str] | None = None,
    hours: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    filtered_posts = posts_df
    filtered_aggregates = aggregates_df
    if category != "All topics":
        if "topic" in filtered_posts:
            filtered_posts = filtered_posts[filtered_posts["topic"].eq(category)]
        if "keyword" in filtered_aggregates:
            filtered_aggregates = filtered_aggregates[
                filtered_aggregates["keyword"].fillna("").astype(str).str.casefold()
                == category.casefold()
            ]
    query = search_term.strip().casefold()
    if query:
        post_text = filtered_posts.fillna("").astype(str).agg(" ".join, axis=1).str.casefold()
        filtered_posts = filtered_posts[post_text.str.contains(query, regex=False)]
        # Aggregates have no post text, so text searches use the matching posts for sentiment totals.
        filtered_aggregates = filtered_aggregates.iloc[0:0]
    if sentiments:
        filtered_posts = filtered_posts[filtered_posts["label"].isin([value.casefold() for value in sentiments])]
        filtered_aggregates = filtered_aggregates.iloc[0:0]
    if sources and "source" in filtered_posts:
        filtered_posts = filtered_posts[filtered_posts["source"].fillna("unknown").isin(sources)]
        filtered_aggregates = filtered_aggregates.iloc[0:0]
    if hours and "event_time" in filtered_posts:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours)
        filtered_posts = filtered_posts[filtered_posts["event_time"] >= cutoff]
        filtered_aggregates = filtered_aggregates[
            filtered_aggregates["window_start"] >= cutoff
        ] if "window_start" in filtered_aggregates else filtered_aggregates
    return filtered_posts, filtered_aggregates


def render_insights(posts_df: pd.DataFrame) -> None:
    if posts_df.empty:
        return
    st.markdown('<div class="section-label">Actionable insights</div>', unsafe_allow_html=True)
    columns = st.columns(3)
    negative_share = (posts_df["label"] == "negative").mean()
    columns[0].metric("Negative share", f"{negative_share:.0%}")
    columns[1].metric("Topics detected", f"{posts_df['topic'].nunique():,}")
    columns[2].metric("Sources", f"{posts_df['source'].nunique() if 'source' in posts_df else 0:,}")
    if negative_share >= 0.5:
        st.error("Attention: negative sentiment is above 50% in the selected view.")
    topic_counts = posts_df["topic"].value_counts().head(8)
    word_counts = Counter(
        word for text in posts_df["text"].fillna("").astype(str)
        for word in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text.casefold())
        if word not in {"the", "and", "for", "that", "this", "with", "you", "are"}
    )
    insight_columns = st.columns(2)
    with insight_columns[0]:
        st.caption("Conversation by topic")
        st.bar_chart(topic_counts)
    with insight_columns[1]:
        st.caption("Most frequent terms")
        st.dataframe(
            pd.DataFrame(word_counts.most_common(10), columns=["term", "mentions"]),
            hide_index=True,
            use_container_width=True,
        )


def render_live() -> None:
    if st_autorefresh:
        st_autorefresh(interval=5000, key="refresh")
    st.sidebar.markdown("## Pulse")
    st.sidebar.caption("Live public sentiment intelligence")
    st.sidebar.markdown(
        "Track how a conversation is shifting while it is still happening. "
        "The stream processes incoming posts, scores them, and writes minute-level aggregates."
    )
    try:
        posts, aggregates, prerecorded = read_data()
    except RuntimeError as exc:
        st.sidebar.warning("Live services are unavailable; showing the bundled demo.")
        logger.warning("%s", exc)
        posts, aggregates, prerecorded = read_demo_data()
    has_data = bool(posts or aggregates)
    if has_data and not st.session_state.get("dashboard_data_logged", False):
        logger.info(
            "Dashboard data is now available: %d posts and %d aggregates",
            len(posts),
            len(aggregates),
        )
        st.session_state["dashboard_data_logged"] = True
    if not has_data:
        st.markdown(
            '<div class="hero"><div class="eyebrow">Waiting for the stream</div>'
            "<h1>See the conversation as it unfolds.</h1>"
            "<p>Start Kafka, Cassandra, Spark, and a producer. "
            "This view will populate automatically when the first scored posts arrive.</p></div>",
            unsafe_allow_html=True,
        )
        st.info("No data is available yet. Start Kafka, Cassandra, and a producer.")
        return
    posts_df, aggregates_df = prepare_frames(posts, aggregates)
    post_topics = set(posts_df["topic"].dropna().astype(str).unique()) if "topic" in posts_df else set()
    aggregate_topics = set(aggregates_df["keyword"].dropna().astype(str).str.title().unique()) if "keyword" in aggregates_df else set()
    categories = sorted(post_topics | aggregate_topics)
    st.sidebar.markdown("### Explore the stream")
    category = st.sidebar.selectbox("Topic / category", ["All topics", *categories])
    search_term = st.sidebar.text_input(
        "Search posts",
        placeholder="Search a topic, phrase, or source",
        help="Searches the posts currently available in the dashboard.",
    )
    source_options = sorted(posts_df["source"].fillna("unknown").astype(str).unique()) if "source" in posts_df else []
    selected_sources = st.sidebar.multiselect("Sources", source_options, default=source_options)
    selected_sentiments = st.sidebar.multiselect(
        "Sentiment", ["positive", "negative", "neutral"], default=["positive", "negative", "neutral"]
    )
    hours_label = st.sidebar.select_slider(
        "Time window", options=["All available", "1 hour", "6 hours", "24 hours"], value="All available"
    )
    hours = None if hours_label == "All available" else int(hours_label.split()[0])
    posts_df, aggregates_df = filter_data(
        posts_df, aggregates_df, category, search_term, selected_sentiments, selected_sources, hours
    )
    if posts_df.empty and aggregates_df.empty:
        st.warning("No matching sentiment data. Try another topic or search phrase.")
        return
    st.markdown(
        '<div class="hero"><div class="eyebrow"><span class="live-dot"></span>Live intelligence</div>'
        "<h1>What is the conversation feeling right now?</h1>"
        "<p>Real-time sentiment signals from the active stream, updated every five seconds "
        "so teams can respond before the conversation is over.</p></div>",
        unsafe_allow_html=True,
    )
    if prerecorded:
        st.info("This view contains pre-recorded demo data.")
    if category != "All topics" or search_term.strip():
        scope = category if category != "All topics" else "all topics"
        detail = f" for **{scope}**"
        if search_term.strip():
            detail += f" matching **{search_term.strip()}**"
        st.info(f"Showing sentiment{detail}.")
    st.markdown('<div class="section-label">At a glance</div>', unsafe_allow_html=True)
    render_kpis(posts_df, aggregates_df)
    render_insights(posts_df)

    chart_columns = st.columns([1.35, 1])
    with chart_columns[0]:
        st.markdown('<div class="section-label">Sentiment over time</div>', unsafe_allow_html=True)
        if not aggregates_df.empty and "window_start" in aggregates_df:
            trend = aggregates_df.set_index("window_start")[
                [column for column in ("positive", "negative", "neutral") if column in aggregates_df]
            ]
            st.area_chart(trend, color=["#34d399", "#fb7185", "#fbbf24"])
        elif "label" in posts_df:
            st.bar_chart(posts_df["label"].value_counts())
    with chart_columns[1]:
        st.markdown('<div class="section-label">Share of sentiment</div>', unsafe_allow_html=True)
        counts = {
            label: int(aggregates_df[label].sum())
            for label in ("positive", "negative", "neutral")
            if label in aggregates_df
        }
        if not counts and "label" in posts_df:
            counts = posts_df["label"].value_counts().to_dict()
        if counts:
            st.bar_chart(pd.Series(counts, name="events"))
        else:
            st.caption("Aggregates will appear after the first completed window.")

    st.markdown('<div class="section-label">Latest signals</div>', unsafe_allow_html=True)
    feed_columns = st.columns([1.6, 1])
    with feed_columns[0]:
        st.subheader("What people are saying")
        st.checkbox("Mask profanity", value=True, key="mask")
        for row in posts_df.head(12).to_dict("records"):
            label = str(row.get("label") or "unknown").lower()
            text = str(row.get("text") or "")
            if st.session_state.get("mask", True):
                text = mask(text)
            timestamp = row.get("event_time")
            time_text = timestamp.strftime("%H:%M:%S UTC") if pd.notna(timestamp) else "time unavailable"
            st.markdown(f"**{label.title()}** · `{time_text}`  \n{text}")
            st.divider()
    with feed_columns[1]:
        st.subheader("Stream context")
        if not posts_df.empty and "source" in posts_df:
            source_counts = posts_df["source"].fillna("unknown").value_counts()
            st.dataframe(
                source_counts.rename("posts").rename_axis("source").reset_index(),
                hide_index=True,
                use_container_width=True,
            )
        if not aggregates_df.empty and "keyword" in aggregates_df:
            st.caption("Tracked topics")
            st.write(", ".join(sorted(aggregates_df["keyword"].dropna().astype(str).unique())))
    st.download_button(
        "Download selected posts",
        posts_df.to_csv(index=False).encode("utf-8"),
        file_name="pulse-selected-posts.csv",
        mime="text/csv",
        use_container_width=True,
    )


def main() -> None:
    page = st.sidebar.radio("Page", ["Live", "Model"])
    if page == "Model":
        render_model()
    else:
        render_live()


if __name__ == "__main__":
    configure_page()
    main()
