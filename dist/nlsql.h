#ifndef NLSQL_H
#define NLSQL_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(_WIN32) && defined(NLSQL_BUILD_SHARED)
#define NLSQL_API __declspec(dllexport)
#define NLSQL_DEPRECATED(message) __declspec(deprecated(message))
#elif defined(_WIN32)
#define NLSQL_API __declspec(dllimport)
#define NLSQL_DEPRECATED(message) __declspec(deprecated(message))
#elif defined(__GNUC__) || defined(__clang__)
#define NLSQL_API __attribute__((visibility("default")))
#define NLSQL_DEPRECATED(message) __attribute__((deprecated(message)))
#else
#define NLSQL_API
#define NLSQL_DEPRECATED(message)
#endif

#define NLSQL_VERSION "0.1.2"
#define NLSQL_IR_VERSION 2u
#define NLSQL_ABI_VERSION 1u

typedef enum {
    NLSQL_OK = 0,
    NLSQL_E_INVALID_ARGUMENT,
    NLSQL_E_OOM,
    NLSQL_E_LIMIT,
    NLSQL_E_PARSE,
    NLSQL_E_SCHEMA,
    NLSQL_E_POLICY,
    NLSQL_E_UNSUPPORTED,
    NLSQL_E_TYPE,
    NLSQL_E_DIALECT,
    NLSQL_E_INTERNAL
} nlsql_status;

typedef enum {
    NLSQL_DIALECT_POSTGRES = 0,
    NLSQL_DIALECT_SQLITE = 1,
    NLSQL_DIALECT_DUCKDB = 2,
    NLSQL_DIALECT_MYSQL = 3,
    NLSQL_DIALECT_SQLSERVER = 4
} nlsql_dialect;

typedef enum {
    NLSQL_TYPE_UNKNOWN = 0,
    NLSQL_TYPE_NULL = 1,
    NLSQL_TYPE_BOOLEAN = 2,
    NLSQL_TYPE_INT64 = 3,
    NLSQL_TYPE_UINT64 = 4,
    NLSQL_TYPE_DECIMAL = 5,
    NLSQL_TYPE_FLOAT64 = 6,
    NLSQL_TYPE_TEXT = 7,
    NLSQL_TYPE_BINARY = 8,
    NLSQL_TYPE_UUID = 9,
    NLSQL_TYPE_DATE = 10,
    NLSQL_TYPE_TIMESTAMP = 11,
    NLSQL_TYPE_TIMESTAMPTZ = 12
} nlsql_type;

typedef enum {
    NLSQL_TABLE_NONE = 0,
    NLSQL_TABLE_TENANT_SCOPED = 1u << 0,
    NLSQL_TABLE_VIEW = 1u << 1
} nlsql_table_flags;

typedef enum {
    NLSQL_COLUMN_NONE = 0,
    NLSQL_COLUMN_PRIMARY_KEY = 1u << 0,
    NLSQL_COLUMN_NOT_NULL = 1u << 1,
    NLSQL_COLUMN_TENANT_KEY = 1u << 2,
    NLSQL_COLUMN_SENSITIVE = 1u << 3
} nlsql_column_flags;

typedef enum {
    NLSQL_PARAM_USER = 0,
    NLSQL_PARAM_POLICY = 1,
    NLSQL_PARAM_TRUSTED = 2
} nlsql_param_source;

typedef enum {
    NLSQL_RISK_LOW = 0,
    NLSQL_RISK_MODERATE = 1,
    NLSQL_RISK_HIGH = 2,
    NLSQL_RISK_DENIED = 3
} nlsql_risk;

typedef enum {
    NLSQL_JOIN_INNER = 0,
    NLSQL_JOIN_LEFT = 1,
    NLSQL_JOIN_RIGHT = 2,
    NLSQL_JOIN_FULL = 3
} nlsql_join_type;

typedef struct nlsql_context nlsql_context;
typedef struct nlsql_schema nlsql_schema;
typedef struct nlsql_schema_builder nlsql_schema_builder;
typedef struct nlsql_policy nlsql_policy;
typedef struct nlsql_compile_result nlsql_compile_result;

typedef struct {
    size_t max_ir_bytes;
    size_t max_schema_objects;
    size_t max_sql_bytes;
    size_t max_nodes;
    size_t max_joins;
    size_t max_selected_fields;
    size_t default_limit;
    size_t max_limit;
} nlsql_limits;

typedef struct {
    nlsql_limits limits;
    int diagnostic_errors;
} nlsql_config;

typedef struct {
    const char *sql;
    size_t length;
} nlsql_sql_view;

typedef struct {
    size_t position;
    const char *name;
    nlsql_type type;
    nlsql_param_source source;
    int runtime_required;
} nlsql_param_view;

typedef struct {
    size_t offset;
    size_t line;
    size_t column;
    nlsql_status status;
    const char *code;
    const char *message;
} nlsql_diagnostic_view;

typedef struct {
    const char *question;
    const nlsql_schema *schema;
    const nlsql_policy *policy;
    nlsql_dialect dialect;
} nlsql_question_request;

typedef struct {
    const char *ir;
    const nlsql_schema *schema;
    const nlsql_policy *policy;
    nlsql_dialect dialect;
    const char *trace_id;
} nlsql_compile_request;

typedef struct {
    const char *cte_name;
    const char *cte_ir;
    const char *query_ir;
    const nlsql_schema *schema;
    const nlsql_policy *policy;
    nlsql_dialect dialect;
} nlsql_cte_request;

typedef enum {
    NLSQL_SET_UNION = 0,
    NLSQL_SET_UNION_ALL = 1,
    NLSQL_SET_INTERSECT = 2,
    NLSQL_SET_EXCEPT = 3
} nlsql_set_operator;

typedef struct {
    const char *left_ir;
    const char *right_ir;
    const nlsql_schema *schema;
    const nlsql_policy *policy;
    nlsql_dialect dialect;
    nlsql_set_operator operation;
} nlsql_set_request;

typedef nlsql_status (*nlsql_infer_fn)(void *user_data, const char *prompt, size_t prompt_length, char *output, size_t output_capacity, size_t *output_length);

typedef struct {
    nlsql_infer_fn infer;
    void *user_data;
} nlsql_inference;

NLSQL_API nlsql_status nlsql_build_inference_prompt(const nlsql_question_request *request, char *output, size_t capacity, size_t *required);
NLSQL_API nlsql_status nlsql_compile_inferred(nlsql_context *ctx, const nlsql_question_request *request, const nlsql_inference *inference, nlsql_compile_result **out);

NLSQL_API nlsql_status nlsql_context_create(const nlsql_config *config, nlsql_context **out);
NLSQL_API void nlsql_context_destroy(nlsql_context *ctx);
NLSQL_API const char *nlsql_status_name(nlsql_status status);
NLSQL_API const char *nlsql_dialect_name(nlsql_dialect dialect);
NLSQL_API unsigned nlsql_abi_version(void);

NLSQL_API nlsql_status nlsql_schema_builder_create(nlsql_context *ctx, nlsql_schema_builder **out);
NLSQL_API nlsql_status nlsql_schema_builder_add_table(nlsql_schema_builder *builder, const char *schema, const char *table, unsigned flags);
NLSQL_API nlsql_status nlsql_schema_builder_add_column(nlsql_schema_builder *builder, const char *schema, const char *table, const char *column, nlsql_type type, unsigned flags);
NLSQL_API nlsql_status nlsql_schema_builder_add_foreign_key(nlsql_schema_builder *builder, const char *from_schema, const char *from_table, const char *from_column, const char *to_schema, const char *to_table, const char *to_column);
NLSQL_API nlsql_status nlsql_schema_builder_finalize(nlsql_schema_builder *builder, nlsql_schema **out);
NLSQL_API void nlsql_schema_builder_destroy(nlsql_schema_builder *builder);
NLSQL_API void nlsql_schema_destroy(nlsql_schema *schema);

NLSQL_API nlsql_status nlsql_policy_create(nlsql_context *ctx, nlsql_policy **out);
NLSQL_API nlsql_status nlsql_policy_allow_table(nlsql_policy *policy, const char *schema, const char *table);
NLSQL_API nlsql_status nlsql_policy_deny_column(nlsql_policy *policy, const char *schema, const char *table, const char *column);
NLSQL_API nlsql_status nlsql_policy_require_tenant(nlsql_policy *policy, const char *schema, const char *table, const char *column);
NLSQL_API nlsql_status nlsql_policy_require_tenant_typed(nlsql_policy *policy, const char *schema, const char *table, const char *column, nlsql_type type);
NLSQL_API nlsql_status nlsql_policy_set_limits(nlsql_policy *policy, size_t max_joins, size_t max_limit);
NLSQL_API nlsql_status nlsql_policy_set_runtime_tenant(nlsql_policy *policy, const char *name, nlsql_type type);
NLSQL_API void nlsql_policy_destroy(nlsql_policy *policy);

NLSQL_API nlsql_status nlsql_compile_ir(nlsql_context *ctx, const nlsql_compile_request *request, nlsql_compile_result **out);
NLSQL_API nlsql_status nlsql_compile_cte(nlsql_context *ctx, const nlsql_cte_request *request, nlsql_compile_result **out);
NLSQL_API nlsql_status nlsql_compile_set(nlsql_context *ctx, const nlsql_set_request *request, nlsql_compile_result **out);
NLSQL_API nlsql_status nlsql_compile_question(nlsql_context *ctx, const nlsql_question_request *request, nlsql_compile_result **out);
NLSQL_API void nlsql_compile_result_destroy(nlsql_compile_result *result);
NLSQL_API nlsql_sql_view nlsql_result_sql(const nlsql_compile_result *result);
NLSQL_API const char *nlsql_result_canonical_ir(const nlsql_compile_result *result);
NLSQL_API const char *nlsql_result_manifest(const nlsql_compile_result *result);
NLSQL_API const char *nlsql_result_error(const nlsql_compile_result *result);
NLSQL_API nlsql_status nlsql_result_status(const nlsql_compile_result *result);
NLSQL_API size_t nlsql_result_param_count(const nlsql_compile_result *result);
NLSQL_API nlsql_param_view nlsql_result_param(const nlsql_compile_result *result, size_t index);
NLSQL_API nlsql_risk nlsql_result_risk(const nlsql_compile_result *result);
NLSQL_API unsigned nlsql_result_complexity(const nlsql_compile_result *result);
NLSQL_API uint64_t nlsql_result_fingerprint(const nlsql_compile_result *result);
NLSQL_API double nlsql_result_relevance_score(const nlsql_compile_result *result);
NLSQL_API size_t nlsql_result_diagnostic_count(const nlsql_compile_result *result);
NLSQL_API nlsql_diagnostic_view nlsql_result_diagnostic(const nlsql_compile_result *result, size_t index);

#ifdef __cplusplus
}
#endif
#endif
