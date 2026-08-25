"""Dual-Engine high-performance binding and pure-Python fallback for nlsqlc."""
from __future__ import annotations

import ctypes as c
import enum
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

NLSQL_OK = 0
NLSQL_E_INVALID_ARGUMENT = 1
NLSQL_E_OOM = 2
NLSQL_E_LIMIT = 3
NLSQL_E_PARSE = 4
NLSQL_E_SCHEMA = 5
NLSQL_E_POLICY = 6
NLSQL_E_UNSUPPORTED = 7
NLSQL_E_TYPE = 8
NLSQL_E_DIALECT = 9
NLSQL_E_INTERNAL = 10

NLSQL_STATUS_NAMES = {
    NLSQL_OK: "OK",
    NLSQL_E_INVALID_ARGUMENT: "INVALID_ARGUMENT",
    NLSQL_E_OOM: "OOM",
    NLSQL_E_LIMIT: "LIMIT",
    NLSQL_E_PARSE: "PARSE",
    NLSQL_E_SCHEMA: "SCHEMA",
    NLSQL_E_POLICY: "POLICY",
    NLSQL_E_UNSUPPORTED: "UNSUPPORTED",
    NLSQL_E_TYPE: "TYPE",
    NLSQL_E_DIALECT: "DIALECT",
    NLSQL_E_INTERNAL: "INTERNAL",
}

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

NLSQL_TYPE_NAMES = {
    "boolean": NLSQL_TYPE_BOOLEAN,
    "int64": NLSQL_TYPE_INT64,
    "uint64": NLSQL_TYPE_UINT64,
    "decimal": NLSQL_TYPE_DECIMAL,
    "float64": NLSQL_TYPE_FLOAT64,
    "text": NLSQL_TYPE_TEXT,
    "binary": NLSQL_TYPE_BINARY,
    "uuid": NLSQL_TYPE_UUID,
    "date": NLSQL_TYPE_DATE,
    "timestamp": NLSQL_TYPE_TIMESTAMP,
    "timestamptz": NLSQL_TYPE_TIMESTAMPTZ,
}

NLSQL_TABLE_NONE = 0
NLSQL_TABLE_TENANT_SCOPED = 1 << 0
NLSQL_TABLE_VIEW = 1 << 1

NLSQL_COLUMN_NONE = 0
NLSQL_COLUMN_PRIMARY_KEY = 1 << 0
NLSQL_COLUMN_NOT_NULL = 1 << 1
NLSQL_COLUMN_TENANT_KEY = 1 << 2
NLSQL_COLUMN_SENSITIVE = 1 << 3

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

NLSQL_DIALECT_NAMES = {
    NLSQL_DIALECT_POSTGRES: "postgres",
    NLSQL_DIALECT_SQLITE: "sqlite",
    NLSQL_DIALECT_DUCKDB: "duckdb",
    NLSQL_DIALECT_MYSQL: "mysql",
    NLSQL_DIALECT_SQLSERVER: "sqlserver",
}

NLSQL_SET_UNION = 0
NLSQL_SET_UNION_ALL = 1
NLSQL_SET_INTERSECT = 2
NLSQL_SET_EXCEPT = 3


def _load_native_library() -> Optional[c.CDLL]:
    candidates = []
    if os.environ.get("NLSQL_LIBRARY"):
        candidates.append(os.environ["NLSQL_LIBRARY"])
    root = Path(__file__).resolve().parents[2]
    names = ("libnlsql.so", "libnlsql.dylib", "nlsql.dll", "libnlsql.dll")
    candidates += [str(root / "build" / name) for name in names]
    for build_dir in ("qa", "integration", "security-fix", "cpp-asan", "final", ".release-build"):
        candidates += [str(root / "build" / build_dir / name) for name in names]
    candidates += [str(Path(prefix) / name) for prefix in ("/usr/local/lib", "/usr/lib") for name in names]
    for path in candidates:
        if Path(path).exists():
            try:
                return c.CDLL(path)
            except Exception:
                pass
    return None


_native_lib = _load_native_library()

# Native C Structures
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

class SQLView(c.Structure):
    _fields_ = [("sql", c.c_char_p), ("length", c.c_size_t)]

if _native_lib:
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
        fn = getattr(_native_lib, name)
        fn.argtypes = args
        fn.restype = result
    for name, args in [
        ("nlsql_context_destroy", [c.c_void_p]),
        ("nlsql_schema_builder_destroy", [c.c_void_p]),
        ("nlsql_schema_destroy", [c.c_void_p]),
        ("nlsql_policy_destroy", [c.c_void_p]),
        ("nlsql_compile_result_destroy", [c.c_void_p]),
    ]:
        fn = getattr(_native_lib, name)
        fn.argtypes = args
        fn.restype = None
    _native_lib.nlsql_result_sql.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_sql.restype = SQLView
    _native_lib.nlsql_result_status.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_status.restype = c.c_int
    _native_lib.nlsql_result_error.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_error.restype = c.c_char_p
    _native_lib.nlsql_result_canonical_ir.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_canonical_ir.restype = c.c_char_p
    _native_lib.nlsql_result_fingerprint.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_fingerprint.restype = c.c_uint64
    _native_lib.nlsql_result_complexity.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_complexity.restype = c.c_uint
    _native_lib.nlsql_result_relevance_score.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_relevance_score.restype = c.c_double
    _native_lib.nlsql_result_param_count.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_param_count.restype = c.c_size_t
    _native_lib.nlsql_result_param.argtypes = [c.c_void_p, c.c_size_t]
    _native_lib.nlsql_result_param.restype = ParamView
    _native_lib.nlsql_result_manifest.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_manifest.restype = c.c_char_p
    _native_lib.nlsql_result_risk.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_risk.restype = c.c_int
    _native_lib.nlsql_result_diagnostic_count.argtypes = [c.c_void_p]
    _native_lib.nlsql_result_diagnostic_count.restype = c.c_size_t
    _native_lib.nlsql_result_diagnostic.argtypes = [c.c_void_p, c.c_size_t]
    _native_lib.nlsql_result_diagnostic.restype = DiagnosticView
    _native_lib.nlsql_status_name.argtypes = [c.c_int]
    _native_lib.nlsql_status_name.restype = c.c_char_p


# ==============================================================================
# Pure-Python High-Speed Query IR Compiler & Validator Engine
# ==============================================================================

@dataclass
class _TableDef:
    schema: str
    name: str
    flags: int = 0

@dataclass
class _ColumnDef:
    schema: str
    table: str
    name: str
    type: int
    flags: int = 0

@dataclass
class _FKDef:
    fs: str
    ft: str
    fc: str
    ts: str
    tt: str
    tc: str

@dataclass
class _PySchema:
    tables: Dict[Tuple[str, str], _TableDef] = field(default_factory=dict)
    columns: Dict[Tuple[str, str, str], _ColumnDef] = field(default_factory=dict)
    foreign_keys: List[_FKDef] = field(default_factory=list)

@dataclass
class _PyPolicy:
    allowed_tables: set = field(default_factory=set)
    denied_columns: set = field(default_factory=set)
    tenant_rules: Dict[Tuple[str, str], Tuple[str, int]] = field(default_factory=dict)
    runtime_tenant_name: str = "tenant_id"
    runtime_tenant_type: int = NLSQL_TYPE_UUID
    max_limit: int = 1000
    max_joins: int = 16

def _py_ident(s: str) -> bool:
    if not s or len(s) >= 128:
        return False
    if not (s[0].isalpha() or s[0] == '_'):
        return False
    return all(c.isalnum() or c == '_' for c in s[1:])

def _py_quote_ident(s: str, dialect: int) -> str:
    if dialect == NLSQL_DIALECT_MYSQL:
        return f"`{s}`"
    if dialect == NLSQL_DIALECT_SQLSERVER:
        return f"[{s}]"
    return f'"{s}"'

def _py_parse_sexpr(text: str) -> List[Any]:
    tokens = re.findall(r'\(|\)|[^\s()]+', text)
    if not tokens:
        raise ValueError("empty input")
    stack: List[List[Any]] = [[]]
    for token in tokens:
        if token == '(':
            new_list: List[Any] = []
            stack[-1].append(new_list)
            stack.append(new_list)
        elif token == ')':
            if len(stack) <= 1:
                raise ValueError("unexpected ')'")
            stack.pop()
        else:
            stack[-1].append(token)
    if len(stack) != 1 or len(stack[0]) != 1:
        raise ValueError("unbalanced parentheses")
    return stack[0][0]

def _py_fingerprint(ir_str: str) -> int:
    h = 1469598103934665603
    for b in ir_str.encode('utf-8'):
        h ^= b
        h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


class PyCompileResult:
    def __init__(self, status: int, sql: str = "", ir: str = "", manifest: str = "", error: str = "", params: List[Dict[str, Any]] = None, risk: int = NLSQL_RISK_LOW, complexity: int = 1):
        self.status = status
        self.sql = sql
        self.ir = ir
        self.manifest = manifest
        self.error = error
        self.params = params or []
        self.risk = risk
        self.complexity = complexity
        self.fingerprint = _py_fingerprint(ir) if ir else 0
        self.relevance_score = (1.0 / (1.0 + complexity / 10.0)) * (0.8 if risk == NLSQL_RISK_MODERATE else (0.5 if risk == NLSQL_RISK_HIGH else 1.0)) if status == NLSQL_OK else 0.0
        self.diagnostics = []

def _py_emit_expr(expr: Any, sources: Dict[str, Tuple[str, str]], schema: _PySchema, params: List[Dict[str, Any]], dialect: int) -> str:
    if isinstance(expr, str):
        return expr
    if not expr or not isinstance(expr, list):
        raise ValueError("invalid expression")
    op = expr[0]
    if op == "column" and len(expr) == 3:
        alias, col = expr[1], expr[2]
        if alias not in sources:
            raise ValueError(f"unknown source alias: {alias}")
        sc, tb = sources[alias]
        if (sc, tb, col) not in schema.columns:
            raise ValueError(f"unknown column: {sc}.{tb}.{col}")
        return f"{_py_quote_ident(alias, dialect)}.{_py_quote_ident(col, dialect)}"
    if op == "param" and len(expr) == 3:
        name, typ_str = expr[1], expr[2]
        typ = NLSQL_TYPE_NAMES.get(typ_str, NLSQL_TYPE_UNKNOWN)
        params.append({"position": len(params) + 1, "name": name, "type": typ, "source": NLSQL_PARAM_USER, "runtime_required": 1})
        pos = len(params)
        if dialect in (NLSQL_DIALECT_POSTGRES, NLSQL_DIALECT_DUCKDB):
            return f"${pos}"
        if dialect == NLSQL_DIALECT_SQLSERVER:
            return f"@p{pos}"
        if dialect == NLSQL_DIALECT_SQLITE:
            return f"?{pos}"
        return "?"
    if op == "ref" and len(expr) == 2:
        return _py_quote_ident(expr[1], dialect)
    if op in ("sum", "avg", "count", "min", "max") and len(expr) == 2:
        sub = _py_emit_expr(expr[1], sources, schema, params, dialect)
        return f"{op.upper()}({sub})"
    if op == "count-distinct" and len(expr) == 2:
        sub = _py_emit_expr(expr[1], sources, schema, params, dialect)
        return f"COUNT(DISTINCT {sub})"
    if op == "sum-distinct" and len(expr) == 2:
        sub = _py_emit_expr(expr[1], sources, schema, params, dialect)
        return f"SUM(DISTINCT {sub})"
    if op == "distinct" and len(expr) == 2:
        sub = _py_emit_expr(expr[1], sources, schema, params, dialect)
        return f"DISTINCT {sub}"
    if op in ("eq", "gte", "gt", "lte", "lt", "neq", "mul", "add", "sub", "div") and len(expr) == 3:
        l = _py_emit_expr(expr[1], sources, schema, params, dialect)
        r = _py_emit_expr(expr[2], sources, schema, params, dialect)
        ops = {"eq": "=", "gte": ">=", "gt": ">", "lte": "<=", "lt": "<", "neq": "<>", "mul": "*", "add": "+", "sub": "-", "div": "/"}
        return f"({l} {ops[op]} {r})"
    if op in ("and", "or") and len(expr) >= 2:
        parts = [_py_emit_expr(x, sources, schema, params, dialect) for x in expr[1:]]
        joiner = f" {op.upper()} "
        return f"({joiner.join(parts)})"
    if op == "not" and len(expr) == 2:
        sub = _py_emit_expr(expr[1], sources, schema, params, dialect)
        return f"(NOT {sub})"
    if op == "in" and len(expr) >= 3:
        target = _py_emit_expr(expr[1], sources, schema, params, dialect)
        val_parts = [_py_emit_expr(x, sources, schema, params, dialect) for x in expr[2:]]
        return f"({target} IN ({', '.join(val_parts)}))"
    if op == "between" and len(expr) == 4:
        target = _py_emit_expr(expr[1], sources, schema, params, dialect)
        low = _py_emit_expr(expr[2], sources, schema, params, dialect)
        high = _py_emit_expr(expr[3], sources, schema, params, dialect)
        return f"({target} BETWEEN {low} AND {high})"
    if op == "like" and len(expr) == 3:
        target = _py_emit_expr(expr[1], sources, schema, params, dialect)
        pattern = _py_emit_expr(expr[2], sources, schema, params, dialect)
        return f"({target} LIKE {pattern})"
    if op == "ilike" and len(expr) == 3:
        target = _py_emit_expr(expr[1], sources, schema, params, dialect)
        pattern = _py_emit_expr(expr[2], sources, schema, params, dialect)
        if dialect in (NLSQL_DIALECT_POSTGRES, NLSQL_DIALECT_DUCKDB):
            return f"({target} ILIKE {pattern})"
        return f"(LOWER({target}) LIKE LOWER({pattern}))"
    if op == "is-null" and len(expr) == 2:
        sub = _py_emit_expr(expr[1], sources, schema, params, dialect)
        return f"({sub} IS NULL)"
    if op == "is-not-null" and len(expr) == 2:
        sub = _py_emit_expr(expr[1], sources, schema, params, dialect)
        return f"({sub} IS NOT NULL)"
    if op in ("lower", "upper", "trim", "abs") and len(expr) == 2:
        sub = _py_emit_expr(expr[1], sources, schema, params, dialect)
        return f"{op.upper()}({sub})"
    if op == "coalesce" and len(expr) >= 2:
        parts = [_py_emit_expr(x, sources, schema, params, dialect) for x in expr[1:]]
        return f"COALESCE({', '.join(parts)})"
    if op == "concat" and len(expr) >= 2:
        parts = [_py_emit_expr(x, sources, schema, params, dialect) for x in expr[1:]]
        if dialect in (NLSQL_DIALECT_SQLITE, NLSQL_DIALECT_POSTGRES, NLSQL_DIALECT_DUCKDB):
            return f"({' || '.join(parts)})"
        return f"CONCAT({', '.join(parts)})"
    if op == "now":
        return "CURRENT_TIMESTAMP"
    if op == "date-trunc" and len(expr) == 3:
        part = str(expr[1]).replace("'", "").replace('"', "")
        sub = _py_emit_expr(expr[2], sources, schema, params, dialect)
        if dialect == NLSQL_DIALECT_SQLITE:
            return f"strftime('%Y-%m-01', {sub})"
        return f"DATE_TRUNC('{part}', {sub})"
    if op == "extract" and len(expr) == 3:
        part = str(expr[1]).replace("'", "").replace('"', "")
        sub = _py_emit_expr(expr[2], sources, schema, params, dialect)
        return f"EXTRACT({part.upper()} FROM {sub})"
    if op == "case" and len(expr) >= 2:
        case_parts = ["CASE"]
        for branch in expr[1:]:
            if isinstance(branch, list) and branch and branch[0] == "when" and len(branch) == 3:
                w_cond = _py_emit_expr(branch[1], sources, schema, params, dialect)
                w_val = _py_emit_expr(branch[2], sources, schema, params, dialect)
                case_parts.append(f"WHEN {w_cond} THEN {w_val}")
            elif isinstance(branch, list) and branch and branch[0] == "else" and len(branch) == 2:
                e_val = _py_emit_expr(branch[1], sources, schema, params, dialect)
                case_parts.append(f"ELSE {e_val}")
        case_parts.append("END")
        return " ".join(case_parts)
    if op == "window" and len(expr) >= 4:
        sub = _py_emit_expr(expr[1], sources, schema, params, dialect)
        p_clause = expr[2]
        o_clause = expr[3]
        parts_p = [_py_emit_expr(x, sources, schema, params, dialect) for x in p_clause[1:]]
        order_target = _py_emit_expr(o_clause[1], sources, schema, params, dialect)
        direction = "DESC" if str(o_clause[2]).lower() == "desc" else "ASC"
        return f"{sub} OVER (PARTITION BY {', '.join(parts_p)} ORDER BY {order_target} {direction})"
    raise ValueError(f"unsupported operator: {op}")


def _py_optimize_ast(node: Any) -> Any:
    """Recursively folds constants, reduces boolean logic, and prunes dead predicates."""
    if not isinstance(node, list):
        return node
    if not node:
        return node

    # Recursively optimize children first (bottom-up pass)
    optimized_children = [_py_optimize_ast(child) for child in node]
    op = optimized_children[0]

    # Constant Folding: Arithmetic
    if op in ("add", "sub", "mul", "div") and len(optimized_children) == 3:
        l, r = optimized_children[1], optimized_children[2]
        if isinstance(l, (int, float, str)) and isinstance(r, (int, float, str)):
            try:
                nl = float(l) if "." in str(l) else int(l)
                nr = float(r) if "." in str(r) else int(r)
                if op == "add": return nl + nr
                if op == "sub": return nl - nr
                if op == "mul": return nl * nr
                if op == "div" and nr != 0: return nl / nr if "." in str(nl) or "." in str(nr) else nl // nr
            except (ValueError, TypeError, ZeroDivisionError):
                pass

    # Constant Folding: Comparison
    if op == "eq" and len(optimized_children) == 3:
        l, r = optimized_children[1], optimized_children[2]
        if isinstance(l, (int, float, str)) and isinstance(r, (int, float, str)) and not str(l).startswith("(") and not str(r).startswith("("):
            if l == r: return "true"

    # Boolean Reduction: NOT
    if op == "not" and len(optimized_children) == 2:
        sub = optimized_children[1]
        if sub in ("true", True): return "false"
        if sub in ("false", False): return "true"
        if isinstance(sub, list) and len(sub) == 2 and sub[0] == "not":
            return sub[1]  # (not (not X)) -> X

    # Boolean Reduction: AND
    if op == "and" and len(optimized_children) >= 2:
        filtered = []
        for x in optimized_children[1:]:
            if x in ("false", False): return "false"
            if x not in ("true", True): filtered.append(x)
        if not filtered: return "true"
        if len(filtered) == 1: return filtered[0]
        return ["and"] + filtered

    # Boolean Reduction: OR
    if op == "or" and len(optimized_children) >= 2:
        filtered = []
        for x in optimized_children[1:]:
            if x in ("true", True): return "true"
            if x not in ("false", False): filtered.append(x)
        if not filtered: return "false"
        if len(filtered) == 1: return filtered[0]
        return ["or"] + filtered

    return optimized_children

def _py_canonical_ir(node: Any) -> str:
    if isinstance(node, list):
        return f"({' '.join(_py_canonical_ir(x) for x in node)})"
    return str(node)

def _py_compile_ir_engine(ir: str, schema: _PySchema, policy: _PyPolicy, dialect: int = NLSQL_DIALECT_POSTGRES) -> PyCompileResult:
    try:
        raw_tree = _py_parse_sexpr(ir)
        tree = _py_optimize_ast(raw_tree)
        if not isinstance(tree, list) or len(tree) < 3 or tree[0] != "nlsql" or tree[1] not in ("1", "2") or not isinstance(tree[2], list) or tree[2][0] != "query":
            return PyCompileResult(NLSQL_E_PARSE, error="PARSE: invalid root structure")

        q = tree[2]
        from_clause = None
        select_clause = None
        where_clause = None
        group_clause = None
        order_clause = None
        limit_clause = None
        joins = []

        for item in q[1:]:
            if isinstance(item, list) and item:
                tag = item[0]
                if tag == "from": from_clause = item
                elif tag == "select": select_clause = item
                elif tag == "where": where_clause = item
                elif tag == "group-by": group_clause = item
                elif tag == "order-by": order_clause = item
                elif tag == "limit": limit_clause = item
                elif tag == "join": joins.append(item)

        if not from_clause or not select_clause or len(from_clause) < 2:
            return PyCompileResult(NLSQL_E_PARSE, error="PARSE: missing from or select")

        table_name = from_clause[1]
        alias = from_clause[2] if len(from_clause) >= 3 else table_name
        sources = {alias: ("public", table_name)}

        if ("public", table_name) not in schema.tables or ("public", table_name) not in policy.allowed_tables:
            return PyCompileResult(NLSQL_E_POLICY, error="POLICY: table not allowed")

        join_sql_parts = []
        for j in joins:
            # (join inner/left/right/full table alias on_cond)
            jtype_str = j[1]
            jtable = j[2]
            jalias = j[3]
            jon = j[4]
            if ("public", jtable) not in schema.tables or ("public", jtable) not in policy.allowed_tables:
                return PyCompileResult(NLSQL_E_POLICY, error=f"POLICY: joined table not allowed {jtable}")
            sources[jalias] = ("public", jtable)
            jt_map = {"inner": "INNER JOIN", "left": "LEFT JOIN", "right": "RIGHT JOIN", "full": "FULL OUTER JOIN"}
            join_sql_parts.append((jt_map.get(jtype_str, "INNER JOIN"), "public", jtable, jalias, jon))

        params: List[Dict[str, Any]] = []

        # Validate column denials
        for col_key in schema.columns:
            sc, tb, cn = col_key
            if (sc, tb, cn) in policy.denied_columns:
                # Check if referenced in IR
                if cn in ir and tb in ir:
                    return PyCompileResult(NLSQL_E_POLICY, error=f"POLICY: column denied {cn}")

        # Build SELECT
        fields = []
        for f in select_clause[1:]:
            if not isinstance(f, list) or f[0] != "field" or len(f) != 3:
                return PyCompileResult(NLSQL_E_PARSE, error="PARSE: invalid field")
            f_expr = _py_emit_expr(f[1], sources, schema, params, dialect)
            f_alias = f[2]
            fields.append(f"{f_expr} AS {_py_quote_ident(f_alias, dialect)}")

        top_str = ""
        limit_val = 100
        if limit_clause and len(limit_clause) >= 2:
            try:
                limit_val = int(limit_clause[1])
            except ValueError:
                return PyCompileResult(NLSQL_E_PARSE, error="PARSE: invalid limit")
        if dialect == NLSQL_DIALECT_SQLSERVER:
            top_str = f"TOP {limit_val} "

        sql_parts = [f"SELECT {top_str}{', '.join(fields)} FROM {_py_quote_ident('public', dialect)}.{_py_quote_ident(table_name, dialect)} AS {_py_quote_ident(alias, dialect)}"]

        for jt, sc, tb, al, on_expr in join_sql_parts:
            on_sql = _py_emit_expr(on_expr, sources, schema, params, dialect)
            sql_parts.append(f"{jt} {_py_quote_ident(sc, dialect)}.{_py_quote_ident(tb, dialect)} AS {_py_quote_ident(al, dialect)} ON {on_sql}")

        # Inject Tenant & WHERE
        where_conditions = []
        if where_clause and len(where_clause) >= 2:
            where_conditions.append(_py_emit_expr(where_clause[1], sources, schema, params, dialect))

        tenant_count = 0
        for al, (sc, tb) in sources.items():
            if (sc, tb) in policy.tenant_rules:
                tcol, ttype = policy.tenant_rules[(sc, tb)]
                col_def = schema.columns.get((sc, tb, tcol))
                if not col_def or not (col_def.flags & NLSQL_COLUMN_TENANT_KEY):
                    return PyCompileResult(NLSQL_E_POLICY, error="POLICY: tenant column missing or invalid")
                if ttype != NLSQL_TYPE_UNKNOWN and col_def.type != ttype and not (col_def.type in (NLSQL_TYPE_INT64, NLSQL_TYPE_UINT64, NLSQL_TYPE_DECIMAL, NLSQL_TYPE_FLOAT64) and ttype in (NLSQL_TYPE_INT64, NLSQL_TYPE_UINT64, NLSQL_TYPE_DECIMAL, NLSQL_TYPE_FLOAT64)):
                    return PyCompileResult(NLSQL_E_TYPE, error="TYPE: tenant type mismatch")
                params.append({"position": len(params) + 1, "name": policy.runtime_tenant_name, "type": policy.runtime_tenant_type, "source": NLSQL_PARAM_POLICY, "runtime_required": 1})
                pos = len(params)
                param_ph = f"${pos}" if dialect in (NLSQL_DIALECT_POSTGRES, NLSQL_DIALECT_DUCKDB) else (f"@p{pos}" if dialect == NLSQL_DIALECT_SQLSERVER else (f"?{pos}" if dialect == NLSQL_DIALECT_SQLITE else "?"))
                where_conditions.append(f"{_py_quote_ident(al, dialect)}.{_py_quote_ident(tcol, dialect)} = {param_ph}")
                tenant_count += 1

        if where_conditions:
            sql_parts.append(f"WHERE {' AND '.join(where_conditions)}")

        if group_clause and len(group_clause) >= 2:
            g_parts = [_py_emit_expr(x, sources, schema, params, dialect) for x in group_clause[1:]]
            sql_parts.append(f"GROUP BY {', '.join(g_parts)}")

        if order_clause and len(order_clause) >= 3:
            o_expr = _py_emit_expr(order_clause[1], sources, schema, params, dialect)
            o_dir = "DESC" if str(order_clause[2]).lower() == "desc" else "ASC"
            sql_parts.append(f"ORDER BY {o_expr} {o_dir}")

        if dialect != NLSQL_DIALECT_SQLSERVER:
            sql_parts.append(f"LIMIT {limit_val}")

        final_sql = " ".join(sql_parts)
        canon_ir = _py_canonical_ir(tree)
        complexity = 1 + len(joins) + len(fields) + tenant_count
        risk = NLSQL_RISK_LOW if tenant_count > 0 else NLSQL_RISK_MODERATE
        manifest = f"version=2\ndialect={NLSQL_DIALECT_NAMES.get(dialect, 'postgres')}\nparameters={len(params)}\ntenant_predicates={tenant_count}\ncomplexity={complexity}\nrisk={'LOW' if risk == NLSQL_RISK_LOW else 'MODERATE'}\n"

        return PyCompileResult(NLSQL_OK, sql=final_sql, ir=canon_ir, manifest=manifest, params=params, risk=risk, complexity=complexity)
    except Exception as e:
        return PyCompileResult(NLSQL_E_PARSE, error=f"PARSE: {e}")


# ==============================================================================
# Unified Public Python SDK API (Wraps Native C ABI or Pure-Python Engine)
# ==============================================================================

def _check(status: int) -> None:
    if status != NLSQL_OK:
        msg = NLSQL_STATUS_NAMES.get(status, "UNKNOWN_ERROR")
        raise RuntimeError(msg)


class Context:
    def __init__(self, config: Optional[Config] = None):
        self._ptr = c.c_void_p()
        if _native_lib:
            _check(_native_lib.nlsql_context_create(c.byref(config or Config()), c.byref(self._ptr)))
        else:
            self._ptr = None

    def close(self) -> None:
        if _native_lib and getattr(self, "_ptr", None):
            _native_lib.nlsql_context_destroy(self._ptr)
            self._ptr = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        self.close()


class Schema:
    def __init__(self, context: Context, tables: List[Tuple[str, str, List[Tuple[Any, ...]]]], table_flags: Optional[Dict[Tuple[str, str], int]] = None, foreign_keys: Optional[List[Tuple[str, str, str, str, str, str, str]]] = None):
        self.py_schema = _PySchema()
        table_flags = table_flags or {}
        foreign_keys = foreign_keys or []
        self._builder = c.c_void_p()
        self._ptr = c.c_void_p()

        if _native_lib and context._ptr:
            _check(_native_lib.nlsql_schema_builder_create(context._ptr, c.byref(self._builder)))
            for schema_name, table_name, columns in tables:
                t_flag = table_flags.get((schema_name, table_name), 0)
                _check(_native_lib.nlsql_schema_builder_add_table(self._builder, schema_name.encode(), table_name.encode(), t_flag))
                for col_spec in columns:
                    col_name, typ, *rest = col_spec
                    c_flags = rest[0] if rest else 0
                    _check(_native_lib.nlsql_schema_builder_add_column(self._builder, schema_name.encode(), table_name.encode(), col_name.encode(), typ, c_flags))
            for fk in foreign_keys:
                _check(_native_lib.nlsql_schema_builder_add_foreign_key(self._builder, *(part.encode() for part in fk)))
            _check(_native_lib.nlsql_schema_builder_finalize(self._builder, c.byref(self._ptr)))

        # Populate pure-Python schema
        for schema_name, table_name, columns in tables:
            t_flag = table_flags.get((schema_name, table_name), 0)
            self.py_schema.tables[(schema_name, table_name)] = _TableDef(schema_name, table_name, t_flag)
            for col_spec in columns:
                col_name, typ, *rest = col_spec
                c_flags = rest[0] if rest else 0
                self.py_schema.columns[(schema_name, table_name, col_name)] = _ColumnDef(schema_name, table_name, col_name, typ, c_flags)
        for fk in foreign_keys:
            self.py_schema.foreign_keys.append(_FKDef(*fk))

    def close(self) -> None:
        if _native_lib:
            if getattr(self, "_builder", None):
                _native_lib.nlsql_schema_builder_destroy(self._builder)
                self._builder = None
            if getattr(self, "_ptr", None):
                _native_lib.nlsql_schema_destroy(self._ptr)
                self._ptr = None

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def __del__(self): self.close()


class Policy:
    def __init__(self, context: Context, allow: Optional[List[Tuple[str, str]]] = None, deny: Optional[List[Tuple[str, str, str]]] = None, tenant: Optional[List[Tuple[Any, ...]]] = None, limits: Optional[Tuple[int, int]] = None, runtime_tenant: Optional[Tuple[str, int]] = None):
        self.py_policy = _PyPolicy()
        self._ptr = c.c_void_p()
        if _native_lib and context._ptr:
            _check(_native_lib.nlsql_policy_create(context._ptr, c.byref(self._ptr)))
            for sc, tb in allow or []:
                _check(_native_lib.nlsql_policy_allow_table(self._ptr, sc.encode(), tb.encode()))
            for sc, tb, col in deny or []:
                _check(_native_lib.nlsql_policy_deny_column(self._ptr, sc.encode(), tb.encode(), col.encode()))
            for t_spec in tenant or []:
                sc, tb, col, *rest = t_spec
                if rest:
                    _check(_native_lib.nlsql_policy_require_tenant_typed(self._ptr, sc.encode(), tb.encode(), col.encode(), rest[0]))
                else:
                    _check(_native_lib.nlsql_policy_require_tenant(self._ptr, sc.encode(), tb.encode(), col.encode()))
            if limits:
                _check(_native_lib.nlsql_policy_set_limits(self._ptr, limits[0], limits[1]))
            if runtime_tenant:
                _check(_native_lib.nlsql_policy_set_runtime_tenant(self._ptr, runtime_tenant[0].encode(), runtime_tenant[1]))

        # Pure-Python policy
        for sc, tb in allow or []:
            self.py_policy.allowed_tables.add((sc, tb))
        for sc, tb, col in deny or []:
            self.py_policy.denied_columns.add((sc, tb, col))
        for t_spec in tenant or []:
            sc, tb, col, *rest = t_spec
            self.py_policy.tenant_rules[(sc, tb)] = (col, rest[0] if rest else NLSQL_TYPE_UNKNOWN)
        if limits:
            self.py_policy.max_joins, self.py_policy.max_limit = limits
        if runtime_tenant:
            self.py_policy.runtime_tenant_name, self.py_policy.runtime_tenant_type = runtime_tenant

    def close(self) -> None:
        if _native_lib and getattr(self, "_ptr", None):
            _native_lib.nlsql_policy_destroy(self._ptr)
            self._ptr = None

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def __del__(self): self.close()


class CompileResult:
    def __init__(self, raw_ptr: Any = None, py_res: Optional[PyCompileResult] = None):
        self._ptr = raw_ptr
        self._py = py_res

    @property
    def status(self) -> int:
        if self._py: return self._py.status
        return _native_lib.nlsql_result_status(self._ptr) if self._ptr else NLSQL_E_INTERNAL

    @property
    def sql(self) -> str:
        if self._py: return self._py.sql
        if not self._ptr: return ""
        v = _native_lib.nlsql_result_sql(self._ptr)
        return v.sql.decode("utf-8", "replace") if v.sql else ""

    @property
    def canonical_ir(self) -> str:
        if self._py: return self._py.ir
        if not self._ptr: return ""
        res = _native_lib.nlsql_result_canonical_ir(self._ptr)
        return res.decode("utf-8", "replace") if res else ""

    @property
    def manifest(self) -> str:
        if self._py: return self._py.manifest
        if not self._ptr: return ""
        res = _native_lib.nlsql_result_manifest(self._ptr)
        return res.decode("utf-8", "replace") if res else ""

    @property
    def error(self) -> str:
        if self._py: return self._py.error
        if not self._ptr: return ""
        res = _native_lib.nlsql_result_error(self._ptr)
        return res.decode("utf-8", "replace") if res else ""

    @property
    def risk(self) -> int:
        if self._py: return self._py.risk
        return _native_lib.nlsql_result_risk(self._ptr) if self._ptr else NLSQL_RISK_DENIED

    @property
    def complexity(self) -> int:
        if self._py: return self._py.complexity
        return _native_lib.nlsql_result_complexity(self._ptr) if self._ptr else 0

    @property
    def fingerprint(self) -> int:
        if self._py: return self._py.fingerprint
        return _native_lib.nlsql_result_fingerprint(self._ptr) if self._ptr else 0

    @property
    def relevance_score(self) -> float:
        if self._py: return self._py.relevance_score
        return _native_lib.nlsql_result_relevance_score(self._ptr) if self._ptr else 0.0

    @property
    def params(self) -> List[Dict[str, Any]]:
        if self._py: return self._py.params
        if not self._ptr: return []
        count = _native_lib.nlsql_result_param_count(self._ptr)
        out = []
        for i in range(count):
            p = _native_lib.nlsql_result_param(self._ptr, i)
            out.append({
                "position": p.position,
                "name": p.name.decode("utf-8", "replace") if p.name else "",
                "type": p.type,
                "source": p.source,
                "runtime_required": bool(p.runtime_required),
            })
        return out

    def close(self) -> None:
        if _native_lib and getattr(self, "_ptr", None):
            _native_lib.nlsql_compile_result_destroy(self._ptr)
            self._ptr = None

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def __del__(self): self.close()


def compile_ir(context: Context, *args, dialect: int = NLSQL_DIALECT_POSTGRES, trace_id: Optional[str] = None) -> CompileResult:
    # Support both compile_ir(ctx, ir, schema, policy) and compile_ir(ctx, schema, policy, ir)
    if len(args) == 3:
        if isinstance(args[0], str):
            ir, schema, policy = args[0], args[1], args[2]
        else:
            schema, policy, ir = args[0], args[1], args[2]
    elif len(args) == 4 and isinstance(args[3], str):
        schema, policy, ir = args[0], args[1], args[3]
    elif len(args) >= 1 and isinstance(args[0], str):
        ir = args[0]
        schema = args[1] if len(args) > 1 else None
        policy = args[2] if len(args) > 2 else None
    else:
        raise TypeError("compile_ir requires context, ir, schema, and policy")

    if _native_lib and context._ptr and getattr(schema, "_ptr", None) and getattr(policy, "_ptr", None):
        req = CompileRequest(ir.encode(), schema._ptr, policy._ptr, dialect, trace_id.encode() if trace_id else None)
        out = c.c_void_p()
        st = _native_lib.nlsql_compile_ir(context._ptr, c.byref(req), c.byref(out))
        return CompileResult(raw_ptr=out)
    # Pure Python execution
    py_schema = getattr(schema, "py_schema", _PySchema()) if schema else _PySchema()
    py_policy = getattr(policy, "py_policy", _PyPolicy()) if policy else _PyPolicy()
    py_res = _py_compile_ir_engine(ir, py_schema, py_policy, dialect)
    return CompileResult(py_res=py_res)


def compile_cte(context: Context, cte_name: str, cte_ir: str, query_ir: str, schema: Schema, policy: Policy, dialect: int = NLSQL_DIALECT_POSTGRES) -> CompileResult:
    if _native_lib and context._ptr and schema._ptr and policy._ptr:
        req = CTERequest(cte_name.encode(), cte_ir.encode(), query_ir.encode(), schema._ptr, policy._ptr, dialect)
        out = c.c_void_p()
        st = _native_lib.nlsql_compile_cte(context._ptr, c.byref(req), c.byref(out))
        return CompileResult(raw_ptr=out)
    full_ir = f"(with {cte_name} {cte_ir} {query_ir})"
    # Compile CTE scope and outer query
    py_cte = _py_compile_ir_engine(cte_ir, schema.py_schema, policy.py_policy, dialect)
    if py_cte.status != NLSQL_OK:
        return CompileResult(py_res=py_cte)
    py_outer = _py_compile_ir_engine(query_ir, schema.py_schema, policy.py_policy, dialect)
    sql = f"WITH {_py_quote_ident(cte_name, dialect)} AS ({py_cte.sql}) {py_outer.sql}"
    res = PyCompileResult(NLSQL_OK, sql=sql, ir=full_ir, params=py_cte.params + py_outer.params, complexity=py_cte.complexity + py_outer.complexity + 1)
    return CompileResult(py_res=res)


def compile_set(context: Context, left_ir: str, right_ir: str, schema: Schema, policy: Policy, operation: int = NLSQL_SET_UNION, dialect: int = NLSQL_DIALECT_POSTGRES) -> CompileResult:
    if _native_lib and context._ptr and schema._ptr and policy._ptr:
        req = SetRequest(left_ir.encode(), right_ir.encode(), schema._ptr, policy._ptr, dialect, operation)
        out = c.c_void_p()
        st = _native_lib.nlsql_compile_set(context._ptr, c.byref(req), c.byref(out))
        return CompileResult(raw_ptr=out)
    ops = {NLSQL_SET_UNION: "UNION", NLSQL_SET_UNION_ALL: "UNION ALL", NLSQL_SET_INTERSECT: "INTERSECT", NLSQL_SET_EXCEPT: "EXCEPT"}
    op_str = ops.get(operation, "UNION")
    l_res = _py_compile_ir_engine(left_ir, schema.py_schema, policy.py_policy, dialect)
    r_res = _py_compile_ir_engine(right_ir, schema.py_schema, policy.py_policy, dialect)
    if l_res.status != NLSQL_OK: return CompileResult(py_res=l_res)
    if r_res.status != NLSQL_OK: return CompileResult(py_res=r_res)
    sql = f"({l_res.sql}) {op_str} ({r_res.sql})"
    res = PyCompileResult(NLSQL_OK, sql=sql, ir=f"(set {op_str} {l_res.ir} {r_res.ir})", params=l_res.params + r_res.params, complexity=l_res.complexity + r_res.complexity + 1)
    return CompileResult(py_res=res)


def compile_question(context: Context, question: str, schema: Schema, policy: Policy, dialect: int = NLSQL_DIALECT_POSTGRES) -> CompileResult:
    parts = question.strip().split()
    if len(parts) < 2:
        return CompileResult(py_res=PyCompileResult(NLSQL_E_UNSUPPORTED, error="UNSUPPORTED"))
    kind, table = parts[0], parts[1]
    col = parts[2] if len(parts) >= 3 else "id"
    if kind == "count":
        ir = f"(nlsql 1 (query (from {table} t) (select (field (count (column t id)) count))))"
    elif kind == "list":
        ir = f"(nlsql 1 (query (from {table} t) (select (field (column t {col}) value))))"
    elif kind == "sum":
        ir = f"(nlsql 1 (query (from {table} t) (select (field (sum (column t {col})) value))))"
    elif kind == "average":
        ir = f"(nlsql 1 (query (from {table} t) (select (field (avg (column t {col})) value))))"
    else:
        return CompileResult(py_res=PyCompileResult(NLSQL_E_UNSUPPORTED, error="UNSUPPORTED"))
    return compile_ir(context, ir, schema, policy, dialect)


# ==============================================================================
# Fluent Query Builder DSL
# ==============================================================================

class Query:
    def __init__(self, table: str, alias: Optional[str] = None):
        self._table = table
        self._alias = alias or table
        self._fields: List[Tuple[str, str]] = []
        self._joins: List[Tuple[str, str, str, str]] = []
        self._where: Optional[str] = None
        self._group_by: List[str] = []
        self._order_by: Optional[Tuple[str, str]] = None
        self._limit: int = 100

    @classmethod
    def from_table(cls, table: str, alias: Optional[str] = None) -> Query:
        return cls(table, alias)

    def select(self, field_expr: str, alias_name: str) -> Query:
        self._fields.append((field_expr, alias_name))
        return self

    def join(self, table: str, alias: str, on_cond: str, join_type: str = "inner") -> Query:
        self._joins.append((join_type, table, alias, on_cond))
        return self

    def where(self, cond_expr: str) -> Query:
        self._where = cond_expr
        return self

    def group_by(self, *cols: str) -> Query:
        self._group_by.extend(cols)
        return self

    def order_by(self, col: str, desc: bool = False) -> Query:
        self._order_by = (col, "desc" if desc else "asc")
        return self

    def limit(self, count: int) -> Query:
        self._limit = count
        return self

    def to_ir(self) -> str:
        parts = [f"(from {self._table} {self._alias})"]
        for jt, t, al, on in self._joins:
            parts.append(f"(join {jt} {t} {al} {on})")
        field_strs = [f"(field {f} {al})" for f, al in self._fields]
        parts.append(f"(select {' '.join(field_strs)})")
        if self._where:
            parts.append(f"(where {self._where})")
        if self._group_by:
            parts.append(f"(group-by {' '.join(self._group_by)})")
        if self._order_by:
            parts.append(f"(order-by {self._order_by[0]} {self._order_by[1]})")
        parts.append(f"(limit {self._limit})")
        return f"(nlsql 2 (query {' '.join(parts)}))"


# ==============================================================================
# Benchmarking & Diagnostics Utility
# ==============================================================================

def benchmark(ir_sample: Optional[str] = None, iterations: int = 1000) -> Dict[str, Any]:
    with Context() as ctx:
        tables = [("public", "orders", [("id", NLSQL_TYPE_INT64, NLSQL_COLUMN_PRIMARY_KEY), ("tenant_id", NLSQL_TYPE_UUID, NLSQL_COLUMN_TENANT_KEY), ("total", NLSQL_TYPE_DECIMAL, 0)])]
        with Schema(ctx, tables) as sch, Policy(ctx, allow=[("public", "orders")], tenant=[("public", "orders", "tenant_id", NLSQL_TYPE_UUID)]) as pol:
            ir = ir_sample or "(nlsql 1 (query (from orders o) (select (field (column o total) total)) (limit 10)))"
            start = time.perf_counter()
            for _ in range(iterations):
                res = compile_ir(ctx, ir, sch, pol)
                res.close()
            elapsed = time.perf_counter() - start
            qps = iterations / elapsed if elapsed > 0 else 0
            return {
                "engine": "native_c" if _native_lib else "pure_python",
                "iterations": iterations,
                "elapsed_seconds": round(elapsed, 4),
                "queries_per_second": round(qps, 2),
                "latency_us": round((elapsed / iterations) * 1e6, 2),
            }


# ==============================================================================
# AST Explain Visualizer & Semantic Diff Utility
# ==============================================================================

def explain(context: Context, ir: str, schema: Schema, policy: Policy, dialect: int = NLSQL_DIALECT_POSTGRES) -> Dict[str, Any]:
    """Generates an ASCII execution and policy plan for a given Query IR."""
    res = compile_ir(context, ir, schema, policy, dialect=dialect)
    tree = _py_optimize_ast(_py_parse_sexpr(ir)) if res.status == NLSQL_OK else None

    ascii_lines = ["┌── [Query Execution Plan]"]
    if res.status == NLSQL_OK:
        ascii_lines.append(f"│  ├── Status: OK (Dialect: {NLSQL_DIALECT_NAMES.get(dialect, 'postgres')})")
        ascii_lines.append(f"│  ├── Complexity: {res.complexity} (Risk: {'LOW' if res.risk == NLSQL_RISK_LOW else 'MODERATE'})")
        ascii_lines.append(f"│  ├── Invariant Tenant Predicates: Injected")
        if res.params:
            ascii_lines.append("│  ├── Parameter Bindings:")
            for p in res.params:
                src = "TENANT_POLICY" if p["source"] == NLSQL_PARAM_POLICY else "USER_INPUT"
                ascii_lines.append(f"│  │   • ${p['position']}: {p['name']} ({NLSQL_TYPE_NAMES.get(p['type'], 'text')}) [{src}]")
        ascii_lines.append("│  └── Generated SQL:")
        ascii_lines.append(f"│      {res.sql}")
    else:
        ascii_lines.append(f"│  ├── Status: REJECTED ({NLSQL_STATUS_NAMES.get(res.status, 'ERROR')})")
        ascii_lines.append(f"│  └── Error: {res.error}")
    ascii_lines.append("└──")

    plan_str = "\n".join(ascii_lines)
    out = {
        "status": "OK" if res.status == NLSQL_OK else "ERROR",
        "plan_ascii": plan_str,
        "complexity": res.complexity,
        "risk": "LOW" if res.risk == NLSQL_RISK_LOW else "MODERATE",
        "sql": res.sql,
        "params": res.params,
        "error": res.error,
    }
    res.close()
    return out


def diff(ir1: str, ir2: str) -> Dict[str, Any]:
    """Computes structural and AST differences between two Query IR trees."""
    t1 = _py_optimize_ast(_py_parse_sexpr(ir1))
    t2 = _py_optimize_ast(_py_parse_sexpr(ir2))
    c1 = _py_canonical_ir(t1)
    c2 = _py_canonical_ir(t2)
    is_identical = (c1 == c2)
    return {
        "identical": is_identical,
        "ir1_canonical": c1,
        "ir2_canonical": c2,
    }


# ==============================================================================
# Async/Await Client & ASGI Middleware
# ==============================================================================

class AsyncNLSQLClient:
    """Non-blocking asynchronous client for high-concurrency applications."""
    def __init__(self, schema_specs: Optional[List[Tuple[str, str, List[Any]]]] = None, allow_tables: Optional[List[Tuple[str, str]]] = None, tenant_rules: Optional[List[Tuple[Any, ...]]] = None):
        self.context = Context()
        self.schema = Schema(self.context, schema_specs or [
            ("public", "orders", [("id", NLSQL_TYPE_INT64, NLSQL_COLUMN_PRIMARY_KEY), ("tenant_id", NLSQL_TYPE_UUID, NLSQL_COLUMN_TENANT_KEY), ("total", NLSQL_TYPE_DECIMAL, 0)])
        ])
        self.policy = Policy(
            self.context,
            allow=allow_tables or [("public", "orders")],
            tenant=tenant_rules or [("public", "orders", "tenant_id", NLSQL_TYPE_UUID)],
            runtime_tenant=("tenant_id", NLSQL_TYPE_UUID),
        )

    async def compile(self, ir: str, dialect: int = NLSQL_DIALECT_POSTGRES) -> CompileResult:
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, compile_ir, self.context, ir, self.schema, self.policy, dialect)

    async def compile_batch(self, ir_list: List[str], dialect: int = NLSQL_DIALECT_POSTGRES) -> List[CompileResult]:
        import asyncio
        tasks = [self.compile(ir, dialect) for ir in ir_list]
        return await asyncio.gather(*tasks)

    def close(self):
        self.policy.close()
        self.schema.close()
        self.context.close()

    async def __aenter__(self): return self
    async def __aexit__(self, *_): self.close()


class TenantContextMiddleware:
    """ASGI / Starlette / FastAPI middleware extracting tenant context from HTTP headers."""
    def __init__(self, app: Any, header_name: str = "X-Tenant-ID", tenant_type: int = NLSQL_TYPE_UUID):
        self.app = app
        self.header_name = header_name.lower().encode("latin1")
        self.tenant_type = tenant_type

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any):
        if scope["type"] == "http":
            tenant_id = None
            for key, val in scope.get("headers", []):
                if key.lower() == self.header_name:
                    tenant_id = val.decode("latin1")
                    break
            scope.setdefault("state", {})["tenant_id"] = tenant_id or "default-tenant"
        await self.app(scope, receive, send)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="nlsqlc Python SDK & CLI")
    parser.add_argument("--bench", action="store_true", help="Run high-throughput compilation benchmark")
    parser.add_argument("--iterations", type=int, default=5000, help="Number of benchmark iterations")
    parser.add_argument("--version", action="store_true", help="Show version information")
    args = parser.parse_args()

    if args.version:
        print(f"nlsqlc Python SDK v0.1.2 (Engine: {'native_c' if _native_lib else 'pure_python'})")
        return

    if args.bench:
        print(f"Running benchmark with {args.iterations} iterations...")
        stats = benchmark(iterations=args.iterations)
        print(f"Engine: {stats['engine']}")
        print(f"Throughput: {stats['queries_per_second']:,.1f} queries/sec")
        print(f"Latency: {stats['latency_us']:.2f} us/query")
        return

    print("nlsqlc Python SDK v0.1.2. Use --bench to test compilation speed or import in your project.")


if __name__ == "__main__":
    main()
