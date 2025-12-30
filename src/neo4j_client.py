"""Utility to call the local `neo4j-mcp` MCP server script to execute Cypher.

This is a thin helper that launches the repo-local `neo4j-mcp` script and
sends a single JSON request (line-delimited) then reads a single JSON response.
Used for lightweight integration tests and simple orchestration tasks.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any, Dict


def execute_cypher_via_mcp(cypher: str, timeout: int = 5) -> Dict[str, Any]:
    """Execute a Cypher statement by invoking the local `neo4j-mcp` script.

    Returns the parsed JSON response `result` dictionary.
    """
    cmd = [sys.executable, "neo4j-mcp"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    req = {"id": "1", "tool": "neo4j_cypher_executor", "args": {"cypher": cypher}}
    line = json.dumps(req)
    outs = proc.stdout
    ins = proc.stdin
    ins.write(line + "\n")
    ins.flush()
    # read one line response
    resp_line = outs.readline()
    if not resp_line:
        stderr = proc.stderr.read()
        proc.kill()
        raise RuntimeError(f"No response from neo4j-mcp; stderr={stderr}")
    resp = json.loads(resp_line)
    if not resp.get("ok"):
        raise RuntimeError(f"neo4j-mcp error: {resp.get('error')}")
    return resp.get("result")
