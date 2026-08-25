# nlsqlc Enterprise Architecture

This document provides a comprehensive technical overview of the nlsqlc compiler architecture, enterprise service gateway, worker subsystems, memory management, and security boundaries.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 NLSQLC ENTERPRISE SYSTEM                                  │
├──────────────────────────┬─────────────────────────────┬─────────────────────────────────┤
│    Client & SDK Layer    │     Service Gateway Layer   │       Core Engine & Workers     │
├──────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ • Python SDK (Async/Sync)│ • HTTP/1.1 & REST Gateway   │ • C11 Constrained IR v2 Compiler│
│ • C++17/C++20 RAII DSL   │ • Multi-threaded Worker Pool│ • Plan Cache & FNV-1a Hashing   │
│ • CLI Tooling            │ • Token Bucket Rate Limiter │ • Multi-source & Multi-CTE      │
│ • REPL & Formatters      │ • Prometheus /metrics       │ • Live Schema Watcher & Drift   │
│ • Database Introspectors │ • OpenTelemetry Tracing     │ • Chaos & Limit Test Harness    │
└──────────────────────────┴─────────────────────────────┴─────────────────────────────────┘
```

## Subsystem Breakdown

### 1. Compiler Core Subsystem (`src/nlsql.c`, `include/nlsql/nlsql.h`)
- **Lexing & Parsing**: S-expression recursive descent parser enforcing a maximum AST nesting depth of 128 and maximum token length of 128 characters.
- **Schema Resolution & Foreign Key Graph**: Validates all referenced tables and columns against an explicitly declared schema. Validates joins against declared foreign keys.
- **Tenant Predicate Injection**: Injects parameterized equality predicates on tenant isolation keys deterministically, ensuring model outputs cannot cross tenant boundaries.
- **Dialect Code Emission**: Emits dialect-precise SQL across PostgreSQL, SQLite, DuckDB, MySQL, and SQL Server.

### 2. Service Gateway Subsystem (`tools/server.py`)
- **High-Throughput Threaded HTTP Daemon**: Multi-threaded request handling with `/v1/compile`, `/v1/validate`, and `/v1/question` endpoints.
- **Rate Limiting**: Thread-safe token bucket rate limiter isolating tenants and preventing denial-of-service query flooding.
- **Zero-Downtime Hot Reloading**: Atomic schema and policy swapping via `/v1/schema/reload` and `/v1/policy/reload`.

### 3. Background Migration & Drift Worker (`tools/worker.py`)
- **Schema Snapshotting**: Continuous SHA-256 state hashing of database catalogs.
- **Drift Alerting**: Detects new unmapped tables/columns and triggers policy synchronization alerts.

### 4. Telemetry & Observability Subsystem (`tools/monitor.py`)
- **Prometheus Metrics**: Uptime, request volume, success/failure counts, and p50/p99 compilation latency histograms.
- **Anomaly Detection**: Statistical complexity analysis flagging abnormal query shapes or policy violation spikes.
