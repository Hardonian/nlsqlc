# Roadmap

0.1.2 enterprise expansion completed:
- Multi-source join trees (`inner`, `left`, `right`, `full`) with strict foreign key graph resolution and policy authorization.
- Multi-CTE and bounded recursive CTE compilation with parameter position rebasing.
- Rich expression grammar: `or`, `not`, `in`, `between`, `like`/`ilike`, `is-null`/`is-not-null`, `case/when`, `coalesce`, scalar string/math/date ops, distinct aggregations.
- Enterprise HTTP/1.1 microservice gateway daemon (`tools/server.py`) with token-bucket rate limiting and zero-downtime hot reloading.
- Continuous background schema watcher & migration drift detection worker (`tools/worker.py`).
- Observability and Prometheus telemetry monitoring subsystem (`tools/monitor.py`).
- Dual-Engine Python SDK (instant pure-Python fallback + native C acceleration) with fluent query builder and benchmarking.
- Multi-dialect conformance test suite across PostgreSQL, SQLite, DuckDB, MySQL, and SQL Server.
- Stress, chaos, and AST depth limit test suite.
