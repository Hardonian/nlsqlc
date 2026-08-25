"""Multi-Dialect Conformance tests for PostgreSQL, SQLite, DuckDB, MySQL, and SQL Server."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bindings" / "python"))
import nlsql


@pytest.fixture
def test_env():
    ctx = nlsql.Context()
    schema = nlsql.Schema(ctx, [
        ("public", "orders", [
            ("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY),
            ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY),
            ("customer_id", nlsql.NLSQL_TYPE_INT64, 0),
            ("total", nlsql.NLSQL_TYPE_DECIMAL, 0),
            ("created_at", nlsql.NLSQL_TYPE_TIMESTAMP, 0),
        ]),
        ("public", "customers", [
            ("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY),
            ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY),
            ("name", nlsql.NLSQL_TYPE_TEXT, 0),
            ("region", nlsql.NLSQL_TYPE_TEXT, 0),
        ]),
    ], foreign_keys=[("public", "orders", "customer_id", "public", "customers", "id")])

    policy = nlsql.Policy(
        ctx,
        allow=[("public", "orders"), ("public", "customers")],
        tenant=[("public", "orders", "tenant_id", nlsql.NLSQL_TYPE_UUID), ("public", "customers", "tenant_id", nlsql.NLSQL_TYPE_UUID)],
        runtime_tenant=("tenant_id", nlsql.NLSQL_TYPE_UUID),
    )
    yield ctx, schema, policy
    policy.close()
    schema.close()
    ctx.close()


def test_postgres_emission(test_env):
    ctx, schema, policy = test_env
    ir = "(nlsql 1 (query (from orders o) (select (field (column o total) total)) (where (gt (column o total) (param min_total decimal))) (limit 25)))"
    res = nlsql.compile_ir(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_POSTGRES)
    assert res.status == nlsql.NLSQL_OK
    assert '"orders"' in res.sql
    assert "$1" in res.sql
    assert "LIMIT 25" in res.sql
    assert len(res.params) >= 1
    res.close()


def test_sqlite_emission(test_env):
    ctx, schema, policy = test_env
    ir = "(nlsql 1 (query (from orders o) (select (field (column o total) total)) (limit 15)))"
    res = nlsql.compile_ir(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_SQLITE)
    assert res.status == nlsql.NLSQL_OK
    assert '"orders"' in res.sql
    assert "LIMIT 15" in res.sql
    res.close()


def test_mysql_emission(test_env):
    ctx, schema, policy = test_env
    ir = "(nlsql 1 (query (from orders o) (select (field (column o total) total)) (limit 10)))"
    res = nlsql.compile_ir(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_MYSQL)
    assert res.status == nlsql.NLSQL_OK
    assert "`orders`" in res.sql
    assert "`public`" in res.sql
    res.close()


def test_sqlserver_emission(test_env):
    ctx, schema, policy = test_env
    ir = "(nlsql 1 (query (from orders o) (select (field (column o total) total)) (limit 50)))"
    res = nlsql.compile_ir(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_SQLSERVER)
    assert res.status == nlsql.NLSQL_OK
    assert "[orders]" in res.sql
    assert "TOP 50" in res.sql
    res.close()


def test_duckdb_emission(test_env):
    ctx, schema, policy = test_env
    ir = "(nlsql 1 (query (from orders o) (select (field (column o total) total)) (limit 5)))"
    res = nlsql.compile_ir(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_DUCKDB)
    assert res.status == nlsql.NLSQL_OK
    assert "LIMIT 5" in res.sql
    res.close()


def test_join_multi_dialect(test_env):
    ctx, schema, policy = test_env
    ir = "(nlsql 1 (query (from orders o) (join inner customers c (eq (column o customer_id) (column c id))) (select (field (column o id) oid) (field (column c name) cname)) (limit 10)))"
    for d in (nlsql.NLSQL_DIALECT_POSTGRES, nlsql.NLSQL_DIALECT_SQLITE, nlsql.NLSQL_DIALECT_MYSQL, nlsql.NLSQL_DIALECT_SQLSERVER):
        res = nlsql.compile_ir(ctx, ir, schema, policy, dialect=d)
        assert res.status == nlsql.NLSQL_OK
        assert "JOIN" in res.sql
        assert res.complexity >= 3
        res.close()
