"""`python -m mdept.row` appends attempt rows to triage records, or writes nothing.

Every case runs on a staged copy of the private fixture, whose records carry the
attempts table followed by prose (MD_0006) or ending the file (MD_0007). A row lands
right under the table's last row, every other byte stays, and any refusal leaves
every record as it was.
"""

import datetime
import shutil
from pathlib import Path

import pytest

from mdept import row

FIXTURES = Path(__file__).resolve().parent / "fixtures"
EM_DASH = "\u2014"
ROW_0006 = "| 2026-11-01 | S3 | a five line argument | it closes | 12 min | claude-opus-5-5 |\n"
LAST_0006 = ("| 2026-09-02 | S1 | rational scan over a finite range | no counterexample found "
             "| 20 min | claude-fable-5-1 |\n")


def stage(tmp_path: Path) -> Path:
    for base in ("good_public", "good_private"):
        shutil.copytree(FIXTURES / base, tmp_path / base,
                        ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path / "good_private"


def snapshot(root: Path) -> dict:
    return {p.name: p.read_bytes() for p in sorted((root / "triage").iterdir())}


def args_0006(root: Path, **override) -> list[str]:
    flags = {"--stage": "S3", "--tried": "a five line argument", "--showed": "it closes",
             "--time": "12 min", "--model": "claude-opus-5-5", "--date": "2026-11-01"}
    flags.update(override)
    out = ["MD_0006", "--root", str(root)]
    for flag, value in flags.items():
        if value is not None:
            out += [flag, value]
    return out


def test_row_lands_under_the_last_row_and_before_the_prose(tmp_path, capsys):
    root = stage(tmp_path)
    path = root / "triage" / "MD_0006.md"
    before = path.read_text(encoding="utf-8")
    assert row.main(args_0006(root)) == 0
    assert capsys.readouterr().out == "row MD_0006 S3\n"
    assert path.read_text(encoding="utf-8") == before.replace(LAST_0006, LAST_0006 + ROW_0006, 1)


def test_row_on_a_table_that_ends_the_file_without_a_newline(tmp_path):
    root = stage(tmp_path)
    path = root / "triage" / "MD_0007.md"
    before = path.read_text(encoding="utf-8").rstrip("\n")
    path.write_text(before, encoding="utf-8")
    assert row.main(["MD_0007", "--root", str(root), "--stage", "S1", "--tried", "t",
                     "--showed", "s", "--time", "1 min", "--model", "m", "--date", "2026-11-02"]) == 0
    assert path.read_text(encoding="utf-8") == before + "\n| 2026-11-02 | S1 | t | s | 1 min | m |\n"


def test_date_defaults_to_today(tmp_path):
    root = stage(tmp_path)
    assert row.main(args_0006(root, **{"--date": None})) == 0
    text = (root / "triage" / "MD_0006.md").read_text(encoding="utf-8")
    assert f"| {datetime.date.today().isoformat()} | S3 | a five line argument |" in text


def test_root_is_found_from_the_working_directory(tmp_path, monkeypatch):
    root = stage(tmp_path)
    monkeypatch.chdir(root / "triage")
    argv = args_0006(root)
    del argv[1:3]  # no --root
    assert row.main(argv) == 0
    assert ROW_0006 in (root / "triage" / "MD_0006.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("override, reason", [
    ({"--tried": "a | b"}, "pipe"),
    ({"--showed": f"closes {EM_DASH} mostly"}, "em dash"),
    ({"--time": "  "}, "empty"),
    ({"--model": "a\nb"}, "newline"),
    ({"--stage": "S3 review"}, "single word"),
    ({"--date": "2026-02-30"}, "calendar date"),
])
def test_a_bad_field_writes_nothing(tmp_path, capsys, override, reason):
    root = stage(tmp_path)
    before = snapshot(root)
    assert row.main(args_0006(root, **override)) == 1
    err = capsys.readouterr().err
    assert err.startswith("FAIL ") and reason in err
    assert snapshot(root) == before


def test_a_missing_record_writes_nothing(tmp_path, capsys):
    root = stage(tmp_path)
    argv = args_0006(root)
    argv[0] = "MD_0001"
    assert row.main(argv) == 1
    assert "triage/MD_0001.md" in capsys.readouterr().err
    assert not (root / "triage" / "MD_0001.md").exists()


@pytest.mark.parametrize("mangle, reason", [
    (lambda t: t.replace("| Date | Stage |", "| When | Stage |"), "no attempts table"),
    (lambda t: t + "\n" + t[t.index("| Date"):], "2 attempts tables"),
    (lambda t: t.replace("|---|---|---|---|---|---|\n", ""), "no attempts table"),
])
def test_a_record_without_one_attempts_table_writes_nothing(tmp_path, capsys, mangle, reason):
    root = stage(tmp_path)
    path = root / "triage" / "MD_0006.md"
    path.write_text(mangle(path.read_text(encoding="utf-8")), encoding="utf-8")
    before = snapshot(root)
    assert row.main(args_0006(root)) == 1
    assert reason in capsys.readouterr().err
    assert snapshot(root) == before


BATCH = """MD_0006
S3
a five line argument
it closes
12 min
claude-opus-5-5
---
MD_0007
S1
a scan
nothing
3 min
m
---

MD_0006
review
hostile pass
ACCEPT
4 min
m2
"""


def test_from_file_writes_every_block_in_order(tmp_path, capsys):
    root = stage(tmp_path)
    batch = tmp_path / "rows.txt"
    batch.write_text(BATCH, encoding="utf-8")
    assert row.main(["--from-file", str(batch), "--root", str(root), "--date", "2026-11-01"]) == 0
    assert capsys.readouterr().out == "row MD_0006 S3\nrow MD_0007 S1\nrow MD_0006 review\n"
    text = (root / "triage" / "MD_0006.md").read_text(encoding="utf-8")
    assert LAST_0006 + ROW_0006 + "| 2026-11-01 | review | hostile pass | ACCEPT | 4 min | m2 |\n" in text
    assert "| 2026-11-01 | S1 | a scan | nothing | 3 min | m |\n" in (
        root / "triage" / "MD_0007.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("bad, reason", [
    (BATCH.replace("ACCEPT", "ACC|EPT"), "block 3"),
    (BATCH.replace("m2\n", ""), "block 3: 5 lines"),
    (BATCH.replace("MD_0007", "MD_0001"), "block 2"),
])
def test_from_file_writes_nothing_when_any_block_is_bad(tmp_path, capsys, bad, reason):
    root = stage(tmp_path)
    batch = tmp_path / "rows.txt"
    batch.write_text(bad, encoding="utf-8")
    before = snapshot(root)
    assert row.main(["--from-file", str(batch), "--root", str(root)]) == 1
    assert reason in capsys.readouterr().err
    assert snapshot(root) == before


def test_from_file_excludes_the_single_row_flags(tmp_path):
    root = stage(tmp_path)
    batch = tmp_path / "rows.txt"
    batch.write_text(BATCH, encoding="utf-8")
    with pytest.raises(SystemExit):
        row.main(["MD_0006", "--from-file", str(batch), "--root", str(root)])
