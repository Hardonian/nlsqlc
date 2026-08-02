# Query IR v1

The model-facing language is a bounded, comment-free S-expression. There is exactly one top-level `(nlsql 1 ...)` form. Identifiers are ASCII `[A-Za-z_][A-Za-z0-9_.]*`; SQL text is not a valid IR form.

Implemented subset in 0.1: query, from, inner join, select/field, column, param, sum/avg/count/min/max, eq/gte/gt/lte/lt/neq/mul, where, and, group-by, order-by/ref, and limit.

All unrecognized nodes fail closed. The parser imposes byte, node, token, and nesting limits from the context configuration.
