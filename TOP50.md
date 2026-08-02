# Top 50 execution register

This is the ranked repository backlog. `DONE` means verified in the current repository or GitHub Actions evidence. `NEXT` means a real remaining boundary item; it is not represented as completed by documentation alone.

| Rank | Item | Status | Evidence / next action |
|---:|---|---|---|
| 1 | C11 Make build | DONE | `make clean && make all` |
| 2 | Native C tests | DONE | `make test` |
| 3 | CMake/CTest | DONE | GitHub build workflow |
| 4 | Meson build/test | DONE | GitHub build workflow |
| 5 | C++17 binding smoke | DONE | GitHub build workflow |
| 6 | Python ctypes smoke | DONE | Python binding test |
| 7 | SQLite integration | DONE | SQLite integration test |
| 8 | ThreadSanitizer | DONE | GitHub build workflow |
| 9 | MemorySanitizer | DONE | GitHub build workflow |
| 10 | Clang fuzz smoke | DONE | 250 fuzz runs in CI |
| 11 | Structured diagnostics | DONE | Additive C API and Python result diagnostics |
| 12 | Source locations | DONE | Offset/line/column result view |
| 13 | Full Python compile entry points | DONE | IR, CTE, set, question wrappers |
| 14 | Python result metadata | DONE | Params, manifest, risk, fingerprint, diagnostics |
| 15 | Explicit importer tenancy | DONE | No conventional-name inference |
| 16 | Typed native tenancy | DONE | Parser/API/schema type validation |
| 17 | Importer missing-column rejection | DONE | Importer regression tests |
| 18 | Identifier property tests | DONE | Hypothesis suite |
| 19 | Tenant policy property tests | DONE | Hypothesis suite |
| 20 | SQL quoting property tests | DONE | Hypothesis suite |
| 21 | Historical ABI fixture | DONE | Prior-header consumer against current library |
| 22 | Five-dialect emission coverage | DONE | Existing native tests/fixtures |
| 23 | CTE bounded behavior | DONE | Existing CTE API/tests |
| 24 | Set-operation parameter rebasing | DONE | Existing set tests |
| 25 | Question fast path | DONE | Existing question tests |
| 26 | CMake install consumer | DONE | GitHub package-install gate |
| 27 | pkg-config install check | DONE | GitHub package-install gate |
| 28 | Shared-library SONAME | DONE | CMake configuration and release verification |
| 29 | Amalgamation synchronization | DONE | Release generation and compile gate |
| 30 | Release checksum verification | DONE | `tools/verify-release.sh` |
| 31 | Release provenance evidence | DONE | Release sidecar verification |
| 32 | Release consistency checker | DONE | `check-release-consistency.sh` |
| 33 | Release evidence checker | DONE | `check-release-evidence.py` |
| 34 | OSS-Fuzz build scaffold | DONE | `oss-fuzz/` and CI fuzz target |
| 35 | PostgreSQL live CI execution | DONE | Live database workflow |
| 36 | MySQL live CI execution | DONE | Live database workflow |
| 37 | DuckDB live CI execution | DONE | Live database workflow |
| 38 | SQL Server live CI execution | DONE | Live database workflow |
| 39 | Public onboarding URL | DONE | README clone command |
| 40 | CI status visibility | DONE | README workflow badges |
| 41 | Contributor development guide | DONE | `docs/DEVELOPMENT.md` |
| 42 | Bug report intake | DONE | GitHub issue form |
| 43 | Feature request intake | DONE | GitHub issue form |
| 44 | Pull-request review checklist | DONE | PR template |
| 45 | Code ownership routing | DONE | `.github/CODEOWNERS` |
| 46 | Public repository visibility | DONE | GitHub repository setting |
| 47 | Multi-source query grammar | NEXT | Design/version IR extension and add parser tests |
| 48 | Multi-CTE and recursive CTE support | NEXT | Define bounded grammar and policy rules |
| 49 | Provider adapter examples | NEXT | Add optional out-of-core integration examples |
| 50 | Cross-platform release matrix | NEXT | Add Windows/macOS runners and packaging checks |

The remaining `NEXT` items are intentionally not marked complete. They change the language boundary or require additional provider/platform design and should arrive as reviewed, versioned changes rather than speculative stubs.
