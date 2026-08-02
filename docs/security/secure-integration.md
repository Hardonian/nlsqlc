# Secure integration

Treat model output as untrusted text. Call `nlsql_compile_ir` only after the model has returned the constrained IR form. Bind every manifest parameter through your database driver. Never concatenate the returned SQL with caller values. Treat schema and policy definitions as deployment configuration, review them, bound their sizes, and keep runtime tenant values outside the compiler.
