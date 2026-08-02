# Security policy

## Scope

The nlsqlc core parses bounded Query IR and emits parameterized read-only SQL. It does not execute SQL, connect to a database, load extensions, access the network, or invoke a shell. Reports should identify whether the issue affects the core, CLI configuration loader, importer, binding, or release tooling.

## Reporting

Do not disclose exploitable vulnerabilities in public issues. Send a private report to the repository maintainer through the authenticated project contact or private security-advisory mechanism. Include:

- affected version and commit
- compiler/platform
- minimal reproduction or test input
- expected and observed behavior
- whether tenant isolation, policy enforcement, memory safety, or release integrity is affected

Do not include credentials, customer data, production connection strings, or private keys in a report.

## Response targets

- Acknowledge: 3 business days.
- Initial triage: 7 calendar days.
- Mitigation or documented status: 30 calendar days where practical.
- Coordinated disclosure: agreed with the reporter and affected downstream users.

## Release policy

Security fixes are tested against the current supported release and `main`. Releases include checksums, an SPDX SBOM, and provenance metadata. The project does not claim that fuzzing, static analysis, or a checksum proves the absence of vulnerabilities.

## Supported versions

Only the latest release and the current development branch receive security fixes unless a downstream support commitment explicitly states otherwise. Compatibility impact and migration notes are recorded in `CHANGELOG.md`.
