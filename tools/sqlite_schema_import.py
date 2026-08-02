#!/usr/bin/env python3
"""Import a SQLite database schema into nlsqlc's trusted .nlschema format."""
from __future__ import annotations
import argparse
import os
import sqlite3
import tempfile
from pathlib import Path


def sql_type(declared: str) -> str:
    t = declared.upper()
    if "INT" in t:
        return "int64"
    if any(x in t for x in ("REAL", "FLOA", "DOUB")):
        return "float64"
    if any(x in t for x in ("DEC", "NUM")):
        return "decimal"
    if "BOOL" in t:
        return "boolean"
    if any(x in t for x in ("BLOB", "BINARY")):
        return "binary"
    if "UUID" in t:
        return "uuid"
    if "DATE" in t and "TIME" not in t:
        return "date"
    if "TIME" in t:
        return "timestamp"
    return "text"


def ident(value: str) -> str:
    if not value or not (value[0].isalpha() or value[0] == "_") or any(not (c.isalnum() or c == "_") for c in value):
        raise ValueError(f"unsafe SQLite identifier: {value!r}")
    return value


def import_schema(database: Path, tenant_columns: dict[str, str] | None = None) -> str:
    """Import schema with explicit tenancy mapping keyed by table name.

    No column is treated as a tenant key unless the caller explicitly maps it.
    """
    tenant_columns = tenant_columns or {}
    uri = f"file:{database.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        rows = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        out = ["nlschema 1"]
        tables = {ident(row[0]) for row in rows}
        for table in sorted(tables):
            columns = db.execute(f'PRAGMA table_info("{table}")').fetchall()
            names = {ident(str(row[1])) for row in columns}
            tenant_column = tenant_columns.get(table)
            if tenant_column is not None and tenant_column not in names:
                raise ValueError(f"configured tenant column is missing from table {table}: {tenant_column}")
            tenant = " tenant" if tenant_column else ""
            out.append(f"table public {table}{tenant}")
            for _, name, declared, notnull, _, pk in columns:
                name = ident(str(name))
                flags = []
                if pk:
                    flags.append("pk")
                if notnull:
                    flags.append("not_null")
                if tenant_column is not None and name == tenant_column:
                    flags.append("tenant_key")
                suffix = " " + ",".join(flags) if flags else ""
                out.append(f"column public {table}.{name} {sql_type(str(declared))}{suffix}")
            fks = db.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
            for _, _, parent, from_col, to_col, *_ in sorted(fks, key=lambda row: (str(row[3]), str(row[2]), str(row[4]))):
                parent = ident(str(parent)); from_col = ident(str(from_col)); to_col = ident(str(to_col))
                if parent not in tables:
                    raise ValueError(f"foreign key references unknown table: {parent}")
                out.append(f"fk public {table}.{from_col} public {parent}.{to_col}")
        return "\n".join(out) + "\n"


def atomic_write(path: Path, content: str) -> None:
    path = path.absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tenant-table", action="append", default=[], metavar="TABLE=COLUMN", help="Explicitly mark a table column as tenant key; repeatable")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error(f"database does not exist: {args.database}")
    tenant_columns: dict[str, str] = {}
    for mapping in args.tenant_table:
        if "=" not in mapping:
            parser.error(f"invalid --tenant-table mapping: {mapping!r}; expected TABLE=COLUMN")
        table, column = mapping.split("=", 1)
        try:
            tenant_columns[ident(table)] = ident(column)
        except ValueError as exc:
            parser.error(str(exc))
    atomic_write(args.output, import_schema(args.database, tenant_columns))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
