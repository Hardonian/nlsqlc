# Closure register

Revision under test: current working tree on `main` (local-only, not pushed).

## Closed

- Structured diagnostic record and source location accessors were added without changing existing public signatures.
- Python ctypes binding now covers all non-callback compile entry points and result metadata.
- SQLite importer tenancy is explicit and fails closed for missing configured columns.
- Native `.nlpolicy` typed tenant records are parsed, validated against the trusted schema, and the checked-in tenant example passes `validate-ir`.
- Hypothesis-based importer safety properties and importer tenancy regressions are executable.
- Meson execution was installed in the user tool environment and verified.
- Historical-header ABI consumer fixture is executable.
- OSS-Fuzz build integration scaffold is present.
- Release consistency checker is executable.

## Open / external gates

- Real PostgreSQL, DuckDB, MySQL, and SQL Server execution require credentials, running engines, and DB drivers. The matrix reports these as `BLOCKED`, not green.
- OSS-Fuzz upstream registration and continuous corpus execution require project submission/infra outside this repository.
- Public release publication and detached signing require an operator-controlled release key/target.

## Rollback

Revert the focused local changes with `git diff` review followed by `git checkout -- <named-file>` only for this work, or use `git revert <commit>` after a local commit. No remote history was changed.