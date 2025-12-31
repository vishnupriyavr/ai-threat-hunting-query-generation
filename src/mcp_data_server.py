"""Lightweight data-plane MCP stub for local development and testing.

Exposes two tools via a simple line-delimited JSON stdin/stdout protocol:
- `pandas_analyzer`: basic EDA functions (schema, missingness, top-N)
- `athena_sql_executor`: minimal SQL query execution against a local CSV file

This is designed to be called via `MCPServerStdio(command="python mcp_data_server.py")`
so that agents can access a local data source without needing live cloud resources.
It requires `duckdb` and `pandas` to be installed.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any, Dict, List
import socket
import threading

try:
    import duckdb
    import pandas as pd
    from src.confidence import compute_confidence
    _DUCKDB_AVAILABLE = True
except ImportError:
    _DUCKDB_AVAILABLE = False


class AthenaExecutor:
    def __init__(self, csv_path: str):
        if not _DUCKDB_AVAILABLE:
            raise ImportError("duckdb and pandas are required for AthenaExecutor")
        self._csv_path = csv_path
        if csv_path != ":memory:":
            # create a persistent, named DB in the same dir as the CSV
            self._db_path = os.path.splitext(csv_path)[0] + ".duckdb"
            self._conn = duckdb.connect(self._db_path)
            # Use PRAGMA to increase thread count
            self._conn.execute("PRAGMA threads=4")
            self._conn.execute("PRAGMA log_query_path='mcp_data_server.log'")
            # create a view on the CSV for querying
            self._conn.execute(f"CREATE OR REPLACE VIEW logs AS SELECT * FROM read_csv_auto('{self._csv_path}')")
        else:
            self._conn = duckdb.connect(":memory:")

    def pandas_analyzer(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action")
        if not action:
            raise ValueError("'action' is required in args")
        df = self._conn.execute("SELECT * FROM logs").fetchdf()

        if action == "schema":
            schema = pd.io.json.build_table_schema(df, index=False)
            return {"columns": schema["fields"]}

        if action == "missingness":
            sample = int(args.get("sample", 1000))
            missing = df.head(sample).isnull().sum()
            total = len(df.head(sample))
            return {"missingness": {col: {"missing": int(m), "total": total} for col, m in missing.items()}}

        if action == "top_values":
            col = args.get("column")
            if not col:
                raise ValueError("'column' is required for top_values")
            limit = int(args.get("limit", 10))
            counts = df[col].value_counts()
            top = counts.nlargest(limit)
            return [{"value": val, "cnt": int(cnt)} for val, cnt in top.items()]

        raise ValueError(f"unknown pandas_analyzer action: {action}")

    def athena_sql_executor(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        sql = args.get("sql") or args.get("query")
        if not sql:
            raise ValueError("'sql' or 'query' is required")
        limit = int(args.get("limit", 100))
        # Use a python-based prepared statement to avoid injection issues
        res = self._conn.execute(sql + f" LIMIT {limit}").fetchdf()
        return res.to_dict(orient="records")

    def result_summarizer(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rows = args.get("rows")
        if rows is None:
            # if no rows provided, sample from the full dataset
            sample_size = int(args.get("sample", 10))
            rows = self.athena_sql_executor({"sql": "SELECT * FROM logs", "limit": sample_size})

        intent = args.get("intent_keywords")
        conf = compute_confidence(rows, intent)
        matches = conf.get("score", 0.0) > 0.1
        out = {"matches_intent": matches, "confidence": conf.get("score"), "explanation": conf.get("explanation"), "rows": rows}

        # allow persisting confidence score to an outcomes.json file
        if args.get("persist") and args.get("hypothesis_id"):
            out_path = args.get("outcomes_path") or "assignment/hypotheses_outcomes.json"
            if os.path.exists(out_path):
                with open(out_path, "r") as f:
                    data = json.load(f)
                # find entry for hypothesis and update confidence
                entry = next((it for it in data if isinstance(it, dict) and args["hypothesis_id"] in it), None)
                if entry:
                    entry[args["hypothesis_id"]].setdefault("meta", {})["confidence"] = conf.get("score")
                    with open(out_path, "w") as f:
                        json.dump(data, f, indent=2)
                    out["persisted"] = True

        # allow persisting rows as an outcome
        if args.get("persist_outcome") and args.get("hypothesis_id"):
            out_path = args.get("outcomes_path") or "assignment/hypotheses_outcomes.json"
            if os.path.exists(out_path):
                with open(out_path, "r") as f:
                    data = json.load(f)
                entry = next((it for it in data if isinstance(it, dict) and args["hypothesis_id"] in it), None)
                if entry:
                    # map rows by eventID to avoid duplicates
                    for r in rows:
                        if "eventID" in r:
                            entry[args["hypothesis_id"]].setdefault(r["eventID"], r)
                    with open(out_path, "w") as f:
                        json.dump(data, f, indent=2)
                    out["outcome_persisted"] = True

        return out


def handle_request(executor: AthenaExecutor, req: Dict[str, Any]) -> Dict[str, Any]:
    tool = req.get("tool")
    args = req.get("args", {})
    if tool == "pandas_analyzer":
        return executor.pandas_analyzer(args)
    if tool == "athena_sql_executor":
        return executor.athena_sql_executor(args)
    if tool == "result_summarizer":
        return executor.result_summarizer(args)
    if tool == "ping":
        return {"pong": True}
    raise ValueError(f"unknown tool '{tool}'")

def main() -> None:
    if not _DUCKDB_AVAILABLE:
        print(json.dumps({"ok": False, "error": "duckdb or pandas not installed; run `pip install pandas duckdb`"}))
        sys.exit(1)

    csv_path = os.environ.get("CSV_PATH") or "dataset/nineteenFeaturesDf.csv"
    if not os.path.exists(csv_path) and csv_path != ":memory:":
        print(json.dumps({"ok": False, "error": f"CSV_PATH '{csv_path}' does not exist"}))
        sys.exit(1)

    exe = AthenaExecutor(csv_path=csv_path)

    tcp_port = os.environ.get("MCP_TCP_PORT")
    if tcp_port:
        port = int(tcp_port)

        def handle_conn(conn, addr):
            try:
                data = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break
                raw = data.decode().strip()
                if not raw:
                    return
                req = json.loads(raw)
                rid = req.get("id")
                try:
                    result = handle_request(exe, req)
                    resp = {"id": rid, "ok": True, "result": result}
                except Exception as exc:
                    resp = {"id": rid, "ok": False, "error": str(exc), "trace": traceback.format_exc()}
            except Exception as exc:
                resp = {"id": None, "ok": False, "error": f"invalid request: {exc}", "raw": raw}
            conn.sendall((json.dumps(resp, default=str) + "\n").encode())
            conn.close()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        s.listen(5)
        print(f"Data MCP TCP server listening on {port}", file=sys.stderr)
        try:
            while True:
                conn, addr = s.accept()
                t = threading.Thread(target=handle_conn, args=(conn, addr), daemon=True)
                t.start()
        finally:
            s.close()
    else:
        for raw in sys.stdin:
            raw = raw.strip()
            if not raw:
                continue
            try:
                req = json.loads(raw)
                rid = req.get("id")
                try:
                    result = handle_request(exe, req)
                    resp = {"id": rid, "ok": True, "result": result}
                except Exception as exc:
                    resp = {"id": rid, "ok": False, "error": str(exc), "trace": traceback.format_exc()}
            except Exception as exc:
                resp = {"id": None, "ok": False, "error": f"invalid request: {exc}", "raw": raw}

            print(json.dumps(resp, default=str), flush=True)


if __name__ == "__main__":
    main()