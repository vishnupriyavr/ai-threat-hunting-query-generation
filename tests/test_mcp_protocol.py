import json
from src.mcp_data_server import AthenaExecutor, handle_request


def test_handle_request_ping():
    exe = AthenaExecutor()
    req = {"id": "x", "tool": "ping", "args": {}}
    res = handle_request(exe, req)
    assert res == {"pong": True}


def test_handle_request_unknown_tool_raises():
    exe = AthenaExecutor()
    try:
        handle_request(exe, {"id": "y", "tool": "nope", "args": {}})
        assert False, "Expected ValueError for unknown tool"
    except ValueError:
        pass
