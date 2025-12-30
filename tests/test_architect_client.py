import os
os.environ.setdefault("OPENAI_API_KEY", "test")
from importlib import import_module

mod = import_module("src.agents")
architect_apply_cql = mod.architect_apply_cql


def test_architect_apply_cql_create_and_match():
    res = architect_apply_cql("CREATE (n:Test {name: 'x'})")
    assert res.get("ack") is True

    res2 = architect_apply_cql("MATCH (n) RETURN n.eventName AS eventName, count(*) as count")
    assert "rows" in res2 and isinstance(res2["rows"], list)
