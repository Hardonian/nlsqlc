# Verification and release readiness

Date: 2026-08-02

## Evidence run

Release-gate command: `tools/release.sh 0.1.2`

- Make build/test: passed; core, security-negative, question, CTE-scope, type, and dialect checks passed.
- Strict GCC and Clang warning builds: passed.
- CMake Release build and CTest: passed, 2/2.
- ThreadSanitizer library/test build and runtime: passed.
- MemorySanitizer library/test build and runtime: passed locally and added to CI.
- ASan/UBSan fuzz target: passed 250 executions in the current closure run; prior 1,000-run run also passed.
- GCC analyzer and Clang analyzer: passed in the recorded release gate.
- SQLite importer: passed database → generated schema → CLI validation/compilation.
- SQLite emitted-SQL integration through the Python binding: passed against SQLite 3.53.1.
- C++17 binding and Python ctypes binding: passed smoke tests.
- Installed CMake package and pkg-config downstream consumers: passed.
- Shared-library export audit: passed; only declared public `nlsql_*` symbols are exported.
- Amalgamation standalone compile: passed.
- Release archive, internal checksums, external checksum, sidecar provenance, and SPDX SBOM: passed.
- Standalone `tools/verify-release.sh 0.1.2`: passed.
- Detached GPG signing workflow: passed with an isolated temporary keyring; no private key retained.
- Meson execution is not claimed because `meson` is not installed on this host.
- Live execution against PostgreSQL, SQLite, DuckDB, MySQL, and SQL Server is not claimed because those database clients/servers are not part of the compiler test environment; dialect SQL/placeholder fixtures are covered.

## Verified scope

The 0.1.2 release is a bounded, read-only, policy-checked SQL compiler. It includes typed expressions, tenant enforcement, FK-backed joins, windows, set operations, scoped single-source non-recursive CTEs, five dialect emitters, deterministic question helpers, inference callback revalidation, SQLite schema import, C++/Python bindings, fuzzing, sanitizer/static-analysis coverage, checksums, SBOM, and signing tooling.

## Explicit limits

- The core does not bundle an LLM, natural-language model, database driver, network stack, or SQL execution engine.
- Natural-language integration is callback-based; callback output is treated as untrusted IR and revalidated.
- CTE support is intentionally limited to one non-recursive source query and projected outer relation scope.
- External database execution and Meson remain environment-dependent verification gaps.

## Verdict

Technical: 0.1.2 release slice verified locally.

Security: fail-closed compiler behavior, tenant/policy enforcement, fuzzing, sanitizers, and static-analysis gates passed for the tested scope.

Packaging: archive, reproducibility, checksum, sidecar provenance, SBOM, CMake export, pkg-config, amalgamation, binding, and signing workflows passed.

External/production: local compiler readiness is verified; live database compatibility and external publication are not claimed without their environments.
