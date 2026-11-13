"""Where an inbox run stands: five counts on one line, then the names behind them.

Run from the private repo (or with `--root` naming it):

    python -m mdept.inbox_status [--root PATH]

The first line is

    new=<n> closable_open=<n> entries_without_current_fidelity=<n> check_fails=<n> later_day_owed=<n>

and a line follows for each nonzero count, naming what it counts (the
`check_fails` lines come last, one per failure):

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
- `later_day_owed`: the `conjectured` entries with a file under `proofs/` that owe the
  later-day check `proven-informal` needs (`later_day_owed`), each as
  `MD_0197 (check from 2026-11-14, settle --date 2026-11-13)`.

A request or entry that cannot be read fails the command with its error, as the
check would; a failing check is counted, never raised.
"""

from __future__ import annotations

import argparse
import datetime
import sys

from . import CheckError, ConfigError
from . import check as check_mod
from . import family as family_mod
from . import parse, query, schema

COUNTS = ("new", "closable_open", "entries_without_current_fidelity", "check_fails", "later_day_owed")

# Stages whose row changes the proof or the statement. The stages cannot tell a change
# of substance from a wording repair, so every one counts (the conservative reading).
PROOF_CHANGE_STAGES = ("S3", "S1+S3", "S3-extract", "S3-fix", "S3-note", "fixes", "repair",
                       "statement")
LATER_DAY_CHECK_STAGE = "later-day-check"


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


def later_day_owed(entry, root) -> str | None:
    """`<id> (check from <day>, settle --date <day>)` when a conjectured entry owes its check.

    The entry owes one when it is `conjectured`, has `proofs/<ID>.md`, and no
    `later-day-check` row is dated after D, the date of the last row whose stage is in
    `PROOF_CHANGE_STAGES`. The settle date is the later of D and the stipulated date
    (I18); the check runs strictly after it.
    """
    if entry.status != "conjectured" or not (root / "proofs" / f"{entry.id}.md").is_file():
        return None
    where = f"triage/{entry.id}.md"
    if not (root / where).is_file():
        raise CheckError(f"{where}: no attempt record, but proofs/{entry.id}.md exists")
    rows = parse.attempt_rows(root / where, where)
    changes = [day for day, stage in rows if stage in PROOF_CHANGE_STAGES]
    if not changes:
        raise CheckError(f"{where}: proofs/{entry.id}.md exists but no row has a stage in "
                         f"{list(PROOF_CHANGE_STAGES)}")
    last = max(changes)
    if any(stage == LATER_DAY_CHECK_STAGE and day > last for day, stage in rows):
        return None
    settle = max(last, datetime.date.fromisoformat(entry.at("provenance.stipulated_by.date")))
    return f"{entry.id} (check from {settle + datetime.timedelta(days=1)}, settle --date {settle})"


def status(root=None) -> dict:
    """The five lists behind the counts, each in a stable order."""
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
        owed = later_day_owed(entry, private.root)
        if owed is not None:
            found["later_day_owed"].append(owed)
    try:
        check_mod.run(private.root, family=True)
    except CheckError as exc:
        found["check_fails"] = check_mod.failure_lines(str(exc), config_error=False)
    except ConfigError as exc:
        found["check_fails"] = check_mod.failure_lines(str(exc), config_error=True)
    return found


def render(found: dict) -> list[str]:
    lines = [" ".join(f"{name}={len(found[name])}" for name in COUNTS)]
    for name in COUNTS:
        if name != "check_fails" and found[name]:
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
