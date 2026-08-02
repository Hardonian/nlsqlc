# nlsqlc C API reference

The stable public API is `include/nlsql/nlsql.h`. It is C11 and C++-compatible (`extern "C"`), owns no database connection, and never executes SQL.

## Compilation

1. Create a context.
2. Build and finalize a trusted schema.
3. Build a trusted policy.
4. Submit `nlsql_compile_request` to `nlsql_compile_ir`.
5. Inspect SQL, parameters, risk, complexity, canonical IR, fingerprint, and manifest.
6. Destroy the result and trusted objects.

`nlsql_compile_cte` compiles a bounded single-source CTE and an outer query against a temporary projected relation scope. The outer query can reference only fields projected by the CTE; underlying tables and unprojected columns are not visible through the CTE alias. CTE and outer parameters are rebased deterministically.

`nlsql_compile_set` independently compiles two IR branches and combines them as `UNION`, `UNION ALL`, `INTERSECT`, or `EXCEPT`, rebasing numbered parameters.

The dialect fixture suite exercises Postgres, SQLite, DuckDB, MySQL, and SQL Server parameter conventions.

`nlsql_compile_inferred` accepts an application-owned inference callback. The callback output is untrusted and is always recompiled through the normal parser/schema/policy path.

The repository also ships a dependency-free C++17 RAII wrapper at `bindings/cpp/nlsql.hpp`. It wraps context/result lifetime and the IR/set compile entry points while preserving the C ABI and error statuses.

## Ownership

- Context, schema builder, schema, policy, inference output, and compile result are caller-managed.
- Result views point into the compile result and become invalid after `nlsql_compile_result_destroy`.
- The library never frees caller-owned schema/policy objects.

## Security contract

- Raw SQL is not accepted as input.
- Identifiers must resolve against trusted schema metadata.
- Joins must match declared foreign keys.
- Tenant predicates are injected after model IR parsing.
- Runtime values are represented as parameters.
- Compilation performs no network, filesystem, shell, or database operations.

## Versioning

`NLSQL_VERSION` and `NLSQL_IR_VERSION` identify the public ABI/IR contract. Callers should reject unsupported IR versions before persisting or replaying model output.
