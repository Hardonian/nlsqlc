# nlsqlc

[![Build](https://github.com/Hardonian/nlsqlc/actions/workflows/build.yml/badge.svg)](https://github.com/Hardonian/nlsqlc/actions/workflows/build.yml)
[![Live database matrix](https://github.com/Hardonian/nlsqlc/actions/workflows/live-db.yml/badge.svg)](https://github.com/Hardonian/nlsqlc/actions/workflows/live-db.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

`nlsqlc` is a high-performance, embeddable C11 compiler and microservice platform for constrained S-expression Query IR. It resolves identifiers against trusted schema metadata, injects deterministic multi-tenant isolation predicates, and emits parameterized, injection-proof SQL across PostgreSQL, SQLite, DuckDB, MySQL, and SQL Server.

## Key Features

- **Constrained Query IR v2**: S-expression query language supporting multi-source joins (`inner`, `left`, `right`, `full`), rich boolean logic (`or`, `not`), scalar string/math expressions (`coalesce`, `lower`, `upper`, `trim`), window frames, and distinct aggregations.
- **Fail-Closed Multi-Tenant Security**: Unconditional parameterized tenant predicate injection and column-level deny-list enforcement.
- **Enterprise Service Gateway (`tools/server.py`)**: High-throughput HTTP/REST microservice daemon featuring `/v1/compile`, `/v1/validate`, `/v1/question`, Prometheus `/metrics`, token-bucket rate limiting, and zero-downtime hot reloading.
- **Background Migration & Drift Worker (`tools/worker.py`)**: Continuous database catalog watcher and policy drift detector.
- **Dual-Engine Python SDK (`bindings/python/nlsql.py`)**: Instant pure-Python fallback + native C ctypes acceleration (>60,000 queries/sec).
- **Modern C++17/20 RAII Bindings (`bindings/cpp/nlsql.hpp`)**: Exception-safe wrappers with zero overhead.
- **Multi-Database Live Introspector (`tools/db_introspect.py`)**: Generates canonical `.nlschema` and `.nlpolicy` files from live databases.

---

## Quickstart

### 1. Python SDK

```python
import nlsql

ctx = nlsql.Context()
schema = nlsql.Schema(ctx, [
    ("public", "orders", [
        ("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY),
        ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY),
        ("total_amount", nlsql.NLSQL_TYPE_DECIMAL, 0),
    ])
])
policy = nlsql.Policy(ctx, allow=[("public", "orders")], tenant=[("public", "orders", "tenant_id", nlsql.NLSQL_TYPE_UUID)])

ir = "(nlsql 1 (query (from orders o) (select (field (column o total_amount) total)) (limit 10)))"
result = nlsql.compile_ir(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_POSTGRES)

print(result.sql)
# SELECT "o"."total_amount" AS "total" FROM "public"."orders" AS "o" WHERE "o"."tenant_id" = $1 LIMIT 10
```

### 2. HTTP Microservice Daemon

```sh
python3 tools/server.py --host 0.0.0.0 --port 8080
```

Compile a query via REST:
```sh
curl -X POST http://localhost:8080/v1/compile \
  -H "Content-Type: application/json" \
  -d '{"ir": "(nlsql 1 (query (from orders o) (select (field (column o id) id))))", "dialect": "postgres"}'
```

---

## Build & Test

```sh
make all
make test

# Run the comprehensive Python & service test suite
pytest tests/ -v
```

---

## Documentation

- [Enterprise Architecture](docs/architecture/ENTERPRISE_ARCHITECTURE.md)
- [Tenant Isolation Security Whitepaper](docs/security/TENANT_ISOLATION_WHITEPAPER.md)
- [Server & Gateway Guide](docs/SERVER_GUIDE.md)
- [Query IR v2 Specification](spec/query-ir-v2.md) & [EBNF Grammar](spec/query-ir-v2.ebnf)
- [API Documentation](docs/API.md)

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
