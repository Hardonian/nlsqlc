"""Dependency-free ctypes binding for the nlsqlc C ABI."""
from __future__ import annotations
import ctypes as c
import os
from pathlib import Path

NLSQL_OK = 0
NLSQL_TYPE_UNKNOWN = 0
NLSQL_TYPE_NULL = 1
NLSQL_TYPE_BOOLEAN = 2
NLSQL_TYPE_INT64 = 3
NLSQL_TYPE_UINT64 = 4
NLSQL_TYPE_DECIMAL = 5
NLSQL_TYPE_FLOAT64 = 6
NLSQL_TYPE_TEXT = 7
NLSQL_TYPE_BINARY = 8
NLSQL_TYPE_UUID = 9
NLSQL_TYPE_DATE = 10
NLSQL_TYPE_TIMESTAMP = 11
NLSQL_TYPE_TIMESTAMPTZ = 12
NLSQL_PARAM_USER = 0
NLSQL_PARAM_POLICY = 1
NLSQL_PARAM_TRUSTED = 2
NLSQL_RISK_LOW = 0
NLSQL_RISK_MODERATE = 1
NLSQL_RISK_HIGH = 2
NLSQL_RISK_DENIED = 3
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

class QuestionRequest(c.Structure):
    _fields_ = [("question", c.c_char_p), ("schema", c.c_void_p), ("policy", c.c_void_p), ("dialect", c.c_int)]

class CTERequest(c.Structure):
    _fields_ = [("cte_name", c.c_char_p), ("cte_ir", c.c_char_p), ("query_ir", c.c_char_p), ("schema", c.c_void_p), ("policy", c.c_void_p), ("dialect", c.c_int)]

class SetRequest(c.Structure):
    _fields_ = [("left_ir", c.c_char_p), ("right_ir", c.c_char_p), ("schema", c.c_void_p), ("policy", c.c_void_p), ("dialect", c.c_int), ("operation", c.c_int)]

class ParamView(c.Structure):
    _fields_ = [("position", c.c_size_t), ("name", c.c_char_p), ("type", c.c_int), ("source", c.c_int), ("runtime_required", c.c_int)]

class DiagnosticView(c.Structure):
    _fields_ = [("offset", c.c_size_t), ("line", c.c_size_t), ("column", c.c_size_t), ("status", c.c_int), ("code", c.c_char_p), ("message", c.c_char_p)]

for name, args, result in [
    ("nlsql_context_create", [c.POINTER(Config), c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_schema_builder_create", [c.c_void_p, c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_schema_builder_add_table", [c.c_void_p, c.c_char_p, c.c_char_p, c.c_uint], c.c_int),
    ("nlsql_schema_builder_add_column", [c.c_void_p, c.c_char_p, c.c_char_p, c.c_char_p, c.c_int, c.c_uint], c.c_int),
    ("nlsql_schema_builder_finalize", [c.c_void_p, c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_policy_create", [c.c_void_p, c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_policy_allow_table", [c.c_void_p, c.c_char_p, c.c_char_p], c.c_int),
    ("nlsql_policy_deny_column", [c.c_void_p, c.c_char_p, c.c_char_p, c.c_char_p], c.c_int),
    ("nlsql_policy_require_tenant", [c.c_void_p, c.c_char_p, c.c_char_p, c.c_char_p], c.c_int),
    ("nlsql_policy_require_tenant_typed", [c.c_void_p, c.c_char_p, c.c_char_p, c.c_char_p, c.c_int], c.c_int),
    ("nlsql_policy_set_limits", [c.c_void_p, c.c_size_t, c.c_size_t], c.c_int),
    ("nlsql_policy_set_runtime_tenant", [c.c_void_p, c.c_char_p, c.c_int], c.c_int),
    ("nlsql_schema_builder_add_foreign_key", [c.c_void_p, c.c_char_p, c.c_char_p, c.c_char_p, c.c_char_p, c.c_char_p, c.c_char_p], c.c_int),
    ("nlsql_compile_ir", [c.c_void_p, c.POINTER(CompileRequest), c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_compile_cte", [c.c_void_p, c.POINTER(CTERequest), c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_compile_set", [c.c_void_p, c.POINTER(SetRequest), c.POINTER(c.c_void_p)], c.c_int),
    ("nlsql_compile_question", [c.c_void_p, c.POINTER(QuestionRequest), c.POINTER(c.c_void_p)], c.c_int),
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
_lib.nlsql_result_param_count.argtypes = [c.c_void_p]; _lib.nlsql_result_param_count.restype = c.c_size_t
_lib.nlsql_result_param.argtypes = [c.c_void_p, c.c_size_t]; _lib.nlsql_result_param.restype = ParamView
_lib.nlsql_result_manifest.argtypes = [c.c_void_p]; _lib.nlsql_result_manifest.restype = c.c_char_p
_lib.nlsql_result_risk.argtypes = [c.c_void_p]; _lib.nlsql_result_risk.restype = c.c_int
_lib.nlsql_result_diagnostic_count.argtypes = [c.c_void_p]; _lib.nlsql_result_diagnostic_count.restype = c.c_size_t
_lib.nlsql_result_diagnostic.argtypes = [c.c_void_p, c.c_size_t]; _lib.nlsql_result_diagnostic.restype = DiagnosticView
_lib.nlsql_status_name.argtypes = [c.c_int]; _lib.nlsql_status_name.restype = c.c_char_p
class SQLView(c.Structure):
    _fields_ = [("sql", c.c_char_p), ("length", c.c_size_t)]
_lib.nlsql_result_sql.restype = SQLView


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
    def __init__(self, context: Context, tables: list[tuple[str, str, list[tuple[str, int]]]], table_flags: dict[tuple[str, str], int] | None = None, foreign_keys: list[tuple[str, str, str, str, str, str, str]] | None = None):
        self._builder = c.c_void_p(); _check(_lib.nlsql_schema_builder_create(context._ptr, c.byref(self._builder)))
        table_flags = table_flags or {}
        for schema, table, columns in tables:
            _check(_lib.nlsql_schema_builder_add_table(self._builder, schema.encode(), table.encode(), table_flags.get((schema, table), 0)))
            for column_spec in columns:
                column, typ, *rest = column_spec
                flags = rest[0] if rest else 0
                _check(_lib.nlsql_schema_builder_add_column(self._builder, schema.encode(), table.encode(), column.encode(), typ, flags))
        for fk in foreign_keys or []:
            _check(_lib.nlsql_schema_builder_add_foreign_key(self._builder, *(part.encode() for part in fk)))
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
    def __init__(self, context: Context, tables: list[tuple[str, str]], tenants: list[tuple[str, str, str] | tuple[str, str, str, int]] | None = None, runtime_tenant: tuple[str, int] | None = None, denies: list[tuple[str, str, str]] | None = None, limits: tuple[int, int] | None = None):
        self._ptr = c.c_void_p(); _check(_lib.nlsql_policy_create(context._ptr, c.byref(self._ptr)))
        for schema, table in tables: _check(_lib.nlsql_policy_allow_table(self._ptr, schema.encode(), table.encode()))
        for tenant in tenants or []:
            schema, table, column, *declared = tenant
            if declared:
                self.require_tenant_typed(schema, table, column, declared[0])
            else:
                self.require_tenant(schema, table, column)
        for schema, table, column in denies or []: self.deny_column(schema, table, column)
        if limits: self.set_limits(*limits)
        if runtime_tenant: self.set_runtime_tenant(*runtime_tenant)
    def deny_column(self, schema: str, table: str, column: str) -> None:
        _check(_lib.nlsql_policy_deny_column(self._ptr, schema.encode(), table.encode(), column.encode()))
    def require_tenant(self, schema: str, table: str, column: str) -> None:
        _check(_lib.nlsql_policy_require_tenant(self._ptr, schema.encode(), table.encode(), column.encode()))
    def require_tenant_typed(self, schema: str, table: str, column: str, typ: int) -> None:
        _check(_lib.nlsql_policy_require_tenant_typed(self._ptr, schema.encode(), table.encode(), column.encode(), typ))
    def set_limits(self, joins: int, limit: int) -> None:
        _check(_lib.nlsql_policy_set_limits(self._ptr, joins, limit))
    def set_runtime_tenant(self, name: str, typ: int) -> None:
        _check(_lib.nlsql_policy_set_runtime_tenant(self._ptr, name.encode(), typ))
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
    def manifest(self) -> str | None:
        value = _lib.nlsql_result_manifest(self._ptr)
        return value.decode() if value else None
    @property
    def risk(self) -> int: return int(_lib.nlsql_result_risk(self._ptr))
    @property
    def params(self) -> list[ParamView]: return [_lib.nlsql_result_param(self._ptr, i) for i in range(_lib.nlsql_result_param_count(self._ptr))]
    @property
    def diagnostics(self) -> list[DiagnosticView]: return [_lib.nlsql_result_diagnostic(self._ptr, i) for i in range(_lib.nlsql_result_diagnostic_count(self._ptr))]
    @property
    def relevance_score(self) -> float: return float(_lib.nlsql_result_relevance_score(self._ptr))
    def close(self) -> None:
        ptr = getattr(self, "_ptr", None)
        if ptr:
            _lib.nlsql_compile_result_destroy(ptr); self._ptr = None
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def __del__(self): self.close()

def compile_ir(context: Context, schema: Schema, policy: Policy, ir: str, dialect: int = NLSQL_DIALECT_POSTGRES, trace_id: str | None = None) -> Result:
    request = CompileRequest(ir.encode(), schema._ptr, policy._ptr, dialect, trace_id.encode() if trace_id else None)
    ptr = c.c_void_p(); _check(_lib.nlsql_compile_ir(context._ptr, c.byref(request), c.byref(ptr)))
    return Result(ptr)


def compile_cte(context: Context, schema: Schema, policy: Policy, cte_name: str, cte_ir: str, query_ir: str, dialect: int = NLSQL_DIALECT_POSTGRES) -> Result:
    request = CTERequest(cte_name.encode(), cte_ir.encode(), query_ir.encode(), schema._ptr, policy._ptr, dialect)
    ptr = c.c_void_p(); _check(_lib.nlsql_compile_cte(context._ptr, c.byref(request), c.byref(ptr)))
    return Result(ptr)


def compile_set(context: Context, schema: Schema, policy: Policy, left_ir: str, right_ir: str, operation: int, dialect: int = NLSQL_DIALECT_POSTGRES) -> Result:
    request = SetRequest(left_ir.encode(), right_ir.encode(), schema._ptr, policy._ptr, dialect, operation)
    ptr = c.c_void_p(); _check(_lib.nlsql_compile_set(context._ptr, c.byref(request), c.byref(ptr)))
    return Result(ptr)


def compile_question(context: Context, schema: Schema, policy: Policy, question: str, dialect: int = NLSQL_DIALECT_POSTGRES) -> Result:
    request = QuestionRequest(question.encode(), schema._ptr, policy._ptr, dialect)
    ptr = c.c_void_p(); _check(_lib.nlsql_compile_question(context._ptr, c.byref(request), c.byref(ptr)))
    return Result(ptr)
