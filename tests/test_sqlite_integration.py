#!/usr/bin/env python3
"""Execute emitted SQLite SQL through the public ctypes binding."""
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bindings" / "python"))
os.environ.setdefault("NLSQL_LIBRARY", str(ROOT / "build" / "integration" / "libnlsql.so"))
import nlsql  # noqa: E402


def main() -> int:
    context = nlsql.Context()
    schema = nlsql.Schema(context, [("public", "orders", [("id", nlsql.NLSQL_TYPE_INT64)])])
    policy = nlsql.Policy(context, [("public", "orders")])
    result = nlsql.compile_ir(
        context,
        schema,
        policy,
        "(nlsql 1 (query (from orders o) (select (field (column o id) id))))",
        dialect=1,
    )
    connection = sqlite3.connect(":memory:")
    connection.execute("attach database ':memory:' as public")
    connection.execute("create table public.orders (id integer not null)")
    connection.executemany("insert into public.orders(id) values (?)", [(7,), (11,)])
    rows = connection.execute(result.sql).fetchall()
    assert rows == [(7,), (11,)], (result.sql, rows)
    print("sqlite_integration_pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
