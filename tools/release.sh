#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-0.1.1}"
OUT="${ROOT}/release"
BUILD="${ROOT}/.release-build"
cd "$ROOT"
rm -rf "$BUILD" "$OUT"
mkdir -p "$OUT"
cp src/nlsql.c dist/nlsql.c
python3 - "$ROOT/dist/nlsql.c" <<'PY'
from pathlib import Path
p = Path(__import__('sys').argv[1])
s = p.read_text()
s = s.replace('#include "nlsql/nlsql.h"', '#include "nlsql.h"')
p.write_text(s)
PY
cmp -s <(sed 's/#include "nlsql.h"/#include "nlsql\/nlsql.h"/' dist/nlsql.c) src/nlsql.c
cc -std=c11 -O2 -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes -Wformat=2 -Wundef -Werror -Iinclude -c dist/nlsql.c -o "$BUILD-dist.o"
cmake -S . -B "$BUILD" -DCMAKE_BUILD_TYPE=Release -DNLSQL_BUILD_TESTS=ON -DNLSQL_BUILD_CLI=ON
cmake --build "$BUILD" --parallel
ctest --test-dir "$BUILD" --output-on-failure
ASAN_OPTIONS=detect_leaks=1 cc -std=c11 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Iinclude src/nlsql.c tests/test_core.c -o "$BUILD-asan"
ASAN_OPTIONS=detect_leaks=1 "$BUILD-asan" >/dev/null
STAGE="$OUT/nlsqlc-${VERSION}"
mkdir -p "$STAGE"
cp -a LICENSE NOTICE README.md CHANGELOG.md RELEASE_READINESS.md SECURITY.md include dist src cli examples spec tools CMakeLists.txt Makefile meson.build install.sh "$STAGE/"
printf 'nlsqlc %s\n' "$VERSION" > "$STAGE/VERSION"
find "$STAGE" -type f -print0 | sort -z | xargs -0 sha256sum > "$STAGE/SHA256SUMS"
python3 - "$STAGE" "$STAGE/sbom.spdx.json" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
files=[]
for p in sorted(root.rglob('*')):
    if p.is_file() and p != out:
        files.append({'SPDXID':'SPDXRef-'+str(len(files)+1),'fileName':str(p.relative_to(root)),'checksums':[{'algorithm':'SHA256','checksumValue':__import__('hashlib').sha256(p.read_bytes()).hexdigest()}]})
doc={'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT','name':'nlsqlc','documentNamespace':'https://nlsqlc.local/spdx/nlsqlc','files':files}
out.write_text(json.dumps(doc, indent=2)+'\n')
PY
TARBALL="$OUT/nlsqlc-${VERSION}.tar.gz"
tar -C "$OUT" -czf "$TARBALL" "nlsqlc-${VERSION}"
sha256sum "$TARBALL" > "$TARBALL.sha256"
rm -rf "$BUILD" "$BUILD-dist.o" "$BUILD-asan"
printf 'RELEASE_ARTIFACT=%s\nCHECKSUM=%s\n' "$TARBALL" "$TARBALL.sha256"
