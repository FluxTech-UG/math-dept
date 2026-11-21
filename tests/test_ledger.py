"""The validator refuses what would otherwise pass unseen, driven by a fixture ledger.

`tests/fixtures/good_public/` and `tests/fixtures/good_private/` are small,
valid repos: four released entries beside a Lean result and a counterexample,
and two unreleased entries beside an inbox, a triage record, an extract and a
consumer repo.

Each case under `tests/fixtures/broken/` is an OVERLAY: the files it contains
replace their counterparts in the base repo, and nothing else changes. A case
is therefore a readable one-field diff, and the test asserts that the failure
names the invariant the diff was designed to break, not merely that something
failed. The cases are the silent ones: a status claimed without its support,
a formal pointer whose Lean statement has drifted from the entry, and private
machinery named in the public repo's text.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

from mdept import CheckError, ConfigError, check, index

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASES = ("good_public", "good_private")


@dataclass(frozen=True)
class Case:
    """One deliberate break: which base, which modes, the invariant it must raise, and,
    where one invariant enforces several rules, the words that name the rule it breaks."""

    name: str
    base: str
    invariant: str
    modes: dict
    regen: bool = False
    rule: str = ""


PLAIN: dict = {}
LEAN = {"lean": True}

CASES = [
    Case("I04_cited_without_source", "good_public", "I4 status/evidence", PLAIN),
    Case("I05_statement_hash_drift", "good_public", "I5 formal pointer", LEAN),
    Case("I23_private_machinery", "good_public", "I23 public text", PLAIN,
         rule="docs/notes.md:5"),
]


def stage(tmp_path: Path) -> Path:
    """Copy both bases side by side, so `repos.yaml`'s public_sibling resolves."""
    for base in BASES:
        shutil.copytree(FIXTURES / base, tmp_path / base,
                        ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def apply_overlay(root: Path, overlay: Path) -> None:
    for source in sorted(overlay.rglob("*")):
        if source.is_dir():
            continue
        destination = root / source.relative_to(overlay)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, destination)


@pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])
def test_broken_case_raises_its_own_invariant(case, tmp_path):
    root = stage(tmp_path) / case.base
    apply_overlay(root, FIXTURES / "broken" / case.name)
    if case.regen:
        index.write(root)
    with pytest.raises((CheckError, ConfigError)) as raised:
        check.run(root, **case.modes)
    message = str(raised.value)
    assert message.startswith(case.invariant), (
        f"{case.name} was designed to break {case.invariant} but raised: {message}"
    )
    assert case.rule in message, f"{case.name} was designed to break {case.rule!r} but raised: {message}"
