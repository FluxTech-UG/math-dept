#!/usr/bin/env python3
"""Emit a cc-run batch file, one step per open request candidate.

    python scripts/gen_prove_queue.py [--private PATH] [--out prompts/]

Scans the private inbox for requests in state `new` or `triaged` and writes
`prompts/prove-queue-<date>.md` in the cc-run batch format: YAML frontmatter,
then one `# step-name` section per candidate chained by `depends_on`, then a
final audit step whose verdict is GO or STOP.

This is the queue generator, not the queue runner. It is only useful once a
headless session can drive `lake build` through Bash; until then the same steps
are worked interactively per `docs/triage.md`, and this script exists so the
queue is generated from the inbox rather than typed.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

CANDIDATE_RE = re.compile(r"^###\s+(C\d+)\s*(.*?)\s*$", re.MULTILINE)
FRONT_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.DOTALL)
STATE_RE = re.compile(r"^state:\s*(\w+)", re.MULTILINE)
PRIORITY_RE = re.compile(r"^priority:\s*(\w+)", re.MULTILINE)

FRONTMATTER = "---\nmax_turns: 150\neffort: xhigh\n---\n"
PRIORITY_ORDER = {"high": 0, "normal": 1, "low": 2}


def open_requests(private: Path) -> list[tuple[str, str, list[tuple[str, str]]]]:
    """(stem, priority, [(candidate, title)]) for every request still in inbox/."""
    inbox = private / "inbox"
    if not inbox.is_dir():
        raise SystemExit(f"FAIL {inbox} does not exist; the inbox lives in math-dept-private")
    found = []
    for path in sorted(inbox.glob("*.md")):
        if path.name == "TEMPLATE.md":
            continue
        text = path.read_text(encoding="utf-8")
        match = FRONT_RE.match(text)
        if match is None:
            raise SystemExit(f"FAIL {path}: no YAML front matter")
        front, body = match.group(1), match.group(2)
        state = STATE_RE.search(front)
        if state is None or state.group(1) not in ("new", "triaged"):
            continue
        priority = PRIORITY_RE.search(front)
        candidates = [(m.group(1), m.group(2)) for m in CANDIDATE_RE.finditer(body)]
        if candidates:
            found.append((path.stem, priority.group(1) if priority else "normal", candidates))
    return sorted(found, key=lambda r: (PRIORITY_ORDER.get(r[1], 1), r[0]))


def step(name: str, depends_on: str | None, prompt: str) -> str:
    header = f"# {name}\n" + (f"depends_on: {depends_on}\n" if depends_on else "")
    return f"{header}\n{prompt}\n"


def render(requests: list, date: str) -> str:
    sections = [FRONTMATTER]
    previous = None
    for stem, priority, candidates in requests:
        for candidate, title in candidates:
            name = f"{len(sections):02d}-{stem}-{candidate.lower()}"
            sections.append(
                step(
                    name,
                    previous,
                    "## What and Why\n"
                    f"Triage `MDR:{stem}#{candidate}` ({title or 'untitled'}), priority {priority}, "
                    "following `docs/triage.md`. Run the statement-fidelity round trip first, then "
                    f"`python -m mdept.new --request {stem} --candidate {candidate}`, then the ladder "
                    "S0 to S4 with the budgets in that runbook.\n\n"
                    "## Constraints\n"
                    "- The statement's type is frozen once it compiles. A different statement is a new ID.\n"
                    "- `sorry` only under `MathDeptPrivate/Conjectures/`.\n"
                    "- A refutation at any stage ends the ladder.\n\n"
                    "## Done When\n"
                    "- The entry has a status, evidence, and `settled_by`, or is `open` with a triage record.\n"
                    "- `make regen && make check` passes.\n"
                    f"- Git commit with message: \"{{id}}: triaged from MDR:{stem}#{candidate}\"\n",
                )
            )
            previous = name
    sections.append(
        step(
            f"{len(sections):02d}-audit-{date}",
            previous,
            "## What and Why\n"
            "Audit every entry this queue touched and issue one verdict for the batch.\n\n"
            "## Constraints\n"
            "- Run `make lean`, then `python -m mdept.check --run-counterexamples --lean --family`.\n"
            "- For every `proven-formal` entry, compare `statement_hash` against the `type` field of its\n"
            "  declaration in `audit/latest.json`. A mismatch is a STOP, not a regeneration.\n"
            "- Re-audit anything a cloud prover produced locally before trusting it.\n\n"
            "## Done When\n"
            "- The report ends with a single line, `GO` or `STOP <reason>`.\n"
            "- Git commit with message: \"prove queue audit\"\n",
        )
    )
    return "\n---\n\n".join(sections)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/gen_prove_queue.py", description=__doc__.splitlines()[0])
    parser.add_argument("--private", default=None, help="the private repo (default: ../math-dept-private)")
    parser.add_argument("--out", default="prompts", help="output directory (default: prompts/)")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    private = Path(args.private).resolve() if args.private else root.parent / "math-dept-private"
    if not private.is_dir():
        print(f"FAIL {private} does not exist; pass --private", file=sys.stderr)
        return 1

    requests = open_requests(private)
    if not requests:
        print("ok inbox is empty; no queue to generate")
        return 0

    date = datetime.date.today().isoformat()
    target = Path(args.out)
    target = target if target.is_absolute() else root / target
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"prove-queue-{date}.md"
    path.write_text(render(requests, date), encoding="utf-8")
    print(f"ok {path}: {sum(len(c) for _, _, c in requests)} candidates from {len(requests)} requests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
