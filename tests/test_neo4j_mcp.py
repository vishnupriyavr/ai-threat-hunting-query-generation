from src.neo4j_mcp_server import Neo4jExecutor, handle_request


def test_neo4j_create_ack():
    exe = Neo4jExecutor()
    req = {"id": "1", "tool": "neo4j_cypher_executor", "args": {"cypher": "CREATE (n:Test {name: 'x'})"}}
    res = handle_request(exe, req)
    assert res.get("ack") is True
    assert res.get("created") == 1


def test_neo4j_match_returns_rows():
    exe = Neo4jExecutor()
    req = {"id": "2", "tool": "neo4j_cypher_executor", "args": {"cypher": "MATCH (n) RETURN n.eventName AS eventName, count(*) as count"}}
    res = handle_request(exe, req)
    assert "rows" in res and isinstance(res["rows"], list)
    assert "columns" in res


def test_neo4j_ping():
    exe = Neo4jExecutor()
    req = {"id": "p", "tool": "ping", "args": {}}
    res = handle_request(exe, req)
    assert res == {"pong": True}
