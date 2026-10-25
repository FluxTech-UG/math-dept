"""`python -m mdept.settle` writes an entry's settlement and nothing else.

Each round trip starts from a settled fixture entry, unsettles it in a staged
copy, settles it again through the command with the fixture's own values, and
requires the file to come back byte for byte: the settled fields are the only
lines the command may touch. The refusals leave the file as it was.
"""

import difflib
import json
import shutil
from pathlib import Path

import pytest

from mdept import ConfigError, audit, settle

FIXTURES = Path(__file__).resolve().parent / "fixtures"

TYPE_0001 = "∀ (n : Nat), n + 0 = n"
TYPE_0007 = "∀ (n : Nat), 0 + n = n"

SETTLED_BLOCK_0001 = (
    "  settled_by:\n"
    "    who: claude\n"
    "    date: 2026-09-02\n"
    "    how: lean\n"
    "    checked_by: null\n"
    "    model: claude-fable-5-1\n"
)
SETTLED_BLOCK_0002 = (
    "  settled_by:\n"
    "    who: claude\n"
    "    date: 2026-09-03\n"
    "    how: counterexample\n"
    "    checked_by: null\n"
    "    model: claude-fable-5-1\n"
)
SETTLED_BLOCK_0007 = SETTLED_BLOCK_0001.replace("2026-09-02", "2026-09-03")
HASH_0001 = "statement_hash: ac4e57f2bdf5b0308d8c267d88d952cf2e08b5bb500150c466d157b96fced5c1\n"
HASH_0007 = "statement_hash: 25068dc19e6dc85ef79aac9f32c251728026124bb37e44afcce198c66d50f78e\n"


def stage(tmp_path: Path) -> tuple[Path, Path]:
    for base in ("good_public", "good_private"):
        shutil.copytree(FIXTURES / base, tmp_path / base)
    return tmp_path / "good_public", tmp_path / "good_private"


def write_audit(root: Path, declarations: dict, sources_sha: str | None = None) -> None:
    payload = {
        "schema_version": audit.SCHEMA_VERSION,
        "ok": True,
        "sorry_violations": [],
        "sources_sha256": audit.sources_sha256(root) if sources_sha is None else sources_sha,
        "lean_toolchain": "leanprover/lean4:v4.33.1",
        "mathlib_rev": "fixture",
        "declarations": declarations,
        "counterexamples": {},
    }
    (root / "audit").mkdir(parents=True, exist_ok=True)
    (root / "audit" / "latest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"fixture drifted: {old!r} occurs {text.count(old)} times"
    return text.replace(old, new)


def unsettle(path: Path, status_line: str, block: str, formal: tuple[str, str] | None = None,
             hash_line: str | None = None) -> str:
    """Rewrite a settled fixture entry to conjectured in place; return the settled original."""
    original = path.read_text(encoding="utf-8")
    text = replace_once(original, status_line, "status: conjectured\n")
    text = replace_once(text, block, "  settled_by: null\n")
    if formal is not None:
        text = replace_once(text, f"  decl: {formal[0]}\n", "  decl: null\n")
        text = replace_once(text, f"  file: {formal[1]}\n", "  file: null\n")
    if hash_line is not None:
        text = replace_once(text, hash_line, "statement_hash: null\n")
    path.write_text(text, encoding="utf-8")
    return original


def changed_lines(before: str, after: str) -> list[str]:
    return [line for line in difflib.ndiff(before.splitlines(), after.splitlines())
            if line.startswith(("- ", "+ "))]


def test_a_conjectured_entry_settles_to_refuted_touching_only_the_settled_fields(tmp_path, capsys):
    public, _ = stage(tmp_path)
    path = public / "ledger" / "MD_0002.md"
    original = unsettle(path, "status: refuted\n", SETTLED_BLOCK_0002)
    unsettled = path.read_text(encoding="utf-8")

    code = settle.main(["MD_0002", "--root", str(public), "--status", "refuted", "--by", "claude",
                        "--model", "claude-fable-5-1", "--date", "2026-09-03"])

    assert code == 0, capsys.readouterr().err
    settled = path.read_text(encoding="utf-8")
    assert settled == original
    assert changed_lines(unsettled, settled) == [
        "- status: conjectured", "+ status: refuted",
        "-   settled_by: null", *("+ " + line for line in SETTLED_BLOCK_0002.splitlines()),
    ]
    assert "ok 1 entries" in capsys.readouterr().out


def test_proven_formal_fills_the_formal_pointer_and_hash_from_the_audit(tmp_path, capsys):
    public, _ = stage(tmp_path)
    write_audit(public, {"MathDept.MD_0001.statement": {
        "module": "MathDept.Results.MD_0001", "axioms": [], "type": TYPE_0001}})
    path = public / "ledger" / "MD_0001.md"
    original = unsettle(path, "status: proven-formal\n", SETTLED_BLOCK_0001,
                        ("MathDept.MD_0001.statement", "MathDept/Results/MD_0001.lean"), HASH_0001)
    unsettled = path.read_text(encoding="utf-8")

    code = settle.main(["MD_0001", "--root", str(public), "--status", "proven-formal", "--by", "claude",
                        "--model", "claude-fable-5-1", "--date", "2026-09-02"])

    assert code == 0, capsys.readouterr().err
    settled = path.read_text(encoding="utf-8")
    assert settled == original
    assert sorted(changed_lines(unsettled, settled)) == sorted([
        "- status: conjectured", "+ status: proven-formal",
        "-   decl: null", "+   decl: MathDept.MD_0001.statement",
        "-   file: null", "+   file: MathDept/Results/MD_0001.lean",
        "-   settled_by: null", *("+ " + line for line in SETTLED_BLOCK_0001.splitlines()),
        "- statement_hash: null", "+ " + HASH_0001.rstrip("\n"),
    ])


def test_the_private_repo_settles_against_its_own_library(tmp_path, capsys):
    _, private = stage(tmp_path)
    write_audit(private, {"MathDept.MD_0007.statement": {
        "module": "MathDeptPrivate.Results.MD_0007", "axioms": [], "type": TYPE_0007}})
    path = private / "ledger" / "MD_0007.md"
    original = unsettle(path, "status: proven-formal\n", SETTLED_BLOCK_0007,
                        ("MathDept.MD_0007.statement", "MathDeptPrivate/Results/MD_0007.lean"), HASH_0007)

    code = settle.main(["MD_0007", "--root", str(private), "--status", "proven-formal", "--by", "claude",
                        "--model", "claude-fable-5-1", "--date", "2026-09-03"])

    assert code == 0, capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == original
    assert "[private repo]" in capsys.readouterr().out


def refused(capsys, root: Path, entry: str, *args: str) -> str:
    path = root / "ledger" / f"{entry}.md"
    before = path.read_bytes()
    code = settle.main([entry, "--root", str(root), *args])
    assert code == 1
    assert path.read_bytes() == before, "a refused settlement left the entry file changed"
    return capsys.readouterr().err


FORMAL_ARGS = ("--status", "proven-formal", "--by", "claude", "--model", "m")


def test_a_declaration_still_under_conjectures_is_refused(tmp_path, capsys):
    public, _ = stage(tmp_path)
    write_audit(public, {"MathDept.MD_0004.statement": {
        "module": "MathDept.Conjectures.MD_0004", "axioms": [], "type": TYPE_0001}})
    assert "Conjectures" in refused(capsys, public, "MD_0004", *FORMAL_ARGS)


def test_a_declaration_missing_from_the_audit_is_refused(tmp_path, capsys):
    public, _ = stage(tmp_path)
    write_audit(public, {})
    assert "MathDept.MD_0004.statement is not in audit/latest.json" in refused(
        capsys, public, "MD_0004", *FORMAL_ARGS)


def test_a_stale_audit_is_refused(tmp_path, capsys):
    public, _ = stage(tmp_path)
    write_audit(public, {"MathDept.MD_0004.statement": {
        "module": "MathDept.Results.MD_0004", "axioms": [], "type": TYPE_0001}}, sources_sha="0" * 64)
    assert "stale" in refused(capsys, public, "MD_0004", *FORMAL_ARGS)


def test_a_settlement_the_entry_gate_rejects_is_rolled_back(tmp_path, capsys):
    public, _ = stage(tmp_path)
    # MD_0004 carries no counterexample evidence, so I4 rejects `refuted`.
    err = refused(capsys, public, "MD_0004", "--status", "refuted", "--by", "claude", "--model", "m")
    assert "I4 status/evidence" in err and "restored" in err


def test_an_unsettled_status_takes_no_settler(tmp_path, capsys):
    public, _ = stage(tmp_path)
    assert "--by" in refused(capsys, public, "MD_0004", "--status", "open", "--by", "claude")


def test_a_how_that_contradicts_the_status_is_refused(tmp_path, capsys):
    public, _ = stage(tmp_path)
    assert "requires how 'counterexample'" in refused(
        capsys, public, "MD_0004", "--status", "refuted", "--by", "claude", "--model", "m", "--how", "lean")


def test_an_unknown_status_is_refused(tmp_path):
    public, _ = stage(tmp_path)
    with pytest.raises(ConfigError, match="not one of"):
        settle.settle(public, "MD_0004", "proven", by="claude", model="m")


def test_a_layout_the_line_editor_cannot_place_is_refused(tmp_path, capsys):
    public, _ = stage(tmp_path)
    path = public / "ledger" / "MD_0002.md"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "formal:\n  decl: null\n  file: null\n", "formal: {decl: null, file: null}\n")
    path.write_text(text, encoding="utf-8")
    (public / "MathDept" / "Results" / "MD_0002.lean").write_text("-- fixture\n", encoding="utf-8")
    write_audit(public, {"MathDept.MD_0002.statement": {
        "module": "MathDept.Results.MD_0002", "axioms": [], "type": TYPE_0001}})
    assert "formal" in refused(capsys, public, "MD_0002", *FORMAL_ARGS)


def test_a_refutation_may_name_its_compiled_negation(tmp_path, capsys):
    public, _ = stage(tmp_path)
    negation = public / "MathDept" / "Conjectures" / "MD_0002.lean"
    negation.parent.mkdir(parents=True)
    negation.write_text("namespace MathDept.MD_0002\n\ntheorem negation : True := trivial\n\nend MathDept.MD_0002\n",
                        encoding="utf-8")
    write_audit(public, {"MathDept.MD_0002.negation": {
        "module": "MathDept.Conjectures.MD_0002", "axioms": [], "type": TYPE_0001}})
    path = public / "ledger" / "MD_0002.md"
    unsettle(path, "status: refuted\n", SETTLED_BLOCK_0002)

    code = settle.main(["MD_0002", "--root", str(public), "--status", "refuted", "--by", "claude",
                        "--model", "m", "--decl", "MathDept.MD_0002.negation"])

    assert code == 0, capsys.readouterr().err
    text = path.read_text(encoding="utf-8")
    assert "  decl: MathDept.MD_0002.negation\n  file: MathDept/Conjectures/MD_0002.lean\n" in text
    assert f"statement_hash: {audit.type_hash(TYPE_0001)}\n" in text
