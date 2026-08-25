"""Tests for the AST Query Optimizer, Constant Folding, and Extended Operators."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bindings" / "python"))
import nlsql


@pytest.fixture
def env():
    ctx = nlsql.Context()
    schema = nlsql.Schema(ctx, [
        ("public", "orders", [
            ("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY),
            ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY),
            ("customer_id", nlsql.NLSQL_TYPE_INT64, 0),
            ("total", nlsql.NLSQL_TYPE_DECIMAL, 0),
            ("status", nlsql.NLSQL_TYPE_TEXT, 0),
            ("created_at", nlsql.NLSQL_TYPE_TIMESTAMP, 0),
        ])
    ])
    policy = nlsql.Policy(
        ctx,
        allow=[("public", "orders")],
        tenant=[("public", "orders", "tenant_id", nlsql.NLSQL_TYPE_UUID)],
        runtime_tenant=("tenant_id", nlsql.NLSQL_TYPE_UUID),
    )
    yield ctx, schema, policy
    policy.close()
    schema.close()
    ctx.close()


def test_constant_folding_arithmetic():
    ast = ["add", 10, 20]
    opt = nlsql._py_optimize_ast(ast)
    assert opt == 30

    ast2 = ["mul", 6, 7]
    assert nlsql._py_optimize_ast(ast2) == 42


def test_boolean_reductions():
    # (and true X) -> X
    ast = ["and", "true", ["eq", ["column", "o", "id"], 1]]
    opt = nlsql._py_optimize_ast(ast)
    assert opt == ["eq", ["column", "o", "id"], 1]

    # (or false X) -> X
    ast2 = ["or", "false", ["eq", ["column", "o", "id"], 2]]
    opt2 = nlsql._py_optimize_ast(ast2)
    assert opt2 == ["eq", ["column", "o", "id"], 2]

    # (not (not X)) -> X
    ast3 = ["not", ["not", ["eq", ["column", "o", "id"], 3]]]
    opt3 = nlsql._py_optimize_ast(ast3)
    assert opt3 == ["eq", ["column", "o", "id"], 3]


def test_extended_operator_in_and_between(env):
    ctx, schema, policy = env
    ir = "(nlsql 2 (query (from orders o) (select (field (column o id) id)) (where (and (in (column o status) (param s1 text) (param s2 text)) (between (column o total) 10 500))) (limit 10)))"
    res = nlsql.compile_ir(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_POSTGRES)
    assert res.status == nlsql.NLSQL_OK
    assert "IN (" in res.sql
    assert "BETWEEN" in res.sql
    res.close()


def test_extended_operator_like_and_case(env):
    ctx, schema, policy = env
    ir = """(nlsql 2
      (query
        (from orders o)
        (select
          (field (case (when (eq (column o status) (param status_val text)) 1) (else 0)) is_matched))
        (where (like (column o status) (param pattern text)))
        (limit 10)))"""
    res = nlsql.compile_ir(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_POSTGRES)
    assert res.status == nlsql.NLSQL_OK
    assert "CASE WHEN" in res.sql
    assert "LIKE" in res.sql
    res.close()


def test_date_trunc_and_extract(env):
    ctx, schema, policy = env
    ir = """(nlsql 2
      (query
        (from orders o)
        (select
          (field (date-trunc "month" (column o created_at)) order_month)
          (field (extract "year" (column o created_at)) order_year))
        (limit 10)))"""
    res = nlsql.compile_ir(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_POSTGRES)
    assert res.status == nlsql.NLSQL_OK
    assert "DATE_TRUNC" in res.sql
    assert "EXTRACT" in res.sql
    res.close()
