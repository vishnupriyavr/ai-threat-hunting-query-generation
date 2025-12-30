import os
import tempfile

from src.mcp_data_server import AthenaExecutor, handle_request


def make_sample_csv(path):
    import pandas as pd

    df = pd.DataFrame({"eventName": ["ConsoleLogin", "AccessDenied", "ConsoleLogin"], "user": ["alice", "bob", "eve"]})
    df.to_csv(path, index=False)


def test_result_summarizer_samples_and_keyword_matching():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "sample.csv")
        make_sample_csv(path)
        exe = AthenaExecutor(csv_path=path)

        # sample from logs and check for keyword 'access'
        req = {"id": "1", "tool": "result_summarizer", "args": {"sample": 2, "intent_keywords": ["access"]}}
        res = handle_request(exe, req)
        assert "rows" in res
        assert res["matches_intent"] is True
        assert "confidence" in res
        assert 0.0 <= float(res["confidence"]) <= 1.0


def test_result_summarizer_with_rows_passed():
    rows = [{"a": "foo"}, {"a": "bar_access"}]
    exe = AthenaExecutor(csv_path=":memory:")
    req = {"id": "2", "tool": "result_summarizer", "args": {"rows": rows, "intent_keywords": ["access"]}}
    res = handle_request(exe, req)
    assert res["matches_intent"] is True
    assert len(res["rows"]) == 2
    assert "confidence" in res
    assert 0.0 <= float(res["confidence"]) <= 1.0


def test_result_summarizer_persists_confidence_when_requested(tmp_path):
    rows = [{"eventID": "0", "eventName": "AccessDenied"}]
    # create a fake outcomes file to write to
    outcomes_path = str(tmp_path / "hypotheses_outcomes.json")
    with open(outcomes_path, 'w') as f:
        f.write('[]')

    exe = AthenaExecutor(csv_path=":memory:")
    req = {"id": "3", "tool": "result_summarizer", "args": {"rows": rows, "intent_keywords": ["access"], "hypothesis_id": "42", "persist": True, "outcomes_path": outcomes_path}}
    res = handle_request(exe, req)
    assert res["matches_intent"] is True
    assert res["persisted"] is True
    with open(outcomes_path, 'r') as f:
        data = json.load(f)
    entry = next((it for it in data if isinstance(it, dict) and '42' in it), None)
    assert entry is not None
    assert entry['42']['meta']['confidence'] == res['confidence']


def test_result_summarizer_persists_outcome_rows_when_requested(tmp_path):
    rows = [{"eventID": "10", "eventName": "ConsoleLogin", "user": "alice"}]
    outcomes_path = str(tmp_path / "hypotheses_outcomes.json")
    with open(outcomes_path, 'w') as f:
        f.write('[]')

    exe = AthenaExecutor(csv_path=":memory:")
    req = {"id": "4", "tool": "result_summarizer", "args": {"rows": rows, "hypothesis_id": "100", "persist_outcome": True, "outcomes_path": outcomes_path}}
    res = handle_request(exe, req)
    assert res["outcome_persisted"] is True
    with open(outcomes_path, 'r') as f:
        data = json.load(f)
    entry = next((it for it in data if isinstance(it, dict) and '100' in it), None)
    assert entry is not None
    # verify column mapping exists and contains the expected value
    assert entry['100']['eventName']['10'] == 'ConsoleLogin'
