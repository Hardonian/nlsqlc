#ifndef NLSQL_H
#define NLSQL_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(_WIN32) && defined(NLSQL_BUILD_SHARED)
#define NLSQL_API __declspec(dllexport)
#elif defined(_WIN32)
#define NLSQL_API __declspec(dllimport)
#elif defined(__GNUC__) || defined(__clang__)
#define NLSQL_API __attribute__((visibility("default")))
#else
#define NLSQL_API
#endif

#define NLSQL_VERSION "0.1.2"
#define NLSQL_IR_VERSION 1u
#define NLSQL_ABI_VERSION 1u

typedef enum { NLSQL_OK=0, NLSQL_E_INVALID_ARGUMENT, NLSQL_E_OOM, NLSQL_E_LIMIT, NLSQL_E_PARSE, NLSQL_E_SCHEMA, NLSQL_E_POLICY, NLSQL_E_UNSUPPORTED, NLSQL_E_TYPE, NLSQL_E_DIALECT, NLSQL_E_INTERNAL } nlsql_status;
typedef enum { NLSQL_DIALECT_POSTGRES, NLSQL_DIALECT_SQLITE, NLSQL_DIALECT_DUCKDB, NLSQL_DIALECT_MYSQL, NLSQL_DIALECT_SQLSERVER } nlsql_dialect;
typedef enum { NLSQL_TYPE_UNKNOWN, NLSQL_TYPE_NULL, NLSQL_TYPE_BOOLEAN, NLSQL_TYPE_INT64, NLSQL_TYPE_UINT64, NLSQL_TYPE_DECIMAL, NLSQL_TYPE_FLOAT64, NLSQL_TYPE_TEXT, NLSQL_TYPE_BINARY, NLSQL_TYPE_UUID, NLSQL_TYPE_DATE, NLSQL_TYPE_TIMESTAMP, NLSQL_TYPE_TIMESTAMPTZ } nlsql_type;
typedef enum { NLSQL_TABLE_NONE=0, NLSQL_TABLE_TENANT_SCOPED=1u<<0, NLSQL_TABLE_VIEW=1u<<1 } nlsql_table_flags;
typedef enum { NLSQL_COLUMN_NONE=0, NLSQL_COLUMN_PRIMARY_KEY=1u<<0, NLSQL_COLUMN_NOT_NULL=1u<<1, NLSQL_COLUMN_TENANT_KEY=1u<<2, NLSQL_COLUMN_SENSITIVE=1u<<3 } nlsql_column_flags;
typedef enum { NLSQL_PARAM_USER, NLSQL_PARAM_POLICY, NLSQL_PARAM_TRUSTED } nlsql_param_source;
typedef enum { NLSQL_RISK_LOW, NLSQL_RISK_MODERATE, NLSQL_RISK_HIGH, NLSQL_RISK_DENIED } nlsql_risk;

typedef struct nlsql_context nlsql_context;
typedef struct nlsql_schema nlsql_schema;
typedef struct nlsql_schema_builder nlsql_schema_builder;
typedef struct nlsql_policy nlsql_policy;
typedef struct nlsql_compile_result nlsql_compile_result;

typedef struct { size_t max_ir_bytes, max_schema_objects, max_sql_bytes, max_nodes, max_joins, max_selected_fields, default_limit, max_limit; } nlsql_limits;
typedef struct { nlsql_limits limits; int diagnostic_errors; } nlsql_config;
typedef struct { const char *sql; size_t length; } nlsql_sql_view;
typedef struct { size_t position; const char *name; nlsql_type type; nlsql_param_source source; int runtime_required; } nlsql_param_view;
typedef struct { const char *question; const nlsql_schema *schema; const nlsql_policy *policy; nlsql_dialect dialect; } nlsql_question_request;
typedef struct { const char *ir; const nlsql_schema *schema; const nlsql_policy *policy; nlsql_dialect dialect; const char *trace_id; } nlsql_compile_request;
typedef struct { const char *cte_name; const char *cte_ir; const char *query_ir; const nlsql_schema *schema; const nlsql_policy *policy; nlsql_dialect dialect; } nlsql_cte_request;
typedef enum { NLSQL_SET_UNION, NLSQL_SET_UNION_ALL, NLSQL_SET_INTERSECT, NLSQL_SET_EXCEPT } nlsql_set_operator;
typedef struct { const char *left_ir; const char *right_ir; const nlsql_schema *schema; const nlsql_policy *policy; nlsql_dialect dialect; nlsql_set_operator operation; } nlsql_set_request;
typedef nlsql_status (*nlsql_infer_fn)(void *, const char *, size_t, char *, size_t, size_t *);

typedef struct { nlsql_infer_fn infer; void *user_data; } nlsql_inference;

NLSQL_API nlsql_status nlsql_build_inference_prompt(const nlsql_question_request *, char *, size_t, size_t *);
NLSQL_API nlsql_status nlsql_compile_inferred(nlsql_context *, const nlsql_question_request *, const nlsql_inference *, nlsql_compile_result **);

NLSQL_API nlsql_status nlsql_context_create(const nlsql_config *, nlsql_context **);
NLSQL_API void nlsql_context_destroy(nlsql_context *);
NLSQL_API const char *nlsql_status_name(nlsql_status);
NLSQL_API const char *nlsql_dialect_name(nlsql_dialect);
NLSQL_API unsigned nlsql_abi_version(void);

NLSQL_API nlsql_status nlsql_schema_builder_create(nlsql_context *, nlsql_schema_builder **);
NLSQL_API nlsql_status nlsql_schema_builder_add_table(nlsql_schema_builder *, const char *, const char *, unsigned);
NLSQL_API nlsql_status nlsql_schema_builder_add_column(nlsql_schema_builder *, const char *, const char *, const char *, nlsql_type, unsigned);
NLSQL_API nlsql_status nlsql_schema_builder_add_foreign_key(nlsql_schema_builder *, const char *, const char *, const char *, const char *, const char *, const char *);
NLSQL_API nlsql_status nlsql_schema_builder_finalize(nlsql_schema_builder *, nlsql_schema **);
NLSQL_API void nlsql_schema_builder_destroy(nlsql_schema_builder *);
NLSQL_API void nlsql_schema_destroy(nlsql_schema *);

NLSQL_API nlsql_status nlsql_policy_create(nlsql_context *, nlsql_policy **);
NLSQL_API nlsql_status nlsql_policy_allow_table(nlsql_policy *, const char *, const char *);
NLSQL_API nlsql_status nlsql_policy_deny_column(nlsql_policy *, const char *, const char *, const char *);
NLSQL_API nlsql_status nlsql_policy_require_tenant(nlsql_policy *, const char *, const char *, const char *);
NLSQL_API nlsql_status nlsql_policy_set_limits(nlsql_policy *, size_t, size_t);
NLSQL_API nlsql_status nlsql_policy_set_runtime_tenant(nlsql_policy *, const char *, nlsql_type);
NLSQL_API void nlsql_policy_destroy(nlsql_policy *);

NLSQL_API nlsql_status nlsql_compile_ir(nlsql_context *, const nlsql_compile_request *, nlsql_compile_result **);
NLSQL_API nlsql_status nlsql_compile_cte(nlsql_context *, const nlsql_cte_request *, nlsql_compile_result **);
NLSQL_API nlsql_status nlsql_compile_set(nlsql_context *, const nlsql_set_request *, nlsql_compile_result **);
NLSQL_API nlsql_status nlsql_compile_question(nlsql_context *, const nlsql_question_request *, nlsql_compile_result **);
NLSQL_API void nlsql_compile_result_destroy(nlsql_compile_result *);
NLSQL_API nlsql_sql_view nlsql_result_sql(const nlsql_compile_result *);
NLSQL_API const char *nlsql_result_canonical_ir(const nlsql_compile_result *);
NLSQL_API const char *nlsql_result_manifest(const nlsql_compile_result *);
NLSQL_API const char *nlsql_result_error(const nlsql_compile_result *);
NLSQL_API nlsql_status nlsql_result_status(const nlsql_compile_result *);
NLSQL_API size_t nlsql_result_param_count(const nlsql_compile_result *);
NLSQL_API nlsql_param_view nlsql_result_param(const nlsql_compile_result *, size_t);
NLSQL_API nlsql_risk nlsql_result_risk(const nlsql_compile_result *);
NLSQL_API unsigned nlsql_result_complexity(const nlsql_compile_result *);
NLSQL_API uint64_t nlsql_result_fingerprint(const nlsql_compile_result *);
NLSQL_API double nlsql_result_relevance_score(const nlsql_compile_result *);

#ifdef __cplusplus
}
#endif
#endif
