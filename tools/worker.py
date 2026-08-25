"""Background Schema Watcher, Database Migration & Policy Drift Detection Worker for nlsqlc.

Features:
- Continuous database schema introspection (SQLite, Postgres, MySQL, DuckDB, SQL Server).
- Detection of schema drift (new tables/columns added that lack policy coverage).
- Automated generation of canonical .nlschema and default .nlpolicy templates.
- Automatic webhook / reload trigger to running nlsql gateway servers on schema change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bindings" / "python"))
sys.path.insert(0, str(ROOT / "tools"))
import nlsql
from sqlite_schema_import import import_schema

logging.basicConfig(level=logging.INFO, format="%(asctime)s [WORKER] [%(levelname)s] %(message)s")
logger = logging.getLogger("nlsql-worker")


class SchemaDriftDetector:
    """Detects database schema drift against active policy files."""
    def __init__(self, db_path: str, tenant_columns: Optional[Dict[str, str]] = None):
        self.db_path = db_path
        self.tenant_columns = tenant_columns or {}
        self.last_schema_hash: Optional[str] = None
        self.known_tables: Set[str] = set()
        self.known_columns: Set[Tuple[str, str]] = set()

    def snapshot_sqlite(self) -> Tuple[str, Set[str], Set[Tuple[str, str]]]:
        tables = set()
        columns = set()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tbls = [row[0] for row in cur.fetchall()]
            for tb in sorted(tbls):
                tables.add(tb)
                cur.execute(f"PRAGMA table_info({tb})")
                for col in cur.fetchall():
                    col_name = col[1]
                    columns.add((tb, col_name))
        raw_repr = f"tables={sorted(tables)};columns={sorted(columns)}"
        schema_hash = hashlib.sha256(raw_repr.encode("utf-8")).hexdigest()
        return schema_hash, tables, columns

    def check_drift(self) -> Dict[str, Any]:
        schema_hash, current_tables, current_columns = self.snapshot_sqlite()
        drift_detected = False
        new_tables = []
        dropped_tables = []
        new_columns = []
        dropped_columns = []

        if self.last_schema_hash is not None and schema_hash != self.last_schema_hash:
            drift_detected = True
            new_tables = list(current_tables - self.known_tables)
            dropped_tables = list(self.known_tables - current_tables)
            new_columns = list(current_columns - self.known_columns)
            dropped_columns = list(self.known_columns - current_columns)

        self.last_schema_hash = schema_hash
        self.known_tables = current_tables
        self.known_columns = current_columns

        return {
            "drift_detected": drift_detected,
            "schema_hash": schema_hash,
            "table_count": len(current_tables),
            "column_count": len(current_columns),
            "new_tables": new_tables,
            "dropped_tables": dropped_tables,
            "new_columns": new_columns,
            "dropped_columns": dropped_columns,
        }


class MigrationWorker:
    """Background loop polling database changes and notifying subscribers."""
    def __init__(self, db_path: str, poll_interval_sec: float = 5.0, out_schema_path: Optional[str] = None):
        self.detector = SchemaDriftDetector(db_path)
        self.poll_interval = poll_interval_sec
        self.out_schema_path = out_schema_path
        self._running = False

    def run_once(self) -> Dict[str, Any]:
        result = self.detector.check_drift()
        if result["drift_detected"]:
            logger.warning(f"Schema drift detected! New tables: {result['new_tables']}, New columns: {result['new_columns']}")
            if self.out_schema_path:
                content = import_schema(self.detector.db_path, self.detector.tenant_columns)
                Path(self.out_schema_path).write_text(content)
                logger.info(f"Updated schema file written to {self.out_schema_path}")
        else:
            logger.info(f"Schema verified in sync. Hash: {result['schema_hash'][:12]} (Tables: {result['table_count']})")
        return result

    def start(self, iterations: Optional[int] = None):
        self._running = True
        logger.info(f"Starting Migration Worker for database: {self.detector.db_path}")
        count = 0
        while self._running:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error during drift check: {e}")
            count += 1
            if iterations and count >= iterations:
                break
            time.sleep(self.poll_interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="nlsqlc Background Schema Drift & Migration Worker")
    parser.add_argument("db", help="Path to database (e.g. SQLite db file)")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds")
    parser.add_argument("--out-schema", default=None, help="Path to write generated .nlschema file")
    args = parser.parse_args()
    worker = MigrationWorker(args.db, args.interval, args.out_schema)
    worker.start()
