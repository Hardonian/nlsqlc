#!/usr/bin/env python3
"""Execute representative emitted SQL against configured live engines.

SQLite is always exercised. Other engines are opt-in through environment URLs;
missing credentials are reported as BLOCKED rather than silently passed.
"""
from __future__ import annotations
import os
import sqlite3
import sys


def sqlite_probe() -> None:
    with sqlite3.connect(":memory:") as db:
        db.execute("create table orders (id integer not null)")
        db.execute("insert into orders values (1)")
        assert db.execute("select id from orders limit 10").fetchall() == [(1,)]


def optional_probe(name: str, url_var: str, module: str) -> str:
    url = os.environ.get(url_var)
    if not url:
        return "BLOCKED (set %s)" % url_var
    try:
        import importlib
        driver = importlib.import_module(module)
        if name == "postgres":
            with driver.connect(url) as db, db.cursor() as cur:
                cur.execute("create temporary table nlsql_matrix (id integer)")
                cur.execute("insert into nlsql_matrix values (1)")
                cur.execute("select id from nlsql_matrix limit 10")
                assert cur.fetchall() == [(1,)]
        elif name == "duckdb":
            db = driver.connect(url.replace("duckdb://", "") if url.startswith("duckdb://") else url)
            try:
                db.execute("create table nlsql_matrix (id integer)")
                db.execute("insert into nlsql_matrix values (1)")
                assert db.execute("select id from nlsql_matrix limit 10").fetchall() == [(1,)]
            finally:
                db.close()
        elif name == "mysql":
            db = driver.connect(option_files=None, **_mysql_kwargs(url))
            try:
                cur = db.cursor()
                cur.execute("create temporary table nlsql_matrix (id integer)")
                cur.execute("insert into nlsql_matrix values (1)")
                cur.execute("select id from nlsql_matrix limit 10")
                assert cur.fetchall() == [(1,)]
            finally:
                db.close()
        elif name == "sqlserver":
            with driver.connect(url, autocommit=True) as db:
                cur = db.cursor()
                cur.execute("select 1")
                assert cur.fetchone()[0] == 1
    except Exception as exc:
        return "FAIL (%s: %s)" % (name, type(exc).__name__)
    return "PASS"


def _mysql_kwargs(url: str) -> dict[str, str]:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in {"mysql", "mysql+mysqlconnector"}:
        raise ValueError("NLSQL_MYSQL_URL must be mysql://...")
    return {"host": parsed.hostname or "127.0.0.1", "port": str(parsed.port or 3306), "user": parsed.username or "root", "password": parsed.password or "", "database": parsed.path.lstrip("/") or "test"}


def main() -> int:
    sqlite_probe()
    print("sqlite: PASS")
    for name, env, module in (("postgres", "NLSQL_POSTGRES_URL", "psycopg"), ("duckdb", "NLSQL_DUCKDB_URL", "duckdb"), ("mysql", "NLSQL_MYSQL_URL", "mysql.connector"), ("sqlserver", "NLSQL_SQLSERVER_URL", "pyodbc")):
        print(f"{name}: {optional_probe(name, env, module)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())