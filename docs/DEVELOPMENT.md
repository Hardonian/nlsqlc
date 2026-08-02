# Development guide

## Prerequisites

- C11 compiler with warnings-as-errors support
- CMake 3.16+ or Meson 1.x
- Python 3.11+ for importer/integration tests
- `uv` is recommended for isolated Python tooling

The core has no runtime dependency on Python, a database, a network, or a model provider.

## Fast local gate

```sh
set -Eeuo pipefail
make clean
make all
make test
cmake -S . -B /tmp/nlsqlc-cmake -DNLSQL_BUILD_TESTS=ON -DNLSQL_BUILD_CLI=ON
cmake --build /tmp/nlsqlc-cmake --parallel
ctest --test-dir /tmp/nlsqlc-cmake --output-on-failure
```

## Extended gate

```sh
uv venv /tmp/nlsqlc-qa
uv pip install --python /tmp/nlsqlc-qa/bin/python pytest hypothesis
/tmp/nlsqlc-qa/bin/pytest -q tests/test_importer.py tests/test_properties.py
~/.local/bin/meson setup /tmp/nlsqlc-meson
~/.local/bin/meson compile -C /tmp/nlsqlc-meson
~/.local/bin/meson test -C /tmp/nlsqlc-meson --print-errorlogs
tools/check-abi-compat.sh
python3 tools/check-release-evidence.py
```

## Focused development loop

1. Add a failing regression test.
2. Change the smallest implementation surface.
3. Run the focused test.
4. Run the fast local gate.
5. Regenerate `dist/nlsql.c` and `dist/nlsql.h` through `tools/release.sh` when public C sources change.
6. Run `git diff --check` and inspect the staged file list.
7. Explain compatibility, policy, tenant-isolation, and release-evidence impact in the pull request.

## Feedback expected from contributors

Reviewers should comment on correctness, fail-closed behavior, public API/ABI impact, portability, memory ownership, test quality, documentation, and whether the change belongs in the dependency-free core. Small reproducible fixtures are preferred over broad unverified refactors.

## Release verification

```sh
SOURCE_DATE_EPOCH=1700000000 tools/release.sh 0.1.2
tools/verify-release.sh 0.1.2
```

Do not claim live provider compatibility from string fixtures. Use the configured live matrix or the GitHub Actions database workflow.
