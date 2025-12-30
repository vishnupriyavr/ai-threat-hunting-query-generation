"""Profiler orchestration helper.

Calls the `pandas_analyzer` tool on a running data MCP (TCP mode) and
persists an `eda_summary.json` and a few plots into `analysis/eda_output`.
"""

from __future__ import annotations

import json
import os
import socket
from typing import Any, Dict, List

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    _PLOTTING_AVAILABLE = True
except Exception:
    _PLOTTING_AVAILABLE = False


def _send_tcp_request(host: str, port: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall((json.dumps(payload) + "\n").encode())
    data = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
        if b"\n" in data:
            break
    s.close()
    return json.loads(data.decode().strip())


def run_profiler(mcp_host: str = "127.0.0.1", mcp_port: int = 5001, out_dir: str = "analysis/eda_output", sample: int = 10000, top_n: int = 10) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    summary: Dict[str, Any] = {}

    # Schema
    req = {"id": "schema", "tool": "pandas_analyzer", "args": {"action": "schema"}}
    resp = _send_tcp_request(mcp_host, mcp_port, req)
    schema = resp.get("result") if resp.get("ok") else None
    summary["schema"] = schema

    # Missingness
    req2 = {"id": "missing", "tool": "pandas_analyzer", "args": {"action": "missingness", "sample": sample}}
    resp2 = _send_tcp_request(mcp_host, mcp_port, req2)
    missing = resp2.get("result") if resp2.get("ok") else None
    summary["missingness"] = missing

    # Top values for categorical columns (use schema to pick columns)
    top_values: Dict[str, Any] = {}
    cols = []
    try:
        cols = [c["name"] for c in schema.get("columns", [])]
    except Exception:
        cols = []

    # Limit number of columns to query for convenience
    for c in cols[:20]:
        rq = {"id": f"top_{c}", "tool": "pandas_analyzer", "args": {"action": "top_values", "column": c, "limit": top_n}}
        r = _send_tcp_request(mcp_host, mcp_port, rq)
        if r.get("ok"):
            top_values[c] = r.get("result")
    summary["top_values"] = top_values

    # Save summary
    out_path = os.path.join(out_dir, "eda_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # Plots: missingness bar chart if available
    try:
        if _PLOTTING_AVAILABLE:
            if missing and "missingness" in missing:
                ms = missing["missingness"]
                keys = list(ms.keys())
                vals = [ms[k]["missing"] for k in keys]
                fig, ax = plt.subplots(figsize=(max(6, len(keys) * 0.3), 4))
                ax.barh(keys, vals)
                ax.set_xlabel("Missing count (sample)")
                ax.set_title("Missingness (sample)")
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, "missingness.png"))
                plt.close(fig)

            # top values: for first up to 3 columns, create bar charts
            plotted = 0
            for col, rows in top_values.items():
                if not rows:
                    continue
                labels = [r.get("value") for r in rows]
                counts = [r.get("cnt") for r in rows]
                fig, ax = plt.subplots(figsize=(6, 3))
                ax.bar(labels, counts)
                ax.set_title(f"Top values: {col}")
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, f"top_values_{col}.png"))
                plt.close(fig)
                plotted += 1
                if plotted >= 3:
                    break
    except Exception:
        # plotting should not fail the whole run
        pass

    return summary


__all__ = ["run_profiler"]
