import os
import json
import tempfile

from src.mcp_data_server import AthenaExecutor, handle_request


def make_sample_csv(path):
    import pandas as pd

    df = pd.DataFrame({
        "a": [1, 2, None, 4],
        "b": ["x", "x", "", "z"],
        "cat": ["u", "v", "u", "u"],
    })
    df.to_csv(path, index=False)


def test_pandas_schema_and_missingness_top_values():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "sample.csv")
        make_sample_csv(path)
        exe = AthenaExecutor(csv_path=path)

        # schema
        req = {"id": "1", "tool": "pandas_analyzer", "args": {"action": "schema"}}
        res = handle_request(exe, req)
        assert res["columns"] and any(c["name"] == "a" for c in res["columns"]) 

        # missingness
        req2 = {"id": "2", "tool": "pandas_analyzer", "args": {"action": "missingness", "sample": 10}}
        res2 = handle_request(exe, req2)
        assert "missingness" in res2
        assert res2["missingness"]["a"]["sample_size"] == 4

        # top_values
        req3 = {"id": "3", "tool": "pandas_analyzer", "args": {"action": "top_values", "column": "cat", "limit": 2}}
        res3 = handle_request(exe, req3)
        assert "top_values" in res3
        assert any(r["value"] == "u" for r in res3["top_values"]) 


def test_pandas_top_values_missing_column_raises():
    exe = AthenaExecutor(csv_path=":memory:")
    try:
        handle_request(exe, {"id": "x", "tool": "pandas_analyzer", "args": {"action": "top_values"}})
        assert False, "Expected ValueError for missing column"
    except ValueError:
        pass
