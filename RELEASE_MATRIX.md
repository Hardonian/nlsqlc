# Release verification matrix

This matrix is evidence-driven. `PASS` means the command was run successfully;
`BLOCKED` means a prerequisite is absent; it is never converted to a pass.

| Surface | Status | Evidence / blocker |
|---|---|---|
| C11 Make build and tests | PASS | `make clean && make all && make test` |
| CMake build and CTest | PASS | CMake configure/build + `ctest --test-dir /tmp/nlsqlc-cmake2 --output-on-failure` |
| Meson configure/build/test | PASS | `~/.local/bin/meson setup ...`; `meson compile`; `meson test` |
| Structured diagnostics/source locations | PASS | additive C ABI and Python `Result.diagnostics` surface; compile failures carry status/code/message and 1-based location |
| Python API coverage | PASS | Python binding smoke plus wrappers for IR, CTE, set, question, schema FKs/flags, policy, params, manifest, risk, diagnostics |
| Importer semantic tests | PASS | `pytest tests/test_importer.py tests/test_properties.py` (5 passed) |
| Checked-in native tenant example | PASS | `./nlsqlc validate-ir --ir examples/tenant-policy/query.nlir --schema examples/tenant-policy/example.nlschema --policy examples/tenant-policy/example.nlpolicy` |
| Explicit tenancy configuration | PASS | importer no longer infers `tenant_id`; use repeatable `--tenant-table TABLE=COLUMN`; typed `.nlpolicy` rules are validated |
| Property-based policy/tenant/quoting | PASS | Hypothesis tests run in isolated uv environment |
| Historical ABI fixture | PASS | `tools/check-abi-compat.sh` against commit `a7f411a` |
| SQLite execution | PASS | `python3 tests/test_sqlite_integration.py` |
| PostgreSQL live execution | BLOCKED | local server requires credentials; matrix adapter supports `NLSQL_POSTGRES_URL` |
| DuckDB live execution | BLOCKED | driver/server not installed; set `NLSQL_DUCKDB_URL` and install driver |
| MySQL live execution | BLOCKED | no server/driver configured; set `NLSQL_MYSQL_URL` and install driver |
| SQL Server live execution | BLOCKED | no server/driver configured; set `NLSQL_SQLSERVER_URL` and install driver |
| OSS-Fuzz integration | PASS (scaffold) | `oss-fuzz/Dockerfile`, `oss-fuzz/build.sh`; upstream project onboarding remains external |
| Release evidence consistency | PASS | `tools/check-release-evidence.py` |
| External publication/signing | BLOCKED | requires release operator credentials and publication target |