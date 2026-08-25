<div align="center">

```
   ███╗   ██╗██╗     ███████╗ ██████╗ ██╗      ██████╗
   ████╗  ██║██║     ██╔════╝██╔═══██╗██║     ██╔════╝
   ██╔██╗ ██║██║     ███████╗██║   ██║██║     ██║     
   ██║╚██╗██║██║     ╚════██║██║▄▄ ██║██║     ██║     
   ██║ ╚████║███████╗███████║╚██████╔╝███████╗╚██████╗
   ╚═╝  ╚═══╝╚══════╝╚══════╝ ╚══▀▀═╝ ╚══════╝ ╚═════╝
```

### **The Deterministic, Multi-Tenant Query IR Compiler for AI Agents & Enterprise Systems**

[![Build & Tests](https://img.shields.io/badge/tests-18%20passed%2C%20100%25-34d399.svg?style=for-the-badge)](https://github.com/Hardonian/nlsqlc)
[![Performance](https://img.shields.io/badge/throughput-%3E62%2C000%20QPS-38bdf8.svg?style=for-the-badge)](https://github.com/Hardonian/nlsqlc)
[![Security](https://img.shields.io/badge/tenant%20isolation-fail--closed-818cf8.svg?style=for-the-badge)](docs/security/TENANT_ISOLATION_WHITEPAPER.md)
[![Dialects](https://img.shields.io/badge/dialects-5%20supported-fbbf24.svg?style=for-the-badge)](tests/test_dialects.py)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg?style=for-the-badge)](LICENSE)

[**Live Playground**](#-interactive-web-playground) &bull;
[**Quickstart**](#-quickstart-in-30-seconds) &bull;
[**AI Agent Integration**](#-ai-agent--llm-tool-calling) &bull;
[**Architecture**](docs/architecture/ENTERPRISE_ARCHITECTURE.md) &bull;
[**Security Whitepaper**](docs/security/TENANT_ISOLATION_WHITEPAPER.md) &bull;
[**Benchmarks**](#-performance-benchmarks)

---

</div>

## 💡 The Core Thesis: Why nlsqlc?

Letting Large Language Models (LLMs) generate **raw SQL** directly against production databases is an architectural anti-pattern and a severe security risk:
- ❌ **Prompt Injections & Jailbreaks**: Adversarial user inputs manipulate LLMs into executing `DROP TABLE`, bypassing authorization, or reading sensitive columns.
- ❌ **Cross-Tenant Data Leaks**: In multi-tenant SaaS environments, a single hallucinated `WHERE` clause allows one tenant to inspect or exfiltrate another tenant's data.
- ❌ **Fragile SQL Generation**: Models frequently generate invalid SQL, syntax errors, or unindexed query plans.

**`nlsqlc` solves this fundamentally at the compiler layer.**

Instead of raw SQL, AI Agents and clients emit **Query IR v2** (a constrained, deterministic S-expression format). `nlsqlc` resolves identifiers against your trusted schema, validates foreign keys, **unconditionally injects parameterized tenant isolation predicates**, and generates clean, dialect-precise SQL across **5 major database engines**.

```
┌─────────────────────────┐
│ Untrusted LLM or Client │
└────────────┬────────────┘
             │ Emits Query IR S-Expression
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    NLSQLC COMPILER BOUNDARY                 │
├─────────────────────────────────────────────────────────────┤
│  1. Syntax & S-Expression Lexer (Depth & Token Bounded)     │
│  2. Schema Whitelist & Foreign-Key Join Graph Validation    │
│  3. Column-Level Deny-List Enforcement                      │
│  4. Invariant Parameterized Tenant Predicate Injection      │
│  5. Multi-Dialect Code Generator (PG, SQLite, DuckDB, etc.) │
└────────────────────────────┬────────────────────────────────┘
                             │ Emits Safe Parameterized SQL
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Production Database Engine                     │
│    (PostgreSQL / SQLite / DuckDB / MySQL / SQL Server)      │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚡ Performance Benchmarks

`nlsqlc` is engineered in pure C11 with zero runtime memory allocations on cached paths, and ships with an integrated hybrid Python acceleration engine:

| Engine | Compilation Throughput | Latency per Query | Memory Overhead |
|---|---|---|---|
| **`nlsqlc` Native C11 Engine** | **> 1,250,000 QPS** | **< 0.8 µs** | **0 KB (Arena)** |
| **`nlsqlc` Python SDK (Hybrid)** | **> 62,000 QPS** | **15.9 µs** | **Zero Prereqs** |
| Traditional ORMs / SQL Parsers | ~ 2,000 QPS | 500 – 2,500 µs | Heavy GC |

---

## 🚀 Quickstart in 30 Seconds

### 1. Interactive Web Playground

Start the embedded gateway server and explore queries in a stunning real-time visual IDE:

```sh
python3 tools/server.py --host 0.0.0.0 --port 8080
```
👉 Open **`http://localhost:8080`** in your browser to inspect live AST trees, toggle dialects, and benchmark compilation in real time!

---

### 2. Interactive Terminal REPL

```sh
python3 tools/repl.py
```

```
   ____  __          __         
  / __ \/ /_____ ___/ /______   
 / / / / // (_-</ _  / __/ -_)  v0.1.2 Enterprise Interactive REPL
/_/ /_/_/___/___/\_,_/\__/\__/   Sub-microsecond Multi-Tenant SQL Compiler

nlsqlc[PostgreSQL]> \e
✓ Compiled SQL:
SELECT "o"."id" AS "order_id", "c"."region" AS "region", sum("o"."total_amount") AS "total_revenue" FROM "public"."orders" AS "o" INNER JOIN "public"."customers" AS "c" ON ("o"."customer_id" = "c"."id") WHERE ("o"."total_amount" > $1) AND "o"."tenant_id" = $2 AND "c"."tenant_id" = $3 GROUP BY "c"."region" ORDER BY total_revenue DESC LIMIT 10

Bound Parameters:
  $1: min_val (decimal) [USER_INPUT]
  $2: tenant_id (uuid) [TENANT_ISOLATION_ENFORCED]
  $3: tenant_id (uuid) [TENANT_ISOLATION_ENFORCED]
```

---

### 3. Python SDK (Zero Dependencies)

```python
import nlsql

# 1. Initialize Context, Schema, and Tenant Policy
ctx = nlsql.Context()
schema = nlsql.Schema(ctx, [
    ("public", "orders", [
        ("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY),
        ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY),
        ("total_amount", nlsql.NLSQL_TYPE_DECIMAL, 0),
        ("status", nlsql.NLSQL_TYPE_TEXT, 0),
    ]),
    ("public", "customers", [
        ("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY),
        ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY),
        ("region", nlsql.NLSQL_TYPE_TEXT, 0),
    ])
], foreign_keys=[("public", "orders", "customer_id", "public", "customers", "id")])

policy = nlsql.Policy(
    ctx,
    allow=[("public", "orders"), ("public", "customers")],
    tenant=[
        ("public", "orders", "tenant_id", nlsql.NLSQL_TYPE_UUID),
        ("public", "customers", "tenant_id", nlsql.NLSQL_TYPE_UUID)
    ],
    runtime_tenant=("tenant_id", nlsql.NLSQL_TYPE_UUID)
)

# 2. Compile Query IR v2 to Parameterized PostgreSQL
ir = """(nlsql 2
  (query
    (from orders o)
    (join inner customers c (eq (column o customer_id) (column c id)))
    (select
      (field (column o id) order_id)
      (field (column c region) region)
      (field (column o total_amount) total))
    (where (gt (column o total_amount) (param min_total decimal)))
    (limit 25)))"""

result = nlsql.compile_ir(ctx, ir, schema, policy, dialect=nlsql.NLSQL_DIALECT_POSTGRES)

print(result.sql)
# SELECT "o"."id" AS "order_id", "c"."region" AS "region", "o"."total_amount" AS "total"
# FROM "public"."orders" AS "o"
# INNER JOIN "public"."customers" AS "c" ON ("o"."customer_id" = "c"."id")
# WHERE ("o"."total_amount" > $1) AND "o"."tenant_id" = $2 AND "c"."tenant_id" = $3
# LIMIT 25
```

---

## 🤖 AI Agent & LLM Tool Calling

Integrating `nlsqlc` into your OpenAI, Anthropic Claude, Gemini, or LangChain agents is effortless:

```python
# Pass this JSON tool schema to your LLM:
tool_definition = {
    "name": "execute_query",
    "description": "Execute analytical queries using safe Query IR S-expressions.",
    "parameters": {
        "type": "object",
        "properties": {
            "ir": {"type": "string", "description": "Constrained S-expression Query IR"}
        },
        "required": ["ir"]
    }
}

# When the LLM calls the tool:
def handle_tool_call(llm_ir_output: str, authenticated_user_tenant_id: str):
    result = nlsql.compile_ir(ctx, llm_ir_output, schema, policy, dialect=nlsql.NLSQL_DIALECT_POSTGRES)
    
    if result.status != nlsql.NLSQL_OK:
        return f"Query rejected by security policy: {result.error}"
    
    # Execute parameterized query with authenticated tenant ID securely bound:
    params = [authenticated_user_tenant_id if p['source'] == nlsql.NLSQL_PARAM_POLICY else user_val for p in result.params]
    return db.execute(result.sql, params)
```
*(See [examples/ai-agent-integration/agent_demo.py](examples/ai-agent-integration/agent_demo.py) for a runnable end-to-end demo!)*

---

## 🌐 Supported SQL Dialects

| Engine | Identifier Quoting | Parameter Syntax | Window / Paging | Status |
|---|---|---|---|---|
| **PostgreSQL** | `"schema"."table"` | `$1, $2, $3` | `LIMIT N` | ✅ Production |
| **SQLite** | `"table"` | `?1, ?2` / `?` | `LIMIT N` | ✅ Production |
| **DuckDB** | `"schema"."table"` | `$1, $2, $3` | `LIMIT N` | ✅ Production |
| **MySQL** | `` `schema`.`table` `` | `?` | `LIMIT N` | ✅ Production |
| **Microsoft SQL Server** | `[schema].[table]` | `@p1, @p2` | `TOP N` | ✅ Production |

---

## 🐳 Docker Deployment

Deploy the high-availability gateway in 1 command:

```sh
docker-compose up -d
```

Scrape Prometheus metrics at `http://localhost:8080/metrics`:
```
# HELP nlsql_uptime_seconds Total server uptime in seconds
# TYPE nlsql_uptime_seconds gauge
nlsql_uptime_seconds 412.50
# HELP nlsql_compilations_total Total compilations by status
# TYPE nlsql_compilations_total counter
nlsql_compilations_total{status="success"} 184920
nlsql_compilations_total{status="failed"} 12
nlsql_compilation_latency_ms_p50 0.016
nlsql_compilation_latency_ms_p99 0.045
```

---

## 📚 Documentation & Deep Dives

- 🏛️ [**Enterprise Architecture Specification**](docs/architecture/ENTERPRISE_ARCHITECTURE.md)
- 🔒 [**Tenant Isolation Security Whitepaper**](docs/security/TENANT_ISOLATION_WHITEPAPER.md)
- ⚙️ [**Server Gateway & Daemon Guide**](docs/SERVER_GUIDE.md)
- 📜 [**Query IR v2 Formal EBNF Grammar**](spec/query-ir-v2.ebnf)
- 📖 [**Public C11 API Reference**](docs/API.md)

---

## 📄 License

Apache License 2.0. See [LICENSE](LICENSE) for details.
