import json
import os
import tempfile

from evals import evaluation


def test_parse_outcomes_and_summarize():
    # build a fake outcomes list (hypothesis id -> column maps)
    outcomes = [
        {"1": {"eventID": {"0": "e1", "1": "e2"}, "eventName": {"0": "ConsoleLogin", "1": "ConsoleLogin"}}},
        {"2": {"eventName": {"0": "AccessDenied"}}},
    ]
    parsed = evaluation.parse_outcomes(outcomes)
    assert "1" in parsed and "2" in parsed

    # summarize hypothesis 1
    summary1 = evaluation.summarize_hypothesis("1", parsed["1"], hypothesis_meta={"id": "1", "name": "Test", "expected_event": "ConsoleLogin"})
    assert summary1["hypothesis_id"] == "1"
    assert summary1["result_count"] == 2
    assert summary1["success"] is True
    assert summary1["tool_call_ok"] is True


def test_compute_aggregates_and_markdown():
    per_hypo = [
        {"hypothesis_id": "1", "success": True, "tool_call_ok": True, "schema_faithfulness": 80.0, "result_count": 2},
        {"hypothesis_id": "2", "success": False, "tool_call_ok": False, "schema_faithfulness": 50.0, "result_count": 0},
    ]
    ag = evaluation.compute_aggregates(per_hypo)
    assert ag["query_success_rate"] == 50.0
    assert ag["schema_faithfulness"] == 65.0

    md = evaluation.generate_markdown_report(ag, per_hypo)
    assert "Overall Metrics" in md
    assert "Per-Hypothesis Breakdown" in md


def test_rows_to_column_mapping_and_export():
    import tempfile

    rows = [{"eventID": "e1", "a": 1}, {"eventID": "e2", "a": 2}]
    cols = evaluation.rows_to_column_mapping(rows)
    assert "eventID" in cols and "a" in cols
    assert cols["a"]["e1"] == 1

    # test export_agent_outputs_to_hypotheses_outcomes with dict input
    agent_outputs = {"7": rows}
    with tempfile.TemporaryDirectory() as td:
        out_file = os.path.join(td, "out.json")
        evaluation.export_agent_outputs_to_hypotheses_outcomes(agent_outputs, out_path=out_file)
        data = json.loads(open(out_file).read())
        assert isinstance(data, list)
        assert any("7" in item for item in data)

        # test export_agent_outputs_to_files
        out_dir = os.path.join(td, "perhyp")
        evaluation.export_agent_outputs_to_files([{"hypothesis_id": 9, "rows": rows}], out_dir=out_dir)
        files = os.listdir(out_dir)
        assert any(f == "9.json" for f in files)


def test_export_invalid_format_raises():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        invalid = [1, 2, 3]
        try:
            evaluation.export_agent_outputs_to_hypotheses_outcomes(invalid, out_path=os.path.join(td, "o.json"))
            assert False, "Expected ValueError"
        except ValueError:
            pass
