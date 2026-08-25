"""Limits, Chaos, and Security Stress Test Suite for nlsqlc."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bindings" / "python"))
import nlsql


def test_deeply_nested_ast():
    ctx = nlsql.Context()
    schema = nlsql.Schema(ctx, [("public", "orders", [("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY), ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY)])])
    policy = nlsql.Policy(ctx, allow=[("public", "orders")], tenant=[("public", "orders", "tenant_id", nlsql.NLSQL_TYPE_UUID)])

    # Construct nested boolean logic 50 levels deep
    inner = "(eq (column o id) (column o id))"
    for _ in range(50):
        inner = f"(and {inner} (eq (column o id) (column o id)))"
    ir = f"(nlsql 1 (query (from orders o) (select (field (column o id) id)) (where {inner}) (limit 10)))"

    res = nlsql.compile_ir(ctx, ir, schema, policy)
    assert res.status in (nlsql.NLSQL_OK, nlsql.NLSQL_E_LIMIT)
    res.close()
    policy.close()
    schema.close()
    ctx.close()


def test_unbalanced_parentheses_rejection():
    ctx = nlsql.Context()
    schema = nlsql.Schema(ctx, [("public", "orders", [("id", nlsql.NLSQL_TYPE_INT64, 0)])])
    policy = nlsql.Policy(ctx, allow=[("public", "orders")])

    bad_irs = [
        "(nlsql 1 (query (from orders o) (select (field (column o id) id)))",  # missing closing
        "(nlsql 1 (query (from orders o)) (select (field (column o id) id))))", # extra closing
        "(((((((((())))))))))",
        "",
        "SELECT * FROM orders;",  # Raw SQL attempt
    ]

    for bad in bad_irs:
        res = nlsql.compile_ir(ctx, bad, schema, policy)
        assert res.status != nlsql.NLSQL_OK
        res.close()

    policy.close()
    schema.close()
    ctx.close()


def test_schema_scaling_limits():
    ctx = nlsql.Context()
    # Create 50 tables with 10 columns each (500 columns total)
    tables = []
    allow_rules = []
    for t_idx in range(50):
        t_name = f"tbl_{t_idx}"
        cols = [("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY), ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY)]
        for c_idx in range(8):
            cols.append((f"col_{c_idx}", nlsql.NLSQL_TYPE_TEXT, 0))
        tables.append(("public", t_name, cols))
        allow_rules.append(("public", t_name))

    schema = nlsql.Schema(ctx, tables)
    policy = nlsql.Policy(ctx, allow=allow_rules)

    ir = "(nlsql 1 (query (from tbl_42 t) (select (field (column t col_3) c3)) (limit 10)))"
    res = nlsql.compile_ir(ctx, ir, schema, policy)
    assert res.status == nlsql.NLSQL_OK
    assert "tbl_42" in res.sql
    res.close()

    policy.close()
    schema.close()
    ctx.close()


def test_sql_injection_rejection():
    ctx = nlsql.Context()
    schema = nlsql.Schema(ctx, [("public", "orders", [("id", nlsql.NLSQL_TYPE_INT64, 0), ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY)])])
    policy = nlsql.Policy(ctx, allow=[("public", "orders")])

    injections = [
        "(nlsql 1 (query (from orders; DROP TABLE orders;--) (select (field (column o id) id))))",
        "(nlsql 1 (query (from orders o) (select (field (column o id' OR '1'='1) id))))",
        "(nlsql 1 (query (from orders o) (select (field (column o \"id\") id))))",
    ]

    for inj in injections:
        res = nlsql.compile_ir(ctx, inj, schema, policy)
        assert res.status != nlsql.NLSQL_OK
        res.close()

    policy.close()
    schema.close()
    ctx.close()
