from producers.common import matching_keyword, post_message


def test_post_message_contract():
    message = post_message("Great news", "replay", "news", 1)
    assert set(message) == {"post_id", "source", "text", "created_at", "keyword", "true_label"}
    assert message["true_label"] == "1"


def test_keyword_matching():
    assert matching_keyword("Python is useful", ["python"]) == "python"
    assert matching_keyword("No match", ["python"]) is None
    assert matching_keyword("No filter", []) == "all"
