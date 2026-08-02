# Roadmap

0.1.2 hardening completed: deny-column enforcement, FK join validation, typed parameters and expressions, canonical IR output, native CLI schema/policy formats, `validate-ir`, static CLI packaging, deterministic question fast paths, stable IR fingerprints, relevance scoring, windows, set operations, scoped CTE compilation, five-dialect fixtures, SQLite import, C++/Python bindings, inference callback revalidation, ABI versioning, fuzzing, sanitizer/static-analysis gates, signed provenance, and public API documentation.

Remaining boundary work: multi-source/multi-CTE and recursive CTE grammar, optional provider-specific natural-language adapters, live database conformance jobs, and Meson execution when the tool is installed. These are not claimed as shipped.

No release should be called enterprise 1.0-ready until those gates have real passing evidence.
