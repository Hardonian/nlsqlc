"""Interactive CLI REPL for nlsqlc Query IR Compiler."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bindings" / "python"))
import nlsql

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

BANNER = f"""{CYAN}{BOLD}
   ____  __          __         
  / __ \\/ /_____ ___/ /______   
 / / / / // (_-</ _  / __/ -_)  {MAGENTA}v0.1.2 Enterprise Interactive REPL{CYAN}
/_/ /_/_/___/___/\\_,_/\\__/\\__/   {DIM}Sub-microsecond Multi-Tenant SQL Compiler{RESET}
"""

HELP_TEXT = f"""
{BOLD}Commands:{RESET}
  {CYAN}\\d [postgres|sqlite|duckdb|mysql|sqlserver]{RESET} : Switch target SQL dialect
  {CYAN}\\s{RESET}                                      : Show loaded schema tables & columns
  {CYAN}\\p{RESET}                                      : Show active tenant isolation policy
  {CYAN}\\b [N]{RESET}                                   : Run compile benchmark (default: 5000 iter)
  {CYAN}\\e{RESET}                                      : Load and compile a sample multi-join query
  {CYAN}\\q{RESET}, {CYAN}exit{RESET}, {CYAN}quit{RESET}                       : Exit the REPL
  {CYAN}\\h{RESET}, {CYAN}help{RESET}                             : Show this help menu
"""

SAMPLE_QUERY = """(nlsql 2
  (query
    (from orders o)
    (join inner customers c (eq (column o customer_id) (column c id)))
    (select
      (field (column o id) order_id)
      (field (column c region) region)
      (field (sum (column o total_amount)) total_revenue))
    (where (gt (column o total_amount) (param min_val decimal)))
    (group-by (column c region))
    (order-by (ref total_revenue) desc)
    (limit 10)))"""


def main():
    print(BANNER)
    print(f"Type {CYAN}\\h{RESET} for help, {CYAN}\\e{RESET} for sample query, or paste any Query IR.\n")

    ctx = nlsql.Context()
    schema = nlsql.Schema(ctx, [
        ("public", "orders", [
            ("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY),
            ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY),
            ("customer_id", nlsql.NLSQL_TYPE_INT64, 0),
            ("total_amount", nlsql.NLSQL_TYPE_DECIMAL, 0),
            ("status", nlsql.NLSQL_TYPE_TEXT, 0),
        ]),
        ("public", "customers", [
            ("id", nlsql.NLSQL_TYPE_INT64, nlsql.NLSQL_COLUMN_PRIMARY_KEY),
            ("tenant_id", nlsql.NLSQL_TYPE_UUID, nlsql.NLSQL_COLUMN_TENANT_KEY),
            ("region", nlsql.NLSQL_TYPE_TEXT, 0),
            ("tier", nlsql.NLSQL_TYPE_TEXT, 0),
        ]),
    ], foreign_keys=[("public", "orders", "customer_id", "public", "customers", "id")])

    policy = nlsql.Policy(
        ctx,
        allow=[("public", "orders"), ("public", "customers")],
        tenant=[("public", "orders", "tenant_id", nlsql.NLSQL_TYPE_UUID), ("public", "customers", "tenant_id", nlsql.NLSQL_TYPE_UUID)],
        runtime_tenant=("tenant_id", nlsql.NLSQL_TYPE_UUID),
    )

    current_dialect = nlsql.NLSQL_DIALECT_POSTGRES
    dialect_names = {
        nlsql.NLSQL_DIALECT_POSTGRES: "PostgreSQL",
        nlsql.NLSQL_DIALECT_SQLITE: "SQLite",
        nlsql.NLSQL_DIALECT_DUCKDB: "DuckDB",
        nlsql.NLSQL_DIALECT_MYSQL: "MySQL",
        nlsql.NLSQL_DIALECT_SQLSERVER: "SQL Server",
    }

    buffer: list[str] = []

    while True:
        try:
            d_name = dialect_names[current_dialect]
            prompt = f"{CYAN}nlsqlc{RESET}[{GREEN}{d_name}{RESET}]> " if not buffer else f"{DIM}... {RESET}"
            line = input(prompt)
            line_str = line.strip()

            if not buffer:
                if line_str in ("\\q", "exit", "quit"):
                    print(f"{DIM}Goodbye!{RESET}")
                    break
                if line_str in ("\\h", "help"):
                    print(HELP_TEXT)
                    continue
                if line_str == "\\e":
                    line_str = SAMPLE_QUERY
                elif line_str.startswith("\\d"):
                    parts = line_str.split()
                    if len(parts) > 1:
                        target = parts[1].lower()
                        d_map = {
                            "postgres": nlsql.NLSQL_DIALECT_POSTGRES,
                            "postgresql": nlsql.NLSQL_DIALECT_POSTGRES,
                            "sqlite": nlsql.NLSQL_DIALECT_SQLITE,
                            "duckdb": nlsql.NLSQL_DIALECT_DUCKDB,
                            "mysql": nlsql.NLSQL_DIALECT_MYSQL,
                            "sqlserver": nlsql.NLSQL_DIALECT_SQLSERVER,
                        }
                        if target in d_map:
                            current_dialect = d_map[target]
                            print(f"Dialect switched to {GREEN}{dialect_names[current_dialect]}{RESET}")
                        else:
                            print(f"{RED}Unknown dialect: {target}{RESET}")
                    else:
                        print(f"Current dialect: {GREEN}{dialect_names[current_dialect]}{RESET}")
                    continue
                elif line_str == "\\s":
                    print(f"\n{BOLD}Loaded Schema:{RESET}")
                    for (sc, tb), tdef in schema.py_schema.tables.items():
                        print(f"  {CYAN}{sc}.{tb}{RESET}")
                        for (csc, ctb, cn), cdef in schema.py_schema.columns.items():
                            if csc == sc and ctb == tb:
                                flags = []
                                if cdef.flags & nlsql.NLSQL_COLUMN_PRIMARY_KEY: flags.append("PK")
                                if cdef.flags & nlsql.NLSQL_COLUMN_TENANT_KEY: flags.append("TENANT_KEY")
                                f_str = f" {YELLOW}[{', '.join(flags)}]{RESET}" if flags else ""
                                print(f"    • {cn}: {nlsql.NLSQL_TYPE_NAMES.get(cdef.type, 'unknown')}{f_str}")
                    print()
                    continue
                elif line_str == "\\p":
                    print(f"\n{BOLD}Tenant Isolation Policy:{RESET}")
                    print(f"  Runtime Tenant Parameter: {GREEN}${policy.py_policy.runtime_tenant_name}{RESET}")
                    print(f"  Allowed Tables: {', '.join(f'{sc}.{tb}' for sc, tb in policy.py_policy.allowed_tables)}")
                    print(f"  Tenant Rules: {', '.join(f'{sc}.{tb}.{col}' for (sc, tb), (col, _) in policy.py_policy.tenant_rules.items())}\n")
                    continue
                elif line_str.startswith("\\b"):
                    parts = line_str.split()
                    iters = int(parts[1]) if len(parts) > 1 else 5000
                    print(f"{DIM}Running benchmark with {iters} iterations...{RESET}")
                    bench = nlsql.benchmark(SAMPLE_QUERY, iterations=iters)
                    print(f"  Engine: {CYAN}{bench['engine']}{RESET}")
                    print(f"  Throughput: {GREEN}{bench['queries_per_second']:,.1f} queries/sec{RESET}")
                    print(f"  Average Latency: {YELLOW}{bench['latency_us']:.2f} µs{RESET}\n")
                    continue

            # Multi-line handling based on parentheses balance
            buffer.append(line)
            combined = "\n".join(buffer).strip()
            open_p = combined.count("(")
            close_p = combined.count(")")

            if open_p > 0 and open_p <= close_p:
                buffer.clear()
                t0 = time.perf_counter()
                res = nlsql.compile_ir(ctx, combined, schema, policy, dialect=current_dialect)
                elapsed_us = (time.perf_counter() - t0) * 1_000_000

                if res.status == nlsql.NLSQL_OK:
                    print(f"\n{GREEN}{BOLD}✓ Compiled SQL:{RESET}")
                    print(f"{res.sql}\n")
                    if res.params:
                        print(f"{BOLD}Bound Parameters:{RESET}")
                        for p in res.params:
                            p_type = nlsql.NLSQL_TYPE_NAMES.get(p['type'], 'unknown')
                            source_label = f"{YELLOW}TENANT_ISOLATION_ENFORCED{RESET}" if p['source'] == nlsql.NLSQL_PARAM_POLICY else f"{CYAN}USER_INPUT{RESET}"
                            print(f"  ${p['position']}: {BOLD}{p['name']}{RESET} ({p_type}) [{source_label}]")
                    risk_str = f"{GREEN}LOW (Isolated){RESET}" if res.risk == nlsql.NLSQL_RISK_LOW else f"{YELLOW}MODERATE{RESET}"
                    print(f"{DIM}Metrics: complexity={res.complexity} | risk={risk_str} | latency={elapsed_us:.1f}µs{RESET}\n")
                else:
                    print(f"\n{RED}{BOLD}✗ Compilation Error:{RESET} {res.error}")
                    print(f"{DIM}Security Guarantee: Failed closed at compiler boundary.{RESET}\n")
                res.close()
            elif open_p == 0 and combined:
                buffer.clear()
                print(f"{RED}Invalid input: S-expression must start with '(' (type \\h for help){RESET}")

        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Exiting nlsqlc REPL...{RESET}")
            break


if __name__ == "__main__":
    main()
