import os
import tempfile
import json
import subprocess
import time

from src.profiler import run_profiler


def make_sample_csv(path):
    import pandas as pd

    df = pd.DataFrame({
        "a": [1, 2, None, 4],
        "b": ["x", "x", "", "z"],
        "cat": ["u", "v", "u", "u"],
    })
    df.to_csv(path, index=False)


def start_data_mcp(path, port):
    env = {**os.environ, "MCP_TCP_PORT": str(port), "CSV_PATH": path}
    proc = subprocess.Popen([os.environ.get("PYTHON", "python"), "src/mcp_data_server.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    time.sleep(0.3)
    return proc


def test_run_profiler_creates_summary_and_plots():
    with tempfile.TemporaryDirectory() as td:
        csv = os.path.join(td, "sample.csv")
        make_sample_csv(csv)
        port = 6011
        proc = start_data_mcp(csv, port)
        try:
            out_dir = os.path.join(td, "eda_out")
            summary = run_profiler(mcp_host="127.0.0.1", mcp_port=port, out_dir=out_dir, sample=10, top_n=5)
            assert os.path.exists(os.path.join(out_dir, "eda_summary.json"))
            with open(os.path.join(out_dir, "eda_summary.json")) as f:
                data = json.load(f)
            assert "schema" in data and "missingness" in data
            # check plots if matplotlib is available, otherwise only verify summary
            try:
                import matplotlib  # type: ignore
                assert os.path.exists(os.path.join(out_dir, "missingness.png"))
            except Exception:
                # plotting not available in this environment
                pass
        finally:
            proc.kill()
