# ABI and compatibility policy

## Contract

The public C API is declared in `include/nlsql/nlsql.h`. Opaque handles are owned by the API that creates them and must be released with the matching destroy function. Callers must not allocate, copy, or inspect opaque structures.

`NLSQL_ABI_VERSION` and `nlsql_abi_version()` identify the binary contract. A caller should check the runtime value before using optional functionality. `NLSQL_IR_VERSION` identifies the serialized Query IR contract and is independent of the C ABI version.

## Compatibility rules

- Public declarations are additive within a compatible ABI version.
- Existing function signatures, enum values, ownership rules, and struct layouts exposed by value are not changed within a compatible ABI version.
- New enum values require an audit of callers that use exhaustive switches.
- Removing or changing a public symbol requires an ABI version bump and a migration note.
- Deprecated APIs use `NLSQL_DEPRECATED` and remain available for at least one documented release cycle.
- Internal symbols are hidden from shared-library exports.
- Bindings must use the public header and never depend on internal structure layout.

## Verification

The release gate compiles a downstream C consumer against the installed static package, a CMake `find_package(nlsqlc CONFIG REQUIRED)` consumer, and a pkg-config consumer. Shared-library exports are audited to ensure only the declared `nlsql_*` API is visible.

A future incompatible release must retain an old-header/new-library and new-header/old-library compatibility fixture before publication. The project does not claim ABI compatibility across major changes without that evidence.
