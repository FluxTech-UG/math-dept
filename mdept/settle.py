"""Settle one ledger entry: the one way a lead sets `status` and `provenance.settled_by`.

Run, from either repo (or with `--root`):

    python -m mdept.settle MD_0007 --status <status> --by <who> --model <model>
        [--how <how>] [--date YYYY-MM-DD] [--checked-by YYYY-MM-DD]
        [--decl <Lean name>] [--merged-into MD_####]

The command rewrites only the lines of the settled fields in `ledger/MD_0007.md`
and leaves every other byte as it was:

- `status`, and `provenance.settled_by` as a block (who, date, how, checked_by,
  model). `date` defaults to today. `how` defaults to the one the status
  requires (`schema.SETTLING_HOW`); a `--how` that contradicts it is refused.
  An unsettled status (`conjectured`, `open`) writes `settled_by: null` and
  takes none of the settler's flags.
- for `proven-formal`, `formal.decl`, `formal.file` and `statement_hash` from
  `audit/latest.json`: the declaration is `--decl`, else the entry's own
  `formal.decl`, else `MathDept.MD_0007.statement`; its module names the file;
  the hash is `audit.type_hash` of its pretty-printed type, the recipe I5
  checks. A stale audit, a declaration the audit does not list, or one whose
  module is not under `Results/` of this repo's library is refused. For
  `refuted`, `--decl` names a compiled negation and fills the same three
  fields, from any module of this repo's library.
- for `merged`, `merged_into` from `--merged-into`, and `--how` is required.

The entry must already carry its evidence (a counterexample row, a proof row, a
`source`); the command writes provenance, not evidence. It then runs
`python -m mdept.check --entry MD_0007` and prints the result. A failing check
restores the entry file byte for byte, so a settlement lands whole or not at
all.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import sys
from pathlib import Path

import yaml

from . import CheckError, ConfigError
from . import audit as audit_mod
from . import check as check_mod
from . import config, parse, schema


def _iso(value: str, flag: str) -> str:
    if not schema.ISO_DATE_RE.match(value):
        raise ConfigError(f"{flag} {value!r} is not an ISO date YYYY-MM-DD")
    try:
        datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigError(f"{flag} {value!r} is not a real calendar date ({exc})") from exc
    return value


def _formal_pointer(root: Path, entry_id: str, front: dict, decl: str | None,
                    proven: bool) -> dict:
    """`formal.decl`, `formal.file` and `statement_hash` read off the cached audit.

    `proven` holds the declaration to `Results/` of this repo's library; a refuted
    entry's compiled negation may sit anywhere in it.
    """
    data = audit_mod.read_cached_audit(root)
    if data.get("sources_sha256") != audit_mod.sources_sha256(root):
        raise ConfigError(
            f"{audit_mod.CACHED_AUDIT} is stale against the Lean sources on disk; run `make lean` "
            "before settling, so the hash is the type that compiles now")
    name = decl or (front.get("formal") or {}).get("decl") or f"MathDept.{entry_id}.statement"
    if not schema.DECL_RE.match(name):
        raise ConfigError(f"declaration {name!r} is not of the form MathDept.MD_0007.name")
    record = (data.get("declarations") or {}).get(name)
    if record is None:
        raise ConfigError(
            f"{name} is not in {audit_mod.CACHED_AUDIT}; it did not compile, was renamed, or "
            "`make lean` has not run since it was written (name another with --decl)")
    module = record["module"].split(".")
    lib = config.lean_lib(root)
    if module[0] != lib:
        raise ConfigError(f"{name} lives in module {record['module']}, outside this repo's library {lib}")
    if proven and "Conjectures" in module:
        raise ConfigError(
            f"{name} lives in module {record['module']}, still under Conjectures/; move the file "
            "to Results/, run `make lean`, then settle")
    if proven and (len(module) < 3 or module[1] != "Results"):
        raise ConfigError(
            f"{name} lives in module {record['module']}; a proven-formal entry of this repo "
            f"lives under {lib}/Results/")
    lean_file = "/".join(module) + ".lean"
    if not (root / lean_file).is_file():
        raise ConfigError(f"{lean_file}, the file of module {record['module']}, does not exist")
    return {"formal.decl": name, "formal.file": lean_file,
            "statement_hash": audit_mod.type_hash(record["type"])}


def plan(root: Path, entry_id: str, front: dict, status: str, *, by: str | None, model: str | None,
         how: str | None, date: str | None, checked_by: str | None, decl: str | None,
         merged_into: str | None) -> dict:
    """The settled fields as {dotted path: value}, every flag validated first."""
    if status not in schema.STATUSES:
        raise ConfigError(f"--status {status!r} is not one of {list(schema.STATUSES)}")
    changes: dict = {"status": status}
    if status in schema.UNSETTLED_STATUSES:
        given = [flag for flag, value in (("--by", by), ("--model", model), ("--how", how),
                                          ("--date", date), ("--checked-by", checked_by))
                 if value is not None]
        if given:
            raise ConfigError(
                f"status {status!r} is unsettled, so settled_by is null and {', '.join(given)} "
                "has nowhere to go")
        changes["provenance.settled_by"] = None
    else:
        if by is None or model is None:
            raise ConfigError(f"status {status!r} is settled: --by and --model are required")
        if by not in schema.WHO:
            raise ConfigError(f"--by {by!r} is not one of {list(schema.WHO)}")
        if not model.strip():
            raise ConfigError("--model is empty; name the model identifier")
        required = schema.SETTLING_HOW.get(status)
        if how is None:
            if required is None:
                raise ConfigError(f"status {status!r} requires no particular how: name it with --how")
            how = required
        if how not in schema.HOW:
            raise ConfigError(f"--how {how!r} is not one of {list(schema.HOW)}")
        if required is not None and how != required:
            raise ConfigError(f"status {status!r} requires how {required!r}, not {how!r}")
        changes["provenance.settled_by"] = {
            "who": by,
            "date": _iso(date, "--date") if date is not None else datetime.date.today().isoformat(),
            "how": how,
            "checked_by": _iso(checked_by, "--checked-by") if checked_by is not None else None,
            "model": model,
        }
    if status == "merged":
        if merged_into is None:
            raise ConfigError("status 'merged' needs --merged-into MD_#### naming the surviving entry")
        if not schema.ID_RE.match(merged_into) or merged_into == entry_id:
            raise ConfigError(f"--merged-into {merged_into!r} is not another entry's ID")
        changes["merged_into"] = merged_into
    elif merged_into is not None:
        raise ConfigError(f"--merged-into belongs to status 'merged', not {status!r}")
    if status == "proven-formal":
        changes.update(_formal_pointer(root, entry_id, front, decl, proven=True))
    elif status == "refuted" and decl is not None:
        changes.update(_formal_pointer(root, entry_id, front, decl, proven=False))
    elif decl is not None:
        raise ConfigError(f"--decl belongs to 'proven-formal' and 'refuted', not {status!r}")
    return changes


# --- the line editor ---------------------------------------------------------


def _scalar(value) -> str:
    """One YAML scalar as it reads back: plain where plain parses to itself."""
    if value is None:
        return "null"
    if schema.ISO_DATE_RE.match(value):
        return value  # loads as a date, which parse.normalize_dates renders back to this string
    try:
        plain_ok = value.strip() == value and yaml.safe_load(value) == value
    except yaml.YAMLError:
        plain_ok = False
    return value if plain_ok else json.dumps(value, ensure_ascii=False)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _ending(line: str) -> str:
    return "\n" if line.endswith("\n") else ""


class _Front:
    """The front-matter lines of one entry, edited in place one key at a time."""

    def __init__(self, text: str, where: str):
        self.where = where
        self.lines = text.splitlines(keepends=True)
        if not self.lines or self.lines[0].rstrip("\r\n") != "---":
            raise CheckError(f"{where}: no leading '---' front matter fence")
        closers = [i for i in range(1, len(self.lines)) if self.lines[i].rstrip("\r\n") == "---"]
        if not closers:
            raise CheckError(f"{where}: the front matter has no closing '---'")
        self.end = closers[0]

    def _refuse(self, key: str, why: str):
        raise CheckError(f"{self.where}: field '{key}': {why}; settle cannot place the value, "
                         "so the file is left as it is")

    def _find(self, key: str, start: int, stop: int, indent: int) -> int:
        hits = [i for i in range(start, stop)
                if _indent(self.lines[i]) == indent and self.lines[i].lstrip(" ").startswith(f"{key.split('.')[-1]}:")]
        if len(hits) != 1:
            self._refuse(key, f"expected one '{key.split('.')[-1]}:' line at indent {indent}, found {len(hits)}")
        return hits[0]

    def _block(self, key: str, at: int) -> tuple[int, int, int]:
        """(first child, stop, child indent) of the block whose key line is `at`."""
        head = self.lines[at]
        rest = head.split(":", 1)[1].split("#", 1)[0].strip()
        if rest:
            self._refuse(key, f"written inline as {rest!r}; settle edits the block form")
        parent = _indent(head)
        stop = at + 1
        while stop < self.end and (not self.lines[stop].strip() or _indent(self.lines[stop]) > parent):
            stop += 1
        children = [i for i in range(at + 1, stop) if self.lines[i].strip()]
        if not children:
            self._refuse(key, "the block has no children")
        return at + 1, stop, _indent(self.lines[children[0]])

    def _locate(self, dotted: str) -> tuple[int, int]:
        """(line index, indent) of a dotted key, walking blocks from the top level."""
        parts = dotted.split(".")
        start, stop, indent = 1, self.end, 0
        for depth, part in enumerate(parts):
            at = self._find(".".join(parts[: depth + 1]), start, stop, indent)
            if depth == len(parts) - 1:
                return at, indent
            start, stop, indent = self._block(".".join(parts[: depth + 1]), at)
        raise AssertionError("unreachable")

    def set_scalar(self, dotted: str, value) -> None:
        at, indent = self._locate(dotted)
        line = self.lines[at]
        if at + 1 < self.end and self.lines[at + 1].strip() and _indent(self.lines[at + 1]) > indent:
            self._refuse(dotted, "the value runs onto the next line; settle writes one-line scalars")
        self.lines[at] = f"{' ' * indent}{dotted.split('.')[-1]}: {_scalar(value)}{_ending(line)}"

    def set_settled_by(self, value: dict | None) -> None:
        dotted = "provenance.settled_by"
        at, indent = self._locate(dotted)
        line = self.lines[at]
        rest = line.split(":", 1)[1].split("#", 1)[0].strip()
        stop = at + 1
        step = indent  # the provenance block's own step, used when settled_by was null
        if rest == "":
            _, stop, child = self._block(dotted, at)
            step = child - indent
        elif rest != "null":
            self._refuse(dotted, f"written inline as {rest!r}; settle edits null or the block form")
        eol = _ending(line) or "\n"
        if value is None:
            rendered = [f"{' ' * indent}settled_by: null{eol}"]
        else:
            rendered = [f"{' ' * indent}settled_by:\n"] + [
                f"{' ' * (indent + step)}{key}: {_scalar(value[key])}\n" for key in schema.SETTLED_BY_KEYS]
            rendered[-1] = rendered[-1][:-1] + eol
        self.lines[at:stop] = rendered
        self.end += len(rendered) - (stop - at)

    def text(self) -> str:
        return "".join(self.lines)


def _apply(front: dict, changes: dict) -> dict:
    expected = copy.deepcopy(front)
    for dotted, value in changes.items():
        node = expected
        *parents, leaf = dotted.split(".")
        for part in parents:
            node = node[part]
        node[leaf] = copy.deepcopy(value)
    return expected


def settle(root: Path | str, entry_id: str, status: str, *, by: str | None = None,
           model: str | None = None, how: str | None = None, date: str | None = None,
           checked_by: str | None = None, decl: str | None = None,
           merged_into: str | None = None) -> dict:
    """Write the settlement into the entry file; return the fields written. Refuses before writing."""
    root = Path(root).resolve()
    if not schema.ID_RE.match(entry_id):
        raise ConfigError(f"{entry_id!r} is not an entry ID like MD_0007")
    path = root / "ledger" / f"{entry_id}.md"
    if not path.is_file():
        raise ConfigError(f"{entry_id} has no ledger file at {path}")
    front, _, _ = parse.load_front_matter(path)
    schema.validate_front(front, path, config.repo_kind(root))
    changes = plan(root, entry_id, front, status, by=by, model=model, how=how, date=date,
                   checked_by=checked_by, decl=decl, merged_into=merged_into)

    original = path.read_text(encoding="utf-8")
    editor = _Front(original, str(path.relative_to(root)))
    for dotted, value in changes.items():
        if dotted == "provenance.settled_by":
            editor.set_settled_by(value)
        else:
            editor.set_scalar(dotted, value)
    rewritten = editor.text()

    # Read the rewrite back before it touches disk: every settled field must say what
    # was planned, and every other field what it said before.
    front_text, _ = parse.split_front_matter(rewritten, path)
    reread = parse.normalize_dates(yaml.safe_load(front_text))
    if reread != _apply(front, changes):
        raise CheckError(f"{path.relative_to(root)}: the rewritten front matter does not read back "
                         "as the planned settlement; the file is left as it is")
    path.write_text(rewritten, encoding="utf-8")
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.settle", description=__doc__.splitlines()[0])
    parser.add_argument("entry", help="the entry to settle, for example MD_0007")
    parser.add_argument("--status", required=True, help=f"one of {', '.join(schema.STATUSES)}")
    parser.add_argument("--by", default=None, help=f"settled_by.who: one of {', '.join(schema.WHO)}")
    parser.add_argument("--model", default=None, help="settled_by.model: the model identifier")
    parser.add_argument("--how", default=None,
                        help="settled_by.how (default: the one the status requires)")
    parser.add_argument("--date", default=None, help="settled_by.date, YYYY-MM-DD (default: today)")
    parser.add_argument("--checked-by", default=None,
                        help="settled_by.checked_by: the later day a second session checked it")
    parser.add_argument("--decl", default=None,
                        help="proven-formal: the Lean declaration (default: the entry's formal.decl, "
                             "else MathDept.<ID>.statement); refuted: a compiled negation")
    parser.add_argument("--merged-into", default=None, help="merged: the entry this one duplicates")
    parser.add_argument("--root", default=None, help="repo root (default: nearest ancestor with ledger/)")
    args = parser.parse_args(argv)

    try:
        root = config.find_repo_root(args.root)
        path = root / "ledger" / f"{args.entry}.md"
        before = path.read_bytes() if path.is_file() else None
        changes = settle(root, args.entry, args.status, by=args.by, model=args.model, how=args.how,
                         date=args.date, checked_by=args.checked_by, decl=args.decl,
                         merged_into=args.merged_into)
    except (CheckError, ConfigError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    for dotted, value in changes.items():
        print(f"set {dotted}: {json.dumps(value, ensure_ascii=False)}")
    code = check_mod.main(["--root", str(root), "--entry", args.entry])
    if code != 0:
        path.write_bytes(before)
        print(f"FAIL the entry gate rejected the settlement; {path.relative_to(root)} is restored "
              "byte for byte", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # Dispatch to the canonical module, as `mdept.release` does: under `python -m` this
    # file runs as `__main__`, and its classes would differ from the importable ones.
    from mdept.settle import main as _main

    raise SystemExit(_main())
