"""Releasing an entry is all or nothing.

A release moves files between two git repos and then asks both to validate. The
failure that matters is the half-release: the entry leaves the private repo,
the public repo rejects it, and it now exists in neither while both fail their
own checks. These tests pin the two defences against that. Everything knowable
is checked before the first byte moves, and a post-move failure is rolled back.

The Lean audit is mocked rather than run. `release` reads `audit/latest.json`
and never invokes Lean itself, so a fixture audit exercises the real code path
and keeps the suite runnable without a toolchain.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from mdept import CheckError, ConfigError, audit, check, config, index, parse, release, schema
from mdept import family as family_mod

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASES = ("good_public", "good_private")
#: The production map step, kept before `map_writer` may replace it.
REAL_OUTLINE = release._outline
REAL_REQUIRE_OUTLINE = getattr(release, "_require_outline", None)

ENTRY = "MD_0007"
LEAN_PRIVATE = "MathDeptPrivate/Results/MD_0007.lean"
LEAN_PUBLIC = "MathDept/Results/MD_0007.lean"
TYPE_0007 = "∀ (n : Nat), 0 + n = n"
TYPE_0001 = "∀ (n : Nat), n + 0 = n"
TYPE_0008 = "∀ (n : Nat), 0 + (0 + n) = n"
TYPES = {"MD_0001": TYPE_0001, "MD_0007": TYPE_0007, "MD_0008": TYPE_0008}
DEPENDENT = "MD_0008"
PRIVATE_MODULE = "MathDeptPrivate.Results.MD_0007"
PUBLIC_MODULE = "MathDept.Results.MD_0007"


@pytest.fixture(autouse=True)
def map_writer(monkeypatch):
    """A release rewrites `docs/MAP.md` with `repo-outline`, a family tool CI does not carry.

    Where it is on PATH the real tool runs. Where it is not, the map step is
    replaced by a recorder, so the release path is still exercised end to end
    and `test_release_refuses_without_repo_outline` pins the production refusal.
    """
    if shutil.which("repo-outline") is None:
        monkeypatch.setattr(release, "_outline", lambda root: None)
        monkeypatch.setattr(release, "_require_outline", lambda: None, raising=False)


def stage(tmp_path: Path, name: str = "work") -> Path:
    """A throwaway copy of the fixture pair, laid out as siblings."""
    root = tmp_path / name
    root.mkdir()
    for base in BASES:
        shutil.copytree(FIXTURES / base, root / base)
    return root


def write_audit(root: Path, declarations: dict, sources_sha: str) -> None:
    payload = {
        "schema_version": audit.SCHEMA_VERSION,
        "ok": True,
        "sorry_violations": [],
        "sources_sha256": sources_sha,
        "lean_toolchain": "leanprover/lean4:v4.33.1",
        "mathlib_rev": "fixture",
        "declarations": declarations,
        "counterexamples": {},
    }
    (root / "audit").mkdir(parents=True, exist_ok=True)
    (root / "audit" / "latest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def audit_of_disk(root: Path) -> None:
    """What `make lean` would cache for `root` as it stands: one record per Lean file on disk.

    The module is read off the file's path, so a file that moved is reported
    under its new module, exactly as the real audit would.
    """
    declarations = {}
    for path in audit.lean_files(root):
        if path.stem in TYPES:
            module = ".".join(path.relative_to(root).with_suffix("").parts)
            declarations[f"MathDept.{path.stem}.statement"] = {
                "module": module, "axioms": [], "type": TYPES[path.stem],
            }
    write_audit(root, declarations, audit.sources_sha256(root))


def install_fake_audit(monkeypatch) -> list:
    """Replace the release's Lean audit with `audit_of_disk`; the list records each call's root."""
    calls: list[Path] = []

    def fake(root):
        calls.append(Path(root).resolve())
        audit_of_disk(Path(root))

    monkeypatch.setattr(release, "_audit", fake, raising=False)
    return calls


def prepare(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    """Stage the pair regenerated, with both audits fresh for the tree as it is, and fake the audit runner."""
    root = stage(tmp_path)
    public, private = root / "good_public", root / "good_private"
    for repo in (public, private):
        release._regenerate(repo)
        audit_of_disk(repo)
    install_fake_audit(monkeypatch)
    return public, private


def add_private_entry(private: Path, entry_id: str, *, status: str, revises: str | None = None,
                      imports: tuple[str, ...] = (), below_of: tuple[str, ...] = ()) -> Path | None:
    """A second private entry, built from MD_0007's file. With `imports` it gets a Lean file
    under Results/ that imports those modules; without, it has no formal pointer. `below_of`
    fills `between.below_of`.
    """
    front, _, body = parse.load_front_matter(private / "ledger" / f"{ENTRY}.md")
    front["id"] = entry_id
    front["title"] = f"A toy entry {entry_id}"
    front["status"] = status
    front["revises"] = revises
    front["between"] = dict(front["between"], below_of=list(below_of))
    lean_rel = None
    if imports:
        lean_rel = f"MathDeptPrivate/Results/{entry_id}.lean"
        front["formal"] = {"decl": f"MathDept.{entry_id}.statement", "file": lean_rel}
        front["statement_hash"] = audit.type_hash(TYPES[entry_id])
        front["evidence"] = [{"kind": "triage", "path": f"triage/{entry_id}.md"}]
        lines = ["import Mathlib.Data.Nat.Basic", *(f"import {m}" for m in imports), "",
                 "/-!", f"# {entry_id}: uses the definitions of `{imports[0]}`", "-/", "",
                 f"namespace MathDept.{entry_id}", "",
                 "theorem statement (n : Nat) : 0 + (0 + n) = n := by",
                 "  rw [MathDept.MD_0007.statement, MathDept.MD_0007.statement]", "",
                 f"end MathDept.{entry_id}", ""]
        (private / lean_rel).write_text("\n".join(lines), encoding="utf-8")
    else:
        front["formal"] = {"decl": None, "file": None}
        front["statement_hash"] = None
        front["evidence"] = []
    if status in schema.UNSETTLED_STATUSES:
        front["provenance"]["settled_by"] = None
    else:
        record = (private / "triage" / f"{ENTRY}.md").read_text(encoding="utf-8")
        (private / "triage" / f"{entry_id}.md").write_text(record.replace(ENTRY, entry_id), encoding="utf-8")
    dumped = yaml.dump(front, sort_keys=False, allow_unicode=True).rstrip("\n")
    (private / "ledger" / f"{entry_id}.md").write_text(f"---\n{dumped}\n---\n{body}", encoding="utf-8")
    release._regenerate(private)
    return private / lean_rel if lean_rel else None


def snapshot(*roots: Path) -> dict:
    """Every file's bytes under the given roots, generated views and audits included."""
    return {p: p.read_bytes() for root in roots for p in sorted(root.rglob("*")) if p.is_file()}


# --- the unit that was getting the paths wrong ------------------------------


@pytest.mark.parametrize(
    "given, expected",
    [
        ("MathDeptPrivate/Results/MD_0007.lean", "MathDept/Results/MD_0007.lean"),
        ("MathDeptPrivate/Defs/Shared.lean", "MathDept/Defs/Shared.lean"),
        ("proofs/MD_0007.md", "proofs/MD_0007.md"),
        ("counterexamples/MD_0007_toy.py", "counterexamples/MD_0007_toy.py"),
    ],
)
def test_publicize_rewrites_only_the_library_prefix(given, expected):
    assert release.publicize(given) == expected


def test_abstract_provenance_drops_private_rows_and_follows_the_rest_across():
    front, _, _ = parse.load_front_matter(FIXTURES / "good_private" / "ledger" / f"{ENTRY}.md")
    public_front = release.abstract_provenance(front)

    raised_by = public_front["provenance"]["raised_by"]
    assert raised_by["repo"] == "ToyRepo" and raised_by["domain"]
    assert raised_by["doc"] is None and raised_by["anchor"] is None and raised_by["application"] is None

    kinds = [item["kind"] for item in public_front["evidence"]]
    assert "triage" not in kinds, "a private-only row does not survive a release"
    assert public_front["evidence"] == [{"kind": "experiment", "path": LEAN_PUBLIC}], (
        "an evidence row naming a Lean path must follow its file across"
    )
    assert public_front["formal"]["file"] == LEAN_PUBLIC
    assert front["provenance"]["raised_by"]["doc"] is not None, "the private entry is untouched"


def test_the_rewritten_entry_satisfies_the_public_schema():
    front, _, _ = parse.load_front_matter(FIXTURES / "good_private" / "ledger" / f"{ENTRY}.md")
    schema.validate_front(release.abstract_provenance(front), f"ledger/{ENTRY}.md", "public")


# --- the happy path ---------------------------------------------------------


def test_release_lands_the_entry_and_both_repos_still_validate(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    plan = release.release(ENTRY, public, private)

    assert (public / "ledger" / f"{ENTRY}.md").is_file()
    assert not (private / "ledger" / f"{ENTRY}.md").exists()
    assert (public / LEAN_PUBLIC).is_file()
    assert not (private / LEAN_PRIVATE).exists()
    assert (private / "triage" / f"{ENTRY}.md").is_file(), "attempts stay private across a release"

    landed, _, _ = parse.load_front_matter(public / "ledger" / f"{ENTRY}.md")
    assert landed["formal"]["file"] == LEAN_PUBLIC
    assert landed["evidence"] == [{"kind": "experiment", "path": LEAN_PUBLIC}]
    assert landed["provenance"]["raised_by"]["doc"] is None

    assert len(plan["checks"]) == 2
    check.run(public, lean=True)
    check.run(private, lean=True)


def test_release_regenerates_both_lean_roots(tmp_path, monkeypatch):
    """The private repo has no gen_root.py of its own; a release still rewrites its root.

    The generator is the public checkout's single copy, located from the package, so
    neither root can be left stale by a release. Both are checked with the script's own
    `--check` afterwards.
    """
    public, private = prepare(tmp_path, monkeypatch)
    release.release(ENTRY, public, private)
    script = config.gen_root_script()
    for root, lib in ((public, "MathDept"), (private, "MathDeptPrivate")):
        assert (root / f"{lib}.lean").is_file(), f"{lib}.lean was not written by the release"
        result = subprocess.run(
            [sys.executable, str(script), "--check", "--lib", lib, "--root", str(root)],
            cwd=root, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"{lib}.lean is stale after the release:\n{result.stdout}{result.stderr}"


def test_the_released_id_still_resolves_from_the_private_triage_record(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    release.release(ENTRY, public, private)
    record = (private / "triage" / f"{ENTRY}.md").read_text(encoding="utf-8")
    assert ENTRY in record
    check.run(private)


# --- refusals, before anything moves ----------------------------------------


def assert_nothing_moved(public: Path, private: Path) -> None:
    assert (private / "ledger" / f"{ENTRY}.md").is_file()
    assert (private / LEAN_PRIVATE).is_file()
    assert not (public / "ledger" / f"{ENTRY}.md").exists()
    assert not (public / LEAN_PUBLIC).exists()


def test_release_refuses_an_evidence_row_that_would_not_resolve(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    orphan = private / "MathDeptPrivate" / "Defs" / "Shared.lean"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("namespace MathDept.Defs\nend MathDept.Defs\n", encoding="utf-8")
    entry_path = private / "ledger" / f"{ENTRY}.md"
    entry_path.write_text(
        entry_path.read_text(encoding="utf-8").replace(
            "  - kind: experiment\n",
            "  - kind: experiment\n    path: MathDeptPrivate/Defs/Shared.lean\n  - kind: experiment\n",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(CheckError, match="would not exist in the public repo"):
        release.release(ENTRY, public, private)
    assert_nothing_moved(public, private)


def test_release_refuses_when_the_destination_is_taken(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    occupied = public / LEAN_PUBLIC
    occupied.parent.mkdir(parents=True, exist_ok=True)
    occupied.write_text("-- someone got here first\n", encoding="utf-8")
    with pytest.raises(CheckError, match="already exists in the public repo"):
        release.release(ENTRY, public, private)
    assert (private / "ledger" / f"{ENTRY}.md").is_file()
    assert (private / LEAN_PRIVATE).is_file()


def test_release_refuses_an_unsettled_entry(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    with pytest.raises(CheckError, match="I4 status/evidence"):
        release.release("MD_0005", public, private, dry_run=True)


def test_a_dry_run_reports_the_moves_and_touches_nothing(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    plan = release.release(ENTRY, public, private, dry_run=True)
    assert plan["dry_run"] is True
    assert any(LEAN_PUBLIC in destination for _, destination in plan["moves"])
    assert_nothing_moved(public, private)


# --- rollback, after the moves ----------------------------------------------


def generated_files(public: Path, private: Path) -> dict:
    """The bytes of the files a regeneration writes besides the ledger views: both Lean
    roots and, where `repo-outline` runs, both `docs/MAP.md`."""
    files = [public / "MathDept.lean", private / "MathDeptPrivate.lean"]
    if shutil.which("repo-outline") is not None:
        files += [public / "docs" / "MAP.md", private / "docs" / "MAP.md"]
    return {path: path.read_bytes() for path in files}


def test_a_verification_failure_rolls_every_move_back(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    before = (private / "ledger" / f"{ENTRY}.md").read_text(encoding="utf-8")
    audits = {root: (root / "audit" / "latest.json").read_bytes() for root in (public, private)}
    generated = generated_files(public, private)

    def refuse(root, needs_lean):
        raise CheckError("I9a contradiction: injected failure after the moves")

    monkeypatch.setattr(release, "_verify", refuse)
    with pytest.raises(CheckError, match="rolled back"):
        release.release(ENTRY, public, private)

    assert_nothing_moved(public, private)
    assert (private / "ledger" / f"{ENTRY}.md").read_text(encoding="utf-8") == before
    assert (private / "triage" / f"{ENTRY}.md").is_file()
    for root in (public, private):
        for rel, rendered in index.render(root).items():
            assert (root / rel).read_text(encoding="utf-8") == rendered, (
                f"{rel} was left stale by the rollback"
            )
    # The release re-audited both repos after the move; the rollback puts the
    # cached audits back byte for byte, so `--lean` passes on the restored tree.
    for root, cached in audits.items():
        assert (root / "audit" / "latest.json").read_bytes() == cached, f"{root.name}'s audit was not restored"
    # The Lean roots and the file maps are regenerated over the restored tree too.
    for path, data in generated.items():
        assert path.read_bytes() == data, f"{path} was left at its post-release state by the rollback"
    check.run(public, lean=True)
    check.run(private, lean=True)


def test_a_failing_rollback_step_does_not_stop_the_later_ones(tmp_path, monkeypatch):
    """The public root's map step fails during the rollback; the private root is still regenerated,
    the audits still restored, and the error names the original failure and the secondary one."""
    public, private = prepare(tmp_path, monkeypatch)
    audits = {root: (root / "audit" / "latest.json").read_bytes() for root in (public, private)}
    private_root = (private / "MathDeptPrivate.lean").read_bytes()
    rolling_back = []
    real_outline = release._outline

    def refuse(root, needs_lean):
        rolling_back.append(True)
        raise CheckError("I9a contradiction: injected failure after the moves")

    def outline(root):
        if rolling_back and len(rolling_back) == 1:
            rolling_back.append(True)  # only the rollback's first map step, the public one, fails
            raise CheckError("I16 generated: injected map failure during the rollback")
        real_outline(root)

    monkeypatch.setattr(release, "_verify", refuse)
    monkeypatch.setattr(release, "_outline", outline)
    with pytest.raises(CheckError, match="rolled back") as raised:
        release.release(ENTRY, public, private)
    message = str(raised.value)
    assert "injected failure after the moves" in message and "injected map failure during the rollback" in message

    assert_nothing_moved(public, private)
    for rel, rendered in index.render(private).items():
        assert (private / rel).read_text(encoding="utf-8") == rendered, f"private {rel} was left stale"
    assert (private / "MathDeptPrivate.lean").read_bytes() == private_root
    for root, cached in audits.items():
        assert (root / "audit" / "latest.json").read_bytes() == cached, f"{root.name}'s audit was not restored"


def test_a_release_without_repo_outline_moves_nothing(tmp_path, monkeypatch):
    """The map tool is looked for in the preflight, so a dry run fails exactly as a real run would."""
    public, private = prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(release, "_outline", REAL_OUTLINE)
    monkeypatch.setattr(release, "_require_outline", REAL_REQUIRE_OUTLINE, raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(ConfigError, match="repo-outline is not on PATH"):
        release.release(ENTRY, public, private, dry_run=True)
    assert_nothing_moved(public, private)
    with pytest.raises(ConfigError, match="repo-outline is not on PATH"):
        release.release(ENTRY, public, private)
    assert_nothing_moved(public, private)


# --- item: the Lean audit is re-run after the move --------------------------


def test_release_reaudits_each_repo_whose_lean_sources_changed(tmp_path, monkeypatch):
    """Before the move both audits are fresh; the move stales both, so both are re-run, once each."""
    public, private = prepare(tmp_path, monkeypatch)
    calls = install_fake_audit(monkeypatch)
    release.release(ENTRY, public, private)
    assert calls == [public.resolve(), private.resolve()], "public first: the private build requires it"
    check.run(public, lean=True)
    check.run(private, lean=True)


# --- item: links to a released entry resolve from the private repo ----------


def test_a_private_entry_may_link_to_a_released_one(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    add_private_entry(private, DEPENDENT, status="conjectured", revises=ENTRY)
    check.run(private)
    release.release(ENTRY, public, private)
    assert (public / "ledger" / f"{ENTRY}.md").is_file()
    check.run(private)
    check.run(public)


# --- item: a public entry may name an unreleased ID --------------------------


def _set_revises(path: Path, target: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert "revises: null" in text
    path.write_text(text.replace("revises: null", f"revises: {target}", 1), encoding="utf-8")


def test_a_public_link_to_an_unreleased_id_passes_and_renders_as_held(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    _set_revises(public / "ledger" / "MD_0001.md", ENTRY)
    index.write(public)
    check.run(public)
    rendered = (public / index.INDEX_PATH).read_text(encoding="utf-8")
    assert f"| {ENTRY} | {family_mod.HELD} | MD_0001 revises |" in rendered
    held = json.loads((public / index.JSON_PATH).read_text(encoding="utf-8"))["unreleased"]
    assert held == [{"id": ENTRY, "held": family_mod.HELD,
                     "named_by": [{"entry": "MD_0001", "field": "revises"}]}]


def test_a_public_proof_mentioning_an_unreleased_id_passes(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    (public / "proofs").mkdir(exist_ok=True)
    (public / "proofs" / "MD_0001.md").write_text(
        "# MD_0001 proof\n<!-- role: record | status: current 2026-09-04 | cited-by: ledger/MD_0001.md -->\n\n"
        f"The step mirrors the one {ENTRY} takes on the other side.\n",
        encoding="utf-8")
    index.write(public)
    check.run(public)
    held = json.loads((public / index.JSON_PATH).read_text(encoding="utf-8"))["unreleased"]
    assert held == [{"id": ENTRY, "held": family_mod.HELD,
                     "named_by": [{"entry": "MD_0001", "field": "<proof>"}]}]


def test_a_private_link_to_an_id_in_neither_ledger_still_fails(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    _set_revises(private / "ledger" / "MD_0006.md", "MD_0099")
    with pytest.raises(CheckError, match="I8 links: ledger/MD_0006.md: field 'revises': MD_0099 does not exist"):
        check.run(private)


def test_a_public_link_to_an_id_in_neither_ledger_fails_in_the_private_run(tmp_path, monkeypatch):
    """The public run reads the typo as held; the private run resolves through both and fails it."""
    public, private = prepare(tmp_path, monkeypatch)
    _set_revises(public / "ledger" / "MD_0001.md", "MD_0999")
    index.write(public)
    check.run(public)
    with pytest.raises(CheckError, match="I8 links: public sibling ledger/MD_0001.md: field 'revises': "
                                         "MD_0999 does not exist"):
        check.run(private)


def test_a_public_proof_mentioning_an_id_in_neither_ledger_fails_in_the_private_run(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    (public / "proofs").mkdir(exist_ok=True)
    (public / "proofs" / "MD_0001.md").write_text(
        "# MD_0001 proof\n<!-- role: record | status: current 2026-09-04 | cited-by: ledger/MD_0001.md -->\n\n"
        "The step mirrors the one MD_0999 takes on the other side.\n",
        encoding="utf-8")
    index.write(public)
    check.run(public)
    with pytest.raises(CheckError, match="I12 dangling: public sibling proofs/MD_0001.md: field '<MD token>': "
                                         "MD_0999 does not resolve"):
        check.run(private)


def test_a_public_link_to_a_private_merged_entry_fails_in_the_private_run(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    merged = private / "ledger" / "MD_0005.md"
    text = merged.read_text(encoding="utf-8")
    for old, new in (("status: conjectured", "status: merged"), ("merged_into: null", "merged_into: MD_0006"),
                     ("above_of: [MD_0006]", "above_of: []"),
                     ("settled_by: null", "settled_by:\n    who: john\n    date: 2026-09-03\n    how: citation\n"
                                          "    checked_by: null\n    model: null")):
        assert old in text
        text = text.replace(old, new, 1)
    merged.write_text(text, encoding="utf-8")
    survivor = private / "ledger" / "MD_0006.md"
    text = survivor.read_text(encoding="utf-8")
    assert "below_of: [MD_0005]" in text
    survivor.write_text(text.replace("below_of: [MD_0005]", "below_of: []", 1), encoding="utf-8")
    release._regenerate(private)
    check.run(private)
    _set_revises(public / "ledger" / "MD_0001.md", "MD_0005")
    index.write(public)
    check.run(public)
    with pytest.raises(CheckError, match="I8 links: public sibling ledger/MD_0001.md: field 'revises': "
                                         "MD_0005 is merged into MD_0006"):
        check.run(private)


def test_the_private_resolver_is_built_once_per_run(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    ctx = check.run(private)
    assert ctx.family_by_id() is ctx.family_by_id()
    built = []
    real = family_mod.resolver
    monkeypatch.setattr(family_mod, "resolver", lambda *args: built.append(args) or real(*args))
    assert ctx.resolve(ENTRY) is not None and ctx.resolve("MD_0001") is not None
    assert built == []


def test_a_private_mention_of_an_id_in_neither_ledger_still_fails(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    record = private / "triage" / "MD_0006.md"
    record.write_text(record.read_text(encoding="utf-8") + "\nCompared with MD_0099.\n", encoding="utf-8")
    with pytest.raises(CheckError, match="I12 dangling: triage/MD_0006.md: field '<MD token>': MD_0099"):
        check.run(private)


def test_a_release_naming_an_unreleased_private_id_lands(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    entry_path = private / "ledger" / f"{ENTRY}.md"
    _set_revises(entry_path, "MD_0006")
    entry_path.write_text(entry_path.read_text(encoding="utf-8") + "\nIt sharpens to MD_0006.\n",
                          encoding="utf-8")
    release._regenerate(private)
    check.run(private)
    release.release(ENTRY, public, private)
    assert (public / "ledger" / f"{ENTRY}.md").is_file()
    check.run(public)
    check.run(private)
    rendered = (public / index.INDEX_PATH).read_text(encoding="utf-8")
    assert f"| MD_0006 | {family_mod.HELD} | {ENTRY} revises |" in rendered


def test_one_resolver_serves_the_check_and_the_views():
    """The rule has one home: both callers reach `family.resolver`, neither restates it."""
    import inspect

    from mdept import index as index_mod
    assert "family_mod.resolver(" in inspect.getsource(check.Context.resolve)
    assert "family_mod.resolver(" in inspect.getsource(index_mod.render)


# --- item: private imports of a released module are rewritten --------------


def test_release_rewrites_private_imports_of_the_released_module(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    dependent = add_private_entry(private, DEPENDENT, status="proven-formal", imports=(PRIVATE_MODULE,))
    audit_of_disk(private)
    check.run(private, lean=True)

    plan = release.release(ENTRY, public, private)

    text = dependent.read_text(encoding="utf-8")
    assert f"import {PUBLIC_MODULE}\n" in text
    assert PRIVATE_MODULE not in text, "every mention of the moved module follows it"
    assert any(str(dependent) == path for path in plan["rewrites"])
    check.run(private, lean=True)
    check.run(public, lean=True)


def test_a_rollback_restores_the_rewritten_imports(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    dependent = add_private_entry(private, DEPENDENT, status="proven-formal", imports=(PRIVATE_MODULE,))
    audit_of_disk(private)
    before = snapshot(public, private)

    def refuse(root, needs_lean):
        raise CheckError("I9a contradiction: injected failure after the moves")

    monkeypatch.setattr(release, "_verify", refuse)
    with pytest.raises(CheckError, match="rolled back"):
        release.release(ENTRY, public, private)
    after = snapshot(public, private)
    assert after == before, sorted(str(p) for p in set(before) ^ set(after) | {
        p for p in before if p in after and before[p] != after[p]})
    assert PRIVATE_MODULE in dependent.read_text(encoding="utf-8")


def test_an_entry_importing_an_unreleased_private_module_is_refused_alone(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    add_private_entry(private, DEPENDENT, status="proven-formal", imports=(PRIVATE_MODULE,))
    with pytest.raises(CheckError, match="imports a private module"):
        release.release(DEPENDENT, public, private, dry_run=True)


@pytest.mark.parametrize("line", [
    f"import {PRIVATE_MODULE} -- needed",
    "import MathDeptPrivate.Defs.A MathDeptPrivate.Defs.B",
], ids=["trailing-comment", "two-modules-on-one-line"])
def test_a_private_import_is_refused_whatever_follows_it_on_the_line(tmp_path, monkeypatch, line):
    public, private = prepare(tmp_path, monkeypatch)
    lean = add_private_entry(private, DEPENDENT, status="proven-formal", imports=(PRIVATE_MODULE,))
    lean.write_text(lean.read_text(encoding="utf-8").replace(f"import {PRIVATE_MODULE}\n", f"{line}\n", 1),
                    encoding="utf-8")
    with pytest.raises(CheckError, match="imports a private module"):
        release.release(DEPENDENT, public, private, dry_run=True)


def test_a_commented_import_of_a_batch_module_passes(tmp_path, monkeypatch):
    """The comment is cut before the tokens are read, so neither it nor the batch module refuses."""
    public, private = prepare(tmp_path, monkeypatch)
    lean = add_private_entry(private, DEPENDENT, status="proven-formal", imports=(PRIVATE_MODULE,))
    lean.write_text(lean.read_text(encoding="utf-8").replace(
        f"import {PRIVATE_MODULE}\n", f"import {PRIVATE_MODULE} -- MathDeptPrivate.Defs.Unrelated\n", 1),
        encoding="utf-8")
    release.release([ENTRY, DEPENDENT], public, private, dry_run=True)


# --- item: evidence rows at private paths are dropped ------------------------


def test_abstract_provenance_drops_an_experiment_row_at_a_private_path():
    front, _, _ = parse.load_front_matter(FIXTURES / "good_private" / "ledger" / f"{ENTRY}.md")
    front["evidence"] = [*front["evidence"],
                         {"kind": "experiment", "path": "triage/MD_0007_probe.py"},
                         {"kind": "experiment", "path": "sources/MD_0007_table.csv"}]
    public_front = release.abstract_provenance(front)
    assert public_front["evidence"] == [{"kind": "experiment", "path": LEAN_PUBLIC}]
    schema.validate_front(public_front, f"ledger/{ENTRY}.md", "public")


def test_a_proof_row_at_a_private_path_is_dropped_beside_a_settling_one(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    (private / "proofs").mkdir(exist_ok=True)
    (private / "proofs" / f"{ENTRY}.md").write_text(
        f"# {ENTRY} informal proof\n"
        f"<!-- role: record | status: current 2026-09-04 | cited-by: ledger/{ENTRY}.md -->\n\n"
        "Zero is a left identity by induction.\n", encoding="utf-8")
    entry_path = private / "ledger" / f"{ENTRY}.md"
    front, _, body = parse.load_front_matter(entry_path)
    front["evidence"] = [*front["evidence"],
                         {"kind": "proof", "path": f"proofs/{ENTRY}.md"},
                         {"kind": "proof", "path": f"triage/{ENTRY}.md"}]
    entry_path.write_text(release.render_entry(front, body), encoding="utf-8")
    release._regenerate(private)

    release.release(ENTRY, public, private)
    landed, _, _ = parse.load_front_matter(public / "ledger" / f"{ENTRY}.md")
    assert landed["evidence"] == [{"kind": "experiment", "path": LEAN_PUBLIC},
                                  {"kind": "proof", "path": f"proofs/{ENTRY}.md"}]
    assert (public / "proofs" / f"{ENTRY}.md").is_file()
    assert (private / "triage" / f"{ENTRY}.md").is_file(), "the attempt record stays private"


@pytest.mark.parametrize("status, kind, why", [
    ("proven-informal", "proof", "a proven-informal entry carries evidence {kind: proof, path: proofs/MD_0007.md}"),
    ("refuted", "counterexample", "a refuted entry carries evidence {kind: counterexample"),
])
def test_a_release_refuses_when_the_only_settling_row_is_private(status, kind, why):
    front, _, _ = parse.load_front_matter(FIXTURES / "good_private" / "ledger" / f"{ENTRY}.md")
    front["status"] = status
    front["evidence"] = [{"kind": kind, "path": f"triage/{ENTRY}_{kind}.md"}]
    with pytest.raises(CheckError) as raised:
        release.abstract_provenance(front)
    message = str(raised.value)
    assert why in message
    assert f"triage/{ENTRY}_{kind}.md" in message and "private-only" in message


def test_the_public_schema_refuses_an_evidence_row_at_a_private_path():
    front, _, _ = parse.load_front_matter(FIXTURES / "good_public" / "ledger" / "MD_0001.md")
    front["evidence"] = [*front["evidence"], {"kind": "experiment", "path": "triage/MD_0001_probe.py"}]
    with pytest.raises(CheckError, match="private-only surface"):
        schema.validate_front(front, "ledger/MD_0001.md", "public")


# --- item: the inheritance notice resolves through both ledgers --------------


def test_the_inheritance_notice_survives_the_release_of_what_implies_it(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    add_private_entry(private, DEPENDENT, status="conjectured", below_of=(ENTRY,))
    notice = f"I9b: {DEPENDENT} is conjectured but {ENTRY}"
    assert any(n.startswith(notice) for n in check.run(private).notices)
    release.release(ENTRY, public, private)
    assert any(n.startswith(notice) for n in check.run(private).notices), (
        "the notice was lost when the entry that implies it moved to the public repo"
    )
    assert notice in index.render(private)[index.INDEX_PATH]


# --- item: a batch moves, audits and verifies once ---------------------------


def test_a_batch_releases_a_dependent_with_what_it_imports(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    add_private_entry(private, DEPENDENT, status="proven-formal", imports=(PRIVATE_MODULE,))
    audit_of_disk(private)
    calls = install_fake_audit(monkeypatch)
    verified: list[Path] = []
    real_verify = release._verify

    def counting(root, needs_lean):
        verified.append(Path(root))
        return real_verify(root, needs_lean)

    monkeypatch.setattr(release, "_verify", counting)
    plan = release.release([DEPENDENT, ENTRY], public, private)

    assert plan["entries"] == [DEPENDENT, ENTRY]
    for entry_id in (ENTRY, DEPENDENT):
        assert (public / "ledger" / f"{entry_id}.md").is_file()
        assert not (private / "ledger" / f"{entry_id}.md").exists()
    landed = (public / "MathDept" / "Results" / f"{DEPENDENT}.lean").read_text(encoding="utf-8")
    assert f"import {PUBLIC_MODULE}\n" in landed and PRIVATE_MODULE not in landed
    assert calls == [public.resolve(), private.resolve()], "one audit per repo for the whole batch"
    assert len(verified) == 2, "one verification per repo for the whole batch"
    check.run(public, lean=True)
    check.run(private, lean=True)


def test_a_batch_failure_rolls_the_whole_batch_back(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    add_private_entry(private, DEPENDENT, status="proven-formal", imports=(PRIVATE_MODULE,))
    audit_of_disk(private)
    before = snapshot(public, private)

    def refuse(root, needs_lean):
        raise CheckError("I9a contradiction: injected failure after the moves")

    monkeypatch.setattr(release, "_verify", refuse)
    with pytest.raises(CheckError, match="rolled back"):
        release.release([ENTRY, DEPENDENT], public, private)
    assert snapshot(public, private) == before


def test_a_batch_dry_run_reports_every_move_and_touches_nothing(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    add_private_entry(private, DEPENDENT, status="proven-formal", imports=(PRIVATE_MODULE,))
    before = snapshot(public, private)
    plan = release.release([ENTRY, DEPENDENT], public, private, dry_run=True)
    destinations = [d for _, d in plan["moves"]]
    assert str(public / LEAN_PUBLIC) in destinations
    assert str(public / "MathDept" / "Results" / f"{DEPENDENT}.lean") in destinations
    assert snapshot(public, private) == before


def test_a_batch_refuses_a_repeated_id(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    with pytest.raises(CheckError, match="named twice"):
        release.release([ENTRY, ENTRY], public, private, dry_run=True)


def test_the_cli_takes_several_ids(tmp_path, monkeypatch, capsys):
    public, private = prepare(tmp_path, monkeypatch)
    add_private_entry(private, DEPENDENT, status="proven-formal", imports=(PRIVATE_MODULE,))
    code = release.main([ENTRY, DEPENDENT, "--dry-run", "--root", str(public), "--private", str(private)])
    out = capsys.readouterr()
    assert code == 0, out.err
    assert "would move" in out.out and "would rewrite" in out.out
    assert f"{ENTRY} {DEPENDENT}" in out.out


def test_release_refuses_without_repo_outline(tmp_path, monkeypatch):
    root = stage(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(ConfigError, match="repo-outline is not on PATH"):
        REAL_OUTLINE(root / "good_public")
