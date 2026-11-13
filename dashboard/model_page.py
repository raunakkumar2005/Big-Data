"""Static model-results page sourced only from supplied artifacts."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]


def render() -> None:
    metrics = json.loads((ROOT / "model" / "metrics.json").read_text(encoding="utf-8"))
    neutral = json.loads((ROOT / "model" / "neutral_band.json").read_text(encoding="utf-8"))
    words = json.loads((ROOT / "model" / "top_words.json").read_text(encoding="utf-8"))
    st.title("Model")
    st.caption("Supplied pre-trained Spark PipelineModel; no training is performed by this project.")
    st.write({**metrics["data"], "spark": metrics["environment"]["spark"]})
    st.subheader("Classifier comparison")
    st.dataframe([
        {**value, "classifier": key} for key, value in metrics["models"].items()
    ], use_container_width=True)
    st.subheader("Neutral-band trade-off")
    st.dataframe(neutral["table"], use_container_width=True)
    st.info("Neutral is an uncertainty band, not a trained class.")
    st.subheader("Top terms")
    st.json(words)
    for name in ("model_comparison.png", "confusion_matrices.png", "neutral_band.png", "top_words.png"):
        image = ROOT / "model" / "plots" / name
        if image.exists():
            st.image(str(image), caption=name)
    st.subheader("Limitations")
    st.markdown((ROOT / "model" / "model_card.md").read_text(encoding="utf-8"))
