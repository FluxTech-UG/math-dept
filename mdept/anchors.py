"""The anchor grammar: what a provenance anchor may say, and how it resolves.

An anchor names the place in a consumer document that raised a statement. Its
form is read off its own syntax, so the grammar is closed and nothing here has
to know which repo or which document is on the other end: `resolve` takes the
document's text, never its path.

Every form but the last names something the document itself treats as an
identifier, and an identifier outlives the wording around it. The `text:` form
names wording, which is the weakest thing to point at: a retitled heading
unanchors every entry that quoted it, silently, and the entries are found again
only by hand. It is kept for documents that have no ID space at all.

| Anchor | Form | Resolves at |
|---|---|---|
| `A8` | `item` | a line whose text, after list, heading or bold markup, begins `A8.` or `A8` then whitespace |
| `A8(c)` | `item` | the same rule, for a document whose items carry a letter part |
| `§21.3` | `heading` | a heading whose text begins `21.3` |
| `§5 item 20` | `heading-item` | the numbered item `20.` under the heading whose text begins `5` |
| `label:eq:gen-carnot-control` | `label` | `\\label{eq:gen-carnot-control}` |
| `text:"What the basilica cannot control for"` | `text` | that literal string, anywhere in the document |

An item ID matches as a whole token, so `A8` resolves at `A8.` and never at the
sub-item `A8(c).`; the sub-item is reached by anchoring `A8(c)` itself.

Every form but `text` must resolve exactly once. `matches` returns all of them
so the caller can tell "nowhere" from "in two places" and name the lines, and
an ambiguous anchor is as broken as an absent one: it does not say which place
raised the statement. A `text:` anchor takes its first occurrence, because a
phrase repeated in prose is one phrase.

Anything else is form `unknown`, which I7 fails on. `classify` never raises:
naming the failure is the caller's job, because `new` reports a form it does
not resolve and `check` resolves a form it must fail on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Every form `classify` can return. `unknown` is the one that has no resolver.
FORMS = ("item", "heading", "heading-item", "label", "text", "unknown")

#: The forms that must resolve exactly once.
UNIQUE_FORMS = ("item", "heading", "heading-item", "label")

#: One line of grammar, for an error message that has to teach it.
GRAMMAR = (
    "an anchor is `A8` (an item ID), `§21.3` (a numbered heading), "
    "`§5 item 20` (a numbered item under a heading), `label:eq:name` (a LaTeX label), "
    'or `text:"..."` (a literal string, for a document with no ID space)'
)

_ITEM_ID = r"[A-Za-z]{1,3}\d+(?:\([a-z]\))?"
_SECTION_ID = r"(?:[0-9]+|[A-Za-z][0-9]*)(?:\.[0-9A-Za-z]+)*"

ITEM_RE = re.compile(rf"^(?P<item>{_ITEM_ID})$")
HEADING_RE = re.compile(rf"^§\s*(?P<section>{_SECTION_ID})$")
HEADING_ITEM_RE = re.compile(rf"^§\s*(?P<section>{_SECTION_ID})\s+item\s+(?P<number>\d+)$")
LABEL_RE = re.compile(r"^label:(?P<name>[A-Za-z0-9][A-Za-z0-9:_.+-]*)$")
TEXT_RE = re.compile(r'^text:"(?P<text>.+)"$', re.DOTALL)

#: Markdown that sits in front of a line's own text: heading hashes, list
#: bullets, ordered-list numbers, block quotes, in any order and repeated.
_MARKUP_RE = re.compile(r"^\s*(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+|>\s*)+")
#: Emphasis and code markers that open a line's text.
_EMPHASIS_RE = re.compile(r"^(?:\*\*|__|\*|_|`)+")
#: A numbered list item, by its own marker rather than by its text.
_NUMBERED_RE = re.compile(r"^\s*(?P<number>\d+)[.)](?=\s|$)")
_HEADING_LINE_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.*?)\s*$")


@dataclass(frozen=True)
class Hit:
    """Where an anchor resolved: its form, the 1-based line, and that line."""

    form: str
    line: int
    text: str


def classify(anchor: str) -> str:
    """The form this anchor's syntax declares, or 'unknown'."""
    value = str(anchor).strip()
    if TEXT_RE.match(value):
        return "text"
    if LABEL_RE.match(value):
        return "label"
    if HEADING_ITEM_RE.match(value):
        return "heading-item"
    if HEADING_RE.match(value):
        return "heading"
    if ITEM_RE.match(value):
        return "item"
    return "unknown"


def matches(anchor: str, doc_text: str) -> list[Hit]:
    """Every place this anchor resolves, in document order.

    Empty for an `unknown` form, and at most one element for `text`, whose rule
    is the first literal occurrence.
    """
    value = str(anchor).strip()
    form = classify(value)
    if form == "item":
        return _find_item(ITEM_RE.match(value).group("item"), doc_text)
    if form == "heading":
        return _find_heading(HEADING_RE.match(value).group("section"), doc_text)
    if form == "heading-item":
        found = HEADING_ITEM_RE.match(value)
        return _find_heading_item(found.group("section"), found.group("number"), doc_text)
    if form == "label":
        return _find_label(LABEL_RE.match(value).group("name"), doc_text)
    if form == "text":
        return _find_text(TEXT_RE.match(value).group("text"), doc_text)
    return []


def resolve(anchor: str, doc_text: str) -> Hit | None:
    """The one place this anchor resolves, or None when it is nowhere or ambiguous."""
    found = matches(anchor, doc_text)
    if len(found) == 1:
        return found[0]
    if found and classify(anchor) == "text":
        return found[0]
    return None


def line_text(line: str) -> str:
    """A line's own text, with list, heading, quote and emphasis markup removed."""
    stripped = line
    while True:
        shorter = _MARKUP_RE.sub("", stripped, count=1)
        shorter = _EMPHASIS_RE.sub("", shorter, count=1)
        shorter = shorter.lstrip()
        if shorter.startswith("§"):
            shorter = shorter[1:].lstrip()
        if shorter == stripped:
            return stripped.strip()
        stripped = shorter


def _begins_with_item(text: str, item: str) -> bool:
    """True when the line's text opens with this item ID as a whole token.

    The ID is followed by its own period or by whitespace, never by more of an
    identifier: `A8` opens `A8.` and `A8 wins`, and does not open the sub-item
    `A8(c).`, which is anchored as `A8(c)`.
    """
    if not text.startswith(item):
        return False
    rest = text[len(item):]
    return rest == "" or rest[0] == "." or rest[0].isspace()


def _find_item(item: str, doc_text: str) -> list[Hit]:
    found = []
    for number, line in enumerate(doc_text.splitlines(), start=1):
        if _begins_with_item(line_text(line), item):
            found.append(Hit(form="item", line=number, text=line.rstrip()))
    return found


def _begins_with_section(text: str, section: str) -> bool:
    """True when the heading's text opens with this section id, whole.

    The id may not be continued by more of an id, so `21.3` matches neither the
    heading `21.30` nor `21.3.1`, and `21` does not match `21.3`. A trailing
    period is the ordinary markdown form (`## 5. Open items`) and is part of the
    heading's punctuation, not of the number, so it only continues the id when a
    digit or letter follows it.
    """
    if not text.startswith(section):
        return False
    rest = text[len(section):]
    if rest == "":
        return True
    if rest[0].isalnum():
        return False
    if rest[0] == ".":
        return not (len(rest) > 1 and rest[1].isalnum())
    return True


def _headings(doc_text: str):
    for number, line in enumerate(doc_text.splitlines(), start=1):
        found = _HEADING_LINE_RE.match(line)
        if found:
            text = found.group("text")
            if text.startswith("§"):
                text = text[1:].lstrip()
            yield number, len(found.group("hashes")), text, line


def _find_heading(section: str, doc_text: str) -> list[Hit]:
    return [
        Hit(form="heading", line=number, text=line.rstrip())
        for number, _level, text, line in _headings(doc_text)
        if _begins_with_section(text, section)
    ]


def _find_heading_item(section: str, wanted: str, doc_text: str) -> list[Hit]:
    lines = doc_text.splitlines()
    headings = list(_headings(doc_text))
    found = []
    for index, (number, level, text, _line) in enumerate(headings):
        if not _begins_with_section(text, section):
            continue
        end = len(lines)
        for later_number, later_level, _later_text, _later_line in headings[index + 1:]:
            if later_level <= level:
                end = later_number - 1
                break
        for offset in range(number, end):
            item = _NUMBERED_RE.match(lines[offset])
            if item and item.group("number") == wanted:
                found.append(Hit(form="heading-item", line=offset + 1, text=lines[offset].rstrip()))
    return found


def _find_label(name: str, doc_text: str) -> list[Hit]:
    pattern = re.compile(r"\\label\{\s*" + re.escape(name) + r"\s*\}")
    return [
        Hit(form="label", line=number, text=line.rstrip())
        for number, line in enumerate(doc_text.splitlines(), start=1)
        if pattern.search(line)
    ]


def _find_text(literal: str, doc_text: str) -> list[Hit]:
    position = doc_text.find(literal)
    if position < 0:
        return []
    number = doc_text.count("\n", 0, position) + 1
    return [Hit(form="text", line=number, text=doc_text.splitlines()[number - 1].rstrip())]
