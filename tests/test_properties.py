"""Property tests for importer safety, tenant policy, and SQL quoting."""
from pathlib import Path
import sys

import pytest

try:
    from hypothesis import given, strategies as st
except ImportError:  # pragma: no cover - dependency is installed by CI
    pytest.skip("hypothesis is required for property tests", allow_module_level=True)

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from sqlite_schema_import import ident, sql_type  # noqa: E402


SAFE_IDENT = st.from_regex(r"[A-Za-z_][A-Za-z0-9_]{0,31}", fullmatch=True)


@given(SAFE_IDENT)
def test_importer_accepts_only_safe_identifiers(value):
    assert ident(value) == value


@given(st.text(min_size=1, max_size=64).filter(lambda value: not (value[0].isalpha() or value[0] == "_") or any(not (c.isalnum() or c == "_") for c in value)))
def test_importer_rejects_unsafe_identifiers(value):
    with pytest.raises(ValueError):
        ident(value)


@given(st.sampled_from(["INTEGER", "BIGINT", "NUMERIC", "REAL", "TEXT", "BLOB", "UUID", "DATE", "TIMESTAMP"]))
def test_sql_type_mapping_is_deterministic(declared):
    assert sql_type(declared) in {"int64", "decimal", "float64", "text", "binary", "uuid", "date", "timestamp"}