"""Property tests for importer safety, tenant policy, and SQL quoting."""
from __future__ import annotations

import random
import re
import string
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from sqlite_schema_import import ident, sql_type

SAFE_IDENT_REGEX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def test_importer_accepts_safe_identifiers_property():
    """Generative property test ensuring all valid identifiers pass."""
    letters = string.ascii_letters + "_"
    alphanumeric = string.ascii_letters + string.digits + "_"

    for _ in range(500):
        length = random.randint(1, 32)
        first_char = random.choice(letters)
        rest = "".join(random.choice(alphanumeric) for _ in range(length - 1))
        candidate = first_char + rest

        assert SAFE_IDENT_REGEX.match(candidate)
        assert ident(candidate) == candidate


def test_importer_rejects_unsafe_identifiers_property():
    """Generative property test ensuring all invalid identifiers fail-closed."""
    unsafe_samples = [
        "",
        "123order",
        "orders; DROP TABLE",
        "user-name",
        "user.name",
        "orders' OR '1'='1",
        "table$name",
        "order\nname",
        "name\0null",
    ]

    for sample in unsafe_samples:
        with pytest.raises(ValueError):
            ident(sample)

    # Random generation of strings containing illegal characters
    for _ in range(500):
        length = random.randint(1, 20)
        dirty_string = "".join(random.choice(string.printable) for _ in range(length))
        if not SAFE_IDENT_REGEX.match(dirty_string):
            with pytest.raises(ValueError):
                ident(dirty_string)


def test_sql_type_mapping_is_deterministic_property():
    """Validates deterministic mapping across standard SQL datatypes."""
    type_samples = [
        ("INTEGER", "int64"),
        ("INT", "int64"),
        ("BIGINT", "int64"),
        ("SMALLINT", "int64"),
        ("NUMERIC", "decimal"),
        ("DECIMAL(10,2)", "decimal"),
        ("REAL", "float64"),
        ("FLOAT", "float64"),
        ("DOUBLE", "float64"),
        ("TEXT", "text"),
        ("VARCHAR(255)", "text"),
        ("CHAR(10)", "text"),
        ("BLOB", "binary"),
        ("BINARY", "binary"),
        ("UUID", "uuid"),
        ("DATE", "date"),
        ("TIMESTAMP", "timestamp"),
        ("TIMESTAMPTZ", "timestamp"),
        ("UNKNOWN_CUSTOM_TYPE", "text"),
    ]

    for decl, expected in type_samples:
        result = sql_type(decl)
        assert result in {"int64", "decimal", "float64", "text", "binary", "uuid", "date", "timestamp"}
        assert result == expected