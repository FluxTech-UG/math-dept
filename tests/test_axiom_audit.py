"""Guard: every audited declaration rests on the standard axioms.

The Lean script emits one JSON object per declaration and then fails the build
if anything under `Results/`, `Defs/` or `Smoke` reaches for an axiom outside
{propext, Classical.choice, Quot.sound} plus the per-declaration allowlist.
`sorryAx` leaking from a conjecture into a result is caught here, which is the
failure the pure-Python fence cannot see.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from mdept import audit

REPO_ROOT = Path(__file__).resolve().parent.parent
STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def require_lean(reason: str) -> None:
    if os.environ.get("MATHDEPT_REQUIRE_LEAN") == "1":
        pytest.fail(f"MATHDEPT_REQUIRE_LEAN=1 but {reason}")
    pytest.skip(f"{reason}; set MATHDEPT_REQUIRE_LEAN=1 to make this a failure")


def test_audit_script_exists():
    assert (REPO_ROOT / "scripts" / "AxiomAudit.lean").is_file()


def test_allowlist_parses():
    for decl, axiom in audit.read_allowlist(REPO_ROOT):
        assert decl and axiom


def test_axiom_audit_passes():
    if shutil.which("lake") is None:
        require_lean("`lake` is not on PATH")
    result = subprocess.run(
        [sys.executable, "-m", "mdept.audit", "axioms", "--json"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=3600,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    payload = json.loads(result.stdout)
    allowlisted = {(d, a) for d, a in audit.read_allowlist(REPO_ROOT)}
    for decl, record in payload["declarations"].items():
        if ".Results." not in record["module"] and ".Defs." not in record["module"]:
            continue
        offending = {a for a in record["axioms"] if a not in STANDARD_AXIOMS and (decl, a) not in allowlisted}
        assert not offending, f"{decl} depends on {sorted(offending)}"


def test_cached_audit_is_fresh_when_present():
    cached = REPO_ROOT / "audit" / "latest.json"
    if not cached.is_file():
        pytest.skip("audit/latest.json is not committed yet; it appears with the first `make lean`")
    data = json.loads(cached.read_text(encoding="utf-8"))
    assert data["sources_sha256"] == audit.sources_sha256(REPO_ROOT), (
        "audit/latest.json is stale against the Lean sources; run `make lean`"
    )
