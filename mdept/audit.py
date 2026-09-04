"""Three guards over the Lean side, and the JSON contract the ledger reads.

Run: `python -m mdept.audit {sorry|axioms|counterexamples|all} [--json] [--write PATH]`

- `sorry` is pure Python and always runs: it fences `sorry` to `*/Conjectures/`
  and enforces the one-file-per-entry naming and namespace rules.
- `axioms` shells out to Lean (`lake build`, then `lake env lean
  scripts/AxiomAudit.lean`) and parses one JSON object per declaration. A
  missing `lake` is an error here, never a skip: an audit that quietly did not
  run is worse than no audit.
- `counterexamples` executes every artifact and records whether its witness
  verified and whether it is exact.

`all --json --write audit/latest.json` produces the cached contract. The ledger
checker never invokes Lean; it reads that file and refuses it when
`sources_sha256` no longer matches the Lean sources on disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import CheckError, ConfigError
from . import config

LEAN_ENTRY_DIRS = ("Conjectures", "Results")
SORRY_RE = re.compile(r"\bsorry\b")
NAMESPACE_RE = re.compile(r"^namespace\s+(MathDept\.MD_\d{4})\s*$", re.MULTILINE)
ENTRY_STEM_RE = re.compile(r"^MD_\d{4}$")
AUDIT_SCRIPT = "scripts/AxiomAudit.lean"
CACHED_AUDIT = "audit/latest.json"
ALLOWLIST = "audit/axiom-allowlist.txt"
SCHEMA_VERSION = 1


# --- Lean source scanning (no toolchain required) ---------------------------


def strip_lean_comments(text: str) -> str:
    """Blank out `--` line comments and nested `/- -/` blocks, preserving lines."""
    out = []
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        two = text[i : i + 2]
        if depth == 0 and two == "--":
            end = text.find("\n", i)
            end = n if end == -1 else end
            out.append(" " * (end - i))
            i = end
            continue
        if two == "/-":
            depth += 1
            out.append("  ")
            i += 2
            continue
        if two == "-/" and depth > 0:
            depth -= 1
            out.append("  ")
            i += 2
            continue
        char = text[i]
        out.append(char if depth == 0 or char == "\n" else " ")
        i += 1
    return "".join(out)


def lean_files(root: Path) -> list[Path]:
    """Every .lean file under this repo's Lean libraries, sorted by path."""
    found: list[Path] = []
    for library in config.lean_roots(Path(root)):
        found.extend(library.rglob("*.lean"))
    return sorted(found)


def sources_sha256(root: Path) -> str:
    """A digest over every Lean source, so a cached audit can be refused when stale."""
    root = Path(root).resolve()
    digest = hashlib.sha256()
    for path in lean_files(root):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def type_hash(pretty_type: str) -> str:
    """The frozen-statement hash: sha256 of the compiler's pretty-printed type."""
    return hashlib.sha256(pretty_type.encode("utf-8")).hexdigest()


def sorry_violations(root: Path) -> list[dict]:
    """Every breach of the `sorry` fence and the entry-file naming rules."""
    root = Path(root).resolve()
    violations: list[dict] = []
    seen: dict[str, dict[str, Path]] = {}
    for path in lean_files(root):
        rel = str(path.relative_to(root))
        parts = path.relative_to(root).parts
        stage = parts[1] if len(parts) > 2 else None
        text = path.read_text(encoding="utf-8")
        code = strip_lean_comments(text)

        if stage in LEAN_ENTRY_DIRS:
            if not ENTRY_STEM_RE.match(path.stem):
                violations.append({"file": rel, "line": 1,
                                   "reason": f"an entry file is named MD_####.lean, found {path.name!r}"})
            else:
                seen.setdefault(path.stem, {})[stage] = path
                if not NAMESPACE_RE.search(code):
                    violations.append({"file": rel, "line": 1,
                                       "reason": f"missing `namespace MathDept.{path.stem}`; "
                                                 "declarations keep that namespace in both libraries"})
        if stage == "Conjectures":
            continue
        for number, line in enumerate(code.splitlines(), start=1):
            if SORRY_RE.search(line):
                violations.append({"file": rel, "line": number,
                                   "reason": "`sorry` outside */Conjectures/; "
                                             "an unfinished proof lives in Conjectures until it closes"})
    for stem, stages in sorted(seen.items()):
        if len(stages) > 1:
            violations.append({
                "file": str(stages["Results"].relative_to(root)),
                "line": 1,
                "reason": f"{stem} also exists under Conjectures/; an entry has exactly one Lean file",
            })
    return violations


def read_allowlist(root: Path) -> list[tuple[str, str]]:
    """`<decl> <axiom>` pairs from audit/axiom-allowlist.txt. Comments start with #."""
    path = Path(root) / ALLOWLIST
    if not path.is_file():
        return []
    pairs = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise CheckError(
                f"I5 formal pointer: {ALLOWLIST}:{number}: field '<allowlist>': "
                f"expected '<decl> <axiom>', found {raw!r}"
            )
        pairs.append((parts[0], parts[1]))
    return pairs


# --- the Lean-dependent half ------------------------------------------------


def lean_available() -> bool:
    return shutil.which("lake") is not None


def _require_lake() -> None:
    if not lean_available():
        raise ConfigError(
            "`lake` is not on PATH, so the axiom audit cannot run. "
            "Install the toolchain with elan and run `lake exe cache get` before `make lean`."
        )


def _run(command: list[str], root: Path, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout)


def run_axiom_audit(root: Path, build_timeout: int = 3600, audit_timeout: int = 1800) -> dict:
    """Build the package, run the Lean audit script, and parse its JSON lines."""
    root = Path(root).resolve()
    _require_lake()
    script = root / AUDIT_SCRIPT
    if not script.is_file():
        raise ConfigError(f"{AUDIT_SCRIPT} is missing; it is what emits the per-declaration JSON")
    build = _run(["lake", "build"], root, build_timeout)
    if build.returncode != 0:
        raise CheckError(f"I5 formal pointer: lakefile.toml: field '<lake build>': "
                         f"build failed (exit {build.returncode})\n{build.stdout[-4000:]}{build.stderr[-4000:]}")
    result = _run(["lake", "env", "lean", AUDIT_SCRIPT], root, audit_timeout)
    declarations: dict[str, dict] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        record = json.loads(line)
        declarations[record["decl"]] = {
            "module": record["module"],
            "axioms": record.get("axioms") or [],
            "type": record.get("type", ""),
        }
    if result.returncode != 0:
        raise CheckError(f"I5 formal pointer: {AUDIT_SCRIPT}: field '<axiom audit>': "
                         f"the audit rejected the build\n{result.stderr[-4000:]}")
    return declarations


def toolchain(root: Path) -> str:
    path = Path(root) / "lean-toolchain"
    return path.read_text(encoding="utf-8").strip() if path.is_file() else ""


def mathlib_rev(root: Path) -> str:
    """The Mathlib revision Lake actually resolved, from the committed manifest."""
    path = Path(root) / "lake-manifest.json"
    if not path.is_file():
        return ""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for package in manifest.get("packages", []):
        if package.get("name") == "mathlib":
            return package.get("rev") or package.get("inputRev") or ""
    return ""


def counterexample_report(root: Path) -> dict:
    from . import refute as refute_mod

    return refute_mod.run_all(Path(root) / "counterexamples")


def full_audit(root: Path) -> dict:
    """The cached contract: `python -m mdept.audit all --json --write audit/latest.json`."""
    root = Path(root).resolve()
    violations = sorry_violations(root)
    declarations = run_axiom_audit(root)
    counterexamples = counterexample_report(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": not violations and all(c["verified"] for c in counterexamples.values()),
        "sorry_violations": violations,
        "sources_sha256": sources_sha256(root),
        "lean_toolchain": toolchain(root),
        "mathlib_rev": mathlib_rev(root),
        "declarations": declarations,
        "counterexamples": counterexamples,
    }


def read_cached_audit(root: Path) -> dict:
    path = Path(root) / CACHED_AUDIT
    if not path.is_file():
        raise ConfigError(f"{CACHED_AUDIT} does not exist; generate it with `make lean`")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ConfigError(
            f"{CACHED_AUDIT} is schema_version {data.get('schema_version')}, this package reads {SCHEMA_VERSION}"
        )
    return data


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.audit", description=__doc__.splitlines()[0])
    parser.add_argument("what", choices=("sorry", "axioms", "counterexamples", "all"))
    parser.add_argument("--root", default=None, help="repo root (default: nearest ancestor with ledger/)")
    parser.add_argument("--json", action="store_true", help="emit the machine view on stdout")
    parser.add_argument("--write", default=None, help="also write the JSON to this path")
    args = parser.parse_args(argv)

    root = config.find_repo_root(args.root) if args.root is None else Path(args.root).resolve()
    try:
        if args.what == "sorry":
            violations = sorry_violations(root)
            payload = {"ok": not violations, "sorry_violations": violations}
        elif args.what == "axioms":
            declarations = run_axiom_audit(root)
            payload = {"ok": True, "declarations": declarations,
                       "sources_sha256": sources_sha256(root)}
        elif args.what == "counterexamples":
            report = counterexample_report(root)
            payload = {"ok": all(c["verified"] for c in report.values()), "counterexamples": report}
        else:
            payload = full_audit(root)
    except (CheckError, ConfigError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.write:
        target = Path(args.write)
        target = target if target.is_absolute() else root / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    if args.json:
        print(text, end="")
    if not payload["ok"]:
        for violation in payload.get("sorry_violations", []):
            print(f"FAIL {violation['file']}:{violation['line']}: {violation['reason']}", file=sys.stderr)
        for entry_id, record in sorted(payload.get("counterexamples", {}).items()):
            if not record["verified"]:
                print(f"FAIL {record['file']}: witness for {entry_id} did not verify", file=sys.stderr)
        return 1
    if not args.json:
        print(f"ok audit {args.what} [{config.repo_kind(root)} repo]")
    return 0


if __name__ == "__main__":
    # Dispatch to the canonical module: under `python -m`, this file runs as `__main__`
    # and its classes would be distinct from the `mdept.audit` ones that artifacts and
    # callers import, breaking isinstance checks.
    from mdept.audit import main as _main

    raise SystemExit(_main())
