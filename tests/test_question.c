#include "nlsql/nlsql.h"
#include <assert.h>
#include <string.h>

static void setup(nlsql_context **ctx, nlsql_schema **schema, nlsql_policy **policy, nlsql_schema_builder **builder) {
    nlsql_config cfg = {0};
    assert(nlsql_context_create(&cfg, ctx) == NLSQL_OK);
    assert(nlsql_schema_builder_create(*ctx, builder) == NLSQL_OK);
    assert(nlsql_schema_builder_add_table(*builder, "public", "orders", NLSQL_TABLE_TENANT_SCOPED) == NLSQL_OK);
    assert(nlsql_schema_builder_add_column(*builder, "public", "orders", "id", NLSQL_TYPE_INT64, NLSQL_COLUMN_PRIMARY_KEY) == NLSQL_OK);
    assert(nlsql_schema_builder_add_column(*builder, "public", "orders", "total", NLSQL_TYPE_DECIMAL, 0u) == NLSQL_OK);
    assert(nlsql_schema_builder_add_column(*builder, "public", "orders", "tenant_id", NLSQL_TYPE_UUID, NLSQL_COLUMN_TENANT_KEY) == NLSQL_OK);
    assert(nlsql_schema_builder_finalize(*builder, schema) == NLSQL_OK);
    assert(nlsql_policy_create(*ctx, policy) == NLSQL_OK);
    assert(nlsql_policy_allow_table(*policy, "public", "orders") == NLSQL_OK);
    assert(nlsql_policy_require_tenant(*policy, "public", "orders", "tenant_id") == NLSQL_OK);
    assert(nlsql_policy_set_runtime_tenant(*policy, "tenant_id", NLSQL_TYPE_UUID) == NLSQL_OK);
}

static void check_question(const char *question, const char *needle, nlsql_context *ctx, nlsql_schema *schema, nlsql_policy *policy) {
    nlsql_question_request request = {question, schema, policy, NLSQL_DIALECT_POSTGRES};
    nlsql_compile_result *result = NULL;
    nlsql_status status = nlsql_compile_question(ctx, &request, &result);
    assert(status == NLSQL_OK);
    assert(result != NULL);
    assert(strstr(nlsql_result_sql(result).sql, needle) != NULL);
    assert(nlsql_result_param_count(result) == 1u);
    nlsql_compile_result_destroy(result);
}

int main(void) {
    nlsql_context *ctx = NULL;
    nlsql_schema *schema = NULL;
    nlsql_policy *policy = NULL;
    nlsql_schema_builder *builder = NULL;
    nlsql_question_request bad;
    nlsql_compile_result *result = NULL;
    setup(&ctx, &schema, &policy, &builder);
    check_question("count orders", "count(\"t\".\"id\")", ctx, schema, policy);
    check_question("list orders total", "\"t\".\"total\"", ctx, schema, policy);
    check_question("sum orders total", "sum(\"t\".\"total\")", ctx, schema, policy);
    check_question("average orders total", "avg(\"t\".\"total\")", ctx, schema, policy);
    bad.question = "drop orders"; bad.schema = schema; bad.policy = policy; bad.dialect = NLSQL_DIALECT_POSTGRES;
    assert(nlsql_compile_question(ctx, &bad, &result) == NLSQL_E_UNSUPPORTED);
    assert(result == NULL);
    nlsql_policy_destroy(policy);
    nlsql_schema_destroy(schema);
    nlsql_schema_builder_destroy(builder);
    nlsql_context_destroy(ctx);
    return 0;
}
