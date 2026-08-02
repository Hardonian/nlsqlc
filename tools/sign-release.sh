#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:?usage: tools/sign-release.sh VERSION [GPG_KEY] }"
KEY="${2:-${GPG_KEY:-}}"
ARTIFACT="$ROOT/release/nlsqlc-${VERSION}.tar.gz"
CHECKSUM="$ARTIFACT.sha256"
[[ -n "$KEY" ]] || { printf 'GPG key is required; refusing unsigned provenance\n' >&2; exit 2; }
[[ -s "$ARTIFACT" && -s "$CHECKSUM" ]] || { printf 'release artifacts are missing; run tools/release.sh first\n' >&2; exit 2; }
command -v gpg >/dev/null || { printf 'gpg is unavailable\n' >&2; exit 127; }
gpg --batch --yes --local-user "$KEY" --armor --detach-sign --output "$ARTIFACT.asc" "$ARTIFACT"
gpg --batch --yes --local-user "$KEY" --armor --detach-sign --output "$CHECKSUM.asc" "$CHECKSUM"
gpg --batch --verify "$ARTIFACT.asc" "$ARTIFACT"
gpg --batch --verify "$CHECKSUM.asc" "$CHECKSUM"
printf 'SIGNED_ARTIFACT=%s\nSIGNED_CHECKSUM=%s\n' "$ARTIFACT.asc" "$CHECKSUM.asc"
