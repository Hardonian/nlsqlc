# nlsqlc

[![Build](https://github.com/Hardonian/nlsqlc/actions/workflows/build.yml/badge.svg)](https://github.com/Hardonian/nlsqlc/actions/workflows/build.yml)
[![Live database matrix](https://github.com/Hardonian/nlsqlc/actions/workflows/live-db.yml/badge.svg)](https://github.com/Hardonian/nlsqlc/actions/workflows/live-db.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

nlsqlc is a small, embeddable C11 compiler for a constrained S-expression Query IR. It resolves identifiers against trusted schema metadata, injects deterministic tenant predicates, and emits parameterized read-only SQL without a database driver, network stack, model runtime, or external library.

This repository ships nlsqlc 0.1.2: a bounded, read-only, policy-checked SQL compiler for trusted Query IR. It supports schema resolution, tenant predicate injection, FK-backed joins, typed parameters and expressions, windows, policy-checked set operations, scoped single-source CTEs, five SQL dialects, deterministic question fast paths, SQLite schema import, C++17 and Python ctypes bindings, inference callbacks, fuzzing, sanitizers, checksums, an SPDX SBOM, and detached GPG release signatures.

The core deliberately does not execute SQL, connect to databases, call a model, access the network, or accept raw SQL. “Natural language” is an application concern: use `nlsql_compile_inferred` with your own provider callback; its returned IR is always parsed and revalidated. The CTE API is intentionally bounded to one non-recursive source query and a projected outer relation. Unsupported shapes fail closed.

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

The compiler adds the configured default limit and any required tenant predicate. See `spec/query-ir-v1.ebnf` and `tests/test_question.c` for complete examples.

## Five-minute onboarding

```sh
git clone https://github.com/Hardonian/nlsqlc.git nlsqlc
cd nlsqlc
make test
./nlsqlc version
```

Compile a trusted query with the checked-in example files:

```sh
./nlsqlc compile \
  --ir examples/tenant-policy/query.nlir \
  --schema examples/tenant-policy/example.nlschema \
  --policy examples/tenant-policy/example.nlpolicy \
  --dialect postgres
```

Build a schema from SQLite without adding a runtime dependency:

```sh
python3 tools/sqlite_schema_import.py app.db /tmp/app.nlschema
./nlsqlc validate-ir --ir query.nlir --schema /tmp/app.nlschema --policy policy.nlpolicy
```

For embedders, start with `docs/API.md`, `bindings/cpp/nlsql.hpp`, or `bindings/python/nlsql.py`. Every result is owned by the caller and must be destroyed with `nlsql_compile_result_destroy`.

## Developer and contributor feedback

Please report reproducible bugs and feature requests through the [issue tracker](https://github.com/Hardonian/nlsqlc/issues/new/choose). Pull requests should include the exact verification commands and call out API/ABI, security, tenant-isolation, and release-evidence impact. Use the [contributor guide](CONTRIBUTING.md), [development guide](docs/DEVELOPMENT.md), and [pull-request template](.github/PULL_REQUEST_TEMPLATE.md).

- Security vulnerabilities: use the private reporting path in [SECURITY.md](SECURITY.md), never a public issue.
- API and ABI feedback: include a minimal sanitized IR/schema/policy fixture and compiler/toolchain details.
- Roadmap and backlog: see [ROADMAP.md](ROADMAP.md) and [TOP50.md](TOP50.md).
- CI and release evidence: see [RELEASE_MATRIX.md](RELEASE_MATRIX.md) and [CLOSURE_REGISTER.md](CLOSURE_REGISTER.md).

## Project boundaries

The core is deliberately not a database driver, SQL executor, network client, model runtime, or unrestricted natural-language-to-SQL system. Provider integrations belong outside the core and must feed untrusted output back through the parser and policy compiler.

## CLI and trusted formats

The CLI supports `compile` and `validate-ir` with optional trusted `.nlschema` and `.nlpolicy` inputs:

    nlsqlc validate-ir --ir query.nlir --schema schema.nlschema --policy policy.nlpolicy
    nlsqlc compile --ir query.nlir --schema schema.nlschema --policy policy.nlpolicy --dialect postgres

The core still does not read files; file parsing is CLI-only configuration handling. See `spec/native-formats.md`.

The core also exposes `nlsql_compile_set` for policy-checked `UNION`, `UNION ALL`, `INTERSECT`, and `EXCEPT`. Each branch is independently compiled and the resulting parameter positions are rebased deterministically.

## License

Apache License 2.0. See LICENSE.
