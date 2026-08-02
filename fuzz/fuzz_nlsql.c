#include "nlsql/nlsql.h"
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

int LLVMFuzzerTestOneInput(const unsigned char *data, size_t size);

static void fixture(nlsql_context **ctx, nlsql_schema **schema, nlsql_policy **policy, nlsql_schema_builder **builder) {
    nlsql_config cfg = {0};
    if (nlsql_context_create(&cfg, ctx) != NLSQL_OK ||
        nlsql_schema_builder_create(*ctx, builder) != NLSQL_OK ||
        nlsql_schema_builder_add_table(*builder, "public", "orders", NLSQL_TABLE_TENANT_SCOPED) != NLSQL_OK ||
        nlsql_schema_builder_add_column(*builder, "public", "orders", "id", NLSQL_TYPE_INT64, NLSQL_COLUMN_PRIMARY_KEY) != NLSQL_OK ||
        nlsql_schema_builder_add_column(*builder, "public", "orders", "tenant_id", NLSQL_TYPE_UUID, NLSQL_COLUMN_TENANT_KEY) != NLSQL_OK ||
        nlsql_schema_builder_finalize(*builder, schema) != NLSQL_OK ||
        nlsql_policy_create(*ctx, policy) != NLSQL_OK ||
        nlsql_policy_allow_table(*policy, "public", "orders") != NLSQL_OK ||
        nlsql_policy_require_tenant(*policy, "public", "orders", "tenant_id") != NLSQL_OK ||
        nlsql_policy_set_runtime_tenant(*policy, "tenant_id", NLSQL_TYPE_UUID) != NLSQL_OK) {
        abort();
    }
}

int LLVMFuzzerTestOneInput(const unsigned char *data, size_t size) {
    nlsql_context *ctx = NULL;
    nlsql_schema *schema = NULL;
    nlsql_schema_builder *builder = NULL;
    nlsql_policy *policy = NULL;
    nlsql_compile_result *result = NULL;
    nlsql_compile_request request;
    char *ir;
    if (size > 65535u) return 0;
    ir = (char *)calloc(1u, size + 1u);
    if (!ir) return 0;
    memcpy(ir, data, size);
    fixture(&ctx, &schema, &policy, &builder);
    request.ir = ir;
    request.schema = schema;
    request.policy = policy;
    request.dialect = NLSQL_DIALECT_POSTGRES;
    request.trace_id = NULL;
    (void)nlsql_compile_ir(ctx, &request, &result);
    nlsql_compile_result_destroy(result);
    nlsql_policy_destroy(policy);
    nlsql_schema_destroy(schema);
    nlsql_schema_builder_destroy(builder);
    nlsql_context_destroy(ctx);
    free(ir);
    return 0;
}
