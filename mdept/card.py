"""The entry card: the second reading tier, between a catalog line and the entry file.

`card()` collects one entry as data: status and the words a citing line carries,
the Statement and each hypothesis on one line, the informal names, the Lean
declaration, the files that settle it (Lean, informal proof, counterexample),
the entries it links to and that link to it, and where it is cited.
`render_entry()` is the one rendering of that data, as aligned text for
`mdept.query` (a hit, or one entry by ID) or as markdown bullets for the
consumer view `mdept.view`. A linked ID the public ledger lacks prints as
`family.HELD` from a public checkout with no private ledger on disk, which is
what it is from there; with the private ledger loaded, an ID in neither ledger
fails I8 (`family.held`).
"""

from __future__ import annotations

from . import CheckError, graph, schema, words
from . import family as family_mod

#: The evidence kinds a card names as files, beside the Lean file.
CARD_EVIDENCE_KINDS = ("proof", "counterexample")
#: The label column of the text card.
LABEL_WIDTH = 13


def hypotheses(section: str) -> list[str]:
    """The Hypotheses section as one line per `- ` item (continuation lines joined)."""
    items: list[list[str]] = []
    for raw in section.splitlines():
        text = raw.strip()
        if not text:
            continue
        if text.startswith("- "):
            items.append([text[2:]])
        elif items:
            items[-1].append(text)
        else:
            items.append([text])
    return [words.display(" ".join(item)) for item in items]


def card(entry, family, rows=None) -> dict:
    """One entry as card data. `rows` are the family's edges (`graph.edges`), computed when absent."""
    rows = graph.edges(family.entries()) if rows is None else rows
    by_id = family.by_id()
    sections = entry.sections()
    files = []
    if entry.at("formal.file"):
        files.append({"kind": "lean", "path": entry.at("formal.file")})
    for item in entry.front.get("evidence") or []:
        if item["kind"] in CARD_EVIDENCE_KINDS:
            files.append({"kind": item["kind"], "path": item["path"]})
    links = []
    for direction, kind, other in graph.neighbours(rows, entry.id):
        found = by_id.get(other)
        if found is None and not family_mod.held(family.private is not None, by_id.get, other):
            raise CheckError(f"I8 links: {entry.rel}: field '{kind}': {other} is in neither ledger")
        links.append({
            "direction": direction,
            "kind": kind,
            "id": other,
            "status": found.status if found is not None else family_mod.HELD,
            "title": found.title if found is not None else None,
        })
    return {
        "id": entry.id,
        "status": entry.status,
        "kind": entry.kind,
        "title": entry.title,
        "cite_with": list(schema.citation_words(entry.status)),
        "statement": words.display(sections.get("Statement", "")),
        "hypotheses": hypotheses(sections.get("Hypotheses", "")),
        "aka": list(entry.front.get("aka") or []),
        "decl": entry.at("formal.decl"),
        "files": files,
        "links": links,
        "cited_by": list(entry.front.get("cited_by") or []),
    }


def _link_text(link: dict) -> str:
    title = f" {link['title']}" if link["title"] else ""
    if link["direction"] == "out":
        return f"{link['kind']} {link['id']} ({link['status']}){title}"
    return f"{link['id']} {link['kind']} this ({link['status']}){title}"


def _files_text(data: dict) -> str:
    return f"{data['status']}: " + "; ".join(f"{f['kind']} {f['path']}" for f in data["files"])


def _hypothesis_label(text: str, n: int) -> tuple[str, str]:
    """('H1', rest) when the item opens with its own label, else (f'H{n}', text)."""
    head, _, rest = text.partition(" ")
    if head.rstrip(".") and head.rstrip(".")[0] == "H" and head.rstrip(".")[1:].isdigit():
        return head.rstrip("."), rest
    return f"H{n}", text


def render_entry(data: dict, markdown: bool = False, width: int | None = None) -> list[str]:
    """The card as text lines for a terminal, or (`markdown`) as bullets for a generated page.

    `width` cuts the Statement and each hypothesis to that many characters, which is
    how a query hit stays short; the single-ID view and the consumer page pass none.
    The markdown form leaves `cited_by` out: the consumer page lists its own citing
    lines beside the card.
    """

    def fit(text: str) -> str:
        return words.cut(text, width) if width else text

    if markdown:
        return _markdown(data, fit)
    lines = [f"{data['id']}  {data['status']}  {data['title']}"]

    def row(label: str, value: str) -> None:
        lines.append(f"  {label:<{LABEL_WIDTH}}{value}")

    words_needed = data["cite_with"]
    row("cite with", f"one of {', '.join(words_needed)}" if words_needed else "the ID alone (settled)")
    if data["statement"]:
        row("statement", fit(data["statement"]))
    for n, item in enumerate(data["hypotheses"], start=1):
        label, rest = _hypothesis_label(item, n)
        row(label, fit(rest))
    if data["aka"]:
        row("aka", "; ".join(data["aka"]))
    if data["decl"]:
        row("lean", data["decl"])
    if data["files"]:
        row("files", _files_text(data))
    for link in data["links"]:
        row("link", _link_text(link))
    if data["cited_by"]:
        row("cited by", "; ".join(data["cited_by"]))
    return lines


def _markdown(data: dict, fit) -> list[str]:
    lines = []
    if data["cite_with"]:
        lines.append("- **Cite with.** one of " + ", ".join(f"`{w}`" for w in data["cite_with"]))
    if data["statement"]:
        lines.append(f"- **Statement.** {fit(data['statement'])}")
    if data["hypotheses"]:
        lines.append("- **Hypotheses.**")
        lines += [f"  - {fit(item)}" for item in data["hypotheses"]]
    if data["aka"]:
        lines.append("- **Also known as.** " + "; ".join(data["aka"]))
    if data["decl"]:
        lines.append(f"- **Lean.** `{data['decl']}`")
    if data["files"]:
        lines.append(f"- **Files.** {data['status']}: "
                     + "; ".join(f"{f['kind']} `{f['path']}`" for f in data["files"]))
    for link in data["links"]:
        lines.append(f"- **Linked.** {_link_text(link)}")
    return lines
