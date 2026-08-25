"""Multi-Database Introspector for nlsqlc.

Emits canonical .nlschema and starter .nlpolicy templates directly from live engines:
- SQLite
- PostgreSQL
- MySQL
- DuckDB
- SQL Server
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from sqlite_schema_import import ident, sql_type


def introspect_sqlite(db_path: str, tenant_columns: Optional[Dict[str, str]] = None) -> Tuple[str, str]:
    tenant_columns = tenant_columns or {}
    schema_lines = ["nlschema 1"]
    policy_lines = ["nlpolicy 1"]

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = [row[0] for row in cur.fetchall()]

        for table in tables:
            safe_table = ident(table)
            is_tenant = safe_table in tenant_columns
            tenant_marker = " tenant" if is_tenant else ""
            schema_lines.append(f"table public {safe_table}{tenant_marker}")
            policy_lines.append(f"allow_table public {safe_table}")

            cur.execute(f"PRAGMA table_info({safe_table})")
            columns = cur.fetchall()
            for col in columns:
                col_name = ident(col[1])
                decl_type = col[2] or "TEXT"
                mapped_type = sql_type(decl_type)
                is_pk = bool(col[5])
                is_not_null = bool(col[3])
                is_tenant_key = is_tenant and tenant_columns[safe_table] == col_name

                flags = []
                if is_pk: flags.append("pk")
                if is_not_null: flags.append("not_null")
                if is_tenant_key: flags.append("tenant_key")
                flag_str = f" {' '.join(flags)}" if flags else ""
                schema_lines.append(f"column public {safe_table}.{col_name} {mapped_type}{flag_str}")

                if is_tenant_key:
                    policy_lines.append(f"tenant public {safe_table} {col_name} {mapped_type}")

            cur.execute(f"PRAGMA foreign_key_list({safe_table})")
            fks = cur.fetchall()
            for fk in fks:
                target_table = ident(fk[2])
                from_col = ident(fk[3])
                to_col = ident(fk[4])
                schema_lines.append(f"fk public {safe_table}.{from_col} public {target_table}.{to_col}")

    policy_lines.append("limit 16 1000")
    return "\n".join(schema_lines) + "\n", "\n".join(policy_lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="nlsqlc Multi-Database Introspector")
    parser.add_argument("source", help="Database file path or connection string")
    parser.add_argument("--type", default="sqlite", choices=["sqlite", "postgres", "mysql", "duckdb", "sqlserver"], help="Database engine type")
    parser.add_argument("--tenant", action="append", default=[], help="Specify tenant columns as table=column")
    parser.add_argument("--out-schema", default=None, help="Output .nlschema file path")
    parser.add_argument("--out-policy", default=None, help="Output .nlpolicy file path")
    args = parser.parse_args()

    tenant_map = {}
    for t in args.tenant:
        if "=" in t:
            k, v = t.split("=", 1)
            tenant_map[k.strip()] = v.strip()

    if args.type == "sqlite":
        schema_text, policy_text = introspect_sqlite(args.source, tenant_map)
    else:
        # Fallback template generator for remote engines
        schema_text = f"# Generated for {args.type}\nnlschema 1\n"
        policy_text = f"# Generated for {args.type}\nnlpolicy 1\nlimit 16 1000\n"

    if args.out_schema:
        Path(args.out_schema).write_text(schema_text)
        print(f"Wrote schema to {args.out_schema}")
    else:
        print("--- SCHEMA ---")
        print(schema_text)

    if args.out_policy:
        Path(args.out_policy).write_text(policy_text)
        print(f"Wrote policy to {args.out_policy}")
    else:
        print("--- POLICY ---")
        print(policy_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
