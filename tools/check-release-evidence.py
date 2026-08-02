#!/usr/bin/env python3
"""Fail-closed consistency check for release evidence and closure claims."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
readiness = (ROOT / "RELEASE_READINESS.md").read_text()
version = re.search(r'#define NLSQL_VERSION "([0-9.]+)"', (ROOT / "include/nlsql/nlsql.h").read_text()).group(1)
assert f"## {version}" in (ROOT / "CHANGELOG.md").read_text()
assert version in (ROOT / "CMakeLists.txt").read_text()
assert version in (ROOT / "meson.build").read_text()
assert "Meson execution is not claimed" in readiness or "Meson execution" in readiness
assert "Live execution" in readiness
subprocess.run([str(ROOT / "tools/check-release-consistency.sh")], cwd=ROOT, check=True)
print(f"release_evidence_consistency_pass version={version}")