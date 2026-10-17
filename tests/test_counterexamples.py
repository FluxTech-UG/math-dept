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
        "MD_0002": [
            {
                "file": "counterexamples/MD_0002_toy.py",
                "verified": True,
                "exact": True,
            }
        ]
    }


def test_two_artifacts_for_one_entry_are_both_reported(tmp_path):
    """A numeric lead and the exact witness that replaces it both belong to one entry.

    A report keyed by entry alone kept the last artifact loaded and dropped the
    rest, so a witness that stopped verifying could hide behind one that still
    did.
    """
    directory = tmp_path / "counterexamples"
    directory.mkdir()
    (directory / "MD_0002_toy.py").write_text(
        (REPO_ROOT / "tests" / "fixtures" / "good_public" / "counterexamples" / "MD_0002_toy.py")
        .read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (directory / "MD_0002_numeric_lead.py").write_text(
        '"""MD_0002 claims that every integer strictly exceeds its own square."""\n\n'
        "from mdept.refute import Witness\n\n\n"
        "def refute() -> Witness:\n"
        "    return Witness(entry='MD_0002', point={'n': 1.0}, claim=lambda n: n * n > n,\n"
        "                   numeric=True)\n",
        encoding="utf-8",
    )
    report = refute.run_all(directory)
    assert [record["file"] for record in report["MD_0002"]] == [
        "counterexamples/MD_0002_numeric_lead.py",
        "counterexamples/MD_0002_toy.py",
    ]
    assert [record["exact"] for record in report["MD_0002"]] == [False, True]
    assert refute.all_verified(report) is True
    assert len(refute.artifacts(report)) == 2


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


def test_a_relabelled_version_one_audit_is_refused_by_shape(tmp_path):
    """The version number is a claim; the shape is the fact.

    A v1 `counterexamples` mapping relabelled 2 passed the version gate and then
    failed inside a report loop with a TypeError, which named neither the file
    nor the reason.
    """
    import json

    from mdept import ConfigError, audit

    (tmp_path / "audit").mkdir()
    (tmp_path / "audit" / "latest.json").write_text(
        json.dumps({
            "schema_version": audit.SCHEMA_VERSION,
            "counterexamples": {"MD_0002": {"file": "x.py", "verified": True, "exact": True}},
        }),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="version 1 content with a new label"):
        audit.read_cached_audit(tmp_path)


def _write_artifact(directory, name, entry, body="point={'n': 1}, claim=lambda n: n * n > n"):
    (directory / name).write_text(
        '"""A toy claim that every integer strictly exceeds its own square."""\n\n'
        "from mdept.refute import Witness\n\n\n"
        "def refute() -> Witness:\n"
        f"    return Witness(entry={entry!r}, {body})\n",
        encoding="utf-8",
    )


@pytest.fixture
def mixed_directory(tmp_path):
    """Three entries' artifacts, one of them broken, one named off the convention."""
    root = tmp_path
    (root / "ledger").mkdir()
    directory = root / "counterexamples"
    directory.mkdir()
    _write_artifact(directory, "MD_0002_toy.py", "MD_0002")
    _write_artifact(directory, "renamed_witness.py", "MD_0003")
    (directory / "MD_0004_broken.py").write_text("raise RuntimeError('unrelated breakage')\n", encoding="utf-8")
    return root


def test_entry_run_selects_by_name_prefix_and_skips_broken_neighbours(mixed_directory):
    report = refute.run_entry(mixed_directory / "counterexamples", "MD_0002")
    assert report == {"MD_0002": [{"file": "counterexamples/MD_0002_toy.py", "verified": True, "exact": True}]}


def test_entry_run_selects_by_declared_entry(mixed_directory):
    report = refute.run_entry(mixed_directory / "counterexamples", "MD_0003")
    assert report == {"MD_0003": [{"file": "counterexamples/renamed_witness.py", "verified": True, "exact": True}]}


def test_entry_run_with_no_match_names_the_id(mixed_directory, capsys):
    with pytest.raises(CheckError, match="MD_0009"):
        refute.run_entry(mixed_directory / "counterexamples", "MD_0009")
    assert refute.main(["MD_0009", "--root", str(mixed_directory)]) == 1
    assert "FAIL no counterexample artifact for MD_0009" in capsys.readouterr().err


def test_entry_run_refuses_a_name_match_whose_witness_names_another_entry(tmp_path):
    directory = tmp_path / "counterexamples"
    directory.mkdir()
    _write_artifact(directory, "MD_0002_mislabelled.py", "MD_0005")
    with pytest.raises(CheckError, match="MD_0005"):
        refute.run_entry(directory, "MD_0002")


def test_cli_entry_and_all_forms(mixed_directory, capsys):
    assert refute.main(["MD_0002", "--root", str(mixed_directory)]) == 0
    assert capsys.readouterr().out == "ok  MD_0002 counterexamples/MD_0002_toy.py (exact)\n"
    assert refute.main(["--all", "--root", str(mixed_directory)]) == 1
    assert "unrelated breakage" in capsys.readouterr().err
    (mixed_directory / "counterexamples" / "MD_0004_broken.py").unlink()
    assert refute.main(["--all", "--root", str(mixed_directory)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "ok  MD_0002 counterexamples/MD_0002_toy.py (exact)",
        "ok  MD_0003 counterexamples/renamed_witness.py (exact)",
    ]
