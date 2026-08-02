# Releasing

Before a release: run CMake, Make, the amalgamation standalone compile, tests, sanitizers where available, static analysis where available, and inspect the diff. Generate checksums and an SBOM. This 0.1 tree is not yet a release candidate because bindings, fuzzing, full dialect fixtures, and signed provenance are not implemented.
