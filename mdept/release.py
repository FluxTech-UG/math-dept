"""Move a settled entry from the private repo into this public one.

Run: `python -m mdept.release MD_0007 [--dry-run]`

A release moves files and abstracts provenance. It never rewrites the
statement, never renumbers, and never renames a Lean declaration: entries in
both libraries live in `namespace MathDept.MD_0007`, so a consumer that cites
`MathDept.MD_0007.statement` keeps citing the same name after the move. Only
the module path changes, from `MathDeptPrivate.Results.MD_0007` to
`MathDept.Results.MD_0007`.

What is dropped, and why: `raised_by.doc`, `raised_by.anchor` and
`raised_by.application` describe a consumer's internal document and its
reasoning, so they stay private. Evidence rows pointing at `sources/` or
`triage/` are dropped for the same reason, and because a public path that does
not resolve is a dead pointer. What survives is `repo`, a one-line neutral
`domain`, and the who/date/model credit trail, which is the point of recording
provenance at all.

After the move both repos are regenerated and re-checked. The Lean audit is
required exactly when the entry carries a `formal.decl`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from . import CheckError, ConfigError
from . import config, index, parse, schema

MOVABLE_STATUSES = ("cited", "proven-formal", "proven-informal", "refuted")


def _load_entry(root: Path, entry_id: str):
    path = Path(root) / "ledger" / f"{entry_id}.md"
    if not path.is_file():
        raise CheckError(f"I1 filename: {path}: field '<file>': no such entry")
    front, front_text, body = parse.load_front_matter(path)
    return parse.Entry(path=path, root=Path(root).resolve(), front=front, front_text=front_text, body=body)


def abstract_provenance(front: dict) -> dict:
    """Return a copy of the front matter with every private-only field removed."""
    public = {key: front[key] for key in front}
    raised_by = public["provenance"]["raised_by"]
    if raised_by is not None:
        if not raised_by.get("domain"):
            raise CheckError(
                "I3 schema: provenance.raised_by.domain: field 'domain': "
                "a release needs a one-line neutral domain; the private doc and anchor do not survive it"
            )
        public["provenance"] = dict(public["provenance"])
        public["provenance"]["raised_by"] = {
            "repo": raised_by["repo"],
            "domain": raised_by["domain"],
            "doc": None,
            "anchor": None,
            "application": None,
        }
    public["evidence"] = [
        item for item in front["evidence"] if item["kind"] not in schema.PRIVATE_EVIDENCE_KINDS
    ]
    formal = dict(public["formal"])
    if formal["file"]:
        formal["file"] = formal["file"].replace("MathDeptPrivate/", "MathDept/", 1)
    public["formal"] = formal
    return public


def plan_moves(private: Path, public: Path, entry) -> list[tuple[Path, Path]]:
    """Every (source, destination) pair this release performs."""
    entry_id = entry.id
    moves = [(entry.path, public / "ledger" / f"{entry_id}.md")]
    lean_file = entry.at("formal.file")
    if lean_file:
        source = private / lean_file
        if not source.is_file():
            raise CheckError(f"I5 formal pointer: {source}: field 'formal.file': does not exist")
        text = source.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("import MathDeptPrivate"):
                raise CheckError(
                    f"I5 formal pointer: {lean_file}: field '<import>': "
                    f"{line.strip()!r} imports a private module, so this entry cannot be released. "
                    "Release what it depends on first, or inline the definition."
                )
        moves.append((source, public / lean_file.replace("MathDeptPrivate/", "MathDept/", 1)))
    proof = private / "proofs" / f"{entry_id}.md"
    if proof.is_file():
        moves.append((proof, public / "proofs" / f"{entry_id}.md"))
    for artifact in sorted((private / "counterexamples").glob(f"{entry_id}_*.py")):
        moves.append((artifact, public / "counterexamples" / artifact.name))
    return moves


def release(entry_id: str, public: Path, private: Path, dry_run: bool = False) -> dict:
    public, private = Path(public).resolve(), Path(private).resolve()
    if not schema.ID_RE.match(entry_id):
        raise CheckError(f"I1 filename: {entry_id}: field '<id>': not an ID of the form MD_0007")
    if (public / "ledger" / f"{entry_id}.md").exists():
        raise CheckError(f"I2 permanence: ledger/{entry_id}.md: field '<file>': already released")

    entry = _load_entry(private, entry_id)
    if entry.status not in MOVABLE_STATUSES:
        raise CheckError(
            f"I4 status/evidence: {entry.rel}: field 'status': {entry.status!r} is not releasable; "
            f"a release publishes a settled result, one of {list(MOVABLE_STATUSES)}"
        )
    moves = plan_moves(private, public, entry)
    public_front = abstract_provenance(entry.front)
    plan = {"entry": entry_id, "moves": [(str(s), str(d)) for s, d in moves], "dry_run": dry_run}
    if dry_run:
        return plan

    for source, destination in moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))

    target = public / "ledger" / f"{entry_id}.md"
    dumped = yaml.dump(public_front, sort_keys=False, default_flow_style=False, allow_unicode=True).rstrip("\n")
    target.write_text(f"---\n{dumped}\n---\n{entry.body}", encoding="utf-8")

    for root in (private, public):
        _regenerate(root)
    plan["checks"] = [_verify(root, needs_lean=bool(entry.at("formal.decl"))) for root in (private, public)]
    return plan


def _regenerate(root: Path) -> None:
    script = root / "scripts" / "gen_root.py"
    if script.is_file():
        result = subprocess.run(
            [sys.executable, "scripts/gen_root.py", "--write", "--lib", config.lean_lib(root)],
            cwd=root, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise CheckError(f"I16 generated: {root}/scripts/gen_root.py: field '<root>': {result.stderr.strip()}")
    index.write(root)


def _verify(root: Path, needs_lean: bool) -> dict:
    command = [sys.executable, "-m", "mdept.check", "--root", str(root), "--run-counterexamples"]
    if needs_lean:
        command.append("--lean")
    environment = dict(os.environ, MATHDEPT_REQUIRE_LEAN="1")
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, env=environment)
    if result.returncode != 0:
        raise CheckError(
            f"I16 generated: {root}: field '<check>': the release left the repo failing its own checks\n"
            f"{result.stdout}{result.stderr}"
        )
    return {"root": str(root), "stdout": result.stdout.strip()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.release", description=__doc__.splitlines()[0])
    parser.add_argument("entry", help="the entry to release, for example MD_0007")
    parser.add_argument("--root", default=None, help="the public repo (default: nearest ancestor with ledger/)")
    parser.add_argument("--private", default=None, help="the private repo (default: MATHDEPT_PRIVATE or the sibling)")
    parser.add_argument("--dry-run", action="store_true", help="print the moves without performing them")
    args = parser.parse_args(argv)

    try:
        public = config.find_repo_root(args.root) if args.root is None else Path(args.root).resolve()
        if config.is_private(public):
            raise ConfigError(f"{public} is the private repo; release moves INTO the public one")
        private = Path(args.private).resolve() if args.private else config.private_root(public)
        if private is None:
            raise ConfigError(
                "no private repo found. Set MATHDEPT_PRIVATE or place math-dept-private beside this repo."
            )
        plan = release(args.entry, public, private, args.dry_run)
    except (CheckError, ConfigError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    verb = "would move" if args.dry_run else "moved"
    for source, destination in plan["moves"]:
        print(f"{verb} {source} -> {destination}")
    if not args.dry_run:
        print(f"ok released {plan['entry']}; both repos regenerated and checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
