"""Guard: every counterexample artifact still refutes what it claims to refute.

An artifact is evidence only while it runs. This executes each one and demands
that its witness verify: the claim must evaluate to exactly False at the stated
point. The fixture artifacts are included so the contract is exercised even
while the released ledger holds no refutations of its own.
"""

from pathlib import Path

import pytest

from mdept import refute
from mdept.refute import Witness
from mdept import CheckError

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_ARTIFACTS = sorted((REPO_ROOT / "counterexamples").glob("*.py"))
FIXTURE_ARTIFACTS = sorted((REPO_ROOT / "tests" / "fixtures" / "good_public" / "counterexamples").glob("*.py"))
ALL_ARTIFACTS = LEDGER_ARTIFACTS + FIXTURE_ARTIFACTS


@pytest.mark.parametrize("path", ALL_ARTIFACTS, ids=[p.stem for p in ALL_ARTIFACTS])
def test_witness_verifies(path):
    witness = refute.load(path)
    assert isinstance(witness, Witness)
    assert path.stem.startswith(witness.entry + "_"), (
        f"{path.name} does not belong to {witness.entry}"
    )
    assert witness.verify(), f"the claim did not evaluate to False at {witness.point}"


def test_run_all_reports_every_artifact():
    report = refute.run_all(REPO_ROOT / "tests" / "fixtures" / "good_public" / "counterexamples")
    assert report == {
        "MD_0002": {
            "file": "counterexamples/MD_0002_toy.py",
            "verified": True,
            "exact": True,
        }
    }


def test_a_witness_that_does_not_refute_reports_false():
    witness = Witness(entry="MD_0002", point={"n": 2}, claim=lambda n: n * n > n)
    assert witness.verify() is False


def test_an_exact_witness_refuses_a_float():
    witness = Witness(entry="MD_0002", point={"x": 0.5}, claim=lambda x: x > 0)
    with pytest.raises(CheckError, match="is not exact"):
        witness.verify()


def test_a_numeric_witness_accepts_a_float():
    witness = Witness(entry="MD_0002", point={"x": 0.5}, claim=lambda x: x > 1, numeric=True)
    assert witness.verify() is True


def test_a_non_boolean_claim_is_refused():
    witness = Witness(entry="MD_0002", point={"n": 1}, claim=lambda n: "maybe")
    with pytest.raises(CheckError, match="definite True or False"):
        witness.verify()


def test_a_module_without_refute_is_refused(tmp_path):
    artifact = tmp_path / "MD_0002_empty.py"
    artifact.write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(CheckError, match="defines no `refute"):
        refute.load(artifact)


def test_module_invocation_uses_canonical_witness_class():
    """`python -m mdept.refute` runs refute.py as `__main__`; artifacts import the canonical
    `mdept.refute.Witness`. The CLI must dispatch to the canonical module so the isinstance
    check in `load` compares against the class the artifacts actually bound."""
    import subprocess
    import sys
    from pathlib import Path

    import shutil
    import tempfile

    repo = Path(__file__).resolve().parents[1]
    source = repo / "tests" / "fixtures" / "good_public"
    # Run against a copy so the CLI never writes bytecode into the tracked fixture.
    fixture = Path(tempfile.mkdtemp()) / "good_public"
    shutil.copytree(source, fixture, ignore=shutil.ignore_patterns("__pycache__"))
    result = subprocess.run(
        [sys.executable, "-m", "mdept.refute", "--all", "--root", str(fixture)],
        capture_output=True, text=True, cwd=repo, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok " in result.stdout
