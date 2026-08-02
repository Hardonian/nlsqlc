#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REV="${1:-a7f411a}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git -C "$ROOT" show "$REV:include/nlsql/nlsql.h" > "$TMP/nlsql.h"
cc -std=c11 -Wall -Wextra -Werror -I"$TMP" -I"$ROOT/include" -c "$ROOT/src/nlsql.c" -o "$TMP/nlsql.o"
cat > "$TMP/old_consumer.c" <<'EOF'
#include "nlsql.h"
int main(void) { return nlsql_abi_version() == NLSQL_ABI_VERSION ? 0 : 1; }
EOF
cc -std=c11 -Wall -Wextra -Werror -I"$TMP" "$TMP/old_consumer.c" "$TMP/nlsql.o" -o "$TMP/old-consumer"
"$TMP/old-consumer"
printf 'abi_compat_pass revision=%s\n' "$REV"