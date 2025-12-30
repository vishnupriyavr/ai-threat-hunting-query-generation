import json
import socket
import subprocess
import time
import os

from src.mcp_data_server import AthenaExecutor


def start_server_in_subprocess(script: str, env: dict):
    cmd = [os.environ.get('PYTHON', 'python'), script]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, **env})
    # give server time to start
    time.sleep(0.5)
    return proc


def send_json_tcp(port: int, payload: dict) -> dict:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', port))
    s.sendall((json.dumps(payload) + '\n').encode())
    data = b''
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
        if b'\n' in data:
            break
    s.close()
    return json.loads(data.decode().strip())


def test_data_mcp_tcp_athena_executor():
    proc = start_server_in_subprocess('src/mcp_data_server.py', {'MCP_TCP_PORT': '6001', 'CSV_PATH': ':memory:'})
    try:
        # send ping
        resp = send_json_tcp(6001, {"id": "p", "tool": "ping", "args": {}})
        assert resp.get('ok') and resp.get('result', {}).get('pong') is True
    finally:
        proc.kill()
