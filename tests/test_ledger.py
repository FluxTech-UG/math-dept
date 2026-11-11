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
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdept import CheckError, ConfigError, check, index, new, parse, schema
from mdept import family as family_mod

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent
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
COUNTEREXAMPLES = {"run_counterexamples": True}
FAMILY = {"family": True}
LEAN = {"lean": True}

CASES = [
    Case("I01_filename_id_mismatch", "good_public", "I1 filename", PLAIN),
    Case("I02_contiguity_gap", "good_private", "I2 permanence", FAMILY),
    Case("I03_unknown_status", "good_public", "I3 schema", PLAIN),
    Case("I03_plain_words_missing", "good_public", "I3 schema", PLAIN,
         rule="every entry carries a '## In plain words' section"),
    Case("I03_plain_words_other_status", "good_private", "I3 schema", PLAIN,
         rule="names the status of another entry"),
    Case("I03_plain_words_stale_phrase", "good_public", "I3 schema", PLAIN,
         rule="the stale phrase 'no attempt has been made'"),
    Case("I04_cited_without_source", "good_public", "I4 status/evidence", PLAIN),
    Case("I05_statement_hash_drift", "good_public", "I5 formal pointer", LEAN),
    Case("I06_witness_does_not_refute", "good_public", "I6 counterexample", COUNTEREXAMPLES),
    Case("I07_anchor_unresolved", "good_private", "I7 raised-by", FAMILY),
    Case("I07_anchor_ambiguous", "good_private", "I7 raised-by", FAMILY),
    Case("I07_request_anchor", "good_private", "I7 raised-by", FAMILY),
    Case("I08_dangling_link", "good_private", "I8 links", PLAIN),
    Case("I09a_contradiction", "good_public", "I9a contradiction", PLAIN),
    Case("I10_unknown_source_tag", "good_public", "I10 cited source", PLAIN),
    Case("I11_extract_without_tag", "good_private", "I11 tag sync", PLAIN),
    Case("I12_dangling_token", "good_private", "I12 dangling", PLAIN),
    Case("I12_private_pointer_made_public", "good_public", "I12 dangling", PLAIN),
    Case("I13_closed_state_in_inbox", "good_private", "I13 inbox", PLAIN),
    Case("I14_backlink_mismatch", "good_private", "I14 back-link", PLAIN),
    Case("I15_citation_missing_word", "good_private", "I15 citation", FAMILY),
    Case("I15_code_citation_missing_word", "good_private", "I15 citation", FAMILY),
    Case("I16_stale_index", "good_public", "I16 generated", PLAIN),
    Case("I17_em_dash", "good_public", "I17 prose", PLAIN),
    Case("I18_settled_before_stipulated", "good_public", "I18 dates", PLAIN, regen=True),
    Case("I19_missing_role_line", "good_public", "I19 attempt record", PLAIN),
    Case("I20_sorry_in_results", "good_public", "I20 sorry fence", PLAIN),
    Case("I21_unlisted_citation", "good_private", "I21 unlisted citation", FAMILY),
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
    assert [n for n in context.notices if n.startswith("I7:")] == [
        "I7: MD_0006 anchors on wording (text:) in ToyRepo docs/toy.md; "
        "an ID form (A8, §21.3, §5 item 20, label:eq:name) survives a retitle"
    ], "a text: anchor is a notice, and the only entry on one is MD_0006"


def test_the_family_check_reads_the_extended_consumer_form(tmp_path):
    """`repos.yaml` carries `{path, ignore, view}` for ToyRepo, and both hold.

    The ignore glob is what keeps `vendor/` out of I21, and the generated
    marker is what keeps the mirrored notes out. Both files name an entry that
    does not list them, so either one failing to be skipped fails the check.
    """
    root = stage(tmp_path) / "good_private"
    context = check.run(root, family=True)
    toy = context.consumers["ToyRepo"]
    assert toy.ignore == ("vendor/*",) and toy.view == "docs/MATH.md"
    assert toy.ignored("vendor/third_party.md") and not toy.ignored("docs/toy.md")
    assert toy.is_generated(toy.path / "docs/generated_notes.md")
    assert not toy.view_path.exists(), "the view is generated on demand, never required"


def test_a_bare_consumer_path_still_means_the_default_view(tmp_path):
    written = tmp_path / "repos.yaml"
    written.write_text("consumers:\n  Bare: /somewhere/else\n", encoding="utf-8")
    assert parse.load_repos_yaml(written)["consumers"]["Bare"] == {
        "path": "/somewhere/else",
        "paths": ["/somewhere/else"],
        "ignore": [],
        "view": "docs/MATH.md",
        "archived": None,
    }


# --- a consumer path that lists candidates: the first on disk wins ----------


def list_toy_candidates(root: Path, candidates: list[str]) -> None:
    """Rewrite the fixture's `path: consumers/ToyRepo` as a list of candidates."""
    repos = root / "repos.yaml"
    text = repos.read_text(encoding="utf-8")
    assert text.count("    path: consumers/ToyRepo\n") == 1
    listed = ", ".join(f'"{candidate}"' for candidate in candidates)
    repos.write_text(text.replace("    path: consumers/ToyRepo\n", f"    path: [{listed}]\n"),
                     encoding="utf-8")


def test_the_first_candidate_on_disk_is_the_consumer_path(tmp_path):
    root = stage(tmp_path) / "good_private"
    list_toy_candidates(root, ["nowhere/ToyRepo", "consumers/ToyRepo", "consumers"])
    context = check.run(root, family=True)
    toy = context.consumers["ToyRepo"]
    assert toy.path == root / "consumers/ToyRepo"
    assert toy.candidates == (root / "nowhere/ToyRepo", root / "consumers/ToyRepo", root / "consumers")


def test_a_list_with_no_candidate_on_disk_fails_naming_every_candidate(tmp_path):
    root = stage(tmp_path) / "good_private"
    list_toy_candidates(root, ["nowhere/one", "~/nowhere-two-mdept-test"])
    with pytest.raises(CheckError, match="absent from disk") as raised:
        check.run(root, family=True)
    message = str(raised.value)
    assert "consumers.ToyRepo" in message
    assert str(root / "nowhere/one") in message
    assert str(Path("~/nowhere-two-mdept-test").expanduser()) in message


def test_a_single_path_and_a_one_element_list_resolve_the_same(tmp_path):
    root = stage(tmp_path) / "good_private"
    single = family_mod.read_consumers(root / "repos.yaml")["ToyRepo"]
    assert single.path == root / "consumers/ToyRepo"
    assert single.candidates == (root / "consumers/ToyRepo",)
    list_toy_candidates(root, ["consumers/ToyRepo"])
    assert family_mod.read_consumers(root / "repos.yaml")["ToyRepo"] == single


def test_a_single_absent_path_names_no_other_candidate(tmp_path):
    root = stage(tmp_path) / "good_private"
    list_toy_candidates(root, ["nowhere/ToyRepo"])
    with pytest.raises(CheckError) as raised:
        check.run(root, family=True)
    assert str(raised.value).endswith(
        f"{root / 'nowhere/ToyRepo'} is listed but absent from disk; "
        "a listed repo is required, never skipped"
    )


@pytest.mark.parametrize("value", [
    "Listed: {path: []}",
    "Listed: {path: 5}",
    "Listed: {path: [consumers/ToyRepo, 5]}",
    "Listed: {path: [consumers/ToyRepo, '']}",
    "Listed: {path: {nested: mapping}}",
    "Listed: 5",
])
def test_a_malformed_consumer_path_is_refused(value, tmp_path):
    written = tmp_path / "repos.yaml"
    written.write_text(f"consumers:\n  {value}\n", encoding="utf-8")
    with pytest.raises(CheckError, match=r"I7 raised-by: .*field 'consumers\.Listed"):
        parse.load_repos_yaml(written)


# --- an archived consumer: the key resolves, nothing of it is read ----------


SHELVED = "  Shelved:\n    archived: external drive, off-line\n"


def archive_a_consumer(root: Path) -> None:
    """List `Shelved` as archived, and let MD_0007 be raised there with its anchor kept."""
    repos = root / "repos.yaml"
    repos.write_text(repos.read_text(encoding="utf-8") + SHELVED, encoding="utf-8")
    entry = root / "ledger" / "MD_0007.md"
    text = entry.read_text(encoding="utf-8")
    assert text.count("    repo: ToyRepo\n") == 1
    entry.write_text(text.replace("    repo: ToyRepo\n", "    repo: Shelved\n"), encoding="utf-8")
    index.write(root)


def test_an_archived_consumer_parses_without_a_path(tmp_path):
    written = tmp_path / "repos.yaml"
    written.write_text("consumers:\n" + SHELVED, encoding="utf-8")
    assert parse.load_repos_yaml(written)["consumers"]["Shelved"] == {
        "path": None,
        "paths": [],
        "ignore": [],
        "view": "docs/MATH.md",
        "archived": "external drive, off-line",
    }


@pytest.mark.parametrize("value", [
    "{archived: external drive, path: /somewhere}",
    "{archived: external drive, ignore: ['x/*']}",
    "{archived: ''}",
    "{archived: [external drive]}",
])
def test_an_archived_consumer_takes_only_where_it_is_kept(value, tmp_path):
    written = tmp_path / "repos.yaml"
    written.write_text(f"consumers:\n  Shelved: {value}\n", encoding="utf-8")
    with pytest.raises(CheckError, match="consumers.Shelved"):
        parse.load_repos_yaml(written)


def test_the_family_check_resolves_an_archived_key_and_reads_nothing_of_it(tmp_path):
    """MD_0007 is raised by an archived repo, with a doc and an anchor that exist nowhere.

    I7 resolves the key and leaves the anchor unresolved on purpose, and I21
    skips the repo, so the family check passes with the archive off-line.
    """
    root = stage(tmp_path) / "good_private"
    archive_a_consumer(root)
    context = check.run(root, family=True)
    shelved = context.consumers["Shelved"]
    assert shelved.archived == "external drive, off-line" and shelved.path is None
    assert context.by_id["MD_0007"].at("provenance.raised_by.repo") == "Shelved"


def test_a_citation_naming_an_archived_consumer_fails_i15(tmp_path):
    root = stage(tmp_path) / "good_private"
    archive_a_consumer(root)
    entry = root / "ledger" / "MD_0007.md"
    text = entry.read_text(encoding="utf-8")
    entry.write_text(text.replace("cited_by: []", 'cited_by: ["Shelved:docs/toy.md"]'), encoding="utf-8")
    index.write(root)
    with pytest.raises(CheckError) as raised:
        check.run(root, family=True)
    assert str(raised.value).startswith("I15 citation")
    assert "archived" in str(raised.value)


def test_a_view_of_an_archived_consumer_is_refused(tmp_path):
    from mdept import view

    root = stage(tmp_path) / "good_private"
    archive_a_consumer(root)
    with pytest.raises(ConfigError, match="archived"):
        view.generate(family_mod.load_family(root), "Shelved")


def test_every_invariant_has_a_case():
    covered = {case.invariant.split()[0] for case in CASES}
    expected = {f"I{n}" for n in range(1, 22)}
    expected.discard("I9")
    expected.add("I9a")
    assert covered == expected


def test_the_invariant_list_is_the_one_that_runs():
    assert len(check.INVARIANTS) == 22


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
    assert case.rule in message, f"{case.name} was designed to break {case.rule!r} but raised: {message}"


def test_a_plain_words_section_may_name_another_entry_without_its_status(tmp_path):
    """MD_0007's section names MD_0001 as its mirror, with no status word near it."""
    root = stage(tmp_path) / "good_private"
    plain = parse.body_sections((root / "ledger" / "MD_0007.md").read_text(encoding="utf-8"))
    assert "MD_0001" in plain[schema.PLAIN_WORDS_HEADING], "the good case names another entry"
    check.run(root, family=True)


@pytest.mark.parametrize("text", [
    "Unlike MD_0001, which is proven, this bound is strict.",
    "This bound relies on MD_0001 for the base case.",
    "The bound is proven-formal in MD_0001 and restated here.",
])
def test_the_other_status_rule_fires_on_each_form(text):
    rules = [rule for rule, _ in schema.plain_words_problems("MD_0007", "proven-formal", text)]
    assert rules == ["other-status"], text


@pytest.mark.parametrize("text", [
    "MD_0001 was refuted by a small witness, and this bound is the corrected form.",
    "MD_0001 gives the base case, and the induction that follows carries the bound across every open step.",
    "MD_0007 is proven here, by induction on the naturals.",
    "The bound is the mirror of MD_0001. This entry is proven by induction.",
])
def test_the_other_status_rule_passes_a_refutation_a_distant_word_the_own_id_and_the_next_sentence(text):
    assert schema.plain_words_problems("MD_0007", "proven-formal", text) == []


def test_the_stale_phrase_rule_reads_only_unsettled_entries():
    text = "This bound is already settled in the source, so the first draft stands."
    assert [r for r, _ in schema.plain_words_problems("MD_0004", "conjectured", text)] == [
        "stale-phrase", "stale-phrase"]
    assert schema.plain_words_problems("MD_0004", "proven-informal", text) == []


@pytest.mark.parametrize("text", [
    "No proof yet covers four modes.",
])
def test_the_stale_phrase_rule_fires_on_each_phrase(text):
    rules = [rule for rule, _ in schema.plain_words_problems("MD_0004", "conjectured", text)]
    assert rules == ["stale-phrase"], text


def test_a_settled_entry_with_no_evidence_and_no_formal_pointer_fails_i4_with_the_settled_rule(tmp_path):
    """A settled entry stripped of every evidence row, with no formal pointer, fails on the
    general rule before any status-specific one, so the message names what is missing."""
    root = stage(tmp_path) / "good_public"
    apply_overlay(root, FIXTURES / "broken" / "I04_settled_without_evidence")
    index.write(root)
    with pytest.raises(CheckError) as raised:
        check.run(root)
    message = str(raised.value)
    assert message.startswith("I4 status/evidence: ledger/MD_0002.md: field 'evidence'"), message
    assert schema.SETTLED_SUPPORT_RULE in message


# --- one run reports every failing invariant --------------------------------


def _break_prose_and_fence(root: Path) -> None:
    """Two breaks in disjoint files: an em dash in a doc (I17) and a sorry in a Result (I20)."""
    apply_overlay(root, FIXTURES / "broken" / "I17_em_dash")
    apply_overlay(root, FIXTURES / "broken" / "I20_sorry_in_results")


def _first_line_of(lines: list[str], invariant: str) -> int:
    starts = [n for n, line in enumerate(lines) if line.startswith(invariant)]
    assert starts, f"no line starts with {invariant!r}: {lines}"
    return starts[0]


def test_a_run_reports_every_failing_invariant_in_order(tmp_path):
    """The run goes on past a failing invariant, so a fix spanning two invariants is one round."""
    root = stage(tmp_path) / "good_public"
    _break_prose_and_fence(root)
    with pytest.raises(CheckError) as raised:
        check.run(root)
    lines = str(raised.value).splitlines()
    assert _first_line_of(lines, "I17 prose") < _first_line_of(lines, "I20 sorry fence")


def test_the_cli_names_every_failing_invariant(tmp_path, capsys):
    root = stage(tmp_path) / "good_public"
    _break_prose_and_fence(root)
    assert check.main(["--root", str(root)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("FAIL I17 prose"), err
    assert "\nI20 sorry fence" in err, err


def test_the_sorry_fence_reports_every_violation(tmp_path):
    root = stage(tmp_path) / "good_public"
    apply_overlay(root, FIXTURES / "broken" / "I20_sorry_in_results")
    lean = root / "MathDept/Results/MD_0001.lean"
    lean.write_text(lean.read_text(encoding="utf-8").replace(
        "end MathDept.MD_0001",
        "theorem extra (n : Nat) : 0 + n = n := by\n  sorry\n\nend MathDept.MD_0001"), encoding="utf-8")
    with pytest.raises(CheckError) as raised:
        check.run(root)
    fence = [line for line in str(raised.value).splitlines() if line.startswith("I20 sorry fence")]
    assert len(fence) == 2, fence
    assert "line 11:" in fence[0] and "line 14:" in fence[1], fence


def test_the_inbox_check_reports_every_request(tmp_path):
    """An open request marked closed and a closed one missing a candidate's line fail together."""
    root = stage(tmp_path) / "good_private"
    apply_overlay(root, FIXTURES / "broken" / "I13_closed_state_in_inbox")
    closed = root / "inbox/done/2026-08-20-closed.md"
    text = closed.read_text(encoding="utf-8")
    assert text.count("- C3 -> declined:") == 1
    closed.write_text(text[:text.index("- C3 -> declined:")], encoding="utf-8")
    with pytest.raises(CheckError) as raised:
        check.run(root)
    inbox = [line for line in str(raised.value).splitlines() if line.startswith("I13 inbox")]
    assert any("inbox/2026-09-01-toy.md" in line for line in inbox), inbox
    assert any("2026-08-20-closed.md" in line and "C3 has no line" in line for line in inbox), inbox


def test_a_crash_after_a_failure_is_reported_with_it(tmp_path, monkeypatch):
    """An invariant reading a state an earlier failure guards may crash; the crash joins the report.

    With nothing failed before it, the crash is raised as itself.
    """
    def breaks(ctx):
        check.fail("I98 first", "ledger/MD_0001.md", "status", "a recorded failure")

    def crashes(ctx):
        raise RuntimeError("read a state the failure above guards")

    root = stage(tmp_path) / "good_public"
    monkeypatch.setattr(check, "INVARIANTS", (breaks, crashes))
    with pytest.raises(CheckError) as raised:
        check.run(root)
    message = str(raised.value)
    assert message.startswith("I98 first: ledger/MD_0001.md: field 'status': a recorded failure"), message
    assert "crashes" in message and "RuntimeError: read a state the failure above guards" in message
    assert isinstance(raised.value.__cause__, RuntimeError)
    monkeypatch.setattr(check, "INVARIANTS", (crashes,))
    with pytest.raises(RuntimeError, match="read a state"):
        check.run(root)


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
    for heading in schema.required_headings():
        assert heading in parse.body_sections(body)
    assert schema.PLAIN_WORDS_HEADING in parse.body_sections(body)


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
    entry_id, path, anchor_form = new.from_title(root, args)
    assert anchor_form == "none", "an entry born here has no consumer anchor"
    assert entry_id == "MD_0005", "IDs are allocated as max plus one"
    index.write(root)
    check.run(root)
    front, _, _ = parse.load_front_matter(Path(path))
    assert front["provenance"]["stipulated_by"]["who"] == "claude"
    assert front["provenance"]["raised_by"]["doc"] is None, "a public entry carries no private doc pointer"


def test_new_ends_its_output_on_the_allocated_id(tmp_path, capsys):
    root = stage(tmp_path) / "good_public"
    assert new.main(["--root", str(root), "--title", "t", "--kind", "lemma", "--topics", "toy",
                     "--domain", "d", "--who", "john"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[-2].startswith("next: "), "the hint stays above the id line"
    assert lines[-1] == "allocated MD_0005", "a reader of the last line alone gets the id"


def test_new_never_reuses_an_id(tmp_path):
    root = stage(tmp_path) / "good_public"
    args = SimpleNamespace(title="t", kind="lemma", topics="toy", domain="d", who="john",
                           repo="math-dept", model=None)
    first, _, _ = new.from_title(root, args)
    second, _, _ = new.from_title(root, args)
    assert (first, second) == ("MD_0005", "MD_0006")


def _stage_wrapped_request(tmp_path: Path) -> Path:
    """The private fixture plus a request shaped like the inbox TEMPLATE: trailing
    `# ...` comments on its fields and a Statement wrapped across lines."""
    root = stage(tmp_path) / "good_private"
    apply_overlay(root, FIXTURES / "requests" / "wrapped")
    return root


def test_new_request_form_keeps_trailing_comments_on_the_request(tmp_path):
    root = _stage_wrapped_request(tmp_path)
    entry_id, _, _ = new.from_request(root, "2026-09-02-wrapped", "C1", None)
    text = (root / "inbox" / "2026-09-02-wrapped.md").read_text(encoding="utf-8")
    assert f"ledger_ids: [{entry_id}]                       # filled at triage\n" in text
    assert "state: triaged                           # new | triaged | closed\n" in text


def test_new_request_form_carries_a_wrapped_statement_whole(tmp_path):
    root = _stage_wrapped_request(tmp_path)
    _, path, _ = new.from_request(root, "2026-09-02-wrapped", "C1", None)
    statement = parse.body_sections(Path(path).read_text(encoding="utf-8"))["Statement"].strip()
    assert statement == "For every natural $n$,\n$n \\le 2^n$,\nwith equality nowhere."


def test_new_refuses_to_overwrite_an_existing_entry(tmp_path):
    root = stage(tmp_path) / "good_public"
    with pytest.raises(CheckError, match="already exists"):
        new._write_new(root / "ledger" / "MD_0001.md", "would clobber a permanent ID")



# --- the environment never reaches past what a command needs ---------------


def test_a_plain_check_does_not_touch_the_private_side(tmp_path, monkeypatch):
    """A broken `MATHDEPT_PRIVATE` cannot fail a command that has no use for it.

    Consumer and sibling resolution is lazy, so the public repo's own check and
    its generated views never read the private repo or its `repos.yaml`. A
    misconfigured environment variable failing an unrelated command is how an
    operator learns to distrust the checker.
    """
    monkeypatch.setenv("MATHDEPT_PRIVATE", str(tmp_path / "gone"))
    root = stage(tmp_path) / "good_public"
    assert check.run(root).kind == "public"
    assert index.main(["--check", "--root", str(root)]) == 0


def test_an_env_var_pointing_at_a_non_repo_says_so(tmp_path, monkeypatch):
    """The variable promised a repo, so the variable is what the message names.

    A directory with no `ledger/` used to be accepted here and to surface later
    as `I1 filename: no 'ledger/' directory`, which blames an invariant for an
    environment variable and sends the reader to the wrong repo.
    """
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    monkeypatch.setenv("MATHDEPT_PRIVATE", str(not_a_repo))
    located = family_mod.locate(stage(tmp_path) / "good_public")
    with pytest.raises(ConfigError) as raised:
        located.private
    assert "is not a math repo (no ledger/)" in str(raised.value)
    assert "MATHDEPT_PRIVATE" in str(raised.value)
    assert not str(raised.value).startswith("I1 filename")


def test_a_command_run_outside_a_repo_fails_with_a_message(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert index.main(["--check"]) == 1
    assert "no math-dept repo root" in capsys.readouterr().err


# --- cited_by paths, quoted and not ----------------------------------------


@pytest.mark.parametrize(
    "citation,expected",
    [
        ("ToyRepo:docs/toy.md §1", ("ToyRepo", "docs/toy.md", "§1")),
        ("ToyRepo:src/toy.py", ("ToyRepo", "src/toy.py", None)),
        ('Some Repo:"research/a spaced name.md" §2',
         ("Some Repo", "research/a spaced name.md", "§2")),
        ("nothing-like-a-citation", None),
    ],
)
def test_a_cited_by_string_splits_into_repo_path_and_locator(citation, expected):
    assert schema.split_cited_by(citation) == expected


def test_the_quoted_form_is_used_exactly_when_the_path_needs_it():
    assert schema.cited_by_form("ToyRepo", "docs/toy.md") == "ToyRepo:docs/toy.md"
    assert schema.cited_by_form("Some Repo", "a doc.md") == 'Some Repo:"a doc.md"'


def test_a_spaced_path_is_satisfied_by_i15_and_i21_together(tmp_path):
    """The fixture cites `research/toy notes.md`, whose name contains a space.

    Unquoted, I21 would demand a `cited_by` row that I15 could never match,
    because the path regex stopped at the space: the entry would be
    unciteable from that file in both directions at once.
    """
    root = stage(tmp_path) / "good_private"
    context = check.run(root, family=True)
    cited = context.by_id["MD_0006"].front["cited_by"]
    assert 'ToyRepo:"research/toy notes.md" §2' in cited


def test_i21_scans_what_git_would_keep_and_reports_every_file_at_once(tmp_path):
    """A consumer checkout is scanned through git, and every violation is listed.

    A tracked file and an untracked-but-not-ignored file both reach the
    consumer's history and fail; a file under a gitignored `.claude/` (a session
    plan) never does and is not a citation surface. Both failures arrive in one
    run, so a two-file fix is one round.
    """
    root = stage(tmp_path) / "good_private"
    toy = root / "consumers/ToyRepo"
    citing = "Relies on MD_0006 (open).\n"
    (toy / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    (toy / "docs/tracked.md").write_text(citing, encoding="utf-8")
    (toy / "docs/untracked.md").write_text(citing, encoding="utf-8")
    (toy / ".claude/plans").mkdir(parents=True)
    (toy / ".claude/plans/session-plan.md").write_text(citing, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(toy)], check=True)
    tracked = [str(p.relative_to(toy)) for p in toy.rglob("*") if p.is_file()
               and not {".git", ".claude"} & set(p.parts) and p.name != "untracked.md"]
    subprocess.run(["git", "-C", str(toy), "add", "--", *tracked], check=True)
    with pytest.raises(CheckError) as raised:
        check.run(root, family=True)
    lines = str(raised.value).splitlines()
    assert any("ToyRepo:docs/tracked.md" in line for line in lines)
    assert any("ToyRepo:docs/untracked.md" in line for line in lines)
    assert not any(".claude/plans" in line for line in lines)
    assert all(line.startswith("I21 unlisted citation: ") for line in lines)


def test_a_consumer_column_lists_each_entry_once(tmp_path):
    """MD_0006 is cited from two files in ToyRepo and is one row, not two."""
    root = stage(tmp_path) / "good_private"
    consumer_section = [
        line for line in (root / "ledger/INDEX.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("| ToyRepo |")
    ]
    assert len(consumer_section) == 1
    assert consumer_section[0].count("MD_0006") == 2, "once as raised, once as cited"


def test_the_topic_index_is_topic_entries_and_neighbours(tmp_path):
    """Three columns: the topic, its entries, the topics they also file under."""
    root = stage(tmp_path) / "good_public"
    lines = index.render(root)[index.INDEX_PATH].splitlines()
    header = lines.index("## 2. Topic Index") + 2
    assert lines[header] == "| Topic | Entries | Connects to |"
    assert lines[header + 1] == "|---|---|---|"
    rows = lines[header + 2:lines.index("", header)]
    assert rows and all(row.count("|") == 4 for row in rows)


# --- I15 collects every violation -------------------------------------------


def test_i15_reports_every_violation_in_one_run(tmp_path):
    """Two citing lines without their status word fail together, one line each."""
    root = stage(tmp_path) / "good_private"
    toy = root / "consumers/ToyRepo/docs/toy.md"
    text = toy.read_text(encoding="utf-8")
    toy.write_text(text.replace(
        "This section relies on MD_0005 (conjectured, not yet settled) and on\n"
        "MD_0006 (open, pending), so no verdict here depends on either.",
        "This section relies on MD_0005 as a result and on\n"
        "MD_0006 as another, so verdicts here depend on both."), encoding="utf-8")
    with pytest.raises(CheckError) as raised:
        check.run(root, family=True)
    lines = str(raised.value).splitlines()
    assert len(lines) == 2
    assert all(line.startswith("I15 citation: ToyRepo:docs/toy.md:") for line in lines)
    assert "cites MD_0005 without any of" in lines[0]
    assert "cites MD_0006 without any of" in lines[1]


TOY_PARAGRAPH = ("This section relies on MD_0005 (conjectured, not yet settled) and on\n"
                 "MD_0006 (open, pending), so no verdict here depends on either.")


def _rewrite_toy(root: Path, paragraph: str) -> None:
    toy = root / "consumers/ToyRepo/docs/toy.md"
    text = toy.read_text(encoding="utf-8")
    assert TOY_PARAGRAPH in text
    toy.write_text(text.replace(TOY_PARAGRAPH, paragraph), encoding="utf-8")


def test_i15_reads_a_citation_wrapped_at_the_line_end_across_the_break(tmp_path):
    """An ID in a line's last characters carries its status word at the next line's start."""
    root = stage(tmp_path) / "good_private"
    _rewrite_toy(root, "This section relies on the toy bound MD_0005\n"
                       "(conjectured, not yet settled) and on MD_0006 (open, pending), so no\n"
                       "verdict here depends on either.")
    check.run(root, family=True)


def test_i15_does_not_read_the_next_line_for_an_id_away_from_the_line_end(tmp_path):
    root = stage(tmp_path) / "good_private"
    _rewrite_toy(root, "This section relies on MD_0005 as the bound it\n"
                       "uses (conjectured, not yet settled) and on MD_0006 (open, pending), so\n"
                       "no verdict here depends on either.")
    with pytest.raises(CheckError) as raised:
        check.run(root, family=True)
    lines = str(raised.value).splitlines()
    assert len(lines) == 1 and "cites MD_0005 without any of" in lines[0]


def test_citation_text_joins_the_next_line_only_inside_the_wrap_window():
    tail = "x" * (check.WRAP_WINDOW - len("MD_0001") - 1)
    near = ["relies on MD_0001" + tail, "(conjectured)"]
    far = ["relies on MD_0001" + tail + "x" * 2, "(conjectured)"]
    assert check.citation_text(near, 0, "MD_0001") == near[0] + "\n" + near[1]
    assert check.citation_text(far, 0, "MD_0001") == far[0]
    assert check.citation_text(near[:1], 0, "MD_0001") == near[0]


# --- the scoped run (--entry) -----------------------------------------------


def _orphan_for(root: Path, entry_id: str, slug: str = "stray") -> Path:
    orphan = root / "counterexamples" / f"{entry_id}_{slug}.py"
    orphan.write_text("def refute():\n    raise NotImplementedError\n", encoding="utf-8")
    return orphan


def test_a_scoped_run_ignores_another_entrys_orphan(tmp_path):
    """MD_0001 carries an orphan artifact; MD_0003 is clean."""
    root = stage(tmp_path) / "good_public"
    _orphan_for(root, "MD_0001")
    context = check.run(root, entries=["MD_0003"])
    assert [e.id for e in context.entries] == ["MD_0003"]
    with pytest.raises(CheckError, match=r"^I6 counterexample: counterexamples/MD_0001_stray\.py"):
        check.run(root, entries=["MD_0001"])
    with pytest.raises(CheckError, match=r"^I6 counterexample: counterexamples/MD_0001_stray\.py"):
        check.run(root)


def test_a_scoped_run_reports_a_file_that_belongs_to_no_entry(tmp_path):
    root = stage(tmp_path) / "good_public"
    _orphan_for(root, "MD_0042")
    with pytest.raises(CheckError, match=r"^I6 counterexample: counterexamples/MD_0042_stray\.py"):
        check.run(root, entries=["MD_0003"])


def test_a_scoped_run_ignores_another_entrys_lean_file_and_the_views(tmp_path):
    """A half-built Result of MD_0001 and a stale index fail only the full run."""
    root = stage(tmp_path) / "good_public"
    lean = root / "MathDept/Results/MD_0001.lean"
    lean.write_text(lean.read_text(encoding="utf-8").replace("  simp", "  sorry"), encoding="utf-8")
    check.run(root, entries=["MD_0003"])
    with pytest.raises(CheckError, match=r"^I20 sorry fence"):
        check.run(root, entries=["MD_0001"])
    (root / "ledger/INDEX.md").write_text("stale\n", encoding="utf-8")
    check.run(root, entries=["MD_0003"])
    with pytest.raises(CheckError, match=r"^I16 generated"):
        check.run(root)


def test_a_scoped_run_names_every_outcome_id_this_request_did_not_file(tmp_path):
    """A closed request's Outcome names two entries that point at no request.

    `2026-08-20-closed` files MD_0005 and MD_0006. A `related:` line naming the
    public sibling's MD_0001 and the private MD_0007 makes I14 read both as this
    request's claims, so the scoped gate of MD_0007 names both, not only the first.
    """
    root = stage(tmp_path) / "good_private"
    request = root / "inbox/done/2026-08-20-closed.md"
    request.write_text(request.read_text(encoding="utf-8") + "- related: MD_0001, MD_0007\n",
                       encoding="utf-8")
    with pytest.raises(CheckError) as raised:
        check.run(root, entries=["MD_0007"])
    backlinks = [line for line in str(raised.value).splitlines() if line.startswith("I14 back-link")]
    assert len(backlinks) == 2, backlinks
    assert "MD_0001" in backlinks[0] and "MD_0007" not in backlinks[0], backlinks
    assert "MD_0007" in backlinks[1] and "MD_0001" not in backlinks[1], backlinks


@pytest.mark.parametrize("flags, message", [
    (["--entry", "MD_0003", "--family"], "--entry and --family are exclusive"),
    (["--entry", "MD_0003", "--lean"], "--entry and --lean are exclusive"),
    (["--entry", "MD_0099"], "has no ledger file"),
    (["--entry", "0003"], "is not an entry ID"),
])
def test_the_scoped_cli_refuses_what_it_cannot_scope(flags, message, tmp_path, capsys):
    root = stage(tmp_path) / "good_public"
    assert check.main(["--root", str(root), *flags]) == 1
    assert message in capsys.readouterr().err


def test_the_scoped_cli_names_its_scope(tmp_path, capsys):
    root = stage(tmp_path) / "good_public"
    assert check.main(["--root", str(root), "--entry", "MD_0003", "--entry", "MD_0002"]) == 0
    assert "scope: MD_0002, MD_0003" in capsys.readouterr().out


# --- new: request-form flags apply or raise ---------------------------------


def test_new_request_form_applies_kind_and_topics(tmp_path):
    root = _stage_wrapped_request(tmp_path)
    _, path, _ = new.from_request(root, "2026-09-02-wrapped", "C1", None,
                                  kind="proposition", topics="toy, arithmetic")
    front = parse.load_entries(root)[-1].front
    assert Path(path).stem == front["id"]
    assert front["kind"] == "proposition"
    assert front["topics"] == ["toy", "arithmetic"]


def test_new_request_form_raises_on_a_flag_that_contradicts_the_request(tmp_path):
    root = _stage_wrapped_request(tmp_path)
    request = root / "inbox" / "2026-09-02-wrapped.md"
    text = request.read_text(encoding="utf-8")
    request.write_text(text.replace("- **Relation:** generalizes",
                                    "- **Topics:** toy\n- **Relation:** generalizes"), encoding="utf-8")
    with pytest.raises(ConfigError, match=r"--topics 'other' conflicts with the 'Topics' bullet"):
        new.from_request(root, "2026-09-02-wrapped", "C1", None, topics="other")
    assert not (root / "ledger" / "MD_0008.md").exists(), "nothing is written on a conflict"


def test_new_request_form_refuses_title_form_flags(tmp_path):
    root = _stage_wrapped_request(tmp_path)
    with pytest.raises(SystemExit):
        new.main(["--root", str(root), "--request", "2026-09-02-wrapped", "--candidate", "C1",
                  "--who", "john"])
