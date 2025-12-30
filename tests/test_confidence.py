from src.confidence import compute_confidence, llm_explain


def test_compute_confidence_empty():
    res = compute_confidence([], None)
    assert res["score"] == 0.0


def test_compute_confidence_with_keywords():
    rows = [{"a": "foo"}, {"a": "bar_access"}, {"b": "nope"}]
    res = compute_confidence(rows, ["access"])
    assert 0.0 <= res["score"] <= 1.0
    assert "match" in res["explanation"]


def test_llm_explain_stubbed_when_no_key():
    # Ensure safe fallback when OPENAI_API_KEY not set
    import os
    os.environ.pop("OPENAI_API_KEY", None)
    s = llm_explain([{"a": "foo"}], None)
    assert isinstance(s, str)
