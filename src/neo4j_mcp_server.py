"""Lightweight Neo4j MCP stub for local development and testing.

Exposes the tool `neo4j_cypher_executor` via a simple line-delimited JSON stdin/stdout
protocol so `MCPServerStdio(command="neo4j-mcp")` in `src/agents.py` works in tests.

This is a fake executor: it does not require a running Neo4j instance. It supports
basic handling of CREATE/CYPHER commands and returns canned results for MATCH queries.
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, Dict
import socket
import threading
import os


class Neo4jExecutor:
    def __init__(self):
        # store a tiny in-memory representation for created nodes (id -> props)
        self._nodes = []

    def neo4j_cypher_executor(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cypher = args.get("cypher") or args.get("query")
        if not cypher:
            raise ValueError("'cypher' is required in args")

        text = cypher.strip().lower()
        # naive handling
        if text.startswith("create") or text.startswith("merge"):
            # pretend to create nodes and return summary
            self._nodes.append({"cypher": cypher})
            return {"ack": True, "created": 1}

        if text.startswith("match") or text.startswith("return"):
            # return canned sample rows based on simple patterns
            if "eventname" in text or "event_name" in text:
                return {"rows": [{"eventName": "ConsoleLogin", "count": 10}, {"eventName": "AccessDenied", "count": 3}], "columns": ["eventName", "count"]}
            # default
            return {"rows": [{"id": 1}], "columns": ["id"]}

        if text.startswith("call"):
            return {"result": "procedure executed"}

        return {"result": "ok", "query": cypher}


def handle_request(executor: Neo4jExecutor, req: Dict[str, Any]) -> Dict[str, Any]:
    tool = req.get("tool")
    args = req.get("args", {})
    if tool == "neo4j_cypher_executor":
        return executor.neo4j_cypher_executor(args)
    if tool == "ping":
        return {"pong": True}
    raise ValueError(f"unknown tool '{tool}'")


def main() -> None:
    exe = Neo4jExecutor()

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
        print(f"Neo4j MCP TCP server listening on {port}", file=sys.stderr)
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
