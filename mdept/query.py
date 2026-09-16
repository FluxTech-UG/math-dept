"""Search both ledgers, and resolve a request token, from anywhere in the family.

Run:

    python -m mdept.query "removable singularity"
    python -m mdept.query --topic TOPIC
    python -m mdept.query --consumer NAME --status open
    python -m mdept.query MD_0007
    python -m mdept.query --resolve MDR:2026-09-04-three-basin

This is step 0 of the consumer side of `docs/protocol.md`, which used to be a
grep over two directories. A grep finds the ID an author already knew; it does
not find the entry that already settles the statement about to be stipulated
again, and it cannot say what a pending token became. Both ledgers are read, so
a released entry and an unreleased one come back from one query.

What is searched, per entry: `id`, `title`, `topics`, the four body sections
(Statement, Hypotheses, Why it was raised, Current notes), the private
`provenance.raised_by.application` text, and every `cited_by` string. Ranking is
the number of term occurrences across those fields.

Filters and terms compose in one direction: with no filter, the terms select
(an entry with no hit is not in the answer); with a filter, the filter selects
the set and the terms only order it, zero-hit entries last. That way a filter
never hides an entry the filter itself admits, which is what a reader scanning
a topic needs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import CheckError, ConfigError
from . import family as family_mod
from . import schema

#: How much of a statement one line carries before it is cut.
STATEMENT_WIDTH = 120


def searchable(entry) -> dict[str, str]:
    """The fields a query reads, as {field name: text}."""
    sections = entry.sections()
    return {
        "id": entry.id,
        "title": entry.title or "",
        "topics": " ".join(entry.front.get("topics") or []),
        "statement": sections.get("Statement", ""),
        "hypotheses": sections.get("Hypotheses", ""),
        "why": sections.get("Why it was raised", ""),
        "notes": sections.get("Current notes", ""),
        "application": entry.at("provenance.raised_by.application") or "",
        "cited_by": " ".join(entry.front.get("cited_by") or []),
    }


def hits(entry, terms: list[str]) -> int:
    """How many times these terms occur across the searchable fields."""
    if not terms:
        return 0
    haystack = " \n".join(searchable(entry).values()).lower()
    return sum(haystack.count(term.lower()) for term in terms)


def one_line(text: str, width: int = STATEMENT_WIDTH) -> str:
    """A block of prose or LaTeX collapsed to one line, cut to `width`."""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= width else flat[: width - 1].rstrip() + "…"


def citation_words(status: str) -> list[str]:
    """The status words I15 requires on a line citing an entry at this status."""
    return list(schema.citation_words(status))


def as_record(entry, term_hits: int) -> dict:
    """One entry, as the JSON shape every other view is derived from."""
    return {
        "id": entry.id,
        "status": entry.status,
        "title": entry.title,
        "statement": " ".join(entry.sections().get("Statement", "").split()),
        "topics": list(entry.front.get("topics") or []),
        "raised_by": {
            "repo": entry.at("provenance.raised_by.repo"),
            "doc": entry.at("provenance.raised_by.doc"),
            "anchor": entry.at("provenance.raised_by.anchor"),
        },
        "cited_by": list(entry.front.get("cited_by") or []),
        "citation_words": citation_words(entry.status),
        "hits": term_hits,
    }


def _consumer_of(entry) -> set[str]:
    repos = set()
    repo = entry.at("provenance.raised_by.repo")
    if repo:
        repos.add(repo)
    for citation in entry.front.get("cited_by") or []:
        split = schema.split_cited_by(citation)
        if split is not None:
            repos.add(split[0])
    return repos


def search(family, terms: list[str], topic: str | None = None,
           status: str | None = None, consumer: str | None = None) -> dict:
    """The answer to one query, as the JSON shape.

    Every filter is checked against something real before the search runs. A
    filter nobody can satisfy and a search nothing matches both print zero
    entries, and only one of the two is the reader's answer: a mistyped
    `--consumer` or `--topic` reported as "0 entries" reads as "the department
    holds nothing on this", which is the most expensive wrong answer this
    command can give.
    """
    if status is not None and status not in schema.STATUSES:
        raise CheckError(
            f"I3 schema: --status: field 'status': {status!r} is not one of {list(schema.STATUSES)}"
        )
    if consumer is not None:
        family.consumer(consumer)
    if topic is not None:
        known = sorted({t for entry in family.entries() for t in entry.front.get("topics") or []})
        if topic.lower() not in [t.lower() for t in known]:
            raise CheckError(
                f"I3 schema: --topic: field 'topics': no entry carries the topic {topic!r}; "
                f"the ledger's topics are {known}"
            )

    filtered = bool(topic or status or consumer)
    records = []
    for entry in family.entries():
        if topic is not None and topic.lower() not in [t.lower() for t in entry.front.get("topics") or []]:
            continue
        if status is not None and entry.status != status:
            continue
        if consumer is not None and consumer not in _consumer_of(entry):
            continue
        term_hits = hits(entry, terms)
        if not filtered and terms and term_hits == 0:
            continue
        records.append(as_record(entry, term_hits))
    records.sort(key=lambda r: (-r["hits"], r["id"]))
    return {
        "query": {
            "terms": terms,
            "topic": topic,
            "status": status,
            "consumer": consumer,
        },
        "entries": records,
    }


def resolve(family, token: str) -> dict:
    """What a request token became: pending, declined, or the entries it seeded."""
    match = schema.REQUEST_STEM_TOKEN_RE.fullmatch(token.strip())
    if match is None:
        raise CheckError(
            f"I12 dangling: --resolve: field '<MDR token>': {token!r} is not "
            "MDR:YYYY-MM-DD-slug or MDR:YYYY-MM-DD-slug#C2"
        )
    stem, wanted = match.group("stem"), match.group("candidate")
    request = family_mod.request_by_stem(family, stem)
    if wanted is not None and wanted not in request.candidates():
        raise CheckError(
            f"I12 dangling: {request.rel}: field '<MDR token>': no '### {wanted}' heading; "
            f"this request offers {request.candidates()}"
        )
    by_id = family.by_id()
    backlinks: dict[str, list] = {}
    for entry in family.entries():
        back = entry.at("provenance.stipulated_by.request")
        if back and back.startswith(f"MDR:{stem}#"):
            backlinks.setdefault(back.split("#", 1)[1], []).append(entry)

    candidates = {}
    for candidate in request.candidates():
        if wanted is not None and candidate != wanted:
            continue
        candidates[candidate] = _candidate_outcome(request, candidate, backlinks, by_id)
    return {
        "request": stem,
        "state": request.state,
        "from": request.front.get("from") or {},
        "path": request.rel,
        "candidates": candidates,
    }


def _candidate_outcome(request, candidate: str, backlinks: dict, by_id: dict):
    found = backlinks.get(candidate)
    if found:
        return [{"id": e.id, "status": e.status} for e in sorted(found, key=lambda e: e.id)]
    line = request.outcome_line(candidate)
    if line is None:
        return "pending"
    if "declined:" in line:
        return "declined: " + " ".join(line.split("declined:", 1)[1].split())
    ids = sorted(set(schema.ID_TOKEN_RE.findall(line)))
    if ids:
        return [{"id": i, "status": by_id[i].status if i in by_id else "unknown"} for i in ids]
    return "pending"


# --- human views, derived from the JSON -------------------------------------


def render_search(answer: dict) -> list[str]:
    lines = []
    query = answer["query"]
    stated = [f"terms {' '.join(query['terms'])}" if query["terms"] else "no terms"]
    for name in ("topic", "status", "consumer"):
        if query[name]:
            stated.append(f"{name} {query[name]}")
    lines.append(f"{len(answer['entries'])} entries: {', '.join(stated)}")
    lines.append("")
    for record in answer["entries"]:
        plural = "" if record["hits"] == 1 else "s"
        hit = f"  ({record['hits']} hit{plural})" if record["hits"] else ""
        lines.append(f"{record['id']}  {record['status']:<16}{record['title']}{hit}")
        if record["statement"]:
            lines.append(f"    statement  {one_line(record['statement'])}")
        cited = "; ".join(record["cited_by"]) or "nothing cites it yet"
        words = f"  [cite with: {' | '.join(record['citation_words'])}]" if record["citation_words"] else ""
        lines.append(f"    cited by   {cited}{words}")
    return lines


def render_entry(record: dict, also: list[str] | None = None) -> list[str]:
    lines = [
        f"{record['id']}  {record['status']}  {record['title']}",
        "",
        f"  topics       {', '.join(record['topics']) or '.'}",
        f"  statement    {one_line(record['statement'], width=10_000)}",
    ]
    raised = record["raised_by"]
    where = " ".join(str(p) for p in (raised["repo"], raised["doc"], raised["anchor"]) if p)
    lines.append(f"  raised by    {where or '.'}")
    lines.append(f"  cited by     {'; '.join(record['cited_by']) or '.'}")
    if record["citation_words"]:
        lines.append(f"  cite with    one of {', '.join(record['citation_words'])}")
    if also:
        lines.append(f"  named by     {', '.join(also)}")
    return lines


def render_resolve(answer: dict) -> list[str]:
    source = answer["from"]
    where = " ".join(str(p) for p in (source.get("repo"), source.get("doc")) if p)
    lines = [f"MDR:{answer['request']}  state {answer['state']}" + (f"  ({where})" if where else ""), ""]
    for candidate, outcome in sorted(answer["candidates"].items()):
        if isinstance(outcome, str):
            lines.append(f"  {candidate}  {outcome}")
        else:
            became = ", ".join(f"{item['id']} {item['status']}" for item in outcome)
            lines.append(f"  {candidate}  {became}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.query", description=__doc__.splitlines()[0])
    parser.add_argument("terms", nargs="*", default=[], help="search terms, or one MD_#### id")
    parser.add_argument("--root", default=None, help="a math repo root (default: the installed checkout)")
    parser.add_argument("--topic", default=None, help="restrict to one topic")
    parser.add_argument("--status", default=None, help=f"restrict to one of {list(schema.STATUSES)}")
    parser.add_argument("--consumer", default=None, help="restrict to entries raised or cited by this repo")
    parser.add_argument("--resolve", default=None, metavar="MDR:...",
                        help="report what a request token became")
    parser.add_argument("--json", action="store_true", help="emit the machine view on stdout")
    args = parser.parse_args(argv)

    try:
        family = family_mod.load_family(args.root)
        if args.resolve:
            if args.terms:
                parser.error("--resolve takes a request token and no search terms")
            answer = resolve(family, args.resolve)
            human = render_resolve(answer)
        else:
            terms = list(args.terms)
            answer = search(family, terms, args.topic, args.status, args.consumer)
            # One ID as the whole query asks for that entry, not for a ranked
            # list of everything that mentions it. The other entries that name
            # it are still worth one line, because they are how a reader finds
            # the revision or the counterexample that came after.
            named = [terms[0]] if len(terms) == 1 and schema.ID_RE.match(terms[0]) else []
            wanted = [r for r in answer["entries"] if r["id"] in named]
            if wanted:
                also = [r["id"] for r in answer["entries"] if r["id"] not in named]
                human = render_entry(wanted[0], also)
            else:
                human = render_search(answer)
    except (CheckError, ConfigError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(answer, indent=2, sort_keys=True))
        return 0
    for line in human:
        print(line)
    return 0


if __name__ == "__main__":
    # Dispatch to the canonical module: under `python -m`, this file runs as `__main__`
    # and its classes would be distinct from the `mdept.query` ones that artifacts and
    # callers import, breaking isinstance checks.
    from mdept.query import main as _main

    raise SystemExit(_main())
