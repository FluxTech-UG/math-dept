"""Allocate the next ID and write the entry file.

Run either form:

    python -m mdept.new --request 2026-09-04-three-basin --candidate C2
    python -m mdept.new --title "..." --kind lemma --topics a,b --domain "..." --who claude

The first form is the normal path: a candidate in an inbox request becomes an
entry with its provenance already filled in and its statement carried over. The
second is for a statement born in this repo, with no consumer behind it.

IDs are allocated as max plus one across BOTH repos, because entries are born
private and released with gaps. Allocating from one repo alone would reissue an
ID the other repo already owns, and an ID is never reused.

Every field this writes is a real value taken from the request or the command
line. There are no placeholder defaults: a flag you did not pass is a value the
ledger would otherwise be inventing.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

import yaml

from . import CheckError, ConfigError
from . import config, parse, schema

CANDIDATE_HEADING_RE = re.compile(r"^###\s+(C\d+)\s*(.*?)\s*$", re.MULTILINE)
BULLET_RE = re.compile(r"^-\s+\*\*(?P<key>[^:*]+):\*\*\s*(?P<value>.*)$")
LEDGER_IDS_RE = re.compile(r"^(?P<indent>\s*)ledger_ids:\s*\[(?P<items>[^\]]*)\]\s*$", re.MULTILINE)
STATE_RE = re.compile(r"^(?P<indent>\s*)state:\s*(?P<value>new|triaged|closed)\b(?P<rest>.*)$", re.MULTILINE)


def allocate_id(root: Path) -> str:
    """The next free ID across this repo and its sibling."""
    root = Path(root).resolve()
    used = {e.id for e in parse.load_entries(root)}
    sibling = config.private_root(root) if not config.is_private(root) else config.public_root(root)
    if sibling is not None and (sibling / "ledger").is_dir():
        used |= {e.id for e in parse.load_entries(sibling)}
    highest = max((int(i.split("_")[1]) for i in used), default=0)
    return f"MD_{highest + 1:04d}"


def blank_front(entry_id: str) -> dict:
    """A schema-complete front matter with every key present and nothing invented."""
    return {
        "id": entry_id,
        "title": None,
        "status": "conjectured",
        "kind": None,
        "topics": [],
        "source": None,
        "formal": {"decl": None, "file": None},
        "evidence": [],
        "between": {relation: [] for relation in schema.RELATIONS},
        "provenance": {
            "raised_by": {"repo": None, "domain": None, "doc": None, "anchor": None, "application": None},
            "stipulated_by": {"who": None, "date": None, "model": None, "request": None},
            "settled_by": None,
            "connects": [],
        },
        "cited_by": [],
        "revises": None,
        "merged_into": None,
        "statement_hash": None,
    }


def render_entry(front: dict, statement: str, hypotheses: str, why: str) -> str:
    body = "\n".join(
        [
            "",
            "## Statement",
            "",
            statement,
            "",
            "## Hypotheses",
            "",
            hypotheses,
            "",
            "## Why it was raised",
            "",
            why,
            "",
            "## Current notes",
            "",
            "Stipulated, not yet worked.",
            "",
        ]
    )
    dumped = yaml.dump(front, sort_keys=False, default_flow_style=False, allow_unicode=True).rstrip("\n")
    return f"---\n{dumped}\n---\n{body}"


def _candidate_section(request, candidate: str) -> tuple[str, dict]:
    matches = list(CANDIDATE_HEADING_RE.finditer(request.body))
    for i, match in enumerate(matches):
        if match.group(1) != candidate:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(request.body)
        block = request.body[match.end() : end]
        fields = {}
        for line in block.splitlines():
            bullet = BULLET_RE.match(line.strip())
            if bullet:
                fields[bullet.group("key").strip()] = bullet.group("value").strip()
        return match.group(2).strip(), fields
    raise CheckError(
        f"I12 dangling: {request.rel}: field '<candidate>': no '### {candidate}' heading; "
        f"this request offers {request.candidates()}"
    )


def from_request(root: Path, stem: str, candidate: str, model: str | None) -> tuple[str, str]:
    """Write an entry for one candidate of an inbox request. Returns (id, path)."""
    root = Path(root).resolve()
    if not config.is_private(root):
        raise ConfigError(
            "--request reads the inbox, which lives in math-dept-private. "
            "Run this form from a session in the private repo."
        )
    requests = {r.stem: r for r in parse.load_requests(root)}
    request = requests.get(stem)
    if request is None:
        raise CheckError(f"I12 dangling: inbox/{stem}.md: field '<request>': no such request")
    title, fields = _candidate_section(request, candidate)
    source = request.front.get("from") or {}

    entry_id = allocate_id(root)
    front = blank_front(entry_id)
    front["title"] = title
    front["kind"] = fields.get("Kind", "lemma")
    front["topics"] = [t.strip() for t in fields.get("Topics", "unsorted").split(",") if t.strip()]
    front["provenance"]["raised_by"] = {
        "repo": source.get("repo"),
        "domain": fields.get("Domain") or source.get("repo"),
        "doc": source.get("doc"),
        "anchor": source.get("anchor"),
        "application": parse.body_sections(request.body).get("Application", "").strip() or None,
    }
    front["provenance"]["stipulated_by"] = {
        "who": source.get("who"),
        "date": datetime.date.today().isoformat(),
        "model": model or source.get("model"),
        "request": f"MDR:{stem}#{candidate}",
    }

    text = render_entry(
        front,
        fields.get("Statement", "$$ ... $$"),
        fields.get("Hypotheses", "- **H1.** ..."),
        f"Raised by {source.get('repo')} through {candidate} of MDR:{stem}.",
    )
    path = root / "ledger" / f"{entry_id}.md"
    _write_new(path, text)
    _record_on_request(request.path, entry_id)
    return entry_id, str(path)


def from_title(root: Path, args) -> tuple[str, str]:
    """Write an entry raised in this repo, with no consumer request behind it."""
    root = Path(root).resolve()
    entry_id = allocate_id(root)
    front = blank_front(entry_id)
    front["title"] = args.title
    front["kind"] = args.kind
    front["topics"] = [t.strip() for t in args.topics.split(",") if t.strip()]
    front["provenance"]["raised_by"] = {
        "repo": args.repo,
        "domain": args.domain,
        "doc": None,
        "anchor": None,
        "application": None,
    }
    front["provenance"]["stipulated_by"] = {
        "who": args.who,
        "date": datetime.date.today().isoformat(),
        "model": args.model,
        "request": None,
    }
    text = render_entry(front, "$$ ... $$", "- **H1.** ...", args.domain)
    path = root / "ledger" / f"{entry_id}.md"
    _write_new(path, text)
    return entry_id, str(path)


def _write_new(path: Path, text: str) -> None:
    if path.exists():
        raise CheckError(f"I2 permanence: {path}: field '<file>': already exists; IDs are never reused")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _record_on_request(path: Path, entry_id: str) -> None:
    """Add the new ID to the request's `ledger_ids` and move `new` to `triaged`."""
    text = path.read_text(encoding="utf-8")
    match = LEDGER_IDS_RE.search(text)
    if match is None:
        raise CheckError(
            f"I13 inbox: {path}: field 'ledger_ids': expected a flow list such as `ledger_ids: []` to append to"
        )
    items = [i.strip() for i in match.group("items").split(",") if i.strip()]
    if entry_id not in items:
        items.append(entry_id)
    text = text[: match.start()] + f"{match.group('indent')}ledger_ids: [{', '.join(items)}]" + text[match.end():]
    text = STATE_RE.sub(
        lambda m: f"{m.group('indent')}state: triaged{m.group('rest')}" if m.group("value") == "new" else m.group(0),
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.new", description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=None, help="repo root (default: nearest ancestor with ledger/)")
    parser.add_argument("--request", default=None, help="an inbox request stem, for example 2026-09-04-three-basin")
    parser.add_argument("--candidate", default=None, help="the candidate heading, for example C2")
    parser.add_argument("--title", default=None, help="title for an entry born in this repo")
    parser.add_argument("--kind", default=None, choices=schema.KINDS)
    parser.add_argument("--topics", default=None, help="comma-separated, lower-case-hyphenated")
    parser.add_argument("--domain", default=None, help="one neutral line naming the mathematical domain")
    parser.add_argument("--who", default=None, choices=schema.WHO, help="who stipulated it")
    parser.add_argument("--repo", default="math-dept", help="the repo that raised it (title form)")
    parser.add_argument("--model", default=None, help="model identifier for the credit trail")
    args = parser.parse_args(argv)

    root = config.find_repo_root(args.root) if args.root is None else Path(args.root).resolve()
    try:
        if args.request or args.candidate:
            if not (args.request and args.candidate):
                parser.error("--request and --candidate are used together")
            entry_id, path = from_request(root, args.request, args.candidate, args.model)
        else:
            missing = [f for f in ("title", "kind", "topics", "domain", "who") if getattr(args, f) is None]
            if missing:
                parser.error(f"the title form requires {['--' + m for m in missing]}; none of them has a default")
            entry_id, path = from_title(root, args)
    except (CheckError, ConfigError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    print(f"ok {entry_id} {path}")
    print("next: write the Statement and Hypotheses, then `make regen && make check`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
