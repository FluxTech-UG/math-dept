"""Draw the entry figures, `figures/MD_####.svg`, from the counterexample scripts that can.

Run:

    python -m mdept.figures --repo .
    python -m mdept.figures --repo . --timeout 300

A counterexample script that can draw its witness carries the flag `--svg` in its text:
`python counterexamples/MD_0025_slug.py --svg figures/MD_0025.svg` writes one small SVG
and exits, and without the flag the script does what it always did. This command runs
every such script in the repo's `counterexamples/` (the ID read off the file name),
each in the foreground under its own timeout, and reports which wrote its file. The
figures are committed: the site build copies them and never runs a script, so the
published site needs no plotting stack.

One entry has one figure. Two scripts of one entry that both carry the flag are refused
before anything runs, because both would write the same file.

The script side is `svg_main(draw)`: the whole `__main__` body of a drawing script. It
parses `--svg`, and only when the flag is given imports matplotlib, calls `draw(ax)` on a
fresh axes, and saves with the date stripped and a fixed hash salt, so a redraw on the
same matplotlib is byte-identical.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import CheckError, MDeptError
from . import config, schema

FIGURE_FLAG = "--svg"
FIGURES_DIR = "figures"
COUNTEREXAMPLES_DIR = "counterexamples"
#: Seconds one script may take to draw its figure before it is stopped and reported.
TIMEOUT_S = 120
#: The figure's size in inches; small, because it sits in a page column.
FIGURE_SIZE = (5.4, 3.3)


def drawing_scripts(root: Path) -> dict[str, Path]:
    """Entry ID to the one script under `counterexamples/` whose text carries `--svg`."""
    found: dict[str, Path] = {}
    directory = Path(root) / COUNTEREXAMPLES_DIR
    if not directory.is_dir():
        return found
    for script in sorted(directory.glob("*.py")):
        if FIGURE_FLAG not in script.read_text(encoding="utf-8"):
            continue
        if not schema.COUNTEREXAMPLE_STEM_RE.match(script.stem):
            raise CheckError(f"figures: {script}: field '<filename>': a drawing script is named "
                             "MD_####_slug.py, so its figure's ID can be read off the name")
        entry_id = script.stem[:7]
        if entry_id in found:
            raise CheckError(f"figures: {script}: field '<{FIGURE_FLAG}>': {found[entry_id].name} also "
                             f"draws {entry_id}; one entry has one figure, so only one script carries the flag")
        found[entry_id] = script
    return found


def figure_path(root: Path, entry_id: str) -> Path:
    return Path(root) / FIGURES_DIR / f"{entry_id}.svg"


def _script_env() -> dict:
    """The environment a drawing script runs in: this `mdept` first on its import path.

    A script run by path puts its own directory first on `sys.path`, not the repo, so
    without this it imports whichever `mdept` the interpreter has installed, which in a
    worktree or a fresh checkout is not the package running this command.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (str(config.package_root()), env.get("PYTHONPATH"))))
    return env


def draw_all(root: Path, timeout: float = TIMEOUT_S) -> list[dict]:
    """Run every drawing script; one record per script: id, script, ok, and what went wrong.

    Each script draws into a scratch file that replaces the committed figure only once
    the script has exited cleanly, so a failed redraw leaves the last good figure in place.
    """
    root = Path(root).resolve()
    records = []
    for entry_id, script in drawing_scripts(root).items():
        target = figure_path(root, entry_id)
        record = {"id": entry_id, "script": str(script.relative_to(root)), "ok": False, "problem": None}
        records.append(record)
        with tempfile.TemporaryDirectory() as scratch:
            drawn = Path(scratch) / target.name
            try:
                run = subprocess.run([sys.executable, str(script), FIGURE_FLAG, str(drawn)], cwd=root,
                                     capture_output=True, text=True, timeout=timeout, env=_script_env())
            except subprocess.TimeoutExpired:
                record["problem"] = f"no figure within {timeout:g} s"
                continue
            if run.returncode != 0:
                last = run.stderr.strip().splitlines()[-1:] or ["no output"]
                record["problem"] = f"exit {run.returncode}: {last[0]}"
                continue
            if not drawn.is_file() or not drawn.stat().st_size:
                record["problem"] = f"exited 0 but wrote nothing for {FIGURE_FLAG}"
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(drawn, target)
            record["ok"] = True
    return records


def svg_main(draw, argv: list[str] | None = None) -> None:
    """The `__main__` body of a counterexample script that draws its witness.

    Without `--svg` it returns at once, so running the script plainly does what it did
    before. With `--svg PATH` it draws on one axes through `draw(ax)` and writes PATH.
    """
    parser = argparse.ArgumentParser(description="Draw this counterexample's figure.")
    parser.add_argument(FIGURE_FLAG, dest="svg", metavar="PATH", help="write the figure as SVG here")
    args = parser.parse_args(argv)
    if args.svg is None:
        return
    import matplotlib

    matplotlib.use("svg")
    from matplotlib import pyplot as plt

    plt.rcParams.update({"svg.hashsalt": "mdept", "svg.fonttype": "none", "font.size": 9})
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    draw(ax)
    fig.tight_layout()
    path = Path(args.svg)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.figures", description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=None, help="repo root (default: nearest ancestor with ledger/)")
    parser.add_argument("--timeout", type=float, default=TIMEOUT_S,
                        help=f"seconds per script (default {TIMEOUT_S})")
    args = parser.parse_args(argv)
    try:
        root = config.find_repo_root(args.repo)
        records = draw_all(root, args.timeout)
    except MDeptError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    for record in records:
        if record["ok"]:
            print(f"ok {record['id']} {FIGURES_DIR}/{record['id']}.svg from {record['script']}")
        else:
            print(f"FAIL {record['id']} {record['script']}: {record['problem']}", file=sys.stderr)
    failed = [r for r in records if not r["ok"]]
    print(f"{len(records) - len(failed)} of {len(records)} drawing scripts wrote their figure")
    return 1 if failed else 0


if __name__ == "__main__":
    from mdept.figures import main as _main

    raise SystemExit(_main())
