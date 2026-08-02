#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-0.1.2}"
OUT="${ROOT}/release"
BUILD="${ROOT}/.release-build"
cd "$ROOT"
rm -rf "$BUILD" "$OUT"
mkdir -p "$OUT"
cp src/nlsql.c dist/nlsql.c
cp include/nlsql/nlsql.h dist/nlsql.h
python3 - "$ROOT/dist/nlsql.c" <<'PY'
from pathlib import Path
p = Path(__import__('sys').argv[1])
s = p.read_text()
s = s.replace('#include "nlsql/nlsql.h"', '#include "nlsql.h"')
p.write_text(s)
PY
cmp -s <(sed 's/#include "nlsql.h"/#include "nlsql\/nlsql.h"/' dist/nlsql.c) src/nlsql.c
cc -std=c11 -O2 -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes -Wformat=2 -Wundef -Werror -Idist -c dist/nlsql.c -o "$BUILD-dist.o"
cmake -S . -B "$BUILD" -DCMAKE_BUILD_TYPE=Release -DNLSQL_BUILD_TESTS=ON -DNLSQL_BUILD_CLI=ON
cmake --build "$BUILD" --parallel
ctest --test-dir "$BUILD" --output-on-failure
ASAN_OPTIONS=detect_leaks=1 cc -std=c11 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Iinclude src/nlsql.c tests/test_core.c -o "$BUILD-asan"
ASAN_OPTIONS=detect_leaks=1 "$BUILD-asan" >/dev/null
STAGE="$OUT/nlsqlc-${VERSION}"
mkdir -p "$STAGE"
cp -a LICENSE NOTICE README.md CHANGELOG.md RELEASE_READINESS.md RELEASE_MATRIX.md CLOSURE_REGISTER.md SECURITY.md FUZZING.md include dist src cli examples spec docs bindings tools fuzz tests oss-fuzz CMakeLists.txt Makefile meson.build install.sh "$STAGE/"
printf 'nlsqlc %s\n' "$VERSION" > "$STAGE/VERSION"
find "$STAGE" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$STAGE" -type f -name '*.o' -delete
SOURCE_EPOCH="${SOURCE_DATE_EPOCH:-$(git show -s --format=%ct HEAD)}"
[[ "$SOURCE_EPOCH" =~ ^[0-9]+$ ]] || { printf 'SOURCE_DATE_EPOCH must be an integer\n' >&2; exit 2; }
export SOURCE_EPOCH
PROVENANCE="$OUT/nlsqlc-${VERSION}.tar.gz.provenance.slsa.json"
python3 - "$STAGE" "$PROVENANCE" "$VERSION" "$SOURCE_EPOCH" <<'PY'
import hashlib, json, pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
version = sys.argv[3]; epoch = int(sys.argv[4])
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
files = []
for path in sorted(root.rglob('*')):
    if path.is_file() and path != out:
        files.append({'name': str(path.relative_to(root)), 'digest': {'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}})
provenance = {
    '_type': 'https://in-toto.io/Statement/v1',
    'subject': [{'name': f'nlsqlc-{version}.tar.gz', 'digest': {'sha256': 'GENERATED_AFTER_ARCHIVE'}}],
    'predicateType': 'https://slsa.dev/provenance/v1',
    'predicate': {
        'buildDefinition': {
            'buildType': 'https://nlsqlc.local/build/release/v1',
            'externalParameters': {'version': version, 'sourceDateEpoch': epoch},
            'resolvedDependencies': [{'uri': f'git+local://nlsqlc@{commit}', 'digest': {'sha1': commit}}],
        },
        'runDetails': {'builder': {'id': 'https://nlsqlc.local/builder/local-script'}, 'metadata': {'invocationId': commit}},
        'byproducts': files,
    },
}
out.write_text(json.dumps(provenance, indent=2) + '\n')
PY
find "$STAGE" -type f ! -name 'SHA256SUMS' -print0 | sort -z | xargs -0 sha256sum > "$STAGE/SHA256SUMS"
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
export TAR_OPTIONS="--sort=name --mtime=@${SOURCE_EPOCH} --owner=0 --group=0 --numeric-owner"
tar -C "$OUT" -czf "$TARBALL" "nlsqlc-${VERSION}"
ARCHIVE_SHA="$(sha256sum "$TARBALL" | awk '{print $1}')"
python3 - "$PROVENANCE" "$ARCHIVE_SHA" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1]); data = json.loads(p.read_text())
data['subject'][0]['digest']['sha256'] = sys.argv[2]
p.write_text(json.dumps(data, indent=2) + '\n')
PY
sha256sum "$TARBALL" > "$TARBALL.sha256"
rm -rf "$BUILD" "$BUILD-dist.o" "$BUILD-asan"
printf 'RELEASE_ARTIFACT=%s\nCHECKSUM=%s\nPROVENANCE=%s\n' "$TARBALL" "$TARBALL.sha256" "$PROVENANCE"
