#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:?usage: tools/verify-release.sh VERSION}"
OUT="$ROOT/release"
ARTIFACT="$OUT/nlsqlc-${VERSION}.tar.gz"
CHECKSUM="$ARTIFACT.sha256"
STAGE="$OUT/nlsqlc-${VERSION}"
PROVENANCE="$ARTIFACT.provenance.slsa.json"
[[ -s "$ARTIFACT" && -s "$CHECKSUM" && -s "$PROVENANCE" && -d "$STAGE" ]] || { printf 'release files missing; run tools/release.sh %s first\n' "$VERSION" >&2; exit 2; }
sha256sum -c "$CHECKSUM"
(cd "$STAGE" && sha256sum -c SHA256SUMS)
python3 - "$ARTIFACT" "$PROVENANCE" "$VERSION" <<'PY'
import hashlib, json, pathlib, sys, tarfile
artifact = pathlib.Path(sys.argv[1]); provenance = json.loads(pathlib.Path(sys.argv[2]).read_text()); version = sys.argv[3]
expected = provenance['subject'][0]['digest']['sha256']
actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
assert provenance['subject'][0]['name'] == f'nlsqlc-{version}.tar.gz'
assert expected == actual, (expected, actual)
assert provenance['predicateType'] == 'https://slsa.dev/provenance/v1'
assert provenance['predicate']['buildDefinition']['buildType'] == 'https://nlsqlc.local/build/release/v1'
with tarfile.open(artifact, 'r:gz') as archive:
    names = archive.getnames()
assert f'nlsqlc-{version}/sbom.spdx.json' in names
print('release_verification_pass')
PY
