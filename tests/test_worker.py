"""Tests for the nlsqlc background drift & migration worker."""
from __future__ import annotations

import sqlite3
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import worker


def test_schema_drift_detector(tmp_path):
    db_path = tmp_path / "test_drift.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, total NUMERIC)")

    detector = worker.SchemaDriftDetector(str(db_path))
    res1 = detector.check_drift()
    assert res1["table_count"] == 1
    assert res1["column_count"] == 2
    assert res1["drift_detected"] is False

    # Perform a second check with no DB changes
    res2 = detector.check_drift()
    assert res2["drift_detected"] is False

    # Add a new table and new column
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, email TEXT)")
        conn.execute("ALTER TABLE orders ADD COLUMN status TEXT")

    res3 = detector.check_drift()
    assert res3["drift_detected"] is True
    assert "customers" in res3["new_tables"]
    assert ("orders", "status") in res3["new_columns"]
    assert res3["table_count"] == 2
    assert res3["column_count"] == 5


def test_migration_worker_run_once(tmp_path):
    db_path = tmp_path / "app.db"
    out_schema = tmp_path / "app.nlschema"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")

    w = worker.MigrationWorker(str(db_path), poll_interval_sec=0.1, out_schema_path=str(out_schema))
    res = w.run_once()
    assert res["table_count"] == 1
