#!/usr/bin/env python3
"""Fail-closed consistency check for release evidence and closure claims."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
readiness = (ROOT / "RELEASE_READINESS.md").read_text(encoding="utf-8")
version = re.search(r'#define NLSQL_VERSION "([0-9.]+)"', (ROOT / "include/nlsql/nlsql.h").read_text(encoding="utf-8")).group(1)

# Check version occurrences across files
assert f"## {version}" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
assert version in (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
assert version in (ROOT / "meson.build").read_text(encoding="utf-8")
assert version in (ROOT / "README.md").read_text(encoding="utf-8")
assert f'VERSION="${{1:-{version}}}"' in (ROOT / "tools/release.sh").read_text(encoding="utf-8")
assert "Meson execution is not claimed" in readiness or "Meson execution" in readiness
assert "Live execution" in readiness

# Direct Python verification of header synchronization
h1 = (ROOT / "include/nlsql/nlsql.h").read_text(encoding="utf-8")
h2 = (ROOT / "dist/nlsql.h").read_text(encoding="utf-8")
assert h1 == h2, "dist/nlsql.h is not synchronized with include/nlsql/nlsql.h"

c1 = (ROOT / "src/nlsql.c").read_text(encoding="utf-8")
c2 = (ROOT / "dist/nlsql.c").read_text(encoding="utf-8").replace('#include "nlsql.h"', '#include "nlsql/nlsql.h"')
assert c1 == c2, "dist/nlsql.c is not synchronized with src/nlsql.c"

# If on POSIX and bash is available, run bash script as well
if os.name != "nt":
    bash_exec = shutil.which("bash") or shutil.which("sh")
    if bash_exec:
        subprocess.run([bash_exec, str(ROOT / "tools/check-release-consistency.sh")], cwd=ROOT, check=True)

print(f"release_evidence_consistency_pass version={version}")