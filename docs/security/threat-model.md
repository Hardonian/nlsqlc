# Threat model

## Trust boundaries

The question and model output are untrusted. Schema, policy, semantic metadata, compiler configuration, and runtime tenant parameters are trusted caller inputs but must still be bounded. The compiler output is validated SQL text plus metadata; execution is outside the library.

| Threat | Preventive control | Detective control | Residual risk | Tests |
|---|---|---|---|---|
| Prompt injection / raw SQL | model output is parsed only as Query IR | parser rejects SQL-shaped atoms and unknown nodes | adapter prompt quality remains external | raw SQL negative fixtures |
| IR injection / identifier confusion | bounded parser and schema resolution | unknown identifiers fail | trusted schema mistakes | missing-column test |
| Cross-tenant access | deterministic policy predicate injection | manifest counts injected predicates | caller must bind runtime value correctly | tenant bypass regression |
| Policy bypass / alias shadowing | policies operate on resolved source tables | denied/unknown sources fail | future nested query work must preserve invariant | policy suite |
| Unsafe functions, files, network, catalogs | no function execution and allowlisted IR subset | unsupported node status | future features require per-dialect review | negative fixtures |
| Join explosion / resource exhaustion | max nodes, joins, bytes, SQL size, selected fields | deterministic limit errors | host scheduling is external | limit tests |
| Stack exhaustion / deep nesting | bounded node count; parser recursion is bounded by max nodes | parse failure | compiler stack depth should be hardened further | deep corpus |
| Integer overflow / buffer overflow | checked size addition, bounded buffers, length caps | failure-atomic result | compiler-specific UB audit remains | sanitizer builds |
| UAF / double-free / null dereference | ownership cleanup and null checks | ASan/UBSan | additional fuzz coverage needed | sanitizer suite |
| Sensitive logging | core emits no logs and no values in manifest | review output API | caller may log inputs | audit review |
| Unicode confusables | current identifier grammar is ASCII-only | non-ASCII rejected | schema importers need normalization rules | Unicode negatives |
| Cache poisoning | no cache in core 0.1; every compile parses IR | cache callbacks deferred | future cache must revalidate | roadmap gate |
| Hash collision abuse | structural hashing deferred in 0.1 | no cache lookup in core | future implementation risk | roadmap gate |
| Build compromise / artifact tampering | zero-dependency core, pinned CI planned | checksums and SBOM planned | signing not yet implemented | release gate |

## Security posture

The current implementation is deny-by-default for the supported IR subset and read-only by construction. It does not execute SQL, load extensions, invoke a shell, connect to a network, or accept credentials. It is not production-ready until the deferred nested-query policy work, fuzzing, sanitizer matrix, static analysis, and release-signing work are completed.
