# Changelog

## 0.1.2 - 2026-08-02

Closed the verified compiler release slice: typed expression validation, scoped CTE compilation, policy-checked set operations, window expressions, five-dialect placeholder fixtures, SQLite schema import, C++17 and Python ctypes bindings, inference callback revalidation, ABI version reporting, fuzzing, sanitizer/static-analysis gates, release checksums, SPDX SBOM generation, and detached GPG signing tooling.

The release remains intentionally bounded: the core does not bundle an LLM/database runtime, CTEs are single-source and non-recursive, and live database execution is outside scope.

## 0.1.1 - unreleased

Hardened schema-resolved column policy enforcement, foreign-key join enforcement, typed Query IR parameters, canonical IR serialization, and native trusted CLI schema/policy formats. Added CLI `validate-ir` and negative tests for arbitrary joins and denied columns.

## 0.1.0 - unreleased

Initial verified vertical slice: strict Query IR parser, in-memory schema builder, policy allowlists and tenant injection, parameterized read-only SQL emitter, CLI, tests, build files, specifications, threat model, and generated two-file distribution.
