# Closure register

Revision under test: current working tree on `main` (local-only, not pushed).

## Closed

- Structured diagnostic record and source location accessors added with zero ABI breakage.
- Query IR v2 with multi-source joins (`inner`, `left`, `right`, `full`), rich boolean expressions (`or`, `not`), scalar ops (`coalesce`, `lower`, `upper`, `trim`), and distinct aggregations.
- Dual-Engine Python SDK with pure-Python execution fallback, ctypes native compilation acceleration, and query builder DSL.
- Modern C++17/20 RAII headers in `bindings/cpp/nlsql.hpp`.
- Enterprise HTTP/1.1 microservice daemon in `tools/server.py` with Prometheus `/metrics`, token bucket rate limiting, and zero-downtime hot reloading.
- Continuous background schema watcher & policy drift detection worker in `tools/worker.py`.
- Observability and telemetry anomaly detection in `tools/monitor.py`.
- Multi-database live introspector in `tools/db_introspect.py`.
- Exhaustive test suites: `tests/test_dialects.py`, `tests/test_server.py`, `tests/test_worker.py`, `tests/test_limits.py`.
- Enterprise architecture, query IR v2 EBNF specifications, server deployment guide, and tenant isolation security whitepapers.

## Rollback

Revert the focused local changes with `git diff` review followed by `git checkout -- <named-file>` only for this work, or use `git revert <commit>` after a local commit. No remote history was changed.