"""`python -m mdept.figures`: entry figures drawn by the counterexample scripts that carry `--svg`.

The runner cases use toy scripts that write SVG text by hand, so they need no plotting
stack. The last cases hold this repo to its own contract: every committed figure has
the one script that draws it, and every drawing script still draws.
"""

from pathlib import Path

import pytest

from mdept import CheckError, figures, refute

REPO_ROOT = Path(__file__).resolve().parent.parent

DRAWS = """import argparse, sys
parser = argparse.ArgumentParser()
parser.add_argument("--svg")
args = parser.parse_args()
open(args.svg, "w").write('<svg xmlns="http://www.w3.org/2000/svg"><text>{label}</text></svg>')
"""


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "ledger").mkdir()
    (tmp_path / "counterexamples").mkdir()
    return tmp_path


def script(repo: Path, name: str, text: str) -> Path:
    path = repo / "counterexamples" / name
    path.write_text(text, encoding="utf-8")
    return path


def test_only_a_script_carrying_the_flag_runs(repo):
    script(repo, "MD_0002_plain.py", "x = 1\n")
    script(repo, "MD_0003_draws.py", DRAWS.format(label="three"))
    records = figures.draw_all(repo)
    assert [(r["id"], r["ok"]) for r in records] == [("MD_0003", True)]
    assert "three" in (repo / "figures/MD_0003.svg").read_text(encoding="utf-8")
    assert not (repo / "figures/MD_0002.svg").exists()


def test_a_failed_redraw_keeps_the_last_good_figure(repo, capsys):
    (repo / "figures").mkdir()
    (repo / "figures/MD_0003.svg").write_text("<svg>old</svg>", encoding="utf-8")
    script(repo, "MD_0003_breaks.py", "# --svg is accepted, then\nraise SystemExit('no witness today')\n")
    assert figures.main(["--repo", str(repo)]) == 1
    assert "MD_0003" in capsys.readouterr().err
    assert (repo / "figures/MD_0003.svg").read_text(encoding="utf-8") == "<svg>old</svg>"


def test_a_script_that_writes_nothing_is_reported(repo):
    script(repo, "MD_0003_silent.py", "# takes --svg and ignores it\n")
    [record] = figures.draw_all(repo)
    assert not record["ok"] and "wrote nothing" in record["problem"]


def test_a_slow_script_is_stopped_at_its_timeout(repo):
    script(repo, "MD_0003_slow.py", "# --svg\nimport time\ntime.sleep(30)\n")
    [record] = figures.draw_all(repo, timeout=1)
    assert not record["ok"] and "within 1 s" in record["problem"]


def test_two_drawing_scripts_for_one_entry_are_refused(repo):
    script(repo, "MD_0003_a.py", DRAWS.format(label="a"))
    script(repo, "MD_0003_b.py", DRAWS.format(label="b"))
    with pytest.raises(CheckError, match="one entry has one figure"):
        figures.draw_all(repo)


def test_without_the_flag_svg_main_does_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    figures.svg_main(lambda ax: pytest.fail("drew without --svg"), [])
    assert not list(tmp_path.iterdir())


def test_svg_main_writes_the_same_bytes_twice(tmp_path):
    pytest.importorskip("matplotlib", reason="the figures extra (matplotlib) draws the SVG")

    def draw(ax):
        ax.plot([0, 1], [0, 1])

    figures.svg_main(draw, ["--svg", str(tmp_path / "a.svg")])
    figures.svg_main(draw, ["--svg", str(tmp_path / "b.svg")])
    first = (tmp_path / "a.svg").read_bytes()
    assert first.startswith(b"<?xml") and first == (tmp_path / "b.svg").read_bytes()


def test_every_committed_figure_has_its_drawing_script():
    scripts = figures.drawing_scripts(REPO_ROOT)
    committed = sorted(p.stem for p in (REPO_ROOT / figures.FIGURES_DIR).glob("*.svg"))
    assert committed == sorted(scripts), "a figure without its script, or a script never run"


def test_this_repos_drawing_scripts_draw_and_still_refute(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib", reason="the figures extra (matplotlib) draws the SVG")
    for entry_id, path in figures.drawing_scripts(REPO_ROOT).items():
        assert refute.load(path).verify(), f"{path.name} no longer refutes {entry_id}"
    monkeypatch.setattr(figures, "figure_path", lambda root, entry_id: tmp_path / f"{entry_id}.svg")
    records = figures.draw_all(REPO_ROOT)
    assert records and all(r["ok"] for r in records), records
