"""Search both ledgers, and resolve a request token, from anywhere in the family.

Run:

    python -m mdept.query "a conserved quantity gives a unit multiplier"
    python -m mdept.query "eigenvalue perturbation" --status open -k 5
    python -m mdept.query --exact "2^n"
    python -m mdept.query --topic TOPIC
    python -m mdept.query --consumer NAME --status open
    python -m mdept.query MD_0007
    python -m mdept.query --resolve MDR:2026-09-04-three-basin

This is step 0 of the consumer side of `docs/protocol.md`. A grep finds the ID
an author already knew; it does not find the entry that already settles the
statement about to be stipulated again, and it cannot say what a pending token
became. Both ledgers are read, so a released entry and an unreleased one come
back from one query.

What is searched, per entry (`searchable`): `id`, `title`, `topics`, the body
sections (Statement, Hypotheses, In plain words, Why it was raised, Current
notes), `aka`, `phrasings`, the private `provenance.raised_by.application` text,
and every `cited_by` string. The word ranking also reads
`provenance.raised_by.domain` (`ranked_fields`).

Words, the default (`rank`): the query and every field become tokens through
`mdept.words` (LaTeX macros read as words, stopwords dropped, plurals folded),
the query is expanded with `ledger/SYNONYMS.yaml`, and entries are scored by
BM25 over the fields weighted by `FIELD_WEIGHTS`. A score is the share of the
query's attainable score an entry reaches, in [0, 1]. The top `DEFAULT_K` hits
at or above `SCORE_FLOOR` print as cards (`mdept.card`) with their linked
entries, each with its score; when none clears the floor the answer says so in
one line, which tells the reader the ledger may not hold the statement. A
filter restricts the entries ranked.

Exact substrings (`--exact`, `search`): the number of occurrences of each term
as typed, which is what a LaTeX fragment or a path needs. With no filter the
terms select (an entry with no hit is not in the answer); with a filter, the
filter selects the set and the terms only order it, zero-hit entries last, so a
filter never hides an entry it admits. Filters with no terms list that way too.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

from . import CheckError, ConfigError
from . import card as card_mod
from . import family as family_mod
from . import graph, schema, words

#: How much of a statement one line carries before it is cut.
STATEMENT_WIDTH = 120

#: BM25 field weights. A field not named here weighs 1.
FIELD_WEIGHTS = {"aka": 3, "phrasings": 3, "title": 2, "plain": 2}
#: BM25's term-frequency saturation and length normalisation, at their usual values.
BM25_K1 = 1.2
BM25_B = 0.75
#: The share of the query's attainable score a hit must reach to be offered. Set on
#: `bench/queries.yaml` (3 November 2026, before the aka and phrasings backfill): 0.3
#: keeps mined recall@5 at 0.84 and holds 2 of 6 no-answer rows; 0.4 holds 5 of 6 at
#: recall@5 0.76. The lower floor wins because a missed entry is a statement stipulated
#: twice, while a weak hit costs a glance at its score.
SCORE_FLOOR = 0.3
#: How many hits print as cards.
DEFAULT_K = 8
#: How much of a Statement or hypothesis a hit's card carries.
HIT_WIDTH = 320


def searchable(entry) -> dict[str, str]:
    """The fields a query reads, as {field name: text}."""
    sections = entry.sections()
    return {
        "id": entry.id,
        "title": entry.title or "",
        "topics": " ".join(entry.front.get("topics") or []),
        "statement": sections.get("Statement", ""),
        "hypotheses": sections.get("Hypotheses", ""),
        "plain": sections.get(schema.PLAIN_WORDS_HEADING, ""),
        "why": sections.get("Why it was raised", ""),
        "notes": sections.get("Current notes", ""),
        "aka": " \n".join(entry.front.get("aka") or []),
        "phrasings": " \n".join(entry.front.get("phrasings") or []),
        "application": entry.at("provenance.raised_by.application") or "",
        "cited_by": " ".join(entry.front.get("cited_by") or []),
    }


def ranked_fields(entry) -> dict[str, str]:
    """What the ranked search reads: `searchable`, plus the neutral domain line of the provenance.

    The domain names the mathematical area in words a consumer types ("Runge-Kutta
    methods"), so the word ranking reads it; the exact search counts substrings in
    `searchable` alone.
    """
    return dict(searchable(entry), domain=entry.at("provenance.raised_by.domain") or "")


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


def check_filters(family, topic: str | None, status: str | None, consumer: str | None) -> None:
    """Every filter checked against something real before a search runs.

    A filter nobody can satisfy and a search nothing matches both print zero
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


def admits(entry, topic: str | None, status: str | None, consumer: str | None) -> bool:
    """Whether an entry passes the filters (each None filter passes everything)."""
    if topic is not None and topic.lower() not in [t.lower() for t in entry.front.get("topics") or []]:
        return False
    if status is not None and entry.status != status:
        return False
    return consumer is None or consumer in _consumer_of(entry)


def search(family, terms: list[str], topic: str | None = None,
           status: str | None = None, consumer: str | None = None) -> dict:
    """The exact-substring answer to one query, as the JSON shape (`check_filters` first)."""
    check_filters(family, topic, status, consumer)
    filtered = bool(topic or status or consumer)
    records = []
    for entry in family.entries():
        if not admits(entry, topic, status, consumer):
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


class Ranker:
    """BM25 over the weighted fields of a set of entries.

    Each entry's term frequency is the weighted sum over fields of the term's
    count there, and its length the weighted sum of the fields' token counts
    (BM25F with one shared length normalisation). IDF is over the entries.
    """

    def __init__(self, entries):
        self.tf: dict[str, Counter] = {}
        self.length: dict[str, float] = {}
        for entry in entries:
            counts: Counter = Counter()
            length = 0.0
            for name, text in ranked_fields(entry).items():
                weight = FIELD_WEIGHTS.get(name, 1)
                found = words.tokens(text)
                length += weight * len(found)
                for token in found:
                    counts[token] += weight
            self.tf[entry.id] = counts
            self.length[entry.id] = length
        self.n = len(self.tf)
        self.average = (sum(self.length.values()) / self.n) if self.n else 0.0
        self.df: Counter = Counter()
        for counts in self.tf.values():
            self.df.update(counts.keys())

    def idf(self, token: str) -> float:
        df = self.df.get(token, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def ideal(self, token: str) -> float:
        """The most one token can add to a score: its IDF at saturation."""
        return self.idf(token) * (BM25_K1 + 1)

    def score(self, entry_id: str, token: str) -> float:
        tf = self.tf[entry_id].get(token, 0)
        if not tf:
            return 0.0
        norm = 1 - BM25_B + BM25_B * self.length[entry_id] / self.average
        return self.idf(token) * tf * (BM25_K1 + 1) / (tf + BM25_K1 * norm)

    def share(self, entry_id: str, groups) -> float:
        """The entry's score as a share of the query's attainable score, in [0, 1].

        A group contributes its best alternative's score, capped at the group's
        attainable score, which is that of its cheapest alternative: an entry
        that says the ledger's phrase satisfies the consumer's phrase in full.
        """
        reached = attainable = 0.0
        for _count, alternatives in groups:
            cap = min(sum(self.ideal(t) for t in alt) for alt in alternatives)
            best = max(sum(self.score(entry_id, t) for t in alt) for alt in alternatives)
            reached += min(best, cap)
            attainable += cap
        return reached / attainable if attainable else 0.0


def rank(family, terms: list[str], k: int = DEFAULT_K, topic: str | None = None,
         status: str | None = None, consumer: str | None = None,
         ranker: Ranker | None = None, pairs=None) -> dict:
    """The ranked answer to a query in words, as the JSON shape: up to `k` hits at or above the floor.

    `ranker` (a `Ranker` over `family.entries()`) and `pairs` (`words.synonyms_of(family)`)
    are built here when absent; a caller running many queries builds them once.
    """
    if k < 1:
        raise CheckError(f"I3 schema: -k: field 'k': {k} hits asked for; at least 1")
    check_filters(family, topic, status, consumer)
    tokens = words.tokens(" ".join(terms))
    if not tokens:
        raise CheckError(
            f"I3 schema: <query>: field 'terms': {' '.join(terms)!r} has no search word once "
            "stopwords and single letters are dropped"
        )
    groups = words.expand(tokens, words.synonyms_of(family) if pairs is None else pairs)
    entries = family.entries()
    ranker = Ranker(entries) if ranker is None else ranker
    scored = sorted(
        ((ranker.share(entry.id, groups), entry) for entry in entries
         if admits(entry, topic, status, consumer)),
        key=lambda pair: (-pair[0], pair[1].id),
    )
    above = [(share, entry) for share, entry in scored if share >= SCORE_FLOOR]
    rows = graph.edges(entries)
    best_below = next(((share, entry) for share, entry in scored if share < SCORE_FLOOR and share > 0), None)
    return {
        "query": {
            "terms": terms,
            "groups": [[list(alt) for alt in alternatives] for _count, alternatives in groups],
            "topic": topic,
            "status": status,
            "consumer": consumer,
            "k": k,
        },
        "floor": SCORE_FLOOR,
        "above_floor": len(above),
        "hits": [
            {"id": entry.id, "score": round(share, 4), "card": card_mod.card(entry, family, rows)}
            for share, entry in above[:k]
        ],
        "best_below": (None if best_below is None
                       else {"id": best_below[1].id, "score": round(best_below[0], 4)}),
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


def render_one(data: dict, record: dict, also: list[str] | None = None) -> list[str]:
    """One entry asked for by ID: its full card, then where it sits (topics, raised by, named by)."""
    lines = card_mod.render_entry(data)
    raised = record["raised_by"]
    where = " ".join(str(p) for p in (raised["repo"], raised["doc"], raised["anchor"]) if p)
    lines.append(f"  {'topics':<{card_mod.LABEL_WIDTH}}{', '.join(record['topics']) or '.'}")
    lines.append(f"  {'raised by':<{card_mod.LABEL_WIDTH}}{where or '.'}")
    if also:
        lines.append(f"  {'named by':<{card_mod.LABEL_WIDTH}}{', '.join(also)}")
    return lines


def render_rank(answer: dict) -> list[str]:
    """The ranked answer: the floor line, then each hit's card (cut to `HIT_WIDTH`) with its score."""
    floor = answer["floor"]
    if not answer["hits"]:
        best = answer["best_below"]
        tail = f"; the best was {best['id']} at {best['score']:.2f}" if best else ""
        return [f"nothing above the floor ({floor:.2f} of the query's attainable score){tail}. "
                "The ledger may not hold this statement: try other words, or file a request."]
    shown = len(answer["hits"])
    more = answer["above_floor"] - shown
    lines = [f"floor {floor:.2f}: {answer['above_floor']} entries above it"
             + (f", the top {shown} shown (-k for more)" if more > 0 else "")]
    for hit in answer["hits"]:
        lines.append("")
        body = card_mod.render_entry(hit["card"], width=HIT_WIDTH)
        lines.append(f"{body[0]}  [score {hit['score']:.2f}]")
        lines += body[1:]
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
    parser.add_argument("terms", nargs="*", default=[], help="a question in your own words, or one MD_#### id")
    parser.add_argument("-k", type=int, default=DEFAULT_K, help=f"how many hits print as cards (default {DEFAULT_K})")
    parser.add_argument("--exact", action="store_true",
                        help="count each term as an exact substring instead of ranking words")
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
            # One ID as the whole query asks for that entry, not for a ranked
            # list of everything that mentions it. The other entries that name
            # it are still worth one line, because they are how a reader finds
            # the revision or the counterexample that came after.
            named = terms[0] if len(terms) == 1 and schema.ID_RE.match(terms[0]) else None
            if named or args.exact or not terms:
                answer = search(family, terms, args.topic, args.status, args.consumer)
                wanted = [r for r in answer["entries"] if r["id"] == named]
                if wanted:
                    also = [r["id"] for r in answer["entries"] if r["id"] != named]
                    data = card_mod.card(family.by_id()[named], family)
                    answer = dict(answer, card=data)
                    human = render_one(data, wanted[0], also)
                else:
                    human = render_search(answer)
            else:
                answer = rank(family, terms, args.k, args.topic, args.status, args.consumer)
                human = render_rank(answer)
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
