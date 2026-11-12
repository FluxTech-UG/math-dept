"""Where an inbox run stands: four counts on one line, then the names behind them.

Run from the private repo (or with `--root` naming it):

    python -m mdept.inbox_status [--root PATH]

The first line is

    new=<n> closable_open=<n> entries_without_current_fidelity=<n> check_fails=<n>

and a line follows for each nonzero count, naming what it counts:

- `new`: the requests in `inbox/` (not `inbox/done/`) whose state is `new`.
- `closable_open`: the requests in `inbox/` whose every candidate is answered, each
  declined in the Outcome or seeding entries that are all settled (no entry
  `conjectured`, `open` or unknown). The request-to-entry map is `query.resolve`'s.
- `entries_without_current_fidelity`: the unsettled entries of both ledgers
  (`schema.UNSETTLED_STATUSES`) whose attempt record is missing, holds no fidelity
  row, or holds a statement row with no later fidelity row (`parse.stale_statement_row`,
  the rule of I22).
- `check_fails`: the failures of `mdept.check` run in-process with `--family`, after
  the consumer-owned failures `repos.yaml` declares as its baseline, one per line.

A request or entry that cannot be read fails the command with its error, as the
check would; a failing check is counted, never raised.
"""

from __future__ import annotations

import argparse
import sys

from . import CheckError, ConfigError
from . import check as check_mod
from . import family as family_mod
from . import parse, query, schema

COUNTS = ("new", "closable_open", "entries_without_current_fidelity", "check_fails")


def _answered(outcome) -> bool:
    """True for a candidate declined, or seeding entries that are all settled."""
    if isinstance(outcome, str):
        return outcome.startswith("declined:")
    return bool(outcome) and all(
        e["status"] not in schema.UNSETTLED_STATUSES and e["status"] != "unknown" for e in outcome)


def fidelity_gap(record, entry_id: str) -> str | None:
    """Why an unsettled entry has no current fidelity, or None when it has."""
    if not record.is_file():
        return "no attempt record"
    stages = parse.attempt_stages(record, f"triage/{entry_id}.md")
    if not parse.has_fidelity_row(stages):
        return "no fidelity row"
    stale = parse.stale_statement_row(stages)
    if stale is not None:
        return f"row {stale + 1}, a statement edit, has no later fidelity row"
    return None


def status(root=None) -> dict:
    """The four lists behind the counts, each in a stable order."""
    family = family_mod.load_family(root)
    private = family_mod.require_private(family, "mdept.inbox_status")
    found = {name: [] for name in COUNTS}
    for request in family.requests():
        if request.closed:
            continue
        if request.state == "new":
            found["new"].append(request.stem)
        resolved = query.resolve(family, f"MDR:{request.stem}")
        if resolved["candidates"] and all(_answered(o) for o in resolved["candidates"].values()):
            found["closable_open"].append(request.stem)
    for entry in family.entries():
        if entry.status not in schema.UNSETTLED_STATUSES:
            continue
        gap = fidelity_gap(private.root / "triage" / f"{entry.id}.md", entry.id)
        if gap is not None:
            found["entries_without_current_fidelity"].append(f"{entry.id} ({gap})")
    try:
        check_mod.run(private.root, family=True)
    except CheckError as exc:
        found["check_fails"] = check_mod.failure_lines(str(exc), config_error=False)
    except ConfigError as exc:
        found["check_fails"] = check_mod.failure_lines(str(exc), config_error=True)
    return found


def render(found: dict) -> list[str]:
    lines = [" ".join(f"{name}={len(found[name])}" for name in COUNTS)]
    for name in COUNTS[:3]:
        if found[name]:
            lines.append(f"{name}: {', '.join(found[name])}")
    if found["check_fails"]:
        lines.append("check_fails:")
        lines.extend(f"  {failure}" for failure in found["check_fails"])
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.inbox_status", description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=None, help="the private repo (default: located from the cwd)")
    args = parser.parse_args(argv)
    try:
        found = status(args.root)
    except (CheckError, ConfigError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    for line in render(found):
        print(line)
    return 0


if __name__ == "__main__":
    # Dispatch to the canonical module, as `mdept.check` does.
    from mdept.inbox_status import main as _main

    raise SystemExit(_main())
