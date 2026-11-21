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
