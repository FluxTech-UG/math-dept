"""Append attempt rows to triage records: the one way a lead writes a row.

Run, from either repo (or with `--root`):

    python -m mdept.row MD_0007 --stage S3 --tried "..." --showed "..." --time "12 min"
        --model claude-opus-5-5 [--date YYYY-MM-DD]
    python -m mdept.row --from-file rows.txt [--date YYYY-MM-DD]

A row is `| date | stage | tried | showed | time | model |`, the columns of the
attempts table in `triage/MD_0007.md` (`docs/triage.md`, section 4). `--date`
defaults to today and applies to every row of the call.

`--from-file` reads several rows: blocks separated by a line `---`, each block six
lines (entry ID, stage, tried, showed, time, model). Blank lines around a block are
ignored; a blank line inside one is an empty field.

The table is found by its header, wherever it sits in the record: six cells with
`Date` and `Stage` first and `Time` and `Model` last, then the separator line. A
row lands under the table's last row; every other byte of the record stays.

Every row is validated before any file is written, and any problem writes nothing:
an ID that is not `MD_####`, a record that does not exist, a record without exactly
one attempts table, an empty field, a field holding a pipe, a newline or an em dash,
a stage that is not one word (`STAGE_RE`), or a date that is not a real ISO date.
Each row written prints `row MD_0007 S3`.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from . import CheckError, ConfigError
from . import config, parse, schema
from .settle import _iso

FIELDS = ("stage", "tried", "showed", "time", "model")
# A stage is one word: a ladder rung (S0 to S4) or a step such as fidelity or review.
STAGE_RE = re.compile(r"^\S+$")
#: Each character a cell cannot carry, how a refusal names it, and the fix it names.
_PIPE_FIX = "write an absolute value or a divisibility in words ('the absolute value of x', 'a divides b')"
_NEWLINE_FIX = "write the field on one line"
FORBIDDEN = (
    ("|", "a pipe", _PIPE_FIX),
    ("\n", "a newline", _NEWLINE_FIX),
    ("\r", "a newline", _NEWLINE_FIX),
    ("\u2014", "an em dash", "use a period, a comma, a colon or parentheses"),
)
BLOCK_SEPARATOR = "---"


@dataclass(frozen=True)
class Row:
    entry: str
    stage: str
    tried: str
    showed: str
    time: str
    model: str
    where: str  # names the row in a refusal: the command line, or a batch block

    def render(self, date: str) -> str:
        cells = (date, self.stage, self.tried, self.showed, self.time, self.model)
        return "| " + " | ".join(cells) + " |\n"


def make_row(entry: str, fields: dict, where: str) -> Row:
    """One validated row; `where` names it in a refusal."""
    if not schema.ID_RE.match(entry):
        raise ConfigError(f"{where}: {entry!r} is not an entry ID like MD_0007")
    for name in FIELDS:
        value = fields[name]
        if not value.strip():
            raise ConfigError(f"{where}: field {name!r} is empty")
        for char, label, fix in FORBIDDEN:
            if char in value:
                raise ConfigError(f"{where}: field {name!r} holds {label}, which a table row cannot carry; {fix}")
    if not STAGE_RE.match(fields["stage"].strip()):
        raise ConfigError(f"{where}: stage {fields['stage']!r} is not a single word")
    return Row(entry, *(fields[name].strip() for name in FIELDS), where)


def read_blocks(path: Path) -> list[Row]:
    """The rows of a `--from-file` batch, every block validated."""
    if not path.is_file():
        raise ConfigError(f"--from-file {path} does not exist")
    blocks: list[list[str]] = [[]]
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == BLOCK_SEPARATOR:
            blocks.append([])
        else:
            blocks[-1].append(line)
    rows = []
    for number, lines in enumerate(blocks, start=1):
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        where = f"{path.name} block {number}"
        if len(lines) != 6:
            raise ConfigError(f"{where}: {len(lines)} lines; a block is six lines "
                              "(id, stage, tried, showed, time, model)")
        rows.append(make_row(lines[0].strip(), dict(zip(FIELDS, lines[1:])), where))
    return rows


def append_rows(root: Path, rows: list[Row], date: str) -> dict[Path, str]:
    """The rewritten text of every record the rows touch. Writes nothing."""
    texts: dict[Path, str] = {}
    for item in rows:
        path = root / "triage" / f"{item.entry}.md"
        if path not in texts:
            if not path.is_file():
                raise ConfigError(f"{item.where}: {item.entry} has no triage record at triage/{item.entry}.md")
            texts[path] = path.read_text(encoding="utf-8")
        lines = texts[path].splitlines(keepends=True)
        _head, end = parse.attempts_table(lines, f"{item.where}: triage/{item.entry}.md")
        if not lines[end].endswith("\n"):
            lines[end] += "\n"
        lines.insert(end + 1, item.render(date))
        texts[path] = "".join(lines)
    return texts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.row", description=__doc__.splitlines()[0])
    parser.add_argument("entry", nargs="?", default=None, help="the entry, for example MD_0007")
    for name in FIELDS:
        parser.add_argument(f"--{name}", default=None, help=f"the row's {name} cell")
    parser.add_argument("--from-file", default=None,
                        help="a batch: blocks of six lines (id, stage, tried, showed, time, model) "
                             "separated by a line ---")
    parser.add_argument("--date", default=None, help="the rows' date, YYYY-MM-DD (default: today)")
    parser.add_argument("--root", default=None, help="repo root (default: nearest ancestor with ledger/)")
    args = parser.parse_args(argv)

    single = {name: getattr(args, name) for name in FIELDS}
    if args.from_file is not None:
        given = (["MD_####"] if args.entry else []) + [f"--{n}" for n, v in single.items() if v is not None]
        if given:
            parser.error(f"--from-file carries every row; {', '.join(given)} has nowhere to go")
    else:
        missing = (["the entry ID"] if args.entry is None else []) + [
            f"--{n}" for n, v in single.items() if v is None]
        if missing:
            parser.error(f"a single row needs {', '.join(missing)} (or use --from-file)")

    try:
        root = config.find_repo_root(args.root)
        date = _iso(args.date, "--date") if args.date is not None else datetime.date.today().isoformat()
        if args.from_file is not None:
            rows = read_blocks(Path(args.from_file))
        else:
            rows = [make_row(args.entry, single, "the command line")]
        texts = append_rows(root, rows, date)
    except (CheckError, ConfigError) as exc:
        print(f"FAIL {exc}; nothing is written", file=sys.stderr)
        return 1
    for path, text in texts.items():
        path.write_text(text, encoding="utf-8")
    for item in rows:
        print(f"row {item.entry} {item.stage}")
    return 0


if __name__ == "__main__":
    # Dispatch to the canonical module, as `mdept.settle` does.
    from mdept.row import main as _main

    raise SystemExit(_main())
