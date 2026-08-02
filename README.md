# nlsqlc

nlsqlc is a small, embeddable C11 compiler for a constrained S-expression Query IR. It resolves identifiers against trusted schema metadata, injects deterministic tenant predicates, and emits parameterized read-only SQL without a database driver, network stack, model runtime, or external library.

This repository ships the scoped 0.1.2 alpha vertical slice. The static CLI supports trusted IR compilation, schema/policy files, deterministic `count`, `list`, `sum`, and `average` question fast paths, PostgreSQL/SQLite/DuckDB/MySQL/SQL Server parameter styles, stable IR fingerprints, deterministic relevance metrics, a Clang/libFuzzer harness, and release artifacts with checksums and an SPDX SBOM.

It does not yet implement unrestricted natural language, CTEs, set operations, schema importers, language-specific bindings, or signed release provenance. Window expressions are supported in the bounded IR grammar. Those remaining items are explicitly tracked rather than claimed.

## Security boundary

Raw SQL is never accepted as input. Model output must be treated as untrusted Query IR and compiled through the same parser, schema resolver, and policy checks. All runtime values are parameters. Identifiers are quoted only after schema resolution. The core does not execute SQL and contains no network or credential code.

## Build

    make all
    make test

    cmake -S . -B build -DNLSQL_BUILD_TESTS=ON -DNLSQL_BUILD_CLI=ON
    cmake --build build --parallel
    ctest --test-dir build --output-on-failure

The amalgamation can be embedded directly:

    cc -std=c11 -O2 app.c dist/nlsql.c -I dist -o app

## Query IR

See spec/query-ir-v1.ebnf. A minimal input is:

    (nlsql 1
      (query
        (from orders o)
        (select (field (column o status) status))))

The compiler adds the configured default limit and any required tenant predicate. See examples and tests for a complete join query.

## CLI and trusted formats

The CLI supports `compile` and `validate-ir` with optional trusted `.nlschema` and `.nlpolicy` inputs:

    nlsqlc validate-ir --ir query.nlir --schema schema.nlschema --policy policy.nlpolicy
    nlsqlc compile --ir query.nlir --schema schema.nlschema --policy policy.nlpolicy --dialect postgres

The core still does not read files; file parsing is CLI-only configuration handling. See `spec/native-formats.md`.

## License

Apache License 2.0. See LICENSE.
