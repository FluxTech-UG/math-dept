"""`python -m mdept.inbox_status`: the inbox run's measure, one line and the names behind it.

Every case runs on a staged copy of both fixtures. The good private fixture has one
open request (state new, its one candidate pending), and three unsettled entries
across the pair: MD_0004 (public, no attempt record), MD_0005 (no attempt record) and
MD_0006 (a record with no fidelity row).
"""

import shutil
import sys
from pathlib import Path

import pytest

from mdept import inbox_status

FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_ledger import I15_TOY, apply_overlay, declare_baseline  # noqa: E402


def stage(tmp_path: Path) -> Path:
    for base in ("good_public", "good_private"):
        shutil.copytree(FIXTURES / base, tmp_path / base, ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path / "good_private"


def lines_of(root: Path, capsys) -> list[str]:
    assert inbox_status.main(["--root", str(root)]) == 0
    return capsys.readouterr().out.splitlines()


def count(line: str, name: str) -> int:
    """The value of one `name=<n>` field of the first line."""
    fields = dict(field.split("=") for field in line.split())
    return int(fields[name])


PROOF = ("# MD_{n} informal proof\n<!-- role: record | status: current 2026-09-03 | entry: MD_{n} -->\n\n"
         "Informal proof. An attempt record, not a status.\n")
RECORD_HEAD = ("# MD_{n} attempt record\n<!-- role: record | status: current 2026-09-04 | "
               "cited-by: ledger/MD_{n}.md -->\n\n| Date | Stage | Tried | Showed | Time | Model |\n"
               "|---|---|---|---|---|---|\n")
OWING_ROWS = ("| 2026-09-02 | fidelity | round trip | match | 3 min | m |\n"
              "| 2026-09-03 | S3 | informal proof | closed | 20 min | m |\n"
              "| 2026-09-03 | S3-review | hostile review | accept with nits | 10 min | m |\n"
              "| 2026-09-04 | repair | the review's wording nits | applied | 2 min | m |\n"
              "| 2026-09-04 | S3-review | same-day review | accept | 5 min | m |\n")


def give_proof(root: Path, n: str, rows: str) -> None:
    """Write proofs/MD_<n>.md and an attempt record holding `rows`."""
    (root / "proofs").mkdir(exist_ok=True)
    (root / "proofs" / f"MD_{n}.md").write_text(PROOF.format(n=n), encoding="utf-8")
    (root / "triage" / f"MD_{n}.md").write_text(RECORD_HEAD.format(n=n) + rows, encoding="utf-8")


def stipulate(root: Path, date: str) -> None:
    entry = root / "ledger" / "MD_0005.md"
    entry.write_text(entry.read_text(encoding="utf-8").replace("date: 2026-08-20", f"date: {date}"),
                     encoding="utf-8")


def test_the_first_line_is_the_five_counts_and_the_names_follow(tmp_path, capsys):
    lines = lines_of(stage(tmp_path), capsys)
    assert lines[0] == ("new=1 closable_open=0 entries_without_current_fidelity=3 check_fails=0 "
                        "later_day_owed=0")
    assert lines[1] == "new: 2026-09-01-toy"
    assert lines[2] == ("entries_without_current_fidelity: MD_0004 (no attempt record), "
                        "MD_0005 (no attempt record), MD_0006 (no fidelity row)")
    assert len(lines) == 3


def test_a_request_whose_every_candidate_is_answered_is_closable(tmp_path, capsys):
    root = stage(tmp_path)
    request = root / "inbox" / "2026-09-01-toy.md"
    text = request.read_text(encoding="utf-8")
    request.write_text(text.replace("Not yet triaged.", "- C1 -> declined: ill-posed."), encoding="utf-8")
    lines = lines_of(root, capsys)
    assert lines[0].split()[1] == "closable_open=1"
    assert "closable_open: 2026-09-01-toy" in lines


def test_a_statement_edit_after_the_last_round_trip_counts_and_a_new_round_trip_clears_it(tmp_path, capsys):
    root = stage(tmp_path)
    apply_overlay(root, FIXTURES / "broken" / "I22_fidelity_stale")
    lines = lines_of(root, capsys)
    assert "MD_0006 (row 4, a statement edit, has no later fidelity row)" in lines[2]
    record = root / "triage" / "MD_0006.md"
    record.write_text(record.read_text(encoding="utf-8").replace(
        "| 10 min | claude-fable-5-1 |\n",
        "| 10 min | claude-fable-5-1 |\n| 2026-09-04 | fidelity | round trip | match | 3 min | m |\n"),
        encoding="utf-8")
    lines = lines_of(root, capsys)
    assert lines[0].split()[2] == "entries_without_current_fidelity=2"
    assert "MD_0006" not in lines[2]


def test_check_failures_are_counted_in_process_and_baseline_hits_are_not(tmp_path, capsys):
    root = stage(tmp_path)
    apply_overlay(root, FIXTURES / "broken" / "I15_citation_missing_word")
    lines = lines_of(root, capsys)
    assert count(lines[0], "check_fails") == 2
    assert lines[-2:] == [f"  I15 citation: ToyRepo:docs/toy.md:5: field '<line>': cites {i} without any of "
                          f"{w}; the entry is {s}"
                          for i, w, s in (("MD_0005", "['pending', 'conjectured', 'open']", "conjectured"),
                                          ("MD_0006", "['pending', 'conjectured', 'open']", "open"))]
    declare_baseline(root, {**I15_TOY, "text": "cites MD_0005"})
    lines = lines_of(root, capsys)
    assert count(lines[0], "check_fails") == 1
    assert "cites MD_0005" not in "\n".join(lines)


def test_a_conjectured_entry_whose_proof_changed_last_owes_a_check_from_the_next_day(tmp_path, capsys):
    root = stage(tmp_path)
    give_proof(root, "0005", OWING_ROWS)
    lines = lines_of(root, capsys)
    assert count(lines[0], "later_day_owed") == 1
    assert count(lines[0], "check_fails") == 0
    # The last row that changed the proof is the repair of 2026-09-04; reviews change nothing.
    assert "later_day_owed: MD_0005 (check from 2026-09-05, settle --date 2026-09-04)" in lines


def test_a_later_day_check_after_the_last_change_clears_the_entry(tmp_path, capsys):
    root = stage(tmp_path)
    give_proof(root, "0005", OWING_ROWS + "| 2026-09-05 | later-day-check | cold check | accept | 9 min | m |\n")
    lines = lines_of(root, capsys)
    assert count(lines[0], "later_day_owed") == 0
    give_proof(root, "0005", OWING_ROWS + "| 2026-09-05 | later-day-check | cold check | accept | 9 min | m |\n"
               "| 2026-09-05 | S3-fix | the check's finding | applied | 5 min | m |\n")
    lines = lines_of(root, capsys)
    assert "later_day_owed: MD_0005 (check from 2026-09-06, settle --date 2026-09-05)" in lines


def test_a_settled_entry_with_a_proof_is_never_owed(tmp_path, capsys):
    root = stage(tmp_path)
    record = (root / "triage" / "MD_0007.md").read_text(encoding="utf-8")
    give_proof(root, "0007", "")
    (root / "triage" / "MD_0007.md").write_text(
        record + "| 2026-09-04 | S3 | informal proof | closed | 20 min | m |\n", encoding="utf-8")
    lines = lines_of(root, capsys)
    assert count(lines[0], "later_day_owed") == 0
    assert not any(line.startswith("later_day_owed:") for line in lines)


def test_an_entry_stipulated_the_day_of_its_proof_settles_that_day(tmp_path, capsys):
    root = stage(tmp_path)
    stipulate(root, "2026-09-04")
    give_proof(root, "0005", OWING_ROWS)
    lines = lines_of(root, capsys)
    assert "later_day_owed: MD_0005 (check from 2026-09-05, settle --date 2026-09-04)" in lines


def test_an_entry_stipulated_after_its_last_change_settles_on_its_stipulated_date(tmp_path, capsys):
    # I18 refuses a settle date before the stipulated date, and the check must fall
    # strictly after the settle date, so both move to the stipulated date.
    root = stage(tmp_path)
    stipulate(root, "2026-09-10")
    give_proof(root, "0005", OWING_ROWS)
    lines = lines_of(root, capsys)
    assert "later_day_owed: MD_0005 (check from 2026-09-11, settle --date 2026-09-10)" in lines


def test_a_record_row_whose_date_is_not_a_date_is_refused(tmp_path, capsys):
    root = stage(tmp_path)
    give_proof(root, "0005", OWING_ROWS.replace("2026-09-03 | S3 |", "3 Sept | S3 |"))
    assert inbox_status.main(["--root", str(root)]) == 1
    err = capsys.readouterr().err
    assert "triage/MD_0005.md" in err and "'3 Sept'" in err


def test_the_public_repo_alone_is_refused(tmp_path, capsys, monkeypatch):
    root = stage(tmp_path).parent / "good_public"
    monkeypatch.delenv("MATHDEPT_PRIVATE", raising=False)
    assert inbox_status.main(["--root", str(root)]) == 1
    assert "private repo" in capsys.readouterr().err
