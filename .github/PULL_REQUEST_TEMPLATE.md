## Summary

<!-- What changed and why? Keep the core dependency-free and fail-closed. -->

## Verification

- [ ] `make clean && make all && make test`
- [ ] CMake/CTest
- [ ] Relevant Python, importer, ABI, fuzz, or live-database checks
- [ ] Documentation and release evidence updated where applicable

## Compatibility and security

- [ ] Public API/ABI impact is documented
- [ ] Tenant isolation and policy behavior are covered
- [ ] No secrets, credentials, customer data, or generated build output are included
- [ ] Unsupported shapes still fail closed

## Feedback requested

<!-- Name the files, API behavior, or design trade-offs you want reviewers to focus on. -->
