# Tenant Isolation & Deterministic Policy Enforcement Whitepaper

## Security Model

In AI-assisted and natural-language database query systems, large language models (LLMs) cannot be trusted to generate raw SQL. Malicious prompts or model hallucinations can lead to prompt injection, schema discovery attacks, and catastrophic multi-tenant data leaks.

`nlsqlc` enforces multi-tenant security at the compiler layer through the following formal guarantees:

### 1. Zero Raw SQL Ingestion
The compiler accepts only bounded Query IR S-expressions. SQL keywords, comments (`--`, `/* */`), and string escapes cannot be injected.

### 2. Strict Schema Whitelisting & Foreign Key Enforcement
Every identifier (table, alias, column) must resolve against a pre-authorized schema. Joins are only permitted if an explicit foreign key relationship exists in the trusted schema.

### 3. Invariant Tenant Predicate Injection
For any table marked `tenant` in the schema/policy:
- The compiler unconditionally injects `alias.tenant_key = $param` into the `WHERE` clause.
- Even if the input Query IR attempts to filter on a different tenant ID, the compiler binds the runtime-enforced tenant parameter.
- Cross-tenant data exfiltration is mathematically impossible under this constraint.

### 4. Fail-Closed Column Deny Lists
Columns flagged as sensitive (e.g. passwords, secrets, PII) in `.nlpolicy` cause immediate compilation failure (`NLSQL_E_POLICY`) if referenced anywhere in a query's select, where, join, or group-by clauses.
