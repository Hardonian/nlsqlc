#include "nlsql/nlsql.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdint.h>

static char *read_file(const char *path) {
    FILE *f; long n; char *out;
    f = fopen(path, "rb"); if (!f) return NULL;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
    n = ftell(f); if (n < 0 || (unsigned long)n >= (unsigned long)SIZE_MAX || fseek(f, 0, SEEK_SET) != 0) { fclose(f); return NULL; }
    out = (char *)calloc(1, (size_t)n + 1u);
    if (out && fread(out, 1u, (size_t)n, f) != (size_t)n) { free(out); out = NULL; }
    fclose(f); return out;
}

static nlsql_type parse_type(const char *s) {
    if (!s) return NLSQL_TYPE_UNKNOWN;
    if (strcmp(s, "boolean") == 0) return NLSQL_TYPE_BOOLEAN;
    if (strcmp(s, "int64") == 0) return NLSQL_TYPE_INT64;
    if (strcmp(s, "uint64") == 0) return NLSQL_TYPE_UINT64;
    if (strcmp(s, "decimal") == 0) return NLSQL_TYPE_DECIMAL;
    if (strcmp(s, "float64") == 0) return NLSQL_TYPE_FLOAT64;
    if (strcmp(s, "text") == 0) return NLSQL_TYPE_TEXT;
    if (strcmp(s, "binary") == 0) return NLSQL_TYPE_BINARY;
    if (strcmp(s, "uuid") == 0) return NLSQL_TYPE_UUID;
    if (strcmp(s, "date") == 0) return NLSQL_TYPE_DATE;
    if (strcmp(s, "timestamp") == 0) return NLSQL_TYPE_TIMESTAMP;
    if (strcmp(s, "timestamptz") == 0) return NLSQL_TYPE_TIMESTAMPTZ;
    return NLSQL_TYPE_UNKNOWN;
}

static nlsql_dialect parse_dialect(const char *s) {
    if (!s || strcmp(s, "postgres") == 0) return NLSQL_DIALECT_POSTGRES;
    if (strcmp(s, "sqlite") == 0) return NLSQL_DIALECT_SQLITE;
    if (strcmp(s, "duckdb") == 0) return NLSQL_DIALECT_DUCKDB;
    if (strcmp(s, "mysql") == 0) return NLSQL_DIALECT_MYSQL;
    if (strcmp(s, "sqlserver") == 0) return NLSQL_DIALECT_SQLSERVER;
    return (nlsql_dialect)-1;
}

static char *trim_leading(char *line) {
    while (*line != '\0' && isspace((unsigned char)*line)) ++line;
    return line;
}

static int line_word_count(const char *line, size_t minimum, size_t maximum) {
    const unsigned char *p = (const unsigned char *)line;
    size_t count = 0u;
    while (*p != '\0') {
        while (*p != '\0' && isspace(*p)) ++p;
        if (*p == '\0') break;
        ++count;
        while (*p != '\0' && !isspace(*p)) ++p;
    }
    return count >= minimum && count <= maximum;
}

static void usage(void) {
    puts("nlsqlc " NLSQL_VERSION "\n"
         "usage: nlsqlc compile --ir FILE [--schema FILE] [--policy FILE] [--dialect DIALECT] [--json]\n"
         "       nlsqlc validate-ir --ir FILE [--schema FILE] [--policy FILE]\n"
         "       nlsqlc explain --ir FILE [--schema FILE] [--policy FILE] [--dialect DIALECT]\n"
         "       nlsqlc fmt --ir FILE\n"
         "       nlsqlc version\n       nlsqlc grammar\n"
         "formats: .nlschema and .nlpolicy are trusted line-oriented config files");
}

static nlsql_status load_schema(nlsql_context *ctx, const char *path, nlsql_schema **out, nlsql_schema_builder **builder_out) {
    nlsql_schema_builder *b = NULL; char *text = NULL; char *line; nlsql_status st;
    if (nlsql_schema_builder_create(ctx, &b) != NLSQL_OK) return NLSQL_E_OOM;
    if (!path) {
        st = nlsql_schema_builder_add_table(b, "public", "orders", NLSQL_TABLE_TENANT_SCOPED);
        if (st == NLSQL_OK) st = nlsql_schema_builder_add_column(b, "public", "orders", "tenant_id", NLSQL_TYPE_UUID, NLSQL_COLUMN_TENANT_KEY);
        if (st == NLSQL_OK) st = nlsql_schema_builder_add_column(b, "public", "orders", "id", NLSQL_TYPE_INT64, NLSQL_COLUMN_PRIMARY_KEY);
    } else {
        text = read_file(path); if (!text) { nlsql_schema_builder_destroy(b); return NLSQL_E_INVALID_ARGUMENT; }
        line = strtok(text, "\r\n"); st = NLSQL_OK;
        while (line && st == NLSQL_OK) {
            line = trim_leading(line);
            char kind[16] = {0}, a[128] = {0}, bname[128] = {0}, c[128] = {0}, d[128] = {0};
            if (line[0] != '#' && sscanf(line, "%15s", kind) == 1) {
                if (strcmp(kind, "nlschema") == 0 && line_word_count(line, 2u, 2u)) { /* header */ }
                else if (strcmp(kind, "table") == 0 && line_word_count(line, 3u, 4u) && sscanf(line, "%15s %127s %127s %127s", kind, a, bname, c) >= 3)
                    st = nlsql_schema_builder_add_table(b, a, bname, (strcmp(c, "tenant") == 0) ? NLSQL_TABLE_TENANT_SCOPED : 0u);
                else if (strcmp(kind, "column") == 0 && line_word_count(line, 4u, 5u)) {
                    int ncol; char *dot; unsigned flags = 0u; d[0] = 0; ncol = sscanf(line, "%15s %127s %127s %127s %127s", kind, a, bname, c, d);
                    if (ncol < 4) st = NLSQL_E_SCHEMA; else { dot = strchr(bname, '.'); if (strstr(d, "pk")) flags |= NLSQL_COLUMN_PRIMARY_KEY; if (strstr(d, "not_null")) flags |= NLSQL_COLUMN_NOT_NULL; if (strstr(d, "tenant_key")) flags |= NLSQL_COLUMN_TENANT_KEY; if (parse_type(c) == NLSQL_TYPE_UNKNOWN) st = NLSQL_E_SCHEMA; else if (!dot) st = NLSQL_E_SCHEMA; else { *dot = 0; st = nlsql_schema_builder_add_column(b, a, bname, dot + 1, parse_type(c), flags); } }
                } else if (strcmp(kind, "fk") == 0 && line_word_count(line, 5u, 5u) && sscanf(line, "%15s %127s %127s %127s %127s", kind, a, bname, c, d) == 5) {
                    char *dot = strchr(bname, '.'); char *rdot = strchr(d, '.');
                    if (!dot || !rdot) st = NLSQL_E_SCHEMA; else { *dot = 0; *rdot = 0; st = nlsql_schema_builder_add_foreign_key(b, a, bname, dot + 1, c, d, rdot + 1); }
                } else st = NLSQL_E_PARSE;
            }
            line = strtok(NULL, "\r\n");
        }
    }
    free(text);
    if (st != NLSQL_OK) { nlsql_schema_builder_destroy(b); return st; }
    st = nlsql_schema_builder_finalize(b, out); if (st != NLSQL_OK) { nlsql_schema_builder_destroy(b); return st; }
    *builder_out = b; return NLSQL_OK;
}

static nlsql_status load_policy(nlsql_context *ctx, const char *path, nlsql_policy **out) {
    nlsql_policy *p = NULL; char *text = NULL; char *line; nlsql_status st;
    if (nlsql_policy_create(ctx, &p) != NLSQL_OK) return NLSQL_E_OOM;
    if (!path) { st = nlsql_policy_require_tenant(p, "public", "orders", "tenant_id"); }
    else {
        text = read_file(path); if (!text) { nlsql_policy_destroy(p); return NLSQL_E_INVALID_ARGUMENT; }
        line = strtok(text, "\r\n"); st = NLSQL_OK;
        while (line && st == NLSQL_OK) {
            line = trim_leading(line);
            char kind[24] = {0}, a[128] = {0}, b[128] = {0}, c[128] = {0}, d[128] = {0}; size_t joins, limit;
            if (line[0] != '#' && sscanf(line, "%23s", kind) == 1) {
                if (strcmp(kind, "nlpolicy") == 0 && line_word_count(line, 2u, 2u)) { }
                else if (strcmp(kind, "allow_table") == 0 && line_word_count(line, 3u, 3u) && sscanf(line, "%23s %127s %127s", kind, a, b) == 3) st = nlsql_policy_allow_table(p, a, b);
                else if (strcmp(kind, "deny_column") == 0 && line_word_count(line, 4u, 4u) && sscanf(line, "%23s %127s %127s %127s", kind, a, b, c) == 4) st = nlsql_policy_deny_column(p, a, b, c);
                else if (strcmp(kind, "tenant") == 0 && line_word_count(line, 5u, 5u) && sscanf(line, "%23s %127s %127s %127s %127s", kind, a, b, c, d) == 5) { nlsql_type tenant_type = parse_type(d); st = tenant_type == NLSQL_TYPE_UNKNOWN ? NLSQL_E_TYPE : nlsql_policy_require_tenant_typed(p, a, b, c, tenant_type); }
                else if (strcmp(kind, "limit") == 0 && line_word_count(line, 3u, 3u) && sscanf(line, "%23s %zu %zu", kind, &joins, &limit) == 3) st = nlsql_policy_set_limits(p, joins, limit);
                else if (strcmp(kind, "runtime_tenant") == 0 && line_word_count(line, 3u, 3u) && sscanf(line, "%23s %127s %127s", kind, a, b) == 3) st = nlsql_policy_set_runtime_tenant(p, a, parse_type(b));
                else st = NLSQL_E_PARSE;
            }
            line = strtok(NULL, "\r\n");
        }
    }
    free(text); if (st != NLSQL_OK) { nlsql_policy_destroy(p); return st; } *out = p; return NLSQL_OK;
}

int main(int argc, char **argv) {
    nlsql_context *ctx = NULL; nlsql_schema_builder *builder = NULL; nlsql_schema *schema = NULL; nlsql_policy *policy = NULL; nlsql_compile_result *result = NULL;
    nlsql_config cfg = {0}; nlsql_compile_request request = {0}; char *ir = NULL; const char *ir_path = NULL, *schema_path = NULL, *policy_path = NULL; nlsql_status st = NLSQL_OK; int i, json_output = 0; const char *command;
    if (argc < 2 || strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0) { usage(); return argc < 2 ? 2 : 0; }
    command = argv[1]; if (strcmp(command, "version") == 0) { puts(NLSQL_VERSION); return 0; }
    if (strcmp(command, "grammar") == 0) { puts("(nlsql 2 (query (from IDENT [IDENT]) [join ...] (select (field EXPR IDENT) ...) ...))"); return 0; }
    if (strcmp(command, "compile") != 0 && strcmp(command, "validate-ir") != 0 && strcmp(command, "fmt") != 0 && strcmp(command, "explain") != 0) { fprintf(stderr, "unknown command: %s\n", command); return 2; }
    for (i = 2; i < argc; i++) {
        if (strcmp(argv[i], "--ir") == 0 && i + 1 < argc) ir_path = argv[++i];
        else if (strcmp(argv[i], "--schema") == 0 && i + 1 < argc) schema_path = argv[++i];
        else if (strcmp(argv[i], "--policy") == 0 && i + 1 < argc) policy_path = argv[++i];
        else if (strcmp(argv[i], "--json") == 0) json_output = 1;
        else if (strcmp(argv[i], "--dialect") == 0 && i + 1 < argc) { request.dialect = parse_dialect(argv[++i]); if ((int)request.dialect < 0) return 2; }
        else { fprintf(stderr, "unknown argument: %s\n", argv[i]); return 2; }
    }
    if (!ir_path || !(ir = read_file(ir_path))) { fputs("cannot read --ir file\n", stderr); return 2; }
    if (request.dialect == (nlsql_dialect)0) request.dialect = NLSQL_DIALECT_POSTGRES;
    st = nlsql_context_create(&cfg, &ctx); if (st == NLSQL_OK) st = load_schema(ctx, schema_path, &schema, &builder); if (st == NLSQL_OK) st = load_policy(ctx, policy_path, &policy);
    request.ir = ir; request.schema = schema; request.policy = policy;
    if (st == NLSQL_OK) st = nlsql_compile_ir(ctx, &request, &result);
    if (st == NLSQL_OK) {
        if (strcmp(command, "validate-ir") == 0) {
            puts("VALID");
        } else if (strcmp(command, "fmt") == 0) {
            puts(nlsql_result_canonical_ir(result));
        } else if (strcmp(command, "explain") == 0) {
            printf("┌── [Execution Plan & Policy Audit]\n");
            printf("│  ├── Status: VALID (Dialect: %s)\n", nlsql_dialect_name(request.dialect));
            printf("│  ├── Complexity: %u | Risk: %s\n", nlsql_result_complexity(result), nlsql_result_risk(result) == NLSQL_RISK_LOW ? "LOW" : "MODERATE");
            printf("│  ├── Fingerprint: %llu\n", (unsigned long long)nlsql_result_fingerprint(result));
            printf("│  └── Emitted SQL:\n│      %s\n└──\n", nlsql_result_sql(result).sql);
        } else if (json_output) {
            printf("{\"status\":\"OK\",\"dialect\":\"%s\",\"sql\":\"%s\",\"complexity\":%u,\"risk\":\"%s\"}\n",
                   nlsql_dialect_name(request.dialect), nlsql_result_sql(result).sql, nlsql_result_complexity(result),
                   nlsql_result_risk(result) == NLSQL_RISK_LOW ? "LOW" : "MODERATE");
        } else {
            puts(nlsql_result_sql(result).sql);
            puts("-- manifest --");
            fputs(nlsql_result_manifest(result), stdout);
        }
    } else {
        fprintf(stderr, "%s: %s\n", nlsql_status_name(st), result ? nlsql_result_error(result) : "setup failure");
    }
    nlsql_compile_result_destroy(result); nlsql_policy_destroy(policy); nlsql_schema_destroy(schema); nlsql_schema_builder_destroy(builder); nlsql_context_destroy(ctx); free(ir); return st == NLSQL_OK ? 0 : 1;
}