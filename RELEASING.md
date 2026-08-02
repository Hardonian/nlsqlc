# Releasing

Before a release: run CMake, Make, the amalgamation standalone compile, tests, sanitizers where available, static analysis where available, and inspect the diff. Generate checksums and an SBOM. Run `tools/sign-release.sh VERSION GPG_KEY` with an explicitly controlled signing key, then verify both detached signatures before publishing. Cosign/Sigstore is optional and must not be represented as available when it is not installed.
