#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-/usr/local}"
BIN_DIR="${PREFIX}/bin"
LIB_DIR="${PREFIX}/lib"
INCLUDE_DIR="${PREFIX}/include/nlsql"
cd "$ROOT"
make clean
make all
install -d "$BIN_DIR" "$LIB_DIR" "$INCLUDE_DIR"
install -m 0755 nlsqlc "$BIN_DIR/nlsqlc"
install -m 0644 libnlsql.a "$LIB_DIR/libnlsql.a"
install -m 0644 include/nlsql/nlsql.h "$INCLUDE_DIR/nlsql.h"
"$BIN_DIR/nlsqlc" version
printf 'installed nlsqlc to %s\n' "$PREFIX"
