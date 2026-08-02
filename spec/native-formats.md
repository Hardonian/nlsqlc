# Native trusted configuration formats

`.nlschema` is line-oriented and intentionally not JSON/YAML:

```text
nlschema 1
table public orders tenant
column public orders.id int64
column public orders.tenant_id uuid
fk public orders.customer_id public customers.id
```

Supported records: `table schema name [tenant]`, `column schema table.column type`, and `fk schema table.column target_schema target_table.column`. Tables must precede columns; referenced columns must exist before an FK.

`.nlpolicy` records are:

```text
nlpolicy 1
allow_table public orders
deny_column public customers.email
tenant public orders tenant_id uuid
runtime_tenant tenant_id uuid
limit 5 500
```

These are trusted deployment configuration files. Model-generated IR must not use comments or these formats.
