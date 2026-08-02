import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from nlsql import Context, Schema, Policy, NLSQL_TYPE_INT64, compile_ir

ctx = Context()
schema = Schema(ctx, [("public", "orders", [("id", NLSQL_TYPE_INT64)])])
policy = Policy(ctx, [("public", "orders")])
result = compile_ir(ctx, schema, policy, "(nlsql 1 (query (from orders o) (select (field (column o id) id))))")
assert 'SELECT' in result.sql
assert '"orders"' in result.sql
print('python_ctypes_pass')
