"""Tests for the JSON-RPC 2.0 gateway endpoint."""
from __future__ import annotations

import json
import threading
import time
from urllib.request import Request, urlopen
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "bindings" / "python"))
import server


def test_json_rpc_single_and_batch_execution():
    host = "127.0.0.1"
    port = 8993

    gateway = server.NLSQLGateway()
    metrics = server.ServerMetrics()
    limiter = server.TokenBucketRateLimiter()

    class BoundHandler(server.GatewayHTTPHandler):
        pass
    BoundHandler.gateway = gateway
    BoundHandler.metrics = metrics
    BoundHandler.limiter = limiter

    httpd = server.ThreadingHTTPServer((host, port), BoundHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    url = f"http://{host}:{port}/rpc"

    try:
        # 1. Single RPC compile call
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "compile",
            "params": {
                "ir": "(nlsql 1 (query (from orders o) (select (field (column o total_amount) total)) (limit 10)))",
                "dialect": "postgres"
            }
        }).encode("utf-8")

        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == 1
            assert "result" in data
            assert "SELECT" in data["result"]["sql"]

        # 2. Batch RPC call
        batch_payload = json.dumps([
            {
                "jsonrpc": "2.0",
                "id": "req-1",
                "method": "compile",
                "params": {
                    "ir": "(nlsql 1 (query (from orders o) (select (field (column o id) id)) (limit 5)))",
                    "dialect": "sqlite"
                }
            },
            {
                "jsonrpc": "2.0",
                "id": "req-2",
                "method": "validate",
                "params": {
                    "ir": "(nlsql 1 (query (from orders o) (select (field (column o id) id))))"
                }
            }
        ]).encode("utf-8")

        batch_req = Request(url, data=batch_payload, headers={"Content-Type": "application/json"})
        with urlopen(batch_req) as resp:
            batch_data = json.loads(resp.read().decode())
            assert len(batch_data) == 2
            assert batch_data[0]["id"] == "req-1"
            assert "result" in batch_data[0]
            assert batch_data[1]["id"] == "req-2"
            assert batch_data[1]["result"]["valid"] is True

    finally:
        httpd.shutdown()
        server_thread.join(timeout=1.0)
