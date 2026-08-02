# Verification and release readiness

Date: 2026-08-02

## Evidence run

Release-gate command: `tools/release.sh 0.1.2`

- Make build/test: passed; core, negative security, and question fast-path checks passed.
- Strict GCC compile with the requested warning set and `-Werror`: passed.
- Strict Clang compile: passed.
- CMake Release build for static library, shared library, static CLI, and tests: passed with `-Werror` on all targets.
- CTest: 2/2 passed.
- ASan/UBSan core test: passed with leak detection enabled.
- CLI trusted `.nlschema`/`.nlpolicy` validation and PostgreSQL compilation: passed.
- Amalgamation source comparison and standalone compile: passed.
- Static CLI check: passed; `nlsqlc` is statically linked.
- Stable IR fingerprint and relevance metric tests: passed.
- Clang/libFuzzer harness: built and completed 1,000 ASan/UBSan executions without a crash.
- Release archive, SHA-256 checksum, and SPDX 2.3 SBOM: generated under `release/`.
- Meson execution remains unavailable because `meson` is not installed on this host; its strict configuration is present but not claimed as executed.

The repository is release-ready for the scoped 0.1.2 alpha package: a bounded, read-only, policy-checked SQL compiler with typed parameters, canonical IR, tenant enforcement, FK-backed joins, trusted CLI configuration formats, deterministic question fast paths, and a static CLI.

## 1.0 blockers

This is not an enterprise 1.0 release candidate. Remaining blockers are deliberately explicit: unrestricted natural-language inference, CTE/set-operation grammar and emission, full expression type checking, complete dialect-specific conformance fixtures, schema importers, language bindings, ThreadSanitizer/static-analysis matrix, signed provenance, stable schema/policy ABI, and complete public API documentation.

## Verdict

Technical: scoped 0.1.1 alpha release-ready; 1.0 not ready.

Security: the implemented read-only vertical slice passed current negative tests and sanitizers; broader coverage remains required before 1.0.

Packaging: release archive, checksums, and SPDX SBOM generated and verified locally.

External/production: not ready for an enterprise 1.0 claim until the listed blockers are closed.
