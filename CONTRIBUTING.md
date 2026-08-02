# Contributing

Thanks for improving nlsqlc. The project values small, reproducible, fail-closed changes over broad speculative rewrites.

## Before opening an issue

- Search existing issues and documentation.
- Remove credentials, private keys, customer data, and production connection strings.
- For security vulnerabilities, use the private process in `SECURITY.md`, not a public issue.

## Before opening a pull request

Keep the core dependency-free and deny-by-default. Do not add raw SQL execution, network code, credentials, model runtimes, or silent fallbacks to the core.

Run the fast gate:

```sh
make clean && make all && make test
cmake -S . -B /tmp/nlsqlc-cmake -DNLSQL_BUILD_TESTS=ON -DNLSQL_BUILD_CLI=ON
cmake --build /tmp/nlsqlc-cmake --parallel
ctest --test-dir /tmp/nlsqlc-cmake --output-on-failure
```

For Python/importer changes:

```sh
uv venv /tmp/nlsqlc-qa
uv pip install --python /tmp/nlsqlc-qa/bin/python pytest hypothesis
/tmp/nlsqlc-qa/bin/pytest -q tests/test_importer.py tests/test_properties.py
```

For public C changes, run `tools/check-abi-compat.sh`, regenerate the amalgamation through the release workflow, and inspect `git diff --check`.

## Design requirements

1. Add a failing regression test before changing compiler behavior.
2. Preserve the public C ABI unless an explicit versioned change is approved.
3. Treat IR, schema, policy, importer, and provider output as untrusted at their boundaries.
4. Keep tenant isolation explicit and fail closed on missing or mismatched metadata.
5. Do not claim a database dialect works from SQL string fixtures alone; use live execution evidence.
6. Update API, ABI, security, release matrix, and closure documentation when their claims change.

## Review focus

Pull requests should state:

- exact commands and results;
- API/ABI and compatibility impact;
- tenant/policy and security impact;
- memory ownership and error-path behavior;
- portability and build-system impact;
- release-artifact or provenance impact;
- feedback requested from reviewers.

See `docs/DEVELOPMENT.md` for the full development loop and `.github/PULL_REQUEST_TEMPLATE.md` for the review checklist.
