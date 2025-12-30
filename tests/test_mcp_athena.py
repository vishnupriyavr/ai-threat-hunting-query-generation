import os
import tempfile

import pandas as pd

from src.mcp_data_server import AthenaExecutor


def test_athena_basic_query():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "sample.csv")
        df.to_csv(path, index=False)

        exe = AthenaExecutor(csv_path=path)
        res = exe.athena_sql_executor({"sql": "SELECT a, b FROM logs ORDER BY a"})
        assert res["row_count"] == 3
        assert res["columns"] == ["a", "b"]
        assert res["rows"][0]["a"] == 1


def test_athena_limit_applied():
    df = pd.DataFrame({"a": list(range(10)), "b": [str(i) for i in range(10)]})
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "sample2.csv")
        df.to_csv(path, index=False)

        exe = AthenaExecutor(csv_path=path)
        res = exe.athena_sql_executor({"sql": "SELECT a FROM logs ORDER BY a DESC", "limit": 3})
        assert res["row_count"] == 3
        assert res["rows"][0]["a"] == 9


def test_missing_sql_raises():
    exe = AthenaExecutor(csv_path=":memory:")
    try:
        exe.athena_sql_executor({})
        assert False, "Expected ValueError"
    except ValueError:
        pass
