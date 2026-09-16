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
from pathlib import Path

import pytest

from mdept import CheckError, audit, check, index, parse, release, schema

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASES = ("good_public", "good_private")

ENTRY = "MD_0007"
LEAN_PRIVATE = "MathDeptPrivate/Results/MD_0007.lean"
LEAN_PUBLIC = "MathDept/Results/MD_0007.lean"
TYPE_0007 = "∀ (n : Nat), 0 + n = n"
TYPE_0001 = "∀ (n : Nat), n + 0 = n"


def stage(tmp_path: Path, name: str = "work") -> Path:
    """A throwaway copy of the fixture pair, laid out as siblings."""
    root = tmp_path / name
    root.mkdir()
    for base in BASES:
        shutil.copytree(FIXTURES / base, root / base)
    return root


def post_release_shas(tmp_path: Path) -> tuple[str, str]:
    """Both repos' sources_sha256 as they will be after the release.

    Computed by performing the move on a scratch copy and asking the real
    hasher, so the fixture audit cannot drift from what the code computes.
    """
    scratch = stage(tmp_path, "scratch")
    public, private = scratch / "good_public", scratch / "good_private"
    destination = public / LEAN_PUBLIC
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(private / LEAN_PRIVATE), str(destination))
    return audit.sources_sha256(public), audit.sources_sha256(private)


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


def prepare(tmp_path: Path) -> tuple[Path, Path]:
    """Stage the pair and seed both audits for the post-release state."""
    root = stage(tmp_path)
    public, private = root / "good_public", root / "good_private"
    public_sha, private_sha = post_release_shas(tmp_path)
    write_audit(public, {
        "MathDept.MD_0001.statement": {
            "module": "MathDept.Results.MD_0001", "axioms": [], "type": TYPE_0001,
        },
        "MathDept.MD_0007.statement": {
            "module": "MathDept.Results.MD_0007", "axioms": [], "type": TYPE_0007,
        },
    }, public_sha)
    write_audit(private, {}, private_sha)
    return public, private


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


def test_release_lands_the_entry_and_both_repos_still_validate(tmp_path):
    public, private = prepare(tmp_path)
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
    check.run(private)


def test_the_released_id_still_resolves_from_the_private_triage_record(tmp_path):
    public, private = prepare(tmp_path)
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


def test_release_refuses_an_evidence_row_that_would_not_resolve(tmp_path):
    public, private = prepare(tmp_path)
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


def test_release_refuses_when_the_destination_is_taken(tmp_path):
    public, private = prepare(tmp_path)
    occupied = public / LEAN_PUBLIC
    occupied.parent.mkdir(parents=True, exist_ok=True)
    occupied.write_text("-- someone got here first\n", encoding="utf-8")
    with pytest.raises(CheckError, match="already exists in the public repo"):
        release.release(ENTRY, public, private)
    assert (private / "ledger" / f"{ENTRY}.md").is_file()
    assert (private / LEAN_PRIVATE).is_file()


def test_release_refuses_an_unsettled_entry(tmp_path):
    public, private = prepare(tmp_path)
    with pytest.raises(CheckError, match="I4 status/evidence"):
        release.release("MD_0005", public, private, dry_run=True)


def test_a_dry_run_reports_the_moves_and_touches_nothing(tmp_path):
    public, private = prepare(tmp_path)
    plan = release.release(ENTRY, public, private, dry_run=True)
    assert plan["dry_run"] is True
    assert any(LEAN_PUBLIC in destination for _, destination in plan["moves"])
    assert_nothing_moved(public, private)


# --- rollback, after the moves ----------------------------------------------


def test_a_verification_failure_rolls_every_move_back(tmp_path, monkeypatch):
    public, private = prepare(tmp_path)
    before = (private / "ledger" / f"{ENTRY}.md").read_text(encoding="utf-8")

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
    # Plain mode, not `--lean`. The audit this test seeded describes the repo as
    # it would be AFTER the release, so once the rollback restores the tree the
    # cached audit is genuinely stale and `--lean` says so. That is the freshness
    # guard working, and re-running `make lean` is the operator's next step.
    check.run(public)
    check.run(private)
    with pytest.raises(CheckError, match="stale against the Lean sources"):
        check.run(public, lean=True)
