# nlsqlc

nlsqlc is a small, embeddable C11 compiler for a constrained S-expression Query IR. It resolves identifiers against trusted schema metadata, injects deterministic tenant predicates, and emits parameterized read-only SQL without a database driver, network stack, model runtime, or external library.

This repository is an honest 0.1 vertical slice, not a 1.0 release candidate. The implemented core accepts strict Query IR for trusted callers and supports schema tables/columns/foreign keys, allowlists, tenant predicates, selected expressions, inner joins, filters, grouping, ordering, limits, PostgreSQL/SQLite/DuckDB/MySQL/SQL Server parameter styles, and a line-oriented manifest.

It does not yet implement unrestricted natural language, the inference callback pipeline, semantic metrics, CTEs, windows, set operations, schema importers, bindings, fuzz harnesses, or signed release provenance. Those are explicitly tracked as roadmap work rather than claimed capabilities.

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

## License

Apache License 2.0. See LICENSE.
