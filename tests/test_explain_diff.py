"""Tests for explain visualizer and semantic IR diff tool."""
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
            ("total", nlsql.NLSQL_TYPE_DECIMAL, 0),
        ])
    ])
    policy = nlsql.Policy(ctx, allow=[("public", "orders")], tenant=[("public", "orders", "tenant_id", nlsql.NLSQL_TYPE_UUID)])
    yield ctx, schema, policy
    policy.close()
    schema.close()
    ctx.close()


def test_explain_plan_generator(env):
    ctx, schema, policy = env
    ir = "(nlsql 1 (query (from orders o) (select (field (column o total) total)) (limit 10)))"
    plan = nlsql.explain(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_POSTGRES)

    assert plan["status"] == "OK"
    assert "Query Execution Plan" in plan["plan_ascii"]
    assert "Status: OK" in plan["plan_ascii"]
    assert plan["complexity"] > 0
    assert len(plan["params"]) >= 1


def test_semantic_ir_diff():
    ir1 = "(nlsql 1 (query (from orders o) (select (field (column o id) id)) (limit 10)))"
    ir2 = "(nlsql 1   (query   (from orders o)   (select (field (column o id) id))   (limit 10)))"
    ir3 = "(nlsql 1 (query (from orders o) (select (field (column o total) total)) (limit 10)))"

    res_same = nlsql.diff(ir1, ir2)
    assert res_same["identical"] is True

    res_diff = nlsql.diff(ir1, ir3)
    assert res_diff["identical"] is False
