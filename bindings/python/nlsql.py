"""Dependency-free ctypes binding for the nlsqlc C ABI."""
from __future__ import annotations
import ctypes as c
import os
from pathlib import Path

NLSQL_OK = 0
NLSQL_TYPE_INT64 = 3
NLSQL_TYPE_UUID = 9
NLSQL_DIALECT_POSTGRES = 0
NLSQL_DIALECT_SQLITE = 1
NLSQL_DIALECT_DUCKDB = 2
NLSQL_DIALECT_MYSQL = 3
NLSQL_DIALECT_SQLSERVER = 4


def _library() -> c.CDLL:
    candidates = []
    if os.environ.get("NLSQL_LIBRARY"):
        candidates.append(os.environ["NLSQL_LIBRARY"])
    root = Path(__file__).resolve().parents[2]
    names = ("libnlsql.so", "libnlsql.dylib", "nlsql.dll", "libnlsql.dll")
    candidates += [str(root / "build" / name) for name in names]
    for build_dir in ("qa", "integration", "security-fix", "cpp-asan", "final"):
        candidates += [str(root / "build" / build_dir / name) for name in names]
    candidates += [str(Path(prefix) / name) for prefix in ("/usr/local/lib", "/usr/lib") for name in names]
    for path in candidates:
        if Path(path).exists():
            return c.CDLL(path)
    raise RuntimeError("libnlsql.so not found; build the shared library or set NLSQL_LIBRARY")


_lib = _library()

class Limits(c.Structure):
    _fields_ = [(n, c.c_size_t) for n in ("max_ir_bytes", "max_schema_objects", "max_sql_bytes", "max_nodes", "max_joins", "max_selected_fields", "default_limit", "max_limit")]

class Config(c.Structure):
    _fields_ = [("limits", Limits), ("diagnostic_errors", c.c_int)]

class CompileRequest(c.Structure):
    _fields_ = [("ir", c.c_char_p), ("schema", c.c_void_p), ("policy", c.c_void_p), ("dialect", c.c_int), ("trace_id", c.c_char_p)]

for name, args, result in [
    ("nlsql_context_create", [c.POINTER(Config), c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_schema_builder_create", [c.c_void_p, c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_schema_builder_add_table", [c.c_void_p, c.c_char_p, c.c_char_p, c.c_uint], c.c_int),
    ("nlsql_schema_builder_add_column", [c.c_void_p, c.c_char_p, c.c_char_p, c.c_char_p, c.c_int, c.c_uint], c.c_int),
    ("nlsql_schema_builder_finalize", [c.c_void_p, c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_policy_create", [c.c_void_p, c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_policy_allow_table", [c.c_void_p, c.c_char_p, c.c_char_p], c.c_int),
    ("nlsql_compile_ir", [c.c_void_p, c.POINTER(CompileRequest), c.POINTER(c.c_void_p)], c.c_int),
]:
    fn = getattr(_lib, name); fn.argtypes = args; fn.restype = result
for name, args in [("nlsql_context_destroy", [c.c_void_p]), ("nlsql_schema_builder_destroy", [c.c_void_p]), ("nlsql_schema_destroy", [c.c_void_p]), ("nlsql_policy_destroy", [c.c_void_p]), ("nlsql_compile_result_destroy", [c.c_void_p])]:
    fn = getattr(_lib, name); fn.argtypes = args; fn.restype = None
_lib.nlsql_result_sql.argtypes = [c.c_void_p]
_lib.nlsql_result_status.argtypes = [c.c_void_p]; _lib.nlsql_result_status.restype = c.c_int
_lib.nlsql_result_error.argtypes = [c.c_void_p]; _lib.nlsql_result_error.restype = c.c_char_p
_lib.nlsql_result_canonical_ir.argtypes = [c.c_void_p]; _lib.nlsql_result_canonical_ir.restype = c.c_char_p
_lib.nlsql_result_fingerprint.argtypes = [c.c_void_p]; _lib.nlsql_result_fingerprint.restype = c.c_uint64
_lib.nlsql_result_complexity.argtypes = [c.c_void_p]; _lib.nlsql_result_complexity.restype = c.c_uint
_lib.nlsql_result_relevance_score.argtypes = [c.c_void_p]; _lib.nlsql_result_relevance_score.restype = c.c_double
class SQLView(c.Structure):
    _fields_ = [("sql", c.c_char_p), ("length", c.c_size_t)]
_lib.nlsql_result_sql.restype = SQLView
_lib.nlsql_status_name.argtypes = [c.c_int]; _lib.nlsql_status_name.restype = c.c_char_p


def _check(status: int) -> None:
    if status != NLSQL_OK:
        raise RuntimeError(_lib.nlsql_status_name(status).decode())


class Context:
    def __init__(self, config: Config | None = None):
        self._ptr = c.c_void_p(); _check(_lib.nlsql_context_create(c.byref(config or Config()), c.byref(self._ptr)))
    def close(self) -> None:
        ptr = getattr(self, "_ptr", None)
        if ptr:
            _lib.nlsql_context_destroy(ptr); self._ptr = None
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def __del__(self): self.close()

class Schema:
    def __init__(self, context: Context, tables: list[tuple[str, str, list[tuple[str, int]]]]):
        self._builder = c.c_void_p(); _check(_lib.nlsql_schema_builder_create(context._ptr, c.byref(self._builder)))
        for schema, table, columns in tables:
            _check(_lib.nlsql_schema_builder_add_table(self._builder, schema.encode(), table.encode(), 0))
            for column, typ in columns:
                _check(_lib.nlsql_schema_builder_add_column(self._builder, schema.encode(), table.encode(), column.encode(), typ, 0))
        self._ptr = c.c_void_p(); _check(_lib.nlsql_schema_builder_finalize(self._builder, c.byref(self._ptr)))
    def close(self) -> None:
        builder = getattr(self, "_builder", None)
        ptr = getattr(self, "_ptr", None)
        if builder:
            _lib.nlsql_schema_builder_destroy(builder); self._builder = None
        if ptr:
            _lib.nlsql_schema_destroy(ptr); self._ptr = None
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def __del__(self): self.close()

class Policy:
    def __init__(self, context: Context, tables: list[tuple[str, str]]):
        self._ptr = c.c_void_p(); _check(_lib.nlsql_policy_create(context._ptr, c.byref(self._ptr)))
        for schema, table in tables: _check(_lib.nlsql_policy_allow_table(self._ptr, schema.encode(), table.encode()))
    def close(self) -> None:
        ptr = getattr(self, "_ptr", None)
        if ptr:
            _lib.nlsql_policy_destroy(ptr); self._ptr = None
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def __del__(self): self.close()

class Result:
    def __init__(self, ptr): self._ptr = ptr
    @property
    def sql(self) -> str: return _lib.nlsql_result_sql(self._ptr).sql.decode()
    @property
    def status(self) -> int: return _lib.nlsql_result_status(self._ptr)
    @property
    def error(self) -> str | None:
        value = _lib.nlsql_result_error(self._ptr)
        return value.decode() if value else None
    @property
    def canonical_ir(self) -> str: return _lib.nlsql_result_canonical_ir(self._ptr).decode()
    @property
    def fingerprint(self) -> int: return int(_lib.nlsql_result_fingerprint(self._ptr))
    @property
    def complexity(self) -> int: return int(_lib.nlsql_result_complexity(self._ptr))
    @property
    def relevance_score(self) -> float: return float(_lib.nlsql_result_relevance_score(self._ptr))
    def close(self) -> None:
        ptr = getattr(self, "_ptr", None)
        if ptr:
            _lib.nlsql_compile_result_destroy(ptr); self._ptr = None
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def __del__(self): self.close()

def compile_ir(context: Context, schema: Schema, policy: Policy, ir: str, dialect: int = NLSQL_DIALECT_POSTGRES) -> Result:
    request = CompileRequest(ir.encode(), schema._ptr, policy._ptr, dialect, None)
    ptr = c.c_void_p(); _check(_lib.nlsql_compile_ir(context._ptr, c.byref(request), c.byref(ptr)))
    return Result(ptr)
