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

A release is all or nothing. Everything checkable is checked before a single
file moves (the rewritten entry against the public schema, every source present,
every destination free, every surviving path resolving after the move), and if
the post-move verification fails anyway, every move is undone and the private
entry restored before the error is raised. A half-released entry, moved out of
the private repo and rejected by the public one, would leave both repos failing
their own checks with the entry in neither.

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

PRIVATE_LIB_PREFIX = "MathDeptPrivate/"
PUBLIC_LIB_PREFIX = "MathDept/"


def publicize(rel: str) -> str:
    """A private repo-relative path rewritten to its public counterpart.

    Only the library directory changes. Everything else (`proofs/`,
    `counterexamples/`) has the same name in both repos.
    """
    if rel.startswith(PRIVATE_LIB_PREFIX):
        return PUBLIC_LIB_PREFIX + rel[len(PRIVATE_LIB_PREFIX):]
    return rel


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
    # Private-only rows are dropped; every surviving row follows its file across.
    # A row left pointing at MathDeptPrivate/ would be a dead pointer the moment
    # the entry lands, which is exactly what I4 refuses.
    public["evidence"] = [
        {"kind": item["kind"], "path": publicize(item["path"])}
        for item in front["evidence"]
        if item["kind"] not in schema.PRIVATE_EVIDENCE_KINDS
    ]
    formal = dict(public["formal"])
    if formal["file"]:
        formal["file"] = publicize(formal["file"])
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
        moves.append((source, public / publicize(lean_file)))
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

    # Everything knowable before the first byte moves. A dry run gets the same
    # answer as a real one, which is the point of having a dry run.
    preflight(entry, public_front, moves, public)
    if dry_run:
        return plan

    target = public / "ledger" / f"{entry_id}.md"
    original_entry_text = entry.path.read_text(encoding="utf-8")
    completed: list[tuple[Path, Path]] = []
    try:
        for source, destination in moves:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            completed.append((source, destination))

        dumped = yaml.dump(public_front, sort_keys=False, default_flow_style=False,
                           allow_unicode=True).rstrip("\n")
        target.write_text(f"---\n{dumped}\n---\n{entry.body}", encoding="utf-8")

        for root in (private, public):
            _regenerate(root)
        plan["checks"] = [_verify(root, needs_lean=bool(entry.at("formal.decl")))
                          for root in (private, public)]
    except BaseException as failure:
        _roll_back(completed, entry.path, original_entry_text)
        for root in (private, public):
            _regenerate(root)
        raise CheckError(
            f"I4 status/evidence: ledger/{entry_id}.md: field '<release>': "
            f"the release was rolled back and both repos are as they were. "
            f"The failure was: {failure}"
        ) from failure
    return plan


def preflight(entry, public_front: dict, moves: list, public: Path) -> None:
    """Refuse a release that cannot land, before anything moves.

    Four questions, in the order that makes the error most useful: does the
    rewritten entry satisfy the PUBLIC schema, is every source still there, is
    every destination free, and will every path the public entry names actually
    resolve once the moves are done.
    """
    target_entry = f"ledger/{entry.id}.md"
    schema.validate_front(public_front, target_entry, "public")

    for source, destination in moves:
        if not source.exists():
            raise CheckError(
                f"I4 status/evidence: {source}: field '<source>': "
                "this release would move a file that is not there. Nothing has been moved."
            )
        if destination.exists():
            raise CheckError(
                f"I2 permanence: {destination}: field '<destination>': "
                "already exists in the public repo. Nothing has been moved."
            )

    landing = {d.resolve() for _, d in moves}

    def resolves(rel: str) -> bool:
        candidate = (public / rel).resolve()
        return candidate in landing or candidate.exists()

    for i, item in enumerate(public_front["evidence"]):
        if not resolves(item["path"]):
            raise CheckError(
                f"I4 status/evidence: {target_entry}: field 'evidence[{i}].path': "
                f"{item['path']} would not exist in the public repo after this release, so the "
                "entry would land failing its own check. Nothing has been moved. Release what "
                "this points at first, or drop the row."
            )

    formal_file = public_front["formal"]["file"]
    if formal_file and not resolves(formal_file):
        raise CheckError(
            f"I5 formal pointer: {target_entry}: field 'formal.file': "
            f"{formal_file} would not exist in the public repo after this release. "
            "Nothing has been moved."
        )


def _roll_back(completed: list, entry_path: Path, original_entry_text: str) -> None:
    """Undo every move that happened, newest first, and restore the entry file."""
    for source, destination in reversed(completed):
        if destination.exists():
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), str(source))
    if entry_path.exists():
        entry_path.write_text(original_entry_text, encoding="utf-8")


def _regenerate(root: Path) -> None:
    """Rewrite `root`'s Lean root and generated ledger views.

    The one copy of `scripts/gen_root.py` lives in the public checkout beside this
    package; the private repo has none and reaches across for it, exactly as its
    Makefile does. So the script is located from the package, never from `root`, and
    a missing script is a configuration failure rather than a root left stale.
    """
    script = config.gen_root_script()
    result = subprocess.run(
        [sys.executable, str(script), "--write", "--lib", config.lean_lib(root), "--root", str(root)],
        cwd=root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise CheckError(f"I16 generated: {root / (config.lean_lib(root) + '.lean')}: field '<root>': "
                         f"{(result.stderr or result.stdout).strip()}")
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
    # Dispatch to the canonical module: under `python -m`, this file runs as `__main__`
    # and its classes would be distinct from the `mdept.release` ones that artifacts and
    # callers import, breaking isinstance checks.
    from mdept.release import main as _main

    raise SystemExit(_main())
