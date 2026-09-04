"""The invariant suite, driven by a fixture ledger with one break per invariant.

`tests/fixtures/good_public/` and `tests/fixtures/good_private/` are small,
valid repos: four released entries beside a Lean result and a counterexample,
and two unreleased entries beside an inbox, a triage record, an extract and a
consumer repo. Both must pass every mode.

Each case under `tests/fixtures/broken/` is an OVERLAY: the files it contains
replace their counterparts in the base repo, and nothing else changes. A case
is therefore a readable one-field diff, and the test asserts that the failure
names the invariant the diff was designed to break, not merely that something
failed.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdept import CheckError, ConfigError, check, index, new, parse, schema

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent
BASES = ("good_public", "good_private")


@dataclass(frozen=True)
class Case:
    """One deliberate break: which base, which modes, and the invariant it must raise."""

    name: str
    base: str
    invariant: str
    modes: dict
    regen: bool = False


PLAIN: dict = {}
COUNTEREXAMPLES = {"run_counterexamples": True}
FAMILY = {"family": True}
LEAN = {"lean": True}

CASES = [
    Case("I01_filename_id_mismatch", "good_public", "I1 filename", PLAIN),
    Case("I02_contiguity_gap", "good_private", "I2 permanence", FAMILY),
    Case("I03_unknown_status", "good_public", "I3 schema", PLAIN),
    Case("I04_cited_without_source", "good_public", "I4 status/evidence", PLAIN),
    Case("I05_statement_hash_drift", "good_public", "I5 formal pointer", LEAN),
    Case("I06_witness_does_not_refute", "good_public", "I6 counterexample", COUNTEREXAMPLES),
    Case("I07_anchor_not_in_doc", "good_private", "I7 raised-by", FAMILY),
    Case("I08_dangling_link", "good_public", "I8 links", PLAIN),
    Case("I09a_contradiction", "good_public", "I9a contradiction", PLAIN),
    Case("I10_unknown_source_tag", "good_public", "I10 cited source", PLAIN),
    Case("I11_extract_without_tag", "good_private", "I11 tag sync", PLAIN),
    Case("I12_dangling_token", "good_public", "I12 dangling", PLAIN),
    Case("I13_closed_state_in_inbox", "good_private", "I13 inbox", PLAIN),
    Case("I14_backlink_mismatch", "good_private", "I14 back-link", PLAIN),
    Case("I15_citation_missing_word", "good_private", "I15 citation", FAMILY),
    Case("I16_stale_index", "good_public", "I16 generated", PLAIN),
    Case("I17_em_dash", "good_public", "I17 prose", PLAIN),
    Case("I18_settled_before_stipulated", "good_public", "I18 dates", PLAIN, regen=True),
    Case("I19_missing_role_line", "good_public", "I19 attempt record", PLAIN),
    Case("I20_sorry_in_results", "good_public", "I20 sorry fence", PLAIN),
]


def stage(tmp_path: Path) -> Path:
    """Copy both bases side by side, so `repos.yaml`'s public_sibling resolves."""
    for base in BASES:
        shutil.copytree(FIXTURES / base, tmp_path / base)
    return tmp_path


def apply_overlay(root: Path, overlay: Path) -> None:
    for source in sorted(overlay.rglob("*")):
        if source.is_dir():
            continue
        destination = root / source.relative_to(overlay)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


# --- the good fixtures ------------------------------------------------------


@pytest.mark.parametrize("base", BASES)
def test_good_fixture_passes_plain(base, tmp_path):
    root = stage(tmp_path) / base
    assert check.run(root).notices == []


def test_good_public_passes_every_mode(tmp_path):
    root = stage(tmp_path) / "good_public"
    check.run(root, run_counterexamples=True, lean=True)


def test_good_private_passes_family(tmp_path):
    root = stage(tmp_path) / "good_private"
    context = check.run(root, family=True)
    assert context.kind == "private"
    assert context.sibling is not None and context.sibling.name == "good_public"


def test_every_invariant_has_a_case():
    covered = {case.invariant.split()[0] for case in CASES}
    expected = {f"I{n}" for n in range(1, 21)}
    expected.discard("I9")
    expected.add("I9a")
    assert covered == expected


def test_the_invariant_list_is_the_one_that_runs():
    assert len(check.INVARIANTS) == 21


# --- one break per invariant ------------------------------------------------


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


# --- I9b is a notice, not a failure -----------------------------------------


def test_inheritance_is_reported_and_not_failed(tmp_path):
    root = stage(tmp_path) / "good_public"
    apply_overlay(root, FIXTURES / "notice" / "I9b_inheritance")
    index.write(root)
    context = check.run(root)
    assert any(notice.startswith("I9b: MD_0004") for notice in context.notices)
    assert "I9b: MD_0004" in (root / "ledger" / "INDEX.md").read_text(encoding="utf-8")


# --- the template and the allocator agree with the schema -------------------


def test_template_front_matter_validates():
    path = REPO_ROOT / "ledger" / "TEMPLATE.md"
    front, _, body = parse.load_front_matter(path)
    schema.validate_front(front, path, "public")
    for heading in schema.BODY_HEADINGS:
        assert heading in parse.body_sections(body)


def test_new_title_form_writes_an_entry_the_checker_accepts(tmp_path):
    root = stage(tmp_path) / "good_public"
    args = SimpleNamespace(
        title="A statement raised in this repo",
        kind="lemma",
        topics="toy,arithmetic",
        domain="elementary arithmetic on the naturals",
        who="claude",
        repo="math-dept",
        model="claude-fable-5-1",
    )
    entry_id, path = new.from_title(root, args)
    assert entry_id == "MD_0005", "IDs are allocated as max plus one"
    index.write(root)
    check.run(root)
    front, _, _ = parse.load_front_matter(Path(path))
    assert front["provenance"]["stipulated_by"]["who"] == "claude"
    assert front["provenance"]["raised_by"]["doc"] is None, "a public entry carries no private doc pointer"


def test_new_never_reuses_an_id(tmp_path):
    root = stage(tmp_path) / "good_public"
    args = SimpleNamespace(title="t", kind="lemma", topics="toy", domain="d", who="john",
                           repo="math-dept", model=None)
    first, _ = new.from_title(root, args)
    second, _ = new.from_title(root, args)
    assert (first, second) == ("MD_0005", "MD_0006")


def test_new_refuses_to_overwrite_an_existing_entry(tmp_path):
    root = stage(tmp_path) / "good_public"
    with pytest.raises(CheckError, match="already exists"):
        new._write_new(root / "ledger" / "MD_0001.md", "would clobber a permanent ID")

