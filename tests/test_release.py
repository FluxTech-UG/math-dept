"""A release publishes an entry and keeps its private provenance private.

A release moves a settled entry from the private repo into the public one. What
must not cross is the consumer's internal reasoning (`raised_by.doc` and its
kin) and the attempt record: once the public repo is pushed, a leak cannot be
taken back.

The Lean audit is mocked rather than run. `release` reads `audit/latest.json`
and never invokes Lean itself, so a fixture audit exercises the real code path
and keeps the suite runnable without a toolchain.
"""

import json
import shutil
from pathlib import Path

import pytest

from mdept import audit, check, parse, release

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASES = ("good_public", "good_private")

ENTRY = "MD_0007"
LEAN_PRIVATE = "MathDeptPrivate/Results/MD_0007.lean"
LEAN_PUBLIC = "MathDept/Results/MD_0007.lean"
TYPE_0007 = "∀ (n : Nat), 0 + n = n"
TYPE_0001 = "∀ (n : Nat), n + 0 = n"
TYPE_0008 = "∀ (n : Nat), 0 + (0 + n) = n"
TYPES = {"MD_0001": TYPE_0001, "MD_0007": TYPE_0007, "MD_0008": TYPE_0008}


@pytest.fixture(autouse=True)
def map_writer(monkeypatch):
    """A release rewrites `docs/MAP.md` with `repo-outline`, a family tool CI does not carry.

    Where it is on PATH the real tool runs. Where it is not, the map step is
    replaced by a recorder, so the release path is still exercised end to end.
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


# --- the happy path ---------------------------------------------------------


def test_release_lands_the_entry_and_both_repos_still_validate(tmp_path, monkeypatch):
    public, private = prepare(tmp_path, monkeypatch)
    before, _, _ = parse.load_front_matter(private / "ledger" / f"{ENTRY}.md")
    private_fields = {field: before["provenance"]["raised_by"][field]
                      for field in ("doc", "anchor", "application")}
    assert all(private_fields.values()), "the fixture must carry every private field to show it is dropped"
    plan = release.release(ENTRY, public, private)

    assert (public / "ledger" / f"{ENTRY}.md").is_file()
    assert not (private / "ledger" / f"{ENTRY}.md").exists()
    assert (public / LEAN_PUBLIC).is_file()
    assert not (private / LEAN_PRIVATE).exists()
    assert (private / "triage" / f"{ENTRY}.md").is_file(), "attempts stay private across a release"

    landed, _, _ = parse.load_front_matter(public / "ledger" / f"{ENTRY}.md")
    assert landed["formal"]["file"] == LEAN_PUBLIC
    assert landed["evidence"] == [{"kind": "experiment", "path": LEAN_PUBLIC}]
    for field in private_fields:
        assert landed["provenance"]["raised_by"][field] is None, f"raised_by.{field} reached the public entry"
    # Nor may the private text land anywhere else in the public repo (a view, the body).
    # The anchor's value (`T1`) is too short to search for; the front check above covers it.
    for field in ("doc", "application"):
        needle = private_fields[field].encode("utf-8")
        leaks = [path.relative_to(public).as_posix() for path in sorted(public.rglob("*"))
                 if path.is_file() and needle in path.read_bytes()]
        assert not leaks, f"raised_by.{field} ({private_fields[field]!r}) reached the public repo in {leaks}"

    assert len(plan["checks"]) == 2
    check.run(public, lean=True)
    check.run(private, lean=True)

