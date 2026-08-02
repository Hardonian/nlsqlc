#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
version="$(sed -n 's/^#define NLSQL_VERSION "\([0-9.]*\)"/\1/p' include/nlsql/nlsql.h)"
[[ -n "$version" ]] || { printf 'unable to read NLSQL_VERSION\n' >&2; exit 2; }
for file in CMakeLists.txt meson.build; do
  grep -F "${version}" "$file" >/dev/null || { printf 'version mismatch in %s\n' "$file" >&2; exit 1; }
done
grep -F "VERSION=\"\${1:-${version}}\"" tools/release.sh >/dev/null
grep -F "## 0.1.2" CHANGELOG.md >/dev/null
grep -F "${version}" README.md >/dev/null
printf 'release_consistency_pass version=%s\n' "$version"
