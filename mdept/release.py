"""Move settled entries from the private repo into this public one.

Run: `python -m mdept.release MD_0007 [MD_0008 ...] [--dry-run]`

A release moves files and abstracts provenance. It never rewrites the
statement, never renumbers, and never renames a Lean declaration: entries in
both libraries live in `namespace MathDept.MD_0007`, so a consumer that cites
`MathDept.MD_0007.statement` keeps citing the same name after the move. Only
the module path changes, from `MathDeptPrivate.Results.MD_0007` to
`MathDept.Results.MD_0007`, and every private Lean file that names the old
module (its `import` line, and any mention of the module in its comments) is
rewritten to the new one in the same move, so the private library still builds.

What is dropped, and why: `raised_by.doc`, `raised_by.anchor` and
`raised_by.application` describe a consumer's internal document and its
reasoning, so they stay private. Evidence rows of a private-only kind
(`schema.PRIVATE_EVIDENCE_KINDS`) are dropped for the same reason, and so is
every evidence row at a private-only path (`schema.PRIVATE_EVIDENCE_PREFIXES`,
the `sources/` and `triage/` surfaces) whatever its kind, because a public path
that does not resolve is a dead pointer. The release refuses only when the public
front would then fail the public schema or I4: no settling `proof` row left for a
proven-informal entry, no `counterexample` row left for a refuted one. What
survives is `repo`, a one-line neutral `domain`, and the who/date/model credit
trail, which is the point of recording provenance at all.

Several IDs release as one batch. A batch moves every entry, regenerates each
repo once, re-runs the Lean audit once in each repo whose Lean sources changed,
and verifies each repo once. Within a batch an entry may import the module of
another entry in the same batch; outside it, an import of a private module
refuses the release.

A release is all or nothing. Everything checkable is checked before a single
file moves (`repo-outline` on PATH, each rewritten entry against the public schema, every source present,
every destination free, every surviving path resolving after the move), and if the post-move
verification fails anyway, every move and rewrite is undone, both cached audits
are restored byte for byte, and the generated views are rewritten before the
error is raised. Each of those restore steps runs even when an earlier one fails,
and the error names the original failure and every failed restore step. A half-released entry, moved out of the private repo and
rejected by the public one, would leave both repos failing their own checks with
the entry in neither.

After the move both repos are regenerated (Lean root, ledger views, `docs/MAP.md`)
and re-checked. The Lean check (`--lean`) runs exactly when an entry in the
batch carries a `formal.decl`.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from . import CheckError, ConfigError
from . import audit, config, index, parse, schema

MOVABLE_STATUSES = ("cited", "proven-formal", "proven-informal", "refuted")

PRIVATE_LIB_PREFIX = "MathDeptPrivate/"
PUBLIC_LIB_PREFIX = "MathDept/"

PRIVATE_MODULE_PREFIX = "MathDeptPrivate."

#: A Lean `import` line: the rest of the line names one or more modules, then
#: perhaps a `--` comment.
_IMPORT_LINE_RE = re.compile(r"^import\b(.*)$", re.MULTILINE)


def private_imports(text: str) -> list[str]:
    """Every private module a Lean file's `import` lines name, comments cut away."""
    return [token
            for rest in _IMPORT_LINE_RE.findall(text)
            for token in rest.split("--", 1)[0].split()
            if token.startswith(PRIVATE_MODULE_PREFIX)]


def publicize(rel: str) -> str:
    """A private repo-relative path rewritten to its public counterpart.

    Only the library directory changes. Everything else (`proofs/`,
    `counterexamples/`) has the same name in both repos.
    """
    if rel.startswith(PRIVATE_LIB_PREFIX):
        return PUBLIC_LIB_PREFIX + rel[len(PRIVATE_LIB_PREFIX):]
    return rel


def module_of(rel: str) -> str:
    """The Lean module a repo-relative `.lean` path compiles to."""
    return rel[: -len(".lean")].replace("/", ".")


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
    evidence, dropped_at_private_path = [], []
    for item in front["evidence"]:
        if item["kind"] in schema.PRIVATE_EVIDENCE_KINDS:
            continue
        if schema.is_private_evidence_path(item["path"]):
            dropped_at_private_path.append(f"{item['kind']} row at {item['path']}")
            continue
        evidence.append({"kind": item["kind"], "path": publicize(item["path"])})
    problem = schema.settling_evidence_problem(front["id"], front["status"], evidence)
    if problem:
        dropped = (f"; the release drops the {', '.join(dropped_at_private_path)}, which sits on a "
                   "private-only surface" if dropped_at_private_path else "")
        raise CheckError(
            f"I4 status/evidence: ledger/{front['id']}.md: field 'evidence': the released entry would "
            f"fail I4, because {problem}{dropped}. Move the file to proofs/ or counterexamples/ and "
            "point the row there before releasing."
        )
    public["evidence"] = evidence
    formal = dict(public["formal"])
    if formal["file"]:
        formal["file"] = publicize(formal["file"])
    public["formal"] = formal
    return public


def plan_moves(private: Path, public: Path, entry, batch_modules=frozenset()) -> list[tuple[Path, Path]]:
    """Every (source, destination) pair releasing `entry` performs.

    `batch_modules` names the private modules moving in the same batch; an
    import of one of those is rewritten on the way, any other private import
    refuses the release.
    """
    entry_id = entry.id
    moves = [(entry.path, public / "ledger" / f"{entry_id}.md")]
    lean_file = entry.at("formal.file")
    if lean_file:
        source = private / lean_file
        if not source.is_file():
            raise CheckError(f"I5 formal pointer: {source}: field 'formal.file': does not exist")
        text = source.read_text(encoding="utf-8")
        for module in private_imports(text):
            if module not in batch_modules:
                raise CheckError(
                    f"I5 formal pointer: {lean_file}: field '<import>': "
                    f"'import {module}' imports a private module, so this entry cannot be released. "
                    "Release what it depends on first or in the same batch, or inline the definition."
                )
        moves.append((source, public / publicize(lean_file)))
    proof = private / "proofs" / f"{entry_id}.md"
    if proof.is_file():
        moves.append((proof, public / "proofs" / f"{entry_id}.md"))
    for artifact in sorted((private / "counterexamples").glob(f"{entry_id}_*.py")):
        moves.append((artifact, public / "counterexamples" / artifact.name))
    return moves


def plan_rewrites(private: Path, moves: list, batch_modules) -> list[tuple[Path, Path, str, str]]:
    """Every Lean file whose text names a module moving in this batch.

    Returns `(path after the moves, path before them, text before, text after)`
    for each: the moving Lean files at their public destination, and the private
    Lean files that stay behind and import a released module. The module path is
    the only thing that changes.
    """
    if not batch_modules:
        return []
    patterns = [(re.compile(rf"(?<![\w.']){re.escape(m)}(?![\w'])"), "MathDept." + m[len("MathDeptPrivate."):])
                for m in sorted(batch_modules)]

    def rewritten(text: str) -> str:
        for pattern, replacement in patterns:
            text = pattern.sub(replacement, text)
        return text

    moving = {source.resolve(): destination for source, destination in moves}
    rewrites = []
    for path in audit.lean_files(private):
        text = path.read_text(encoding="utf-8")
        new = rewritten(text)
        if new != text:
            rewrites.append((moving.get(path.resolve(), path), path, text, new))
    return rewrites


def release(entry_ids, public: Path, private: Path, dry_run: bool = False) -> dict:
    """Release one entry (an ID) or a batch (a list of IDs), all or nothing."""
    public, private = Path(public).resolve(), Path(private).resolve()
    ids = [entry_ids] if isinstance(entry_ids, str) else list(entry_ids)
    if not ids:
        raise CheckError("I1 filename: <batch>: field '<id>': a release names at least one entry")
    for entry_id in ids:
        if not schema.ID_RE.match(entry_id):
            raise CheckError(f"I1 filename: {entry_id}: field '<id>': not an ID of the form MD_0007")
        if ids.count(entry_id) > 1:
            raise CheckError(f"I1 filename: {entry_id}: field '<id>': named twice in one release")
        if (public / "ledger" / f"{entry_id}.md").exists():
            raise CheckError(f"I2 permanence: ledger/{entry_id}.md: field '<file>': already released")

    entries = [_load_entry(private, entry_id) for entry_id in ids]
    for entry in entries:
        if entry.status not in MOVABLE_STATUSES:
            raise CheckError(
                f"I4 status/evidence: {entry.rel}: field 'status': {entry.status!r} is not releasable; "
                f"a release publishes a settled result, one of {list(MOVABLE_STATUSES)}"
            )
    batch_modules = frozenset(module_of(e.at("formal.file")) for e in entries if e.at("formal.file"))
    moves = [move for entry in entries for move in plan_moves(private, public, entry, batch_modules)]
    rewrites = plan_rewrites(private, moves, batch_modules)
    fronts = {entry.id: abstract_provenance(entry.front) for entry in entries}
    plan = {
        "entries": ids,
        "moves": [(str(s), str(d)) for s, d in moves],
        "rewrites": [str(after) for after, _, _, _ in rewrites],
        "dry_run": dry_run,
    }

    # Everything knowable before the first byte moves. A dry run gets the same
    # answer as a real one, which is the point of having a dry run.
    preflight(entries, fronts, moves, public)
    if dry_run:
        return plan

    roots = (public, private)  # public first: the private Lake package requires it
    originals = {entry.path: entry.path.read_text(encoding="utf-8") for entry in entries}
    originals.update({before: text for _, before, text, _ in rewrites})
    cached_audits = {root: _read_audit_bytes(root) for root in roots}
    sources_before = {root: audit.sources_sha256(root) for root in roots}
    completed: list[tuple[Path, Path]] = []
    try:
        for source, destination in moves:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            completed.append((source, destination))
        for entry in entries:
            target = public / "ledger" / f"{entry.id}.md"
            target.write_text(render_entry(fronts[entry.id], entry.body), encoding="utf-8")
        for after, _, _, new in rewrites:
            after.write_text(new, encoding="utf-8")

        for root in roots:
            _regenerate(root)
        for root in roots:
            if audit.sources_sha256(root) != sources_before[root]:
                _audit(root)
        needs_lean = any(entry.at("formal.decl") for entry in entries)
        plan["checks"] = [_verify(root, needs_lean=needs_lean) for root in (private, public)]
    except BaseException as failure:
        # Every restore step runs whatever the one before it did: a step that
        # stopped the rest would leave a repo at its post-release state.
        steps = [("moving the files back", lambda: _roll_back(completed, originals)),
                 ("restoring the cached audits", lambda: _restore_audits(cached_audits))]
        steps += [(f"regenerating {root}", lambda root=root: _regenerate(root)) for root in roots]
        secondary = []
        for what, step in steps:
            try:
                step()
            except Exception as restore_failure:  # collected and named below, never swallowed
                secondary.append(f"{what} failed: {restore_failure}")
        state = ("the release was rolled back and both repos are as they were"
                 if not secondary else
                 "the release was rolled back, but some restore steps failed, so check both repos "
                 "against git: " + "; ".join(secondary))
        raise CheckError(
            f"I4 status/evidence: {', '.join(f'ledger/{i}.md' for i in ids)}: field '<release>': "
            f"{state}. The failure was: {failure}"
        ) from failure
    return plan


def render_entry(front: dict, body: str) -> str:
    """The public entry file: the abstracted front matter over the unchanged body."""
    dumped = yaml.dump(front, sort_keys=False, default_flow_style=False, allow_unicode=True).rstrip("\n")
    return f"---\n{dumped}\n---\n{body}"


def preflight(entries: list, fronts: dict, moves: list, public: Path) -> None:
    """Refuse a release that cannot land, before anything moves.

    Four questions, in the order that makes the error most useful: does each
    rewritten entry satisfy the PUBLIC schema, is every source still there, is
    every destination free, and will every path a public entry names resolve
    once the moves are done. An ID a released file links to or mentions is not
    asked about: the public repo reads one it holds no entry for as unreleased,
    held in the private ledger (`family.held`). Before all four, the map tool a real run regenerates `docs/MAP.md` with must
    be on PATH, so a dry run fails where a real run would.
    """
    _require_outline()
    for entry in entries:
        schema.validate_front(fronts[entry.id], f"ledger/{entry.id}.md", "public")

    seen_destinations: set[Path] = set()
    for source, destination in moves:
        if not source.exists():
            raise CheckError(
                f"I4 status/evidence: {source}: field '<source>': "
                "this release would move a file that is not there. Nothing has been moved."
            )
        if destination.exists() or destination in seen_destinations:
            raise CheckError(
                f"I2 permanence: {destination}: field '<destination>': "
                "already exists in the public repo. Nothing has been moved."
            )
        seen_destinations.add(destination)

    landing = {d.resolve() for _, d in moves}

    def resolves(rel: str) -> bool:
        candidate = (public / rel).resolve()
        return candidate in landing or candidate.exists()

    for entry in entries:
        target_entry = f"ledger/{entry.id}.md"
        public_front = fronts[entry.id]
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


def _roll_back(completed: list, originals: dict) -> None:
    """Undo every move that happened, newest first, then restore every rewritten file."""
    for source, destination in reversed(completed):
        if destination.exists():
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), str(source))
    for path, text in originals.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _read_audit_bytes(root: Path) -> bytes | None:
    path = root / audit.CACHED_AUDIT
    return path.read_bytes() if path.is_file() else None


def _restore_audits(cached: dict) -> None:
    """Put each repo's cached audit back exactly as it was before the release."""
    for root, data in cached.items():
        path = root / audit.CACHED_AUDIT
        if data is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)


def _regenerate(root: Path) -> None:
    """Rewrite `root`'s Lean root, generated ledger views and file map (what `make regen` does).

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
    _outline(root)


def _require_outline() -> None:
    """Refuse when `repo-outline`, which rewrites `docs/MAP.md`, is not on PATH."""
    if shutil.which("repo-outline") is None:
        raise ConfigError(
            "repo-outline is not on PATH, so a release would leave docs/MAP.md stale in both repos. "
            "Put universal-tools/bin on PATH and run the release again."
        )


def _outline(root: Path) -> None:
    """Rewrite `docs/MAP.md`, which lists the counterexample scripts a release moves."""
    _require_outline()
    result = subprocess.run(["repo-outline", "--write", str(root)], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise CheckError(f"I16 generated: {root / 'docs' / 'MAP.md'}: field '<map>': "
                         f"{(result.stderr or result.stdout).strip()}")


def _audit(root: Path) -> None:
    """Re-run the Lean audit and rewrite `audit/latest.json` (what `make lean` does in `root`)."""
    result = subprocess.run(
        [sys.executable, "-m", "mdept.audit", "all", "--root", str(root), "--write", audit.CACHED_AUDIT],
        cwd=root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise CheckError(
            f"I5 formal pointer: {root / audit.CACHED_AUDIT}: field '<audit>': the Lean audit failed "
            f"after the move\n{result.stdout[-4000:]}{result.stderr[-4000:]}"
        )


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
    parser.add_argument("entries", nargs="+", help="the entries to release as one batch, for example MD_0007")
    parser.add_argument("--root", default=None, help="the public repo (default: nearest ancestor with ledger/)")
    parser.add_argument("--private", default=None, help="the private repo (default: MATHDEPT_PRIVATE or the sibling)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and run the preflight, moving nothing")
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
        plan = release(args.entries, public, private, args.dry_run)
    except (CheckError, ConfigError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    move_verb, rewrite_verb = ("would move", "would rewrite") if args.dry_run else ("moved", "rewrote")
    for source, destination in plan["moves"]:
        print(f"{move_verb} {source} -> {destination}")
    for path in plan["rewrites"]:
        print(f"{rewrite_verb} {path} (module path only)")
    batch = " ".join(plan["entries"])
    if args.dry_run:
        print(f"ok dry run: {batch} pass the preflight ({len(plan['entries'])} entries)")
    else:
        print(f"ok released {batch}; both repos regenerated, audited where Lean changed, and checked")
    return 0


if __name__ == "__main__":
    # Dispatch to the canonical module: under `python -m`, this file runs as `__main__`
    # and its classes would be distinct from the `mdept.release` ones that artifacts and
    # callers import, breaking isinstance checks.
    from mdept.release import main as _main

    raise SystemExit(_main())
