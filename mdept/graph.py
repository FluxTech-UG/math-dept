"""The ledger's links as one edge list: what `ledger/EDGES.tsv` holds and what a card follows.

An edge is `(source entry, kind, target)`. The kinds are the link fields an
entry carries: `revises`, `merged_into`, the four `between` relations, the
`MD_####` tokens of `provenance.connects` (kind `connects`), and one `cited_by`
edge per citation string, whose target is that string (`Repo:path §n`), not an
ID. `Entry.linked_ids` is the one reader of the ID-valued fields; this module
only adds the citations and the reverse view.
"""

from __future__ import annotations

from . import CheckError

#: The edge kinds, in the order a card prints them. The ID-valued kinds are
#: `Entry.linked_ids` field names with their `between.` or `provenance.` prefix dropped.
KINDS = ("revises", "merged_into", "below_of", "above_of", "special_case_of",
         "generalizes", "connects", "cited_by")


def _kind(field_name: str) -> str:
    return field_name.rsplit(".", 1)[-1]


def edges(entries) -> list[tuple[str, str, str]]:
    """Every edge the entries carry, sorted by source, kind order, target."""
    rows = set()
    for entry in entries:
        for field_name, targets in entry.linked_ids().items():
            for target in targets:
                rows.add((entry.id, _kind(field_name), target))
        for citation in entry.front.get("cited_by") or []:
            rows.add((entry.id, "cited_by", str(citation)))
    order = {kind: i for i, kind in enumerate(KINDS)}
    return sorted(rows, key=lambda row: (row[0], order[row[1]], row[2]))


def neighbours(rows, entry_id: str) -> list[tuple[str, str, str]]:
    """The entry links of one entry as (direction, kind, other ID): `out` first, then `in`.

    Citation edges are left out: a card prints `cited_by` as its own line.
    """
    out = [("out", kind, target) for source, kind, target in rows
           if source == entry_id and kind != "cited_by"]
    incoming = [("in", kind, source) for source, kind, target in rows
                if target == entry_id and kind != "cited_by" and source != entry_id]
    return out + sorted(incoming, key=lambda row: (KINDS.index(row[1]), row[2]))


def render_tsv(rows) -> str:
    """`ledger/EDGES.tsv`: a header line, then one tab-separated edge per line."""
    lines = ["source\tkind\ttarget"]
    for row in rows:
        if any("\t" in part or "\n" in part for part in row):
            raise CheckError(
                f"I16 generated: ledger/EDGES.tsv: field '{row[1]}': {row!r} carries a tab or a line "
                "break, which the tab-separated edge list cannot hold"
            )
        lines.append("\t".join(row))
    return "\n".join(lines) + "\n"
