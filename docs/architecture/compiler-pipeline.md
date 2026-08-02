# Architecture

The current core is intentionally small and explicit: bounded S-expression parser, trusted schema registry, policy resolver, parameter allocator, dialect-aware emitter, and audit manifest. There is no SQL execution boundary in the library. The 0.1 implementation is a vertical slice; deferred stages are listed in ROADMAP.md rather than represented by stubs.
