import sqlite3
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from sqlite_schema_import import import_schema  # noqa: E402


def test_tenancy_is_explicit_not_heuristic(tmp_path):
    db_path = tmp_path / "app.db"
    with sqlite3.connect(db_path) as db:
        db.execute("create table orders (id integer, tenant_id text)")
    plain = import_schema(db_path)
    assert "table public orders tenant" not in plain
    assert "tenant_key" not in plain
    configured = import_schema(db_path, {"orders": "tenant_id"})
    assert "table public orders tenant" in configured
    assert "column public orders.tenant_id text tenant_key" in configured


def test_missing_explicit_tenant_column_fails_closed(tmp_path):
    db_path = tmp_path / "app.db"
    with sqlite3.connect(db_path) as db:
        db.execute("create table orders (id integer)")
    with pytest.raises(ValueError, match="configured tenant column"):
        import_schema(db_path, {"orders": "tenant_id"})