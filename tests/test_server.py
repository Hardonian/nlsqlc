"""Integration tests for the nlsqlc HTTP Enterprise Server Gateway."""
from __future__ import annotations

import json
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "bindings" / "python"))

import server


def test_server_full_lifecycle():
    host = "127.0.0.1"
    port = 8991

    gateway = server.NLSQLGateway()
    metrics = server.ServerMetrics()
    limiter = server.TokenBucketRateLimiter(rate=500.0, capacity=1000.0)

    class TestHandler(server.GatewayHTTPHandler):
        pass
    TestHandler.gateway = gateway
    TestHandler.metrics = metrics
    TestHandler.limiter = limiter

    httpd = server.ThreadingHTTPServer((host, port), TestHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    base_url = f"http://{host}:{port}"

    try:
        # 1. Healthz probe
        with urlopen(f"{base_url}/healthz") as resp:
            data = json.loads(resp.read().decode())
            assert data["status"] == "UP"
            assert data["version"] == "0.1.2"

        # 2. Version endpoint
        with urlopen(f"{base_url}/v1/version") as resp:
            data = json.loads(resp.read().decode())
            assert data["name"] == "nlsqlc"
            assert data["ir_version"] == 2

        # 3. Metrics endpoint
        with urlopen(f"{base_url}/metrics") as resp:
            metrics_text = resp.read().decode()
            assert "nlsql_requests_total" in metrics_text
            assert "nlsql_uptime_seconds" in metrics_text

        # 4. Valid compilation
        req_body = json.dumps({
            "ir": "(nlsql 1 (query (from orders o) (select (field (column o total_amount) total)) (limit 10)))",
            "dialect": "postgres"
        }).encode("utf-8")
        req = Request(f"{base_url}/v1/compile", data=req_body, headers={"Content-Type": "application/json"})
        with urlopen(req) as resp:
            res_data = json.loads(resp.read().decode())
            assert res_data["status"] == "OK"
            assert "SELECT" in res_data["sql"]
            assert "FROM" in res_data["sql"]
            assert res_data["complexity"] > 0
            assert res_data["risk"] in ("LOW", "MODERATE")

        # 5. Invalid query rejection
        bad_req_body = json.dumps({
            "ir": "(nlsql 1 (query (from unknown_table x) (select (field (column x id) id))))",
            "dialect": "postgres"
        }).encode("utf-8")
        bad_req = Request(f"{base_url}/v1/compile", data=bad_req_body, headers={"Content-Type": "application/json"})
        try:
            urlopen(bad_req)
            assert False, "Should have raised HTTP 400"
        except HTTPError as e:
            assert e.code == 400
            err_data = json.loads(e.read().decode())
            assert err_data["status"] == "ERROR"

        # 6. Validate IR endpoint
        val_body = json.dumps({
            "ir": "(nlsql 1 (query (from orders o) (select (field (column o id) id))))"
        }).encode("utf-8")
        val_req = Request(f"{base_url}/v1/validate", data=val_body, headers={"Content-Type": "application/json"})
        with urlopen(val_req) as resp:
            val_data = json.loads(resp.read().decode())
            assert val_data["valid"] is True

        # 7. Fast-path Question compilation
        q_body = json.dumps({
            "question": "count orders",
            "dialect": "postgres"
        }).encode("utf-8")
        q_req = Request(f"{base_url}/v1/question", data=q_body, headers={"Content-Type": "application/json"})
        with urlopen(q_req) as resp:
            q_data = json.loads(resp.read().decode())
            assert q_data["status"] == "OK"
            assert "count" in q_data["sql"]

    finally:
        httpd.shutdown()
        server_thread.join(timeout=1.0)
