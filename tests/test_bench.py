"""`python -m mdept.bench`: the bench file's shape, the scores, and the gate on the mined floor and the held-out target."""

import re
import shutil
from pathlib import Path

import pytest

from mdept import ConfigError
from mdept import bench
from mdept import family as family_mod

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASES = ("good_public", "good_private")
REPO_ROOT = Path(__file__).resolve().parent.parent


def stage(tmp_path: Path) -> Path:
    for base in BASES:
        shutil.copytree(FIXTURES / base, tmp_path / base,
                        ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def write(path: Path, rows: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("rows:\n" + rows, encoding="utf-8")
    return path


MINED = (
    "  - {q: adding zero on the left of a natural number, expected: [MD_0007], form: math-words}\n"
    "  - {q: the integers beat their own squares, expected: [MD_0002], form: math-words}\n"
    "  - {q: spectral theory of banana spaceships, expected: [], form: no-answer}\n"
)


# --- the file's shape -------------------------------------------------------------


@pytest.mark.parametrize("row, message", [
    ("  - {q: x y, expected: [MD_0001], form: math-words, weight: 2}\n", "unknown keys \\['weight'\\]"),
    ("  - {q: zero, expected: [MD_1], form: math-words}\n", "not a list of IDs"),
    ("  - {q: zero, expected: [MD_0001], form: guess}\n", "is not one of"),
    ("  - {q: zero, expected: [], form: math-words}\n", "a no-answer row expects no ID"),
    ("  - {q: zero, expected: [MD_0001], form: no-answer}\n", "a no-answer row expects no ID"),
    ("  - {q: the of and, expected: [MD_0001], form: math-words}\n", "has no search word"),
    ("  - {q: zero, expected: [MD_0001], form: math-words, held_out: yes please}\n", "is not true or false"),
])
def test_a_malformed_row_is_refused_with_its_place(tmp_path, row, message):
    path = write(tmp_path / "bench" / "queries.yaml", row)
    with pytest.raises(ConfigError, match=message):
        bench.load(path)


def test_the_repo_bench_file_loads_and_names_only_ledger_ids():
    """The public bench names IDs only; every row parses, and its prose carries no request token."""
    rows = bench.load(REPO_ROOT / bench.BENCH_PATH)
    assert rows
    text = (REPO_ROOT / bench.BENCH_PATH).read_text(encoding="utf-8")
    assert "MDR:" not in text


# --- scores --------------------------------------------------------------------------


def test_the_scores_count_recall_and_the_no_answer_rows(tmp_path):
    root = stage(tmp_path)
    rows = bench.load(write(root / "good_private" / bench.BENCH_PATH, MINED))
    result = bench.run(family_mod.load_family(root / "good_private"), rows)
    assert [r["outcome"] for r in result["rows"]] == ["pass", "pass", "pass"]
    mined = result["splits"]["mined"]
    assert mined["recall@1"] == 1.0 and mined["recall@5"] == 1.0 and mined["no-answer held"] == 1.0


def test_a_wrong_expected_id_is_a_miss(tmp_path):
    root = stage(tmp_path)
    rows = bench.load(write(root / "good_private" / bench.BENCH_PATH,
                            "  - {q: adding zero on the left, expected: [MD_0004], form: math-words}\n"))
    result = bench.run(family_mod.load_family(root / "good_private"), rows)
    assert result["rows"][0]["outcome"] == "fail"
    assert result["splits"]["mined"]["recall@5"] == 0.0
    assert any(line.startswith("miss row 1:") for line in bench.render(result, misses=True))


def test_a_row_naming_only_ids_the_family_lacks_is_reported_not_scored(tmp_path):
    root = stage(tmp_path)
    rows = bench.load(write(root / "good_private" / bench.BENCH_PATH,
                            "  - {q: adding zero, expected: [MD_0099], form: math-words}\n" + MINED))
    result = bench.run(family_mod.load_family(root / "good_private"), rows)
    assert result["rows"][0]["outcome"] == "unresolvable"
    assert result["splits"]["mined"]["rows"] == 3
    assert "unresolvable: 1 rows name only IDs this family does not hold (rows 1)" in bench.render(result, False)


# --- the gate -------------------------------------------------------------------------


def test_the_gate_fails_the_repo_bench_with_wrong_expected_ids(tmp_path, capsys):
    """The repo's own bench file, each expected ID swapped for the next one the family holds, falls below the mined floor.

    An ID the family does not hold stays as written: its row is unresolvable either way.
    """
    held = sorted(entry.id for entry in family_mod.load_family(REPO_ROOT).entries())
    following = dict(zip(held, held[1:] + held[:1]))
    text = (REPO_ROOT / bench.BENCH_PATH).read_text(encoding="utf-8")
    wrong = re.sub(r"expected: \[([^\]]*)\]",
                   lambda m: "expected: [" + re.sub(r"MD_\d{4}", lambda i: following.get(i.group(0), i.group(0)),
                                                    m.group(1)) + "]",
                   text)
    assert wrong != text
    copy = tmp_path / "queries.yaml"
    copy.write_text(wrong, encoding="utf-8")
    assert bench.main(["--root", str(REPO_ROOT), "--file", str(copy), "--check"]) == 1
    assert re.search(r"mined recall@5 [0-9.]+ is below the floor 0\.95", capsys.readouterr().err)


def test_the_gate_passes_the_repo_bench():
    assert bench.main(["--root", str(REPO_ROOT), "--check"]) == 0


def test_the_gate_fails_a_held_out_split_below_its_target(tmp_path, capsys):
    root = stage(tmp_path)
    write(root / "good_private" / bench.BENCH_PATH, MINED
          + "  - {q: adding zero on the left, expected: [MD_0004], form: math-words, held_out: true}\n")
    assert bench.main(["--root", str(root / "good_private"), "--check"]) == 1
    captured = capsys.readouterr()
    assert "held-out recall@5 0.0 is below the target 0.85" in captured.err
    assert "miss row 4:" in captured.out


def test_the_gate_passes_a_held_out_split_at_its_target(tmp_path):
    root = stage(tmp_path)
    write(root / "good_private" / bench.BENCH_PATH, MINED
          + "  - {q: adding zero on the left, expected: [MD_0007], form: math-words, held_out: true}\n")
    assert bench.main(["--root", str(root / "good_private"), "--check"]) == 0
