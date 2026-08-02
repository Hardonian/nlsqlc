# Verification and release readiness

Date: 2026-08-01

## Evidence run

- `make clean && make all && make test`: passed; core test and negative security checks passed.
- strict direct compile with the requested warning set and `-Werror`: passed.
- CMake configure/build/CTest: passed in `build-final` after final join-path hardening.
- amalgamation standalone `examples/minimal/main.c` using `dist/nlsql.c` and `dist/nlsql.h`: passed after final source sync.
- AddressSanitizer/UndefinedBehaviorSanitizer test binary: passed after final join-path hardening.
- Meson: unavailable on this host (`meson` not installed), so Meson execution is not claimed.

## Delivered

The repository at `/home/scott/nlsqlc` contains a zero-runtime-dependency C11 vertical slice with strict Query IR parsing, bounded allocation, schema builder, schema-resolved identifiers, foreign-key-backed inner joins, read-only SQL emission for five parameter styles, policy allowlists, tenant predicate injection, manifest output, CLI, CMake/Make/Meson build descriptions, examples, threat model, specifications, and amalgamation.

## Not delivered

This is not a 1.0 release candidate. Missing: question fast paths, inference callback/prompt builder, semantic metrics, canonical serialization/fingerprints/cache callbacks, CTE/window/set-operation support, full type checking, all dialect-specific conformance fixtures, schema/policy file parsers, bindings, fuzz harnesses, ThreadSanitizer/static-analysis matrix, SBOM/provenance/signatures, and complete public API documentation.

## Verdict

Prototype / early alpha, not production-ready. The security-critical vertical slice is real and tested, but the requested enterprise feature surface is substantially larger than this first implementation.
