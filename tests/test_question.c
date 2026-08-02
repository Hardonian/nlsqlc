#include "nlsql/nlsql.h"
#include <assert.h>
#include <string.h>

static nlsql_status infer_fixture(void *user_data, const char *prompt, size_t prompt_length, char *output, size_t output_capacity, size_t *output_length) {
    const char *ir = "(nlsql 1 (query (from orders t) (select (field (count (column t id)) count))))";
    (void)user_data;
    assert(prompt_length == strlen(prompt));
    assert(strstr(prompt, "Question:") != NULL);
    assert(strlen(ir) < output_capacity);
    memcpy(output, ir, strlen(ir));
    *output_length = strlen(ir);
    return NLSQL_OK;
}

static void setup(nlsql_context **ctx, nlsql_schema **schema, nlsql_policy **policy, nlsql_schema_builder **builder) {
    nlsql_config cfg = {0};
    assert(nlsql_context_create(&cfg, ctx) == NLSQL_OK);
    assert(nlsql_schema_builder_create(*ctx, builder) == NLSQL_OK);
    assert(nlsql_schema_builder_add_table(*builder, "public", "orders", NLSQL_TABLE_TENANT_SCOPED) == NLSQL_OK);
    assert(nlsql_schema_builder_add_column(*builder, "public", "orders", "id", NLSQL_TYPE_INT64, NLSQL_COLUMN_PRIMARY_KEY) == NLSQL_OK);
    assert(nlsql_schema_builder_add_column(*builder, "public", "orders", "total", NLSQL_TYPE_DECIMAL, 0u) == NLSQL_OK);
    assert(nlsql_schema_builder_add_column(*builder, "public", "orders", "region", NLSQL_TYPE_TEXT, 0u) == NLSQL_OK);
    assert(nlsql_schema_builder_add_column(*builder, "public", "orders", "created_at", NLSQL_TYPE_TIMESTAMP, 0u) == NLSQL_OK);
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
    assert(nlsql_result_fingerprint(result) != 0u);
    assert(nlsql_result_relevance_score(result) > 0.0 && nlsql_result_relevance_score(result) <= 1.0);
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
    {
        nlsql_question_request question = {"how many orders", schema, policy, NLSQL_DIALECT_POSTGRES};
        nlsql_inference inference = {infer_fixture, NULL};
        nlsql_compile_result *inferred = NULL;
        char prompt[256];
        size_t required = 0u;
        assert(nlsql_build_inference_prompt(&question, prompt, sizeof(prompt), &required) == NLSQL_OK);
        assert(required == strlen(prompt));
        assert(nlsql_compile_inferred(ctx, &question, &inference, &inferred) == NLSQL_OK);
        assert(inferred != NULL && nlsql_result_sql(inferred).length > 0u);
        nlsql_compile_result_destroy(inferred);
    }
    {
        const char *window_ir = "(nlsql 1 (query (from orders t) (select (field (window (sum (column t total)) (partition-by (column t region)) (order-by (column t created_at) desc)) running_total))))";
        nlsql_compile_request window_request = {window_ir, schema, policy, NLSQL_DIALECT_POSTGRES, NULL};
        nlsql_compile_result *window_result = NULL;
        assert(nlsql_compile_ir(ctx, &window_request, &window_result) == NLSQL_OK);
        assert(strstr(nlsql_result_sql(window_result).sql, " OVER (PARTITION BY") != NULL);
        nlsql_compile_result_destroy(window_result);
    }
    {
        const char *left_ir = "(nlsql 1 (query (from orders t) (select (field (column t id) id))))";
        const char *right_ir = "(nlsql 1 (query (from orders t) (select (field (column t id) id))))";
        nlsql_set_request set_request = {left_ir, right_ir, schema, policy, NLSQL_DIALECT_POSTGRES, NLSQL_SET_UNION_ALL};
        nlsql_compile_result *set_result = NULL;
        assert(nlsql_compile_set(ctx, &set_request, &set_result) == NLSQL_OK);
        assert(strstr(nlsql_result_sql(set_result).sql, " UNION ALL ") != NULL);
        assert(strstr(nlsql_result_sql(set_result).sql, "$1") != NULL);
        assert(strstr(nlsql_result_sql(set_result).sql, "$2") != NULL);
        assert(nlsql_result_param_count(set_result) == 2u);
        nlsql_compile_result_destroy(set_result);
    }
    bad.question = "drop orders"; bad.schema = schema; bad.policy = policy; bad.dialect = NLSQL_DIALECT_POSTGRES;
    assert(nlsql_compile_question(ctx, &bad, &result) == NLSQL_E_UNSUPPORTED);
    assert(result == NULL);
    nlsql_policy_destroy(policy);
    nlsql_schema_destroy(schema);
    nlsql_schema_builder_destroy(builder);
    nlsql_context_destroy(ctx);
    return 0;
}
