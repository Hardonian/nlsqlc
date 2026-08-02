# Tenant isolation

Register a tenant rule for every tenant-scoped table and configure a runtime tenant parameter name. The compiler injects a predicate for every resolved source. The model cannot supply or remove this predicate because it is emitted after source resolution. The caller remains responsible for binding the trusted tenant value to the parameter position reported by the manifest.
