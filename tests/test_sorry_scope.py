"""Guard: the `sorry` fence and the entry-file naming rules, without Lean.

`sorry` is legitimate under `*/Conjectures/` and nowhere else. This check runs
in pure Python so it holds on a machine with no toolchain, which is where a
stray `sorry` would otherwise sit unnoticed until CI.
"""

from pathlib import Path

import pytest

from mdept.audit import sorry_violations, strip_lean_comments

REPO_ROOT = Path(__file__).resolve().parent.parent

CONJECTURE = """import Mathlib.Data.Nat.Basic

namespace MathDept.MD_0009

theorem statement (n : Nat) : n + 0 = n := by
  sorry

end MathDept.MD_0009
"""


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_repo_has_no_sorry_violations():
    assert sorry_violations(REPO_ROOT) == []


def test_sorry_is_allowed_under_conjectures(tmp_path):
    write(tmp_path, "MathDept/Conjectures/MD_0009.lean", CONJECTURE)
    assert sorry_violations(tmp_path) == []


def test_sorry_under_results_is_a_violation(tmp_path):
    write(tmp_path, "MathDept/Results/MD_0009.lean", CONJECTURE)
    violations = sorry_violations(tmp_path)
    assert len(violations) == 1
    assert violations[0]["line"] == 6
    assert "outside */Conjectures/" in violations[0]["reason"]


def test_commented_sorry_is_not_a_violation(tmp_path):
    write(tmp_path, "MathDept/Results/MD_0009.lean",
          CONJECTURE.replace("  sorry", "  simp -- sorry was here\n  /- and sorry here -/"))
    assert sorry_violations(tmp_path) == []


def test_entry_file_must_be_named_for_its_id(tmp_path):
    write(tmp_path, "MathDept/Results/Helpers.lean", CONJECTURE.replace("  sorry", "  simp"))
    reasons = [v["reason"] for v in sorry_violations(tmp_path)]
    assert any("named MD_####.lean" in r for r in reasons)


def test_entry_file_must_open_its_namespace(tmp_path):
    write(tmp_path, "MathDept/Results/MD_0009.lean",
          CONJECTURE.replace("namespace MathDept.MD_0009", "namespace Elsewhere").replace("  sorry", "  simp"))
    reasons = [v["reason"] for v in sorry_violations(tmp_path)]
    assert any("namespace MathDept.MD_0009" in r for r in reasons)


def test_an_id_cannot_be_both_conjecture_and_result(tmp_path):
    write(tmp_path, "MathDept/Conjectures/MD_0009.lean", CONJECTURE)
    write(tmp_path, "MathDept/Results/MD_0009.lean", CONJECTURE.replace("  sorry", "  simp"))
    reasons = [v["reason"] for v in sorry_violations(tmp_path)]
    assert any("exactly one Lean file" in r for r in reasons)


@pytest.mark.parametrize(
    "source",
    [
        "a -- sorry\nb",
        "/- sorry -/ x",
        "/-! doc /- nested sorry -/ -/ x",
    ],
    ids=["line-comment", "block-comment", "nested-block"],
)
def test_comment_stripper_removes_sorry(source):
    assert "sorry" not in strip_lean_comments(source)


def test_comment_stripper_keeps_real_code_and_line_numbers():
    stripped = strip_lean_comments("a -- x\nsorry\n/- y -/")
    assert "sorry" in stripped
    assert len(stripped.splitlines()) == 3
