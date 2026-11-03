"""The search benchmark: does `mdept.query` find the entry a consumer means, from the consumer's words?

Run:

    python -m mdept.bench                 # the report
    python -m mdept.bench --check         # the gate `make check` runs
    python -m mdept.bench --misses        # the report, with every missed row

`bench/queries.yaml` holds rows of a query and the entry IDs it should find.
Each row is run through `query.rank` over the whole family and scored by
recall@1 and recall@5 (an expected ID among the top 1 or 5 hits at or above the
floor) and the mean reciprocal rank; a row with no expected ID is a no-answer
row, and it passes when nothing clears the floor. A row whose every expected ID
the loaded family does not hold (a public checkout without the private ledger)
is reported by line as unresolvable and kept out of the scores.

Two splits. A mined row (the default) is written from the request a statement
came in with, so it measures how well the search finds a statement from the
words it was filed in; its recall is a floor, not a target. A row with
`held_out: true` is written by a context that never saw the entry, from the
consumer's document alone, and it is the split the gate holds to
`HELD_OUT_RECALL_TARGET`. While the file holds no held-out row `--check` prints
the report and passes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import CheckError, ConfigError
from . import config, query, schema, words
from . import family as family_mod

BENCH_PATH = "bench/queries.yaml"
ROW_KEYS = ("q", "expected", "form", "held_out", "source", "note")
REQUIRED_ROW_KEYS = ("q", "expected", "form")
#: How a query is phrased. `no-answer` rows carry no expected ID, and only they do.
FORMS = ("math-words", "engineering-words", "latex", "candidate-title", "restatement", "no-answer")
#: The held-out split's recall@5 the gate requires once the file holds held-out rows.
HELD_OUT_RECALL_TARGET = 0.85
TOP = 5


def load(path: Path) -> list[dict]:
    """The bench rows, checked for shape. Each row gains `line`, its 1-based position in the list."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"{path}: the bench file is missing; it lives at {BENCH_PATH}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: not valid YAML ({exc})") from exc
    if not isinstance(data, dict) or set(data) != {"rows"} or not isinstance(data["rows"], list):
        raise ConfigError(f"{path}: expected one key 'rows' holding a list of query rows")
    rows = []
    for i, row in enumerate(data["rows"], start=1):
        where = f"{path}: rows[{i}]"
        if not isinstance(row, dict):
            raise ConfigError(f"{where}: expected a mapping, got {row!r}")
        unknown = sorted(set(row) - set(ROW_KEYS))
        missing = [k for k in REQUIRED_ROW_KEYS if k not in row]
        if unknown or missing:
            raise ConfigError(f"{where}: unknown keys {unknown}, missing keys {missing}; the keys are {list(ROW_KEYS)}")
        if not isinstance(row["q"], str) or not words.tokens(row["q"]):
            raise ConfigError(f"{where}.q: {row['q']!r} has no search word")
        expected = row["expected"]
        if not isinstance(expected, list) or any(not isinstance(x, str) or not schema.ID_RE.match(x) for x in expected):
            raise ConfigError(f"{where}.expected: {expected!r} is not a list of IDs like MD_0007")
        if row["form"] not in FORMS:
            raise ConfigError(f"{where}.form: {row['form']!r} is not one of {list(FORMS)}")
        if (row["form"] == "no-answer") != (not expected):
            raise ConfigError(f"{where}: a no-answer row expects no ID, and every other row expects at least one")
        held_out = row.get("held_out", False)
        if not isinstance(held_out, bool):
            raise ConfigError(f"{where}.held_out: {held_out!r} is not true or false")
        rows.append(dict(row, held_out=held_out, line=i))
    return rows


def run(family, rows: list[dict]) -> dict:
    """Every row through the ranked search; the per-row outcome and the scores per split and form."""
    entries = family.entries()
    held = {e.id for e in entries}
    ranker = query.Ranker(entries)
    pairs = words.synonyms_of(family)
    outcomes = []
    for row in rows:
        answer = query.rank(family, [row["q"]], k=TOP, ranker=ranker, pairs=pairs)
        got = [hit["id"] for hit in answer["hits"]]
        record = {"line": row["line"], "q": row["q"], "expected": row["expected"], "form": row["form"],
                  "held_out": row["held_out"], "got": got}
        if row["expected"] and not set(row["expected"]) & held:
            record["outcome"] = "unresolvable"
        elif not row["expected"]:
            record["outcome"] = "pass" if not got else "fail"
        else:
            ranks = [got.index(i) + 1 for i in row["expected"] if i in got]
            record["rank"] = min(ranks) if ranks else None
            record["outcome"] = "pass" if ranks else "fail"
        outcomes.append(record)
    return {"rows": outcomes, "splits": _scores(outcomes)}


def _scores(outcomes: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for record in outcomes:
        if record["outcome"] == "unresolvable":
            continue
        split = "held-out" if record["held_out"] else "mined"
        groups.setdefault(split, []).append(record)
        groups.setdefault(f"{split} / {record['form']}", []).append(record)
    scores = {}
    for name, members in sorted(groups.items()):
        answerable = [r for r in members if r["expected"]]
        no_answer = [r for r in members if not r["expected"]]
        line = {"rows": len(members)}
        if answerable:
            line["recall@1"] = round(sum(1 for r in answerable if r.get("rank") == 1) / len(answerable), 3)
            line["recall@5"] = round(sum(1 for r in answerable if r.get("rank")) / len(answerable), 3)
            line["mrr"] = round(sum(1 / r["rank"] for r in answerable if r.get("rank")) / len(answerable), 3)
        if no_answer:
            line["no-answer held"] = round(sum(1 for r in no_answer if r["outcome"] == "pass") / len(no_answer), 3)
        scores[name] = line
    return scores


def gate(result: dict) -> tuple[bool, str]:
    """(passes, why): soft while there is no held-out row, then the held-out recall@5 against its target."""
    held_out = result["splits"].get("held-out")
    if held_out is None:
        return True, "no held-out rows yet: the report is printed and the gate passes"
    recall = held_out.get("recall@5")
    if recall is None or recall < HELD_OUT_RECALL_TARGET:
        return False, f"held-out recall@5 {recall} is below the target {HELD_OUT_RECALL_TARGET}"
    return True, f"held-out recall@5 {recall} meets the target {HELD_OUT_RECALL_TARGET}"


def render(result: dict, misses: bool) -> list[str]:
    lines = []
    for name, line in result["splits"].items():
        lines.append(f"{name:<34}" + "  ".join(f"{k} {v}" for k, v in line.items()))
    unresolvable = [r for r in result["rows"] if r["outcome"] == "unresolvable"]
    if unresolvable:
        lines.append(f"unresolvable: {len(unresolvable)} rows name only IDs this family does not hold "
                     f"(rows {', '.join(str(r['line']) for r in unresolvable)})")
    if misses:
        for record in result["rows"]:
            if record["outcome"] == "fail":
                lines.append(f"miss row {record['line']}: {record['q']!r} expected {record['expected'] or 'nothing'}, "
                             f"got {record['got'] or 'nothing above the floor'}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.bench", description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=None, help="a math repo root (default: nearest ancestor with ledger/)")
    parser.add_argument("--file", default=None, help=f"the bench file (default: <root>/{BENCH_PATH})")
    parser.add_argument("--check", action="store_true", help="fail when the held-out split misses its target")
    parser.add_argument("--misses", action="store_true", help="list every missed row")
    parser.add_argument("--json", action="store_true", help="emit the machine view on stdout")
    args = parser.parse_args(argv)
    try:
        root = config.find_repo_root(args.root) if args.root is None else Path(args.root).resolve()
        rows = load(Path(args.file) if args.file else root / BENCH_PATH)
        result = run(family_mod.load_family(root), rows)
    except (CheckError, ConfigError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    passes, why = gate(result)
    if args.json:
        print(json.dumps(dict(result, gate={"passes": passes, "why": why}), indent=2, sort_keys=True))
    else:
        for line in render(result, args.misses or (args.check and not passes)):
            print(line)
    if args.check and not passes:
        print(f"FAIL bench: {why}", file=sys.stderr)
        return 1
    if not args.json:
        print(f"ok bench: {why}")
    return 0


if __name__ == "__main__":
    # Dispatch to the canonical module: under `python -m`, this file runs as `__main__`
    # and its classes would be distinct from the `mdept.bench` ones that callers import.
    from mdept.bench import main as _main

    raise SystemExit(_main())
