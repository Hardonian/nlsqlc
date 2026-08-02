# Contributing

Keep the core dependency-free and deny-by-default. Add a failing regression test before changing compiler behavior. Run `make test` and the CMake test before submitting. Do not add raw SQL execution, network code, credentials, model runtimes, or silent fallbacks to the core.
