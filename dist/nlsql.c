#include "nlsql.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <limits.h>

#define NLSQL_MAX_TABLES 256u
#define NLSQL_MAX_COLS 2048u
#define NLSQL_MAX_FKS 2048u
#define NLSQL_MAX_RULES 256u
#define NLSQL_MAX_PARAMS 128u
#define NLSQL_MAX_CHILDREN 64u
#define NLSQL_NAME 128u

typedef struct {
    char schema[NLSQL_NAME];
    char name[NLSQL_NAME];
    unsigned flags;
} table_t;

typedef struct {
    char schema[NLSQL_NAME];
    char table[NLSQL_NAME];
    char name[NLSQL_NAME];
    nlsql_type type;
    unsigned flags;
} col_t;

typedef struct {
    char fs[NLSQL_NAME];
    char ft[NLSQL_NAME];
    char fc[NLSQL_NAME];
    char ts[NLSQL_NAME];
    char tt[NLSQL_NAME];
    char tc[NLSQL_NAME];
} fk_t;

typedef struct {
    char schema[NLSQL_NAME];
    char table[NLSQL_NAME];
} allow_t;

typedef struct {
    char schema[NLSQL_NAME];
    char table[NLSQL_NAME];
    char col[NLSQL_NAME];
} deny_t;

typedef struct {
    char schema[NLSQL_NAME];
    char table[NLSQL_NAME];
    char col[NLSQL_NAME];
    nlsql_type type;
} tenant_t;

typedef struct {
    char name[NLSQL_NAME];
    nlsql_type type;
    nlsql_param_source source;
} param_t;

struct nlsql_context {
    nlsql_config cfg;
};

struct nlsql_schema {
    nlsql_context *ctx;
    size_t nt;
    size_t nc;
    size_t nf;
    table_t tables[NLSQL_MAX_TABLES];
    col_t cols[NLSQL_MAX_COLS];
    fk_t fks[NLSQL_MAX_FKS];
};

struct nlsql_schema_builder {
    nlsql_context *ctx;
    nlsql_schema *schema;
};

struct nlsql_policy {
    nlsql_context *ctx;
    size_t na;
    size_t nd;
    size_t ntenant;
    allow_t allow[NLSQL_MAX_RULES];
    deny_t deny[NLSQL_MAX_RULES];
    tenant_t tenant[NLSQL_MAX_RULES];
    size_t max_limit;
    size_t max_joins;
    char runtime_name[NLSQL_NAME];
    nlsql_type runtime_type;
};

struct nlsql_compile_result {
    nlsql_status status;
    char *sql;
    char *ir;
    char *manifest;
    char *error;
    size_t sql_len;
    size_t nparams;
    param_t params[NLSQL_MAX_PARAMS];
    nlsql_risk risk;
    unsigned complexity;
    nlsql_diagnostic_view diagnostic;
    char diagnostic_code[48];
    char diagnostic_message[512];
    int has_diagnostic;
};

typedef struct node node_t;
struct node {
    char *atom;
    size_t off;
    node_t *child[NLSQL_MAX_CHILDREN];
    size_t nchild;
};

typedef struct {
    const char *s;
    size_t n;
    size_t p;
    size_t nodes;
    nlsql_context *ctx;
} parser_t;

typedef struct {
    char schema[NLSQL_NAME];
    char table[NLSQL_NAME];
    char alias[NLSQL_NAME];
} source_t;

typedef struct {
    char *s;
    size_t n;
    size_t cap;
    nlsql_context *ctx;
} buf_t;

const char *nlsql_status_name(nlsql_status);
static void cp(char *d, size_t cap, const char *s) {
    size_t n = s ? strlen(s) : 0u;
    if (n >= cap) n = cap - 1u;
    if (cap) {
        if (n > 0) memcpy(d, s, n);
        d[n] = 0;
    }
}

static void diagnostic_set(nlsql_compile_result *r, nlsql_status status, const char *code, const char *message, size_t offset) {
    size_t i, line = 1u, column = 1u;
    if (!r) return;
    for (i = 0u; i < offset && r->ir && r->ir[i]; i++) {
        if (r->ir[i] == '\n') {
            line++;
            column = 1u;
        } else {
            column++;
        }
    }
    r->diagnostic.offset = offset;
    r->diagnostic.line = line;
    r->diagnostic.column = column;
    r->diagnostic.status = status;
    cp(r->diagnostic_code, sizeof(r->diagnostic_code), code ? code : nlsql_status_name(status));
    cp(r->diagnostic_message, sizeof(r->diagnostic_message), message ? message : nlsql_status_name(status));
    r->diagnostic.code = r->diagnostic_code;
    r->diagnostic.message = r->diagnostic_message;
    r->has_diagnostic = 1;
}

static int eqs(const char *a, const char *b) {
    return a && b && strcmp(a, b) == 0;
}

static int ident(const char *s) {
    size_t i, n;
    if (!s || !*s) return 0;
    n = strlen(s);
    if (n >= NLSQL_NAME || !(isalpha((unsigned char)s[0]) || isdigit((unsigned char)s[0]) || s[0] == '_')) return 0;
    for (i = 1; i < n; i++) {
        if (!(isalnum((unsigned char)s[i]) || s[i] == '_')) return 0;
    }
    return 1;
}

static int add_size(size_t a, size_t b, size_t *o) {
    if (b > SIZE_MAX - a) return 0;
    *o = a + b;
    return 1;
}

static int buf_init(buf_t *b, nlsql_context *c) {
    b->cap = 256;
    b->n = 0;
    b->ctx = c;
    b->s = (char *)calloc(1, b->cap);
    return b->s != NULL;
}

static int buf_need(buf_t *b, size_t add) {
    size_t need, cap;
    char *p;
    if (!add_size(b->n, add, &need) || !add_size(need, 1, &need) || (b->ctx && need > b->ctx->cfg.limits.max_sql_bytes)) return 0;
    if (need <= b->cap) return 1;
    cap = b->cap;
    while (cap < need) {
        if (cap > SIZE_MAX / 2) return 0;
        cap *= 2;
    }
    p = (char *)realloc(b->s, cap);
    if (!p) return 0;
    b->s = p;
    b->cap = cap;
    return 1;
}

static int buf_put(buf_t *b, const char *s) {
    size_t n = strlen(s);
    if (!buf_need(b, n)) return 0;
    memcpy(b->s + b->n, s, n);
    b->n += n;
    b->s[b->n] = 0;
    return 1;
}

static int buf_ch(buf_t *b, char c) {
    if (!buf_need(b, 1)) return 0;
    b->s[b->n++] = c;
    b->s[b->n] = 0;
    return 1;
}

static int buf_ident(buf_t *b, const char *s, nlsql_dialect d) {
    const char *q = (d == NLSQL_DIALECT_MYSQL) ? "`" : (d == NLSQL_DIALECT_SQLSERVER ? "[" : "\"");
    const char *r = (d == NLSQL_DIALECT_SQLSERVER ? "]" : q);
    size_t i;
    if (!ident(s) || !buf_put(b, q)) return 0;
    for (i = 0; s[i]; i++) {
        if (s[i] == '.') {
            if (!buf_put(b, r) || !buf_ch(b, '.') || !buf_put(b, q)) return 0;
        } else if (s[i] == q[0] || s[i] == ']') {
            if (!buf_ch(b, s[i]) || !buf_ch(b, s[i])) return 0;
        } else if (!buf_ch(b, s[i])) return 0;
    }
    return buf_put(b, r);
}

const char *nlsql_status_name(nlsql_status s) {
    switch (s) {
        case NLSQL_OK: return "OK";
        case NLSQL_E_INVALID_ARGUMENT: return "INVALID_ARGUMENT";
        case NLSQL_E_OOM: return "OOM";
        case NLSQL_E_LIMIT: return "LIMIT";
        case NLSQL_E_PARSE: return "PARSE";
        case NLSQL_E_SCHEMA: return "SCHEMA";
        case NLSQL_E_POLICY: return "POLICY";
        case NLSQL_E_UNSUPPORTED: return "UNSUPPORTED";
        case NLSQL_E_TYPE: return "TYPE";
        case NLSQL_E_DIALECT: return "DIALECT";
        default: return "INTERNAL";
    }
}

const char *nlsql_dialect_name(nlsql_dialect d) {
    switch (d) {
        case NLSQL_DIALECT_POSTGRES: return "postgres";
        case NLSQL_DIALECT_SQLITE: return "sqlite";
        case NLSQL_DIALECT_DUCKDB: return "duckdb";
        case NLSQL_DIALECT_MYSQL: return "mysql";
        case NLSQL_DIALECT_SQLSERVER: return "sqlserver";
        default: return "unknown";
    }
}

unsigned nlsql_abi_version(void) {
    return NLSQL_ABI_VERSION;
}

nlsql_status nlsql_context_create(const nlsql_config *in, nlsql_context **out) {
    nlsql_context *c;
    if (!out) return NLSQL_E_INVALID_ARGUMENT;
    c = (nlsql_context *)calloc(1, sizeof(*c));
    if (!c) return NLSQL_E_OOM;
    c->cfg.limits.max_ir_bytes = in && in->limits.max_ir_bytes ? in->limits.max_ir_bytes : 65536u;
    c->cfg.limits.max_schema_objects = in && in->limits.max_schema_objects ? in->limits.max_schema_objects : 4096u;
    c->cfg.limits.max_sql_bytes = in && in->limits.max_sql_bytes ? in->limits.max_sql_bytes : 1048576u;
    c->cfg.limits.max_nodes = in && in->limits.max_nodes ? in->limits.max_nodes : 4096u;
    c->cfg.limits.max_joins = in && in->limits.max_joins ? in->limits.max_joins : 16u;
    c->cfg.limits.max_selected_fields = in && in->limits.max_selected_fields ? in->limits.max_selected_fields : 64u;
    c->cfg.limits.default_limit = in && in->limits.default_limit ? in->limits.default_limit : 100u;
    c->cfg.limits.max_limit = in && in->limits.max_limit ? in->limits.max_limit : 1000u;
    if (c->cfg.limits.default_limit > c->cfg.limits.max_limit) c->cfg.limits.default_limit = c->cfg.limits.max_limit;
    c->cfg.diagnostic_errors = in ? in->diagnostic_errors : 0;
    *out = c;
    return NLSQL_OK;
}

void nlsql_context_destroy(nlsql_context *c) {
    free(c);
}

nlsql_status nlsql_schema_builder_create(nlsql_context *c, nlsql_schema_builder **out) {
    nlsql_schema_builder *b;
    if (!c || !out) return NLSQL_E_INVALID_ARGUMENT;
    b = (nlsql_schema_builder *)calloc(1, sizeof(*b));
    if (!b) return NLSQL_E_OOM;
    b->ctx = c;
    b->schema = (nlsql_schema *)calloc(1, sizeof(*b->schema));
    if (!b->schema) {
        free(b);
        return NLSQL_E_OOM;
    }
    b->schema->ctx = c;
    *out = b;
    return NLSQL_OK;
}

static table_t *table_find(nlsql_schema *s, const char *sc, const char *tn) {
    size_t i;
    if (!s) return NULL;
    for (i = 0; i < s->nt; i++) {
        if (eqs(s->tables[i].schema, sc) && eqs(s->tables[i].name, tn)) return &s->tables[i];
    }
    return NULL;
}

static col_t *col_find(nlsql_schema *s, const char *sc, const char *tn, const char *cn) {
    size_t i;
    if (!s) return NULL;
    for (i = 0; i < s->nc; i++) {
        if (eqs(s->cols[i].schema, sc) && eqs(s->cols[i].table, tn) && eqs(s->cols[i].name, cn)) return &s->cols[i];
    }
    return NULL;
}

nlsql_status nlsql_schema_builder_add_table(nlsql_schema_builder *b, const char *sc, const char *tn, unsigned fl) {
    if (!b || !ident(sc) || !ident(tn)) return NLSQL_E_INVALID_ARGUMENT;
    if (b->schema->nt >= NLSQL_MAX_TABLES || b->schema->nt + b->schema->nc >= b->ctx->cfg.limits.max_schema_objects || table_find(b->schema, sc, tn)) return NLSQL_E_SCHEMA;
    cp(b->schema->tables[b->schema->nt].schema, NLSQL_NAME, sc);
    cp(b->schema->tables[b->schema->nt].name, NLSQL_NAME, tn);
    b->schema->tables[b->schema->nt++].flags = fl;
    return NLSQL_OK;
}

nlsql_status nlsql_schema_builder_add_column(nlsql_schema_builder *b, const char *sc, const char *tn, const char *cn, nlsql_type ty, unsigned fl) {
    if (!b || !ident(sc) || !ident(tn) || !ident(cn) || !table_find(b->schema, sc, tn) || col_find(b->schema, sc, tn, cn) || b->schema->nc >= NLSQL_MAX_COLS) return NLSQL_E_SCHEMA;
    cp(b->schema->cols[b->schema->nc].schema, NLSQL_NAME, sc);
    cp(b->schema->cols[b->schema->nc].table, NLSQL_NAME, tn);
    cp(b->schema->cols[b->schema->nc].name, NLSQL_NAME, cn);
    b->schema->cols[b->schema->nc].type = ty;
    b->schema->cols[b->schema->nc++].flags = fl;
    return NLSQL_OK;
}

nlsql_status nlsql_schema_builder_add_foreign_key(nlsql_schema_builder *b, const char *fs, const char *ft, const char *fc, const char *ts, const char *tt, const char *tc) {
    fk_t *f;
    if (!b || b->schema->nf >= NLSQL_MAX_FKS || !col_find(b->schema, fs, ft, fc) || !col_find(b->schema, ts, tt, tc)) return NLSQL_E_SCHEMA;
    f = &b->schema->fks[b->schema->nf++];
    cp(f->fs, NLSQL_NAME, fs);
    cp(f->ft, NLSQL_NAME, ft);
    cp(f->fc, NLSQL_NAME, fc);
    cp(f->ts, NLSQL_NAME, ts);
    cp(f->tt, NLSQL_NAME, tt);
    cp(f->tc, NLSQL_NAME, tc);
    return NLSQL_OK;
}

nlsql_status nlsql_schema_builder_finalize(nlsql_schema_builder *b, nlsql_schema **out) {
    if (!b || !out) return NLSQL_E_INVALID_ARGUMENT;
    *out = b->schema;
    b->schema = NULL;
    return NLSQL_OK;
}

void nlsql_schema_builder_destroy(nlsql_schema_builder *b) {
    if (b) {
        free(b->schema);
        free(b);
    }
}

void nlsql_schema_destroy(nlsql_schema *s) {
    if (s) free(s);
}

nlsql_status nlsql_policy_create(nlsql_context *c, nlsql_policy **out) {
    nlsql_policy *p;
    if (!c || !out) return NLSQL_E_INVALID_ARGUMENT;
    p = (nlsql_policy *)calloc(1, sizeof(*p));
    if (!p) return NLSQL_E_OOM;
    p->ctx = c;
    p->max_limit = c->cfg.limits.max_limit;
    p->max_joins = c->cfg.limits.max_joins;
    *out = p;
    return NLSQL_OK;
}

nlsql_status nlsql_policy_allow_table(nlsql_policy *p, const char *sc, const char *tn) {
    if (!p || !ident(sc) || !ident(tn) || p->na >= NLSQL_MAX_RULES) return NLSQL_E_INVALID_ARGUMENT;
    cp(p->allow[p->na].schema, NLSQL_NAME, sc);
    cp(p->allow[p->na++].table, NLSQL_NAME, tn);
    return NLSQL_OK;
}

nlsql_status nlsql_policy_deny_column(nlsql_policy *p, const char *sc, const char *tn, const char *cn) {
    if (!p || !ident(sc) || !ident(tn) || !ident(cn) || p->nd >= NLSQL_MAX_RULES) return NLSQL_E_INVALID_ARGUMENT;
    cp(p->deny[p->nd].schema, NLSQL_NAME, sc);
    cp(p->deny[p->nd].table, NLSQL_NAME, tn);
    cp(p->deny[p->nd++].col, NLSQL_NAME, cn);
    return NLSQL_OK;
}

nlsql_status nlsql_policy_require_tenant(nlsql_policy *p, const char *sc, const char *tn, const char *cn) {
    return nlsql_policy_require_tenant_typed(p, sc, tn, cn, NLSQL_TYPE_UNKNOWN);
}

nlsql_status nlsql_policy_require_tenant_typed(nlsql_policy *p, const char *sc, const char *tn, const char *cn, nlsql_type ty) {
    if (!p || !ident(sc) || !ident(tn) || !ident(cn) || p->ntenant >= NLSQL_MAX_RULES || ty == NLSQL_TYPE_NULL) return NLSQL_E_INVALID_ARGUMENT;
    cp(p->tenant[p->ntenant].schema, NLSQL_NAME, sc);
    cp(p->tenant[p->ntenant].table, NLSQL_NAME, tn);
    cp(p->tenant[p->ntenant].col, NLSQL_NAME, cn);
    p->tenant[p->ntenant++].type = ty;
    return NLSQL_OK;
}

nlsql_status nlsql_policy_set_limits(nlsql_policy *p, size_t joins, size_t lim) {
    if (!p || joins == 0 || lim == 0) return NLSQL_E_INVALID_ARGUMENT;
    p->max_joins = joins;
    p->max_limit = lim;
    return NLSQL_OK;
}

nlsql_status nlsql_policy_set_runtime_tenant(nlsql_policy *p, const char *n, nlsql_type t) {
    if (!p || !ident(n) || t == NLSQL_TYPE_UNKNOWN) return NLSQL_E_INVALID_ARGUMENT;
    cp(p->runtime_name, NLSQL_NAME, n);
    p->runtime_type = t;
    return NLSQL_OK;
}

void nlsql_policy_destroy(nlsql_policy *p) {
    free(p);
}

static void skip(parser_t *p) {
    while (p->p < p->n && isspace((unsigned char)p->s[p->p])) p->p++;
}

static void node_free(node_t *);

static node_t *parse_node(parser_t *p) {
    node_t *x;
    size_t start, i, n;
    if (p->nodes++ >= p->ctx->cfg.limits.max_nodes) return NULL;
    skip(p);
    if (p->p >= p->n) return NULL;
    x = (node_t *)calloc(1, sizeof(*x));
    if (!x) return NULL;
    x->off = p->p;
    if (p->s[p->p] == '(') {
        p->p++;
        skip(p);
        while (1) {
            skip(p);
            if (p->p >= p->n || p->s[p->p] == ')') break;
            if (x->nchild >= NLSQL_MAX_CHILDREN) {
                node_free(x);
                return NULL;
            }
            x->child[x->nchild++] = parse_node(p);
            if (!x->child[x->nchild - 1]) {
                node_free(x);
                return NULL;
            }
            skip(p);
        }
        if (p->p >= p->n) {
            node_free(x);
            return NULL;
        }
        p->p++;
        return x;
    }
    start = p->p;
    while (p->p < p->n && !isspace((unsigned char)p->s[p->p]) && p->s[p->p] != ')' && p->s[p->p] != '(') p->p++;
    n = p->p - start;
    if (n == 0 || n >= NLSQL_NAME) {
        node_free(x);
        return NULL;
    }
    x->atom = (char *)calloc(1, n + 1);
    if (!x->atom) {
        free(x);
        return NULL;
    }
    for (i = 0; i < n; i++) x->atom[i] = p->s[start + i];
    return x;
}

static void node_free(node_t *x) {
    size_t i;
    if (!x) return;
    for (i = 0; i < x->nchild; i++) node_free(x->child[i]);
    free(x->atom);
    free(x);
}

static int atom(node_t *x, const char *s) {
    return x && x->nchild == 0 && eqs(x->atom, s);
}

static int list(node_t *x, const char *s) {
    return x && x->nchild > 0 && atom(x->child[0], s);
}

static node_t *find_clause(node_t *q, const char *s) {
    size_t i;
    for (i = 1; i < q->nchild; i++) {
        if (list(q->child[i], s)) return q->child[i];
    }
    return NULL;
}

static int parse_source(node_t *x, size_t ti, size_t ai, char *sc, char *tn, char *al) {
    if (!x || x->nchild <= ai || x->child[ti]->nchild != 0 || x->child[ai]->nchild != 0) return 0;
    cp(tn, NLSQL_NAME, x->child[ti]->atom);
    cp(al, NLSQL_NAME, x->child[ai]->atom);
    cp(sc, NLSQL_NAME, "public");
    return ident(tn) && ident(al);
}

static int param_index(nlsql_compile_result *r, const char *n, nlsql_type ty, nlsql_param_source src) {
    size_t i;
    if (!n) return 0;
    for (i = 0; i < r->nparams; i++) {
        if (eqs(r->params[i].name, n)) {
            if (r->params[i].type != ty || r->params[i].source != src) return 0;
            return (int)i + 1;
        }
    }
    if (r->nparams >= NLSQL_MAX_PARAMS) return 0;
    cp(r->params[r->nparams].name, NLSQL_NAME, n);
    r->params[r->nparams].type = ty;
    r->params[r->nparams].source = src;
    r->nparams++;
    return (int)r->nparams;
}

static nlsql_type type_name(const char *s) {
    if (eqs(s, "boolean")) return NLSQL_TYPE_BOOLEAN;
    if (eqs(s, "int64")) return NLSQL_TYPE_INT64;
    if (eqs(s, "uint64")) return NLSQL_TYPE_UINT64;
    if (eqs(s, "decimal")) return NLSQL_TYPE_DECIMAL;
    if (eqs(s, "float64")) return NLSQL_TYPE_FLOAT64;
    if (eqs(s, "text")) return NLSQL_TYPE_TEXT;
    if (eqs(s, "binary")) return NLSQL_TYPE_BINARY;
    if (eqs(s, "uuid")) return NLSQL_TYPE_UUID;
    if (eqs(s, "date")) return NLSQL_TYPE_DATE;
    if (eqs(s, "timestamp")) return NLSQL_TYPE_TIMESTAMP;
    if (eqs(s, "timestamptz")) return NLSQL_TYPE_TIMESTAMPTZ;
    return NLSQL_TYPE_UNKNOWN;
}

static int emit_expr(buf_t *b, node_t *x, source_t *src, size_t ns, const nlsql_schema *schema, nlsql_compile_result *r, nlsql_dialect d);

static int emit_expr(buf_t *b, node_t *x, source_t *src, size_t ns, const nlsql_schema *schema, nlsql_compile_result *r, nlsql_dialect d) {
    size_t i;
    col_t *c;
    if (!x || x->nchild == 0) return 0;

    /* Column reference (column alias col_name) */
    if (atom(x->child[0], "column") && x->nchild == 3) {
        if (x->child[1]->nchild || x->child[2]->nchild || !ident(x->child[1]->atom) || !ident(x->child[2]->atom)) return 0;
        for (i = 0; i < ns; i++) {
            if (eqs(src[i].alias, x->child[1]->atom)) {
                c = col_find((nlsql_schema *)schema, src[i].schema, src[i].table, x->child[2]->atom);
                if (!c) return 0;
                break;
            }
        }
        if (i == ns) return 0;
        return buf_ident(b, x->child[1]->atom, d) && buf_ch(b, '.') && buf_ident(b, x->child[2]->atom, d);
    }

    /* Parameter (param name type) */
    if (atom(x->child[0], "param") && x->nchild == 3) {
        int idx;
        nlsql_type pt;
        if (x->child[1]->nchild || x->child[2]->nchild || !ident(x->child[1]->atom)) return 0;
        pt = type_name(x->child[2]->atom);
        if (pt == NLSQL_TYPE_UNKNOWN) return 0;
        idx = param_index(r, x->child[1]->atom, pt, NLSQL_PARAM_USER);
        if (!idx) return 0;
        if (d == NLSQL_DIALECT_POSTGRES || d == NLSQL_DIALECT_DUCKDB) {
            char t[32];
            (void)snprintf(t, sizeof(t), "$%d", idx);
            return buf_put(b, t);
        }
        if (d == NLSQL_DIALECT_SQLSERVER) {
            char t[32];
            (void)snprintf(t, sizeof(t), "@p%d", idx);
            return buf_put(b, t);
        }
        if (d == NLSQL_DIALECT_SQLITE) {
            char t[32];
            (void)snprintf(t, sizeof(t), "?%d", idx);
            return buf_put(b, t);
        }
        return buf_ch(b, '?');
    }

    /* Direct Identifier / Alias Reference (ref alias) */
    if (atom(x->child[0], "ref") && x->nchild == 2 && x->child[1]->nchild == 0) {
        return buf_ident(b, x->child[1]->atom, d);
    }

    /* Window functions (window expr (partition-by ...) (order-by ...)) */
    if (x->nchild >= 4 && atom(x->child[0], "window")) {
        size_t k;
        if (!emit_expr(b, x->child[1], src, ns, schema, r, d) || !buf_put(b, " OVER (")) return 0;
        if (!list(x->child[2], "partition-by") || x->child[2]->nchild < 2) return 0;
        if (!buf_put(b, "PARTITION BY ")) return 0;
        for (k = 1; k < x->child[2]->nchild; k++) {
            if (k > 1 && !buf_put(b, ", ")) return 0;
            if (!emit_expr(b, x->child[2]->child[k], src, ns, schema, r, d)) return 0;
        }
        if (!list(x->child[3], "order-by") || x->child[3]->nchild != 3 || !buf_put(b, " ORDER BY ") || !emit_expr(b, x->child[3]->child[1], src, ns, schema, r, d) || !buf_put(b, atom(x->child[3]->child[2], "desc") ? " DESC" : " ASC") || !buf_ch(b, ')')) return 0;
        return 1;
    }

    /* Standard Aggregates */
    if (x->nchild == 2 && (atom(x->child[0], "sum") || atom(x->child[0], "avg") || atom(x->child[0], "count") || atom(x->child[0], "min") || atom(x->child[0], "max"))) {
        const char *fn = x->child[0]->atom;
        return buf_put(b, fn) && buf_ch(b, '(') && emit_expr(b, x->child[1], src, ns, schema, r, d) && buf_ch(b, ')');
    }

    /* Distinct Aggregates: (count-distinct expr), (sum-distinct expr) */
    if (x->nchild == 2 && (atom(x->child[0], "count-distinct") || atom(x->child[0], "sum-distinct"))) {
        const char *fn = atom(x->child[0], "count-distinct") ? "COUNT(DISTINCT " : "SUM(DISTINCT ";
        return buf_put(b, fn) && emit_expr(b, x->child[1], src, ns, schema, r, d) && buf_ch(b, ')');
    }

    /* Binary Comparison and Math Operators */
    if (x->nchild == 3 && (atom(x->child[0], "eq") || atom(x->child[0], "gte") || atom(x->child[0], "gt") || atom(x->child[0], "lte") || atom(x->child[0], "lt") || atom(x->child[0], "neq") || atom(x->child[0], "mul") || atom(x->child[0], "add") || atom(x->child[0], "sub") || atom(x->child[0], "div"))) {
        const char *op = atom(x->child[0], "eq") ? " = " :
                         atom(x->child[0], "gte") ? " >= " :
                         atom(x->child[0], "gt") ? " > " :
                         atom(x->child[0], "lte") ? " <= " :
                         atom(x->child[0], "lt") ? " < " :
                         atom(x->child[0], "neq") ? " <> " :
                         atom(x->child[0], "mul") ? " * " :
                         atom(x->child[0], "add") ? " + " :
                         atom(x->child[0], "sub") ? " - " : " / ";
        return buf_ch(b, '(') && emit_expr(b, x->child[1], src, ns, schema, r, d) && buf_put(b, op) && emit_expr(b, x->child[2], src, ns, schema, r, d) && buf_ch(b, ')');
    }

    /* AND / OR logical operators */
    if (x->nchild >= 2 && (atom(x->child[0], "and") || atom(x->child[0], "or"))) {
        const char *op = atom(x->child[0], "and") ? " AND " : " OR ";
        if (!buf_ch(b, '(')) return 0;
        for (i = 1; i < x->nchild; i++) {
            if (i > 1 && !buf_put(b, op)) return 0;
            if (!emit_expr(b, x->child[i], src, ns, schema, r, d)) return 0;
        }
        return buf_ch(b, ')');
    }

    /* NOT operator (not expr) */
    if (x->nchild == 2 && atom(x->child[0], "not")) {
        return buf_put(b, "(NOT ") && emit_expr(b, x->child[1], src, ns, schema, r, d) && buf_ch(b, ')');
    }

    /* IS NULL / IS NOT NULL */
    if (x->nchild == 2 && atom(x->child[0], "is-null")) {
        return buf_ch(b, '(') && emit_expr(b, x->child[1], src, ns, schema, r, d) && buf_put(b, " IS NULL)");
    }
    if (x->nchild == 2 && atom(x->child[0], "is-not-null")) {
        return buf_ch(b, '(') && emit_expr(b, x->child[1], src, ns, schema, r, d) && buf_put(b, " IS NOT NULL)");
    }

    /* String functions: lower, upper, trim, concat */
    if (x->nchild == 2 && (atom(x->child[0], "lower") || atom(x->child[0], "upper") || atom(x->child[0], "trim") || atom(x->child[0], "abs"))) {
        const char *fn = atom(x->child[0], "lower") ? "LOWER" :
                         atom(x->child[0], "upper") ? "UPPER" :
                         atom(x->child[0], "trim") ? "TRIM" : "ABS";
        return buf_put(b, fn) && buf_ch(b, '(') && emit_expr(b, x->child[1], src, ns, schema, r, d) && buf_ch(b, ')');
    }

    if (atom(x->child[0], "concat") && x->nchild >= 2) {
        if (!buf_put(b, "CONCAT(")) return 0;
        for (i = 1; i < x->nchild; i++) {
            if (i > 1 && !buf_put(b, ", ")) return 0;
            if (!emit_expr(b, x->child[i], src, ns, schema, r, d)) return 0;
        }
        return buf_ch(b, ')');
    }

    /* COALESCE (coalesce e1 e2 ...) */
    if (atom(x->child[0], "coalesce") && x->nchild >= 2) {
        if (!buf_put(b, "COALESCE(")) return 0;
        for (i = 1; i < x->nchild; i++) {
            if (i > 1 && !buf_put(b, ", ")) return 0;
            if (!emit_expr(b, x->child[i], src, ns, schema, r, d)) return 0;
        }
        return buf_ch(b, ')');
    }

    return 0;
}

static int allowed_table(const nlsql_policy *p, const char *sc, const char *tn) {
    size_t i;
    if (!p || p->na == 0) return 0;
    for (i = 0; i < p->na; i++) {
        if (eqs(p->allow[i].schema, sc) && eqs(p->allow[i].table, tn)) return 1;
    }
    return 0;
}

static int policy_tenant(const nlsql_policy *p, const char *sc, const char *tn, const char **cn) {
    size_t i;
    if (!p) return 0;
    for (i = 0; i < p->ntenant; i++) {
        if (eqs(p->tenant[i].schema, sc) && eqs(p->tenant[i].table, tn)) {
            *cn = p->tenant[i].col;
            return 1;
        }
    }
    return 0;
}

static int policy_tenant_valid(const nlsql_policy *p, const nlsql_schema *s, const char *sc, const char *tn) {
    const char *c;
    col_t *x;
    if (!policy_tenant(p, sc, tn, &c)) return 1;
    x = col_find((nlsql_schema *)s, sc, tn, c);
    return x != NULL && (x->flags & NLSQL_COLUMN_TENANT_KEY) != 0u;
}

static int denied_column(const nlsql_policy *p, const char *sc, const char *tn, const char *cn) {
    size_t i;
    if (!p) return 0;
    for (i = 0; i < p->nd; i++) {
        if (eqs(p->deny[i].schema, sc) && eqs(p->deny[i].table, tn) && eqs(p->deny[i].col, cn)) return 1;
    }
    return 0;
}

static int validate_columns(const node_t *x, const source_t *src, size_t ns, const nlsql_schema *s, const nlsql_policy *p) {
    size_t i;
    if (!x) return 0;
    if (list((node_t *)x, "column") && x->nchild == 3) {
        if (x->child[1]->nchild || x->child[2]->nchild) return 0;
        for (i = 0; i < ns; i++) {
            if (eqs(src[i].alias, x->child[1]->atom)) {
                if (!col_find((nlsql_schema *)s, src[i].schema, src[i].table, x->child[2]->atom) ||
                    denied_column(p, src[i].schema, src[i].table, x->child[2]->atom)) return 0;
                break;
            }
        }
        if (i == ns) return 0;
    }
    for (i = 0; i < x->nchild; i++) {
        if (!validate_columns(x->child[i], src, ns, s, p)) return 0;
    }
    return 1;
}

static int numeric_type(nlsql_type t) {
    return t == NLSQL_TYPE_INT64 || t == NLSQL_TYPE_UINT64 || t == NLSQL_TYPE_DECIMAL || t == NLSQL_TYPE_FLOAT64;
}

static int type_compatible(nlsql_type a, nlsql_type b) {
    return a == b || (numeric_type(a) && numeric_type(b));
}

static int policy_tenant_type_valid(const nlsql_policy *p, const nlsql_schema *s, const char *sc, const char *tn) {
    const char *c;
    col_t *x;
    nlsql_type runtime, declared = NLSQL_TYPE_UNKNOWN;
    size_t i;
    if (!policy_tenant(p, sc, tn, &c)) return 1;
    for (i = 0; i < p->ntenant; i++) {
        if (eqs(p->tenant[i].schema, sc) && eqs(p->tenant[i].table, tn)) {
            declared = p->tenant[i].type;
            break;
        }
    }
    if (!policy_tenant_valid(p, s, sc, tn)) return 0;
    x = col_find((nlsql_schema *)s, sc, tn, c);
    runtime = p->runtime_type ? p->runtime_type : NLSQL_TYPE_UUID;
    return x != NULL && (declared == NLSQL_TYPE_UNKNOWN || type_compatible(x->type, declared)) && type_compatible(x->type, runtime);
}

static nlsql_type expr_type(const node_t *x, const source_t *src, size_t ns, const nlsql_schema *s) {
    size_t i;
    if (!x || x->nchild == 0) return NLSQL_TYPE_UNKNOWN;
    if (list((node_t *)x, "column") && x->nchild == 3) {
        for (i = 0; i < ns; i++) {
            if (eqs(src[i].alias, x->child[1]->atom)) {
                col_t *c = col_find((nlsql_schema *)s, src[i].schema, src[i].table, x->child[2]->atom);
                return c ? c->type : NLSQL_TYPE_UNKNOWN;
            }
        }
        return NLSQL_TYPE_UNKNOWN;
    }
    if (list((node_t *)x, "param") && x->nchild == 3) return type_name(x->child[2]->atom);
    if (list((node_t *)x, "ref")) return NLSQL_TYPE_UNKNOWN;
    if (list((node_t *)x, "count") && x->nchild == 2) return NLSQL_TYPE_INT64;
    if (list((node_t *)x, "count-distinct") && x->nchild == 2) return NLSQL_TYPE_INT64;
    if ((list((node_t *)x, "sum") || list((node_t *)x, "avg") || list((node_t *)x, "sum-distinct")) && x->nchild == 2) {
        nlsql_type t = expr_type(x->child[1], src, ns, s);
        return numeric_type(t) ? (list((node_t *)x, "avg") ? NLSQL_TYPE_DECIMAL : t) : NLSQL_TYPE_UNKNOWN;
    }
    if ((list((node_t *)x, "min") || list((node_t *)x, "max") || list((node_t *)x, "abs")) && x->nchild == 2) return expr_type(x->child[1], src, ns, s);
    if ((list((node_t *)x, "mul") || list((node_t *)x, "add") || list((node_t *)x, "sub") || list((node_t *)x, "div")) && x->nchild == 3) {
        nlsql_type a = expr_type(x->child[1], src, ns, s), b = expr_type(x->child[2], src, ns, s);
        return numeric_type(a) && numeric_type(b) ? (a == NLSQL_TYPE_FLOAT64 || b == NLSQL_TYPE_FLOAT64 ? NLSQL_TYPE_FLOAT64 : NLSQL_TYPE_DECIMAL) : NLSQL_TYPE_UNKNOWN;
    }
    if (list((node_t *)x, "window") && x->nchild >= 4) return expr_type(x->child[1], src, ns, s);
    if ((list((node_t *)x, "eq") || list((node_t *)x, "neq") || list((node_t *)x, "gt") || list((node_t *)x, "gte") || list((node_t *)x, "lt") || list((node_t *)x, "lte")) && x->nchild == 3) {
        nlsql_type a = expr_type(x->child[1], src, ns, s), b = expr_type(x->child[2], src, ns, s);
        return type_compatible(a, b) ? NLSQL_TYPE_BOOLEAN : NLSQL_TYPE_UNKNOWN;
    }
    if ((list((node_t *)x, "and") || list((node_t *)x, "or")) && x->nchild >= 2) {
        for (i = 1; i < x->nchild; i++) {
            if (expr_type(x->child[i], src, ns, s) != NLSQL_TYPE_BOOLEAN) return NLSQL_TYPE_UNKNOWN;
        }
        return NLSQL_TYPE_BOOLEAN;
    }
    if (list((node_t *)x, "not") && x->nchild == 2) {
        return expr_type(x->child[1], src, ns, s) == NLSQL_TYPE_BOOLEAN ? NLSQL_TYPE_BOOLEAN : NLSQL_TYPE_UNKNOWN;
    }
    if ((list((node_t *)x, "is-null") || list((node_t *)x, "is-not-null")) && x->nchild == 2) {
        return NLSQL_TYPE_BOOLEAN;
    }
    if ((list((node_t *)x, "lower") || list((node_t *)x, "upper") || list((node_t *)x, "trim") || list((node_t *)x, "concat")) && x->nchild >= 2) {
        return NLSQL_TYPE_TEXT;
    }
    if (list((node_t *)x, "coalesce") && x->nchild >= 2) {
        return expr_type(x->child[1], src, ns, s);
    }
    return NLSQL_TYPE_UNKNOWN;
}

static int type_tree(const node_t *x, const source_t *src, size_t ns, const nlsql_schema *s) {
    size_t i;
    if (!x) return 0;
    if (list((node_t *)x, "where") && x->nchild == 2 && expr_type(x->child[1], src, ns, s) != NLSQL_TYPE_BOOLEAN) return 0;
    if (list((node_t *)x, "join") && x->nchild == 5 && expr_type(x->child[4], src, ns, s) != NLSQL_TYPE_BOOLEAN) return 0;
    if (list((node_t *)x, "field") && x->nchild == 3 && expr_type(x->child[1], src, ns, s) == NLSQL_TYPE_UNKNOWN && !list(x->child[1], "ref")) return 0;
    if (list((node_t *)x, "window") && expr_type(x, src, ns, s) == NLSQL_TYPE_UNKNOWN) return 0;
    for (i = 0; i < x->nchild; i++) {
        if (!type_tree(x->child[i], src, ns, s)) return 0;
    }
    return 1;
}

static int canonical_node(buf_t *b, const node_t *x) {
    size_t i;
    if (!x) return 0;
    if (x->nchild == 0) return buf_put(b, x->atom);
    if (!buf_ch(b, '(')) return 0;
    for (i = 0; i < x->nchild; i++) {
        if (i && !buf_ch(b, ' ')) return 0;
        if (!canonical_node(b, x->child[i])) return 0;
    }
    return buf_ch(b, ')');
}

static int join_allowed(const nlsql_schema *s, const node_t *x, const source_t *sources, size_t nsources, const source_t *target) {
    size_t i, k;
    if (!x || x->nchild != 5 || !list(x->child[4], "eq")) return 0;
    x = x->child[4];
    if (x->nchild != 3 || !list(x->child[1], "column") || !list(x->child[2], "column") || x->child[1]->nchild != 3 || x->child[2]->nchild != 3) return 0;

    for (k = 0; k < nsources; k++) {
        const source_t *a = &sources[k];
        const source_t *b = target;
        for (i = 0; i < s->nf; i++) {
            const fk_t *f = &s->fks[i];
            if (eqs(x->child[1]->child[1]->atom, a->alias) && eqs(x->child[1]->child[2]->atom, f->fc) &&
                eqs(x->child[2]->child[1]->atom, b->alias) && eqs(x->child[2]->child[2]->atom, f->tc) &&
                eqs(a->schema, f->fs) && eqs(a->table, f->ft) &&
                eqs(b->schema, f->ts) && eqs(b->table, f->tt)) return 1;
            if (eqs(x->child[2]->child[1]->atom, a->alias) && eqs(x->child[2]->child[2]->atom, f->fc) &&
                eqs(x->child[1]->child[1]->atom, b->alias) && eqs(x->child[1]->child[2]->atom, f->tc) &&
                eqs(a->schema, f->fs) && eqs(a->table, f->ft) &&
                eqs(b->schema, f->ts) && eqs(b->table, f->tt)) return 1;
        }
    }
    return 0;
}

static int emit_param(buf_t *b, int idx, nlsql_dialect d) {
    char t[32];
    if (d == NLSQL_DIALECT_POSTGRES || d == NLSQL_DIALECT_DUCKDB) (void)snprintf(t, sizeof(t), "$%d", idx);
    else if (d == NLSQL_DIALECT_SQLSERVER) (void)snprintf(t, sizeof(t), "@p%d", idx);
    else if (d == NLSQL_DIALECT_SQLITE) (void)snprintf(t, sizeof(t), "?%d", idx);
    else return buf_ch(b, '?');
    return buf_put(b, t);
}

static int nesting_safe(const char *s, size_t n) {
    size_t i, depth = 0, max = 0;
    for (i = 0; i < n; i++) {
        if (s[i] == '(') {
            if (++depth > 128u) return 0;
            if (depth > max) max = depth;
        } else if (s[i] == ')') {
            if (depth == 0) return 0;
            depth--;
        }
    }
    return depth == 0 && max > 0;
}

static int clauses_valid(node_t *q) {
    size_t i;
    unsigned seen = 0, bit;
    for (i = 1; i < q->nchild; i++) {
        node_t *x = q->child[i];
        if (list(x, "from")) bit = 1u;
        else if (list(x, "join")) bit = 2u;
        else if (list(x, "select")) bit = 4u;
        else if (list(x, "where")) bit = 8u;
        else if (list(x, "group-by")) bit = 16u;
        else if (list(x, "order-by")) bit = 32u;
        else if (list(x, "limit")) bit = 64u;
        else return 0;
        if ((seen & bit) != 0u && bit != 2u) return 0;
        seen |= bit;
    }
    return (seen & 1u) != 0u && (seen & 4u) != 0u;
}

static nlsql_status compile_tree(nlsql_context *c, const nlsql_compile_request *req, nlsql_compile_result *r) {
    parser_t p;
    node_t *root;
    node_t *from, *sel, *where, *grp, *ord, *lim;
    source_t src[32];
    size_t ns = 0, i, j;
    buf_t b, canon = {0};
    size_t joins = 0;
    int tidx;
    const char *tc;
    size_t tenant_count = 0;
    nlsql_status failure = NLSQL_E_PARSE;
    unsigned long limit_value = (unsigned long)c->cfg.limits.default_limit;

    if (req->dialect > NLSQL_DIALECT_SQLSERVER) return NLSQL_E_DIALECT;
    if (!req->ir || !req->schema || !req->policy || strlen(req->ir) > c->cfg.limits.max_ir_bytes) return NLSQL_E_LIMIT;
    p.s = req->ir;
    p.n = strlen(req->ir);
    p.p = 0;
    p.nodes = 0;
    p.ctx = c;
    if (!nesting_safe(p.s, p.n)) return NLSQL_E_LIMIT;
    root = parse_node(&p);
    skip(&p);
    if (!root || p.p != p.n || !list(root, "nlsql") || root->nchild < 3 ||
        !(atom(root->child[1], "1") || atom(root->child[1], "2")) ||
        !list(root->child[2], "query") || !clauses_valid(root->child[2])) {
        node_free(root);
        return NLSQL_E_PARSE;
    }
    from = find_clause(root->child[2], "from");
    sel = find_clause(root->child[2], "select");
    where = find_clause(root->child[2], "where");
    grp = find_clause(root->child[2], "group-by");
    ord = find_clause(root->child[2], "order-by");
    lim = find_clause(root->child[2], "limit");
    if (!from || !sel || from->nchild < 2 || from->nchild > 3 || sel->nchild < 2 || sel->nchild > c->cfg.limits.max_selected_fields + 1) {
        node_free(root);
        return NLSQL_E_PARSE;
    }
    if (!parse_source(from, 1, from->nchild == 3 ? 2 : 1, src[0].schema, src[0].table, src[0].alias) ||
        !table_find((nlsql_schema *)req->schema, src[0].schema, src[0].table) ||
        !allowed_table(req->policy, src[0].schema, src[0].table)) {
        node_free(root);
        return NLSQL_E_POLICY;
    }
    ns = 1;
    for (i = 1; i < root->child[2]->nchild; i++) {
        node_t *x = root->child[2]->child[i];
        if (list(x, "join")) {
            if (x->nchild != 5 || joins++ >= req->policy->max_joins ||
                (!atom(x->child[1], "inner") && !atom(x->child[1], "left") && !atom(x->child[1], "right") && !atom(x->child[1], "full")) ||
                !parse_source(x, 2, 3, src[ns].schema, src[ns].table, src[ns].alias) ||
                !table_find((nlsql_schema *)req->schema, src[ns].schema, src[ns].table) ||
                !allowed_table(req->policy, src[ns].schema, src[ns].table) ||
                !list(x->child[4], "eq") ||
                !join_allowed((nlsql_schema *)req->schema, x, src, ns, &src[ns])) {
                node_free(root);
                return NLSQL_E_POLICY;
            }
            ns++;
            if (ns >= 32) {
                node_free(root);
                return NLSQL_E_LIMIT;
            }
        }
    }
    if (!validate_columns(root->child[2], src, ns, (const nlsql_schema *)req->schema, req->policy)) {
        node_free(root);
        return NLSQL_E_POLICY;
    }
    if (!type_tree(root->child[2], src, ns, (const nlsql_schema *)req->schema)) {
        node_free(root);
        return NLSQL_E_TYPE;
    }
    if (!buf_init(&b, c)) {
        node_free(root);
        return NLSQL_E_OOM;
    }
    if (!buf_put(&b, "SELECT ")) {
        free(b.s);
        node_free(root);
        return NLSQL_E_OOM;
    }
    if (req->dialect == NLSQL_DIALECT_SQLSERVER) {
        if (lim) {
            if (lim->nchild != 2 || lim->child[1]->nchild || !lim->child[1]->atom || !isdigit((unsigned char)lim->child[1]->atom[0])) goto fail;
            limit_value = strtoul(lim->child[1]->atom, NULL, 10);
            if (limit_value == 0 || limit_value > req->policy->max_limit) goto fail;
        }
        if (!buf_put(&b, "TOP ")) goto fail;
        {
            char t[32];
            (void)snprintf(t, sizeof(t), "%lu ", limit_value);
            if (!buf_put(&b, t)) goto fail;
        }
    }
    for (i = 1; i < sel->nchild; i++) {
        node_t *f = sel->child[i];
        if (i > 1 && !buf_put(&b, ", ")) goto fail;
        if (!f || f->nchild != 3 || !list(f, "field") || f->child[2]->nchild || !ident(f->child[2]->atom) || !emit_expr(&b, f->child[1], src, ns, req->schema, r, req->dialect)) goto fail;
        if (!buf_put(&b, " AS ") || !buf_ident(&b, f->child[2]->atom, req->dialect)) goto fail;
    }
    if (!buf_put(&b, " FROM ") || !buf_ident(&b, src[0].schema, req->dialect) || !buf_ch(&b, '.') || !buf_ident(&b, src[0].table, req->dialect) || !buf_put(&b, " AS ") || !buf_ident(&b, src[0].alias, req->dialect)) goto fail;
    for (i = 1; i < ns; i++) {
        node_t *jnode = NULL;
        const char *jtype = " INNER JOIN ";
        for (j = 1; j < root->child[2]->nchild; j++) {
            if (list(root->child[2]->child[j], "join") && eqs(root->child[2]->child[j]->child[3]->atom, src[i].alias)) {
                jnode = root->child[2]->child[j];
                break;
            }
        }
        if (!jnode) goto fail;
        if (atom(jnode->child[1], "left")) jtype = " LEFT JOIN ";
        else if (atom(jnode->child[1], "right")) jtype = " RIGHT JOIN ";
        else if (atom(jnode->child[1], "full")) jtype = " FULL OUTER JOIN ";
        if (!buf_put(&b, jtype) || !buf_ident(&b, src[i].schema, req->dialect) || !buf_ch(&b, '.') || !buf_ident(&b, src[i].table, req->dialect) || !buf_put(&b, " AS ") || !buf_ident(&b, src[i].alias, req->dialect) || !buf_put(&b, " ON ") || !emit_expr(&b, jnode->child[4], src, ns, req->schema, r, req->dialect)) goto fail;
    }
    if (where) {
        if (!buf_put(&b, " WHERE ") || !emit_expr(&b, where->child[1], src, ns, req->schema, r, req->dialect)) goto fail;
    }
    for (i = 0; i < ns; i++) {
        if (policy_tenant(req->policy, src[i].schema, src[i].table, &tc)) {
            if (!policy_tenant_valid(req->policy, (const nlsql_schema *)req->schema, src[i].schema, src[i].table)) {
                failure = NLSQL_E_POLICY;
                goto fail;
            }
            if (!policy_tenant_type_valid(req->policy, (const nlsql_schema *)req->schema, src[i].schema, src[i].table)) {
                failure = NLSQL_E_TYPE;
                goto fail;
            }
            if (!buf_put(&b, where ? " AND " : " WHERE ") || !buf_ident(&b, src[i].alias, req->dialect) || !buf_ch(&b, '.') || !buf_ident(&b, tc, req->dialect) || !buf_put(&b, " = ")) goto fail;
            tenant_count++;
            tidx = param_index(r, req->policy->runtime_name[0] ? req->policy->runtime_name : "tenant_id", req->policy->runtime_type ? req->policy->runtime_type : NLSQL_TYPE_UUID, NLSQL_PARAM_POLICY);
            if (tidx == 0) goto fail;
            if (!emit_param(&b, tidx, req->dialect)) goto fail;
            where = (node_t *)1;
        }
    }
    if (grp) {
        if (!buf_put(&b, " GROUP BY ")) goto fail;
        for (i = 1; i < grp->nchild; i++) {
            if (i > 1 && !buf_put(&b, ", ")) goto fail;
            if (!emit_expr(&b, grp->child[i], src, ns, req->schema, r, req->dialect)) goto fail;
        }
    }
    if (ord) {
        if (ord->nchild != 3 || !buf_put(&b, " ORDER BY ") || !emit_expr(&b, ord->child[1], src, ns, req->schema, r, req->dialect) || !buf_put(&b, atom(ord->child[2], "desc") ? " DESC" : " ASC")) goto fail;
    }
    if (req->dialect != NLSQL_DIALECT_SQLSERVER && lim) {
        unsigned long v;
        if (lim->nchild != 2 || lim->child[1]->nchild || !lim->child[1]->atom || !isdigit((unsigned char)lim->child[1]->atom[0])) goto fail;
        v = strtoul(lim->child[1]->atom, NULL, 10);
        if (v == 0 || v > req->policy->max_limit) goto fail;
        if (!buf_put(&b, " LIMIT ")) goto fail;
        {
            char t[32];
            (void)snprintf(t, sizeof(t), "%lu", v);
            if (!buf_put(&b, t)) goto fail;
        }
    } else if (req->dialect != NLSQL_DIALECT_SQLSERVER) {
        char t[32];
        if (!buf_put(&b, " LIMIT ")) goto fail;
        (void)snprintf(t, sizeof(t), "%lu", (unsigned long)c->cfg.limits.default_limit);
        if (!buf_put(&b, t)) goto fail;
    }
    if (!buf_init(&canon, c) || !canonical_node(&canon, root)) goto fail;
    free(r->ir);
    r->ir = canon.s;
    canon.s = NULL;
    r->sql = b.s;
    r->sql_len = b.n;
    r->complexity = (unsigned)(1 + joins + sel->nchild + tenant_count);
    r->risk = tenant_count ? NLSQL_RISK_LOW : NLSQL_RISK_MODERATE;
    r->status = NLSQL_OK;
    {
        char m[512];
        (void)snprintf(m, sizeof(m), "version=2\ndialect=%s\nparameters=%lu\ntenant_predicates=%lu\ncomplexity=%u\nrisk=%s\n",
                       nlsql_dialect_name(req->dialect), (unsigned long)r->nparams, tenant_count, r->complexity,
                       r->risk == NLSQL_RISK_LOW ? "LOW" : "MODERATE");
        r->manifest = (char *)calloc(1, strlen(m) + 1u);
        if (r->manifest) memcpy(r->manifest, m, strlen(m));
    }
    node_free(root);
    return r->manifest ? NLSQL_OK : NLSQL_E_OOM;
fail:
    free(canon.s);
    free(b.s);
    node_free(root);
    if (r->status == NLSQL_OK) r->status = failure;
    return r->status;
}

nlsql_status nlsql_compile_ir(nlsql_context *c, const nlsql_compile_request *req, nlsql_compile_result **out) {
    nlsql_compile_result *r;
    size_t n;
    if (!c || !req || !out) return NLSQL_E_INVALID_ARGUMENT;
    r = (nlsql_compile_result *)calloc(1, sizeof(*r));
    if (!r) return NLSQL_E_OOM;
    r->error = (char *)calloc(1, 512);
    if (!r->error) {
        free(r);
        return NLSQL_E_OOM;
    }
    n = req->ir ? strlen(req->ir) : 0u;
    r->ir = (char *)calloc(1, n + 1u);
    if (!r->ir) {
        nlsql_compile_result_destroy(r);
        return NLSQL_E_OOM;
    }
    if (req->ir) memcpy(r->ir, req->ir, n);
    r->status = compile_tree(c, req, r);
    if (r->status != NLSQL_OK && r->error[0] == 0) {
        cp(r->error, 512, nlsql_status_name(r->status));
        diagnostic_set(r, r->status, nlsql_status_name(r->status), r->error, r->status == NLSQL_E_PARSE ? strlen(r->ir) : 0u);
    }
    *out = r;
    return r->status;
}

static int append_rebased(buf_t *, const char *, nlsql_dialect, size_t);

static int prepare_cte_scope(nlsql_context *c, const char *ir, const char *name, const nlsql_schema *base, const nlsql_policy *policy, nlsql_schema *scope, nlsql_policy *scoped) {
    parser_t p;
    node_t *root, *q, *from, *select;
    source_t source;
    size_t i;
    if (!ident(name) || !base || !policy) return 0;
    p.s = ir;
    p.n = strlen(ir);
    p.p = 0;
    p.nodes = 0;
    p.ctx = c;
    root = parse_node(&p);
    skip(&p);
    if (!root || p.p != p.n || !list(root, "nlsql") || root->nchild < 3 ||
        !(atom(root->child[1], "1") || atom(root->child[1], "2")) ||
        !list(root->child[2], "query")) {
        node_free(root);
        return 0;
    }
    q = root->child[2];
    from = find_clause(q, "from");
    select = find_clause(q, "select");
    if (!from || !select || from->nchild < 2 || from->nchild > 3 || select->nchild < 2 || !parse_source(from, 1, from->nchild == 3 ? 2 : 1, source.schema, source.table, source.alias)) {
        node_free(root);
        return 0;
    }
    for (i = 1; i < q->nchild; i++) {
        if (list(q->child[i], "join")) {
            node_free(root);
            return 0;
        }
    }
    *scope = *base;
    scope->ctx = c;
    if (scope->nt >= NLSQL_MAX_TABLES || scope->nc + select->nchild - 1u > NLSQL_MAX_COLS) {
        node_free(root);
        return 0;
    }
    cp(scope->tables[scope->nt].schema, NLSQL_NAME, "public");
    cp(scope->tables[scope->nt].name, NLSQL_NAME, name);
    scope->tables[scope->nt++].flags = NLSQL_TABLE_VIEW;
    for (i = 1; i < select->nchild; i++) {
        node_t *f = select->child[i];
        nlsql_type type;
        if (!list(f, "field") || f->nchild != 3 || !ident(f->child[2]->atom)) {
            node_free(root);
            return 0;
        }
        type = expr_type(f->child[1], &source, 1, base);
        if (type == NLSQL_TYPE_UNKNOWN) {
            node_free(root);
            return 0;
        }
        cp(scope->cols[scope->nc].schema, NLSQL_NAME, "public");
        cp(scope->cols[scope->nc].table, NLSQL_NAME, name);
        cp(scope->cols[scope->nc].name, NLSQL_NAME, f->child[2]->atom);
        scope->cols[scope->nc].type = type;
        scope->cols[scope->nc].flags = 0u;
        scope->nc++;
    }
    *scoped = *policy;
    scoped->ctx = c;
    if (scoped->na >= NLSQL_MAX_RULES) {
        node_free(root);
        return 0;
    }
    cp(scoped->allow[scoped->na].schema, NLSQL_NAME, "public");
    cp(scoped->allow[scoped->na].table, NLSQL_NAME, name);
    scoped->na++;
    node_free(root);
    return 1;
}

nlsql_status nlsql_compile_cte(nlsql_context *c, const nlsql_cte_request *q, nlsql_compile_result **out) {
    nlsql_compile_request cr, qr;
    nlsql_compile_result *cte = NULL, *outer = NULL, *res = NULL;
    nlsql_schema scope;
    nlsql_policy scoped;
    buf_t b;
    size_t i, ir_len;
    char *ir;
    if (!c || !q || !out || !q->cte_name || !q->cte_ir || !q->query_ir || !q->schema || !q->policy) return NLSQL_E_INVALID_ARGUMENT;
    cr.ir = q->cte_ir;
    cr.schema = q->schema;
    cr.policy = q->policy;
    cr.dialect = q->dialect;
    cr.trace_id = NULL;
    if (nlsql_compile_ir(c, &cr, &cte) != NLSQL_OK) return cte ? cte->status : NLSQL_E_PARSE;
    if (!prepare_cte_scope(c, q->cte_ir, q->cte_name, q->schema, q->policy, &scope, &scoped)) {
        nlsql_compile_result_destroy(cte);
        return NLSQL_E_TYPE;
    }
    qr = cr;
    qr.ir = q->query_ir;
    qr.schema = &scope;
    qr.policy = &scoped;
    if (nlsql_compile_ir(c, &qr, &outer) != NLSQL_OK) {
        nlsql_compile_result_destroy(cte);
        return outer ? outer->status : NLSQL_E_PARSE;
    }
    res = (nlsql_compile_result *)calloc(1, sizeof(*res));
    if (!res || !buf_init(&b, c)) {
        nlsql_compile_result_destroy(cte);
        nlsql_compile_result_destroy(outer);
        free(res);
        return NLSQL_E_OOM;
    }
    if (!buf_put(&b, "WITH ") || !buf_ident(&b, q->cte_name, q->dialect) || !buf_put(&b, " AS (") || !buf_put(&b, cte->sql) || !buf_put(&b, ") ") || !append_rebased(&b, outer->sql, q->dialect, cte->nparams)) {
        free(b.s);
        nlsql_compile_result_destroy(cte);
        nlsql_compile_result_destroy(outer);
        free(res);
        return NLSQL_E_LIMIT;
    }
    res->sql = b.s;
    res->sql_len = b.n;
    for (i = 0; i < cte->nparams; i++) res->params[res->nparams++] = cte->params[i];
    for (i = 0; i < outer->nparams; i++) res->params[res->nparams++] = outer->params[i];
    ir_len = strlen(cte->ir) + strlen(outer->ir) + strlen(q->cte_name) + 32u;
    ir = (char *)calloc(1, ir_len);
    if (!ir) {
        nlsql_compile_result_destroy(cte);
        nlsql_compile_result_destroy(outer);
        nlsql_compile_result_destroy(res);
        return NLSQL_E_OOM;
    }
    (void)snprintf(ir, ir_len, "(with %s %s %s)", q->cte_name, cte->ir, outer->ir);
    res->ir = ir;
    res->complexity = cte->complexity + outer->complexity + 1u;
    res->risk = cte->risk > outer->risk ? cte->risk : outer->risk;
    {
        char m[512];
        (void)snprintf(m, sizeof(m), "version=2\ndialect=%s\nparameters=%lu\ncomplexity=%u\nrisk=%s\ncte=%s\n",
                       nlsql_dialect_name(q->dialect), (unsigned long)res->nparams, res->complexity,
                       res->risk == NLSQL_RISK_LOW ? "LOW" : res->risk == NLSQL_RISK_MODERATE ? "MODERATE" : "HIGH", q->cte_name);
        res->manifest = (char *)calloc(1, strlen(m) + 1u);
        if (res->manifest) memcpy(res->manifest, m, strlen(m));
    }
    res->status = res->manifest ? NLSQL_OK : NLSQL_E_OOM;
    nlsql_compile_result_destroy(cte);
    nlsql_compile_result_destroy(outer);
    if (res->status != NLSQL_OK) {
        nlsql_compile_result_destroy(res);
        return NLSQL_E_OOM;
    }
    *out = res;
    return NLSQL_OK;
}

static int set_operator_name(nlsql_set_operator op, const char **name) {
    if (op == NLSQL_SET_UNION) { *name = "UNION"; return 1; }
    if (op == NLSQL_SET_UNION_ALL) { *name = "UNION ALL"; return 1; }
    if (op == NLSQL_SET_INTERSECT) { *name = "INTERSECT"; return 1; }
    if (op == NLSQL_SET_EXCEPT) { *name = "EXCEPT"; return 1; }
    return 0;
}

static int append_rebased(buf_t *b, const char *s, nlsql_dialect d, size_t offset) {
    size_t i = 0;
    while (s && s[i]) {
        if ((d == NLSQL_DIALECT_POSTGRES || d == NLSQL_DIALECT_DUCKDB) && s[i] == '$' && isdigit((unsigned char)s[i + 1])) {
            unsigned long n = 0;
            char t[32];
            while (isdigit((unsigned char)s[++i])) n = n * 10u + (unsigned long)(s[i] - '0');
            (void)snprintf(t, sizeof(t), "$%lu", n + (unsigned long)offset);
            if (!buf_put(b, t)) return 0;
            continue;
        }
        if (d == NLSQL_DIALECT_SQLSERVER && s[i] == '@' && s[i + 1] == 'p' && isdigit((unsigned char)s[i + 2])) {
            unsigned long n = 0;
            char t[32];
            i++;
            while (isdigit((unsigned char)s[++i])) n = n * 10u + (unsigned long)(s[i] - '0');
            (void)snprintf(t, sizeof(t), "@p%lu", n + (unsigned long)offset);
            if (!buf_put(b, t)) return 0;
            continue;
        }
        if (d == NLSQL_DIALECT_SQLITE && s[i] == '?' && isdigit((unsigned char)s[i + 1])) {
            unsigned long n = 0;
            char t[32];
            i++;
            while (isdigit((unsigned char)s[++i])) n = n * 10u + (unsigned long)(s[i] - '0');
            (void)snprintf(t, sizeof(t), "?%lu", n + (unsigned long)offset);
            if (!buf_put(b, t)) return 0;
            continue;
        }
        if (!buf_ch(b, s[i++])) return 0;
    }
    return 1;
}

nlsql_status nlsql_compile_set(nlsql_context *c, const nlsql_set_request *q, nlsql_compile_result **out) {
    const char *op;
    nlsql_compile_request lq, rq;
    nlsql_compile_result *l = NULL, *rr = NULL, *res = NULL;
    buf_t b;
    size_t i, ir_len;
    char *ir;
    int n;
    if (!c || !q || !out || !q->left_ir || !q->right_ir || !q->schema || !q->policy || !set_operator_name(q->operation, &op)) return NLSQL_E_INVALID_ARGUMENT;
    lq.ir = q->left_ir;
    lq.schema = q->schema;
    lq.policy = q->policy;
    lq.dialect = q->dialect;
    lq.trace_id = NULL;
    rq = lq;
    rq.ir = q->right_ir;
    if (nlsql_compile_ir(c, &lq, &l) != NLSQL_OK || nlsql_compile_ir(c, &rq, &rr) != NLSQL_OK) {
        nlsql_compile_result_destroy(l);
        nlsql_compile_result_destroy(rr);
        return NLSQL_E_POLICY;
    }
    if (l->nparams + rr->nparams > NLSQL_MAX_PARAMS) {
        nlsql_compile_result_destroy(l);
        nlsql_compile_result_destroy(rr);
        return NLSQL_E_LIMIT;
    }
    res = (nlsql_compile_result *)calloc(1, sizeof(*res));
    if (!res) {
        nlsql_compile_result_destroy(l);
        nlsql_compile_result_destroy(rr);
        return NLSQL_E_OOM;
    }
    res->error = (char *)calloc(1, 512);
    if (!res->error || !buf_init(&b, c)) {
        nlsql_compile_result_destroy(l);
        nlsql_compile_result_destroy(rr);
        nlsql_compile_result_destroy(res);
        return NLSQL_E_OOM;
    }
    if (!buf_put(&b, "(") || !buf_put(&b, l->sql) || !buf_put(&b, ") ") || !buf_put(&b, op) || !buf_put(&b, " (") || !append_rebased(&b, rr->sql, q->dialect, l->nparams) || !buf_put(&b, ")")) {
        free(b.s);
        nlsql_compile_result_destroy(l);
        nlsql_compile_result_destroy(rr);
        nlsql_compile_result_destroy(res);
        return NLSQL_E_LIMIT;
    }
    res->sql = b.s;
    res->sql_len = b.n;
    for (i = 0; i < l->nparams; i++) res->params[res->nparams++] = l->params[i];
    for (i = 0; i < rr->nparams; i++) res->params[res->nparams++] = rr->params[i];
    ir_len = strlen(l->ir) + strlen(rr->ir) + 32u;
    ir = (char *)calloc(1, ir_len);
    if (!ir) {
        nlsql_compile_result_destroy(l);
        nlsql_compile_result_destroy(rr);
        nlsql_compile_result_destroy(res);
        return NLSQL_E_OOM;
    }
    n = snprintf(ir, ir_len, "(set %s %s %s)", op, l->ir, rr->ir);
    if (n < 0 || (size_t)n >= ir_len) {
        free(ir);
        nlsql_compile_result_destroy(l);
        nlsql_compile_result_destroy(rr);
        nlsql_compile_result_destroy(res);
        return NLSQL_E_LIMIT;
    }
    res->ir = ir;
    res->complexity = l->complexity + rr->complexity + 1u;
    res->risk = l->risk > rr->risk ? l->risk : rr->risk;
    {
        char m[512];
        (void)snprintf(m, sizeof(m), "version=2\ndialect=%s\nparameters=%lu\ncomplexity=%u\nrisk=%s\nset_operation=%s\n",
                       nlsql_dialect_name(q->dialect), (unsigned long)res->nparams, res->complexity,
                       res->risk == NLSQL_RISK_LOW ? "LOW" : res->risk == NLSQL_RISK_MODERATE ? "MODERATE" : "HIGH", op);
        res->manifest = (char *)calloc(1, strlen(m) + 1u);
        if (res->manifest) memcpy(res->manifest, m, strlen(m));
    }
    res->status = res->manifest ? NLSQL_OK : NLSQL_E_OOM;
    nlsql_compile_result_destroy(l);
    nlsql_compile_result_destroy(rr);
    if (res->status != NLSQL_OK) {
        nlsql_compile_result_destroy(res);
        return NLSQL_E_OOM;
    }
    *out = res;
    return NLSQL_OK;
}

nlsql_status nlsql_build_inference_prompt(const nlsql_question_request *q, char *out, size_t cap, size_t *required) {
    int n;
    if (!q || !q->question) return NLSQL_E_INVALID_ARGUMENT;
    n = snprintf(NULL, 0, "Return exactly one nlsql Query IR expression for this question. Never emit SQL, comments, literals, or explanations. Question: %s\n", q->question);
    if (n < 0) return NLSQL_E_INTERNAL;
    if (required) *required = (size_t)n;
    if (!out || cap <= (size_t)n) return NLSQL_E_LIMIT;
    (void)snprintf(out, cap, "Return exactly one nlsql Query IR expression for this question. Never emit SQL, comments, literals, or explanations. Question: %s\n", q->question);
    return NLSQL_OK;
}

nlsql_status nlsql_compile_inferred(nlsql_context *c, const nlsql_question_request *q, const nlsql_inference *i, nlsql_compile_result **out) {
    char prompt[4096];
    char *ir;
    size_t prompt_n = 0, ir_n = 0;
    nlsql_status st;
    nlsql_compile_request req;
    if (!c || !q || !i || !i->infer || !out) return NLSQL_E_INVALID_ARGUMENT;
    st = nlsql_build_inference_prompt(q, prompt, sizeof(prompt), &prompt_n);
    if (st != NLSQL_OK) return st;
    (void)prompt_n;
    ir = (char *)calloc(1u, 65537u);
    if (!ir) return NLSQL_E_OOM;
    st = i->infer(i->user_data, prompt, strlen(prompt), ir, 65536u, &ir_n);
    if (st != NLSQL_OK || ir_n > 65536u) {
        free(ir);
        return st == NLSQL_OK ? NLSQL_E_LIMIT : st;
    }
    ir[ir_n] = 0;
    req.ir = ir;
    req.schema = q->schema;
    req.policy = q->policy;
    req.dialect = q->dialect;
    req.trace_id = NULL;
    st = nlsql_compile_ir(c, &req, out);
    free(ir);
    return st;
}

nlsql_status nlsql_compile_question(nlsql_context *c, const nlsql_question_request *req, nlsql_compile_result **out) {
    char kind[32] = {0}, table[NLSQL_NAME] = {0}, column[NLSQL_NAME] = {0}, tail = 0, ir[768];
    int n;
    const nlsql_schema *s;
    if (!c || !req || !req->question || !req->schema || !req->policy || !out) return NLSQL_E_INVALID_ARGUMENT;
    s = (const nlsql_schema *)req->schema;
    n = sscanf(req->question, "%31s %127s %127s %c", kind, table, column, &tail);
    if (n < 2 || n > 3 || !ident(table) || !table_find((nlsql_schema *)s, "public", table)) return NLSQL_E_UNSUPPORTED;
    if (strcmp(kind, "count") == 0) {
        if (n != 2 || !col_find((nlsql_schema *)s, "public", table, "id")) return NLSQL_E_UNSUPPORTED;
        (void)snprintf(ir, sizeof(ir), "(nlsql 1 (query (from %s t) (select (field (count (column t id)) count))))", table);
    } else {
        const char *fn;
        if (n != 3 || !ident(column) || !col_find((nlsql_schema *)s, "public", table, column)) return NLSQL_E_UNSUPPORTED;
        if (strcmp(kind, "list") == 0) fn = "";
        else if (strcmp(kind, "sum") == 0) fn = "sum";
        else if (strcmp(kind, "average") == 0) fn = "avg";
        else if (strcmp(kind, "min") == 0) fn = "min";
        else if (strcmp(kind, "max") == 0) fn = "max";
        else return NLSQL_E_UNSUPPORTED;
        if (fn[0]) (void)snprintf(ir, sizeof(ir), "(nlsql 1 (query (from %s t) (select (field (%s (column t %s)) value))))", table, fn, column);
        else (void)snprintf(ir, sizeof(ir), "(nlsql 1 (query (from %s t) (select (field (column t %s) value))))", table, column);
    }
    if (strlen(ir) >= sizeof(ir) - 1u) return NLSQL_E_LIMIT;
    {
        nlsql_compile_request r = {ir, req->schema, req->policy, req->dialect, NULL};
        return nlsql_compile_ir(c, &r, out);
    }
}

void nlsql_compile_result_destroy(nlsql_compile_result *r) {
    if (r) {
        free(r->sql);
        free(r->ir);
        free(r->manifest);
        free(r->error);
        free(r);
    }
}

nlsql_sql_view nlsql_result_sql(const nlsql_compile_result *r) {
    nlsql_sql_view v = {NULL, 0};
    if (r) {
        v.sql = r->sql;
        v.length = r->sql_len;
    }
    return v;
}

const char *nlsql_result_canonical_ir(const nlsql_compile_result *r) {
    return r ? r->ir : NULL;
}

const char *nlsql_result_manifest(const nlsql_compile_result *r) {
    return r ? r->manifest : NULL;
}

const char *nlsql_result_error(const nlsql_compile_result *r) {
    return r ? r->error : NULL;
}

nlsql_status nlsql_result_status(const nlsql_compile_result *r) {
    return r ? r->status : NLSQL_E_INVALID_ARGUMENT;
}

size_t nlsql_result_param_count(const nlsql_compile_result *r) {
    return r ? r->nparams : 0u;
}

nlsql_param_view nlsql_result_param(const nlsql_compile_result *r, size_t i) {
    nlsql_param_view v = {0, NULL, NLSQL_TYPE_UNKNOWN, NLSQL_PARAM_USER, 0};
    if (r && i < r->nparams) {
        v.position = i + 1u;
        v.name = r->params[i].name;
        v.type = r->params[i].type;
        v.source = r->params[i].source;
        v.runtime_required = (r->params[i].source != NLSQL_PARAM_TRUSTED);
    }
    return v;
}

nlsql_risk nlsql_result_risk(const nlsql_compile_result *r) {
    return r ? r->risk : NLSQL_RISK_DENIED;
}

unsigned nlsql_result_complexity(const nlsql_compile_result *r) {
    return r ? r->complexity : 0u;
}

uint64_t nlsql_result_fingerprint(const nlsql_compile_result *r) {
    const unsigned char *p;
    uint64_t h = 1469598103934665603ULL;
    if (!r || !r->ir) return 0u;
    for (p = (const unsigned char *)r->ir; *p; p++) {
        h ^= (uint64_t)*p;
        h *= 1099511628211ULL;
    }
    return h;
}

double nlsql_result_relevance_score(const nlsql_compile_result *r) {
    double score;
    if (!r || r->status != NLSQL_OK) return 0.0;
    score = 1.0 / (1.0 + (double)r->complexity / 10.0);
    if (r->risk == NLSQL_RISK_MODERATE) score *= 0.8;
    if (r->risk == NLSQL_RISK_HIGH) score *= 0.5;
    if (r->risk == NLSQL_RISK_DENIED) return 0.0;
    return score;
}

size_t nlsql_result_diagnostic_count(const nlsql_compile_result *r) {
    return r && r->has_diagnostic ? 1u : 0u;
}

nlsql_diagnostic_view nlsql_result_diagnostic(const nlsql_compile_result *r, size_t i) {
    nlsql_diagnostic_view v = {0u, 0u, 0u, NLSQL_OK, NULL, NULL};
    if (r && r->has_diagnostic && i == 0u) return r->diagnostic;
    return v;
}
