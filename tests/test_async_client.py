"""Tests for AsyncNLSQLClient and ASGI TenantContextMiddleware."""
from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bindings" / "python"))
import nlsql


def test_async_nlsql_client_lifecycle():
    async def run():
        client = nlsql.AsyncNLSQLClient()
        ir = "(nlsql 1 (query (from orders o) (select (field (column o total) total)) (limit 10)))"

        res = await client.compile(ir, dialect=nlsql.NLSQL_DIALECT_POSTGRES)
        assert res.status == nlsql.NLSQL_OK
        assert "SELECT" in res.sql
        assert "tenant_id" in res.sql
        res.close()

        batch_queries = [
            "(nlsql 1 (query (from orders o) (select (field (column o id) id)) (limit 5)))",
            "(nlsql 1 (query (from orders o) (select (field (column o total) total)) (limit 10)))",
            "(nlsql 1 (query (from orders o) (select (field (column o id) id) (field (column o total) total)) (limit 20)))",
        ]

        batch_results = await client.compile_batch(batch_queries)
        assert len(batch_results) == 3
        for r in batch_results:
            assert r.status == nlsql.NLSQL_OK
            assert "orders" in r.sql
            r.close()

        client.close()

    asyncio.run(run())


def test_asgi_tenant_context_middleware():
    async def run():
        received_scope = {}

        async def mock_app(scope, receive, send):
            nonlocal received_scope
            received_scope = scope

        middleware = nlsql.TenantContextMiddleware(mock_app, header_name="X-Tenant-ID")

        scope = {
            "type": "http",
            "headers": [
                (b"host", b"api.example.com"),
                (b"x-tenant-id", b"tenant-alpha-99"),
            ]
        }

        async def dummy_recv(): return {}
        async def dummy_send(msg): pass

        await middleware(scope, dummy_recv, dummy_send)

        assert "state" in received_scope
        assert received_scope["state"]["tenant_id"] == "tenant-alpha-99"

    asyncio.run(run())
