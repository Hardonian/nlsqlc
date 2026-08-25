"""Complete AI Agent & LLM Tool-Calling Integration Demo with nlsqlc.

Shows how LLMs (OpenAI, Claude, Gemini, DeepSeek, Ollama) interact with
nlsqlc to guarantee zero-SQL-injection and mathematical tenant isolation.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
from pathlib import Path

# Ensure UTF-8 output encoding across Windows/Linux/macOS
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure nlsql bindings are discoverable
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bindings" / "python"))
import nlsql


def setup_sample_database() -> sqlite3.Connection:
    """Setup an in-memory SQLite database simulating multi-tenant SaaS data."""
    conn = sqlite3.connect(":memory:")
    conn.execute("ATTACH DATABASE ':memory:' AS public")
    conn.execute("CREATE TABLE public.orders (id INTEGER PRIMARY KEY, tenant_id TEXT, customer_id INTEGER, total NUMERIC, status TEXT)")
    conn.execute("CREATE TABLE public.customers (id INTEGER PRIMARY KEY, tenant_id TEXT, name TEXT, region TEXT)")

    # Seed Tenant A (Acme Corp)
    conn.execute("INSERT INTO public.customers VALUES (1, 'tenant-acme', 'Alice', 'US-West')")
    conn.execute("INSERT INTO public.orders VALUES (101, 'tenant-acme', 1, 450.00, 'completed')")
    conn.execute("INSERT INTO public.orders VALUES (102, 'tenant-acme', 1, 120.50, 'pending')")

    # Seed Tenant B (Evil Corp)
    conn.execute("INSERT INTO public.customers VALUES (2, 'tenant-evil', 'Bob', 'EU-Central')")
    conn.execute("INSERT INTO public.orders VALUES (201, 'tenant-evil', 2, 99999.00, 'completed')")
    conn.commit()
    return conn


def get_llm_tool_definition() -> dict:
    """The JSON schema provided to LLM function calling / tools."""
    return {
        "name": "execute_database_query",
        "description": "Execute an analytical database query using safe S-expression Query IR format.",
        "parameters": {
            "type": "object",
            "properties": {
                "ir": {
                    "type": "string",
                    "description": "Constrained S-expression Query IR v2 representing the analytical intent."
                }
            },
            "required": ["ir"]
        }
    }


def execute_agent_query(db: sqlite3.Connection, ctx: nlsql.Context, schema: nlsql.Schema, policy: nlsql.Policy, raw_ir: str, authenticated_tenant: str):
    print(f"\n=======================================================")
    print(f"🤖 LLM Generated Query IR:\n{raw_ir}")
    print(f"🔒 Authenticated Session Tenant: '{authenticated_tenant}'")

    # Compile with nlsqlc (Fail-closed compiler)
    result = nlsql.compile_ir(ctx, raw_ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_SQLITE)

    if result.status != nlsql.NLSQL_OK:
        print(f"❌ COMPILER REJECTED: {result.error}")
        print("🛡️ Security Policy Prevented Database Execution.")
        return

    print(f"\n✨ nlsqlc Emitted SQL:\n{result.sql}")

    # Bind parameters securely (tenant parameter injected by policy)
    bound_args = []
    for param in result.params:
        if param["source"] == nlsql.NLSQL_PARAM_POLICY:
            bound_args.append(authenticated_tenant)
        else:
            bound_args.append("completed") # Example user param

    print(f"📌 Executing with Parameter Bindings: {bound_args}")
    cursor = db.cursor()
    cursor.execute(result.sql, bound_args)
    rows = cursor.fetchall()

    print(f"\n📊 Returned Rows for Tenant '{authenticated_tenant}':")
    for r in rows:
        print(f"   {r}")


def main():
    print("=======================================================")
    print("   nlsqlc AI Agent Deterministic Tool Execution Demo   ")
    print("=======================================================")

    db = setup_sample_database()
    ctx = nlsql.Context()

    schema = nlsql.Schema(ctx, [
        ("public", "orders", [
            ("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY),
            ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY),
            ("customer_id", nlsql.NLSQL_TYPE_INT64, 0),
            ("total", nlsql.NLSQL_TYPE_DECIMAL, 0),
            ("status", nlsql.NLSQL_TYPE_TEXT, 0),
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

    # Scenario 1: Legitimate User Query ("Show my orders with customer details")
    legit_ir = """(nlsql 2
      (query
        (from orders o)
        (join inner customers c (eq (column o customer_id) (column c id)))
        (select
          (field (column o id) order_id)
          (field (column c name) customer_name)
          (field (column o total) total_amount))
        (limit 10)))"""

    execute_agent_query(db, ctx, schema, policy, legit_ir, authenticated_tenant="tenant-acme")

    # Scenario 2: Adversarial Prompt Injection
    # Even if an attacker manipulates the prompt to look for other tenant data or unauthorized tables:
    hacked_ir = """(nlsql 2
      (query
        (from orders o)
        (select (field (column o id) id))
        (where (eq (column o tenant_id) (param fake_tenant text)))
        (limit 10)))"""

    # Notice: nlsqlc overrides and enforces the actual caller's tenant!
    execute_agent_query(db, ctx, schema, policy, hacked_ir, authenticated_tenant="tenant-acme")


if __name__ == "__main__":
    main()
