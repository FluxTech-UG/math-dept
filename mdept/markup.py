"""The markdown an entry body uses, rendered to HTML with its math left for KaTeX.

An entry body is a small dialect: paragraphs, bullet and numbered lists (nested by
indentation), `###` headings, block quotes, fenced code, inline code, bold and
italic, `[text](url)` links, and LaTeX in `$...$` and `$$...$$`. This module renders
exactly that, with no third-party markdown package, because a general renderer
treats LaTeX as markdown: `_` and `*` inside a formula become emphasis and the
formula is destroyed before KaTeX ever sees it.

The rule that makes it safe is order. Code spans and math spans are cut out of
the text first and kept verbatim (HTML-escaped, delimiters intact, so the KaTeX
auto-render script in the page finds them); only the text between them is read as
markdown. Every other character is escaped, so no raw HTML from an entry reaches
the page.

A math delimiter without its partner is an error (`MarkupError`), not literal
text: KaTeX would swallow the rest of the paragraph into one broken formula, and
the page would read as rendered while showing nonsense. An escaped dollar `\\$` is
a literal dollar sign and is emitted inside its own element, which keeps the
auto-render script from pairing it with a delimiter.
"""

from __future__ import annotations

import html
import re
from typing import Callable

from . import MDeptError, parse, schema


class MarkupError(MDeptError):
    """A body could not be rendered as written. The message says what and where."""


#: A list item marker: indentation, then `-`, `*`, `+` or `1.` / `1)`, then a space.
LIST_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>[-*+]|(?P<number>\d{1,9})[.)])[ \t]+")
HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>.*?)[ \t#]*$")
FENCE_RE = re.compile(r"^[ \t]*(```|~~~)")
QUOTE_RE = re.compile(r"^[ \t]*>[ \t]?")
LINK_RE = re.compile(r"\[(?P<text>[^\]\n]+)\]\((?P<url>[^)\s]+)\)")
#: Link targets a body may use: a web address, a page-relative path, or a fragment.
SAFE_URL_RE = re.compile(r"^(https?://|#|[A-Za-z0-9_./-]+$)")
BOLD_RE = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
ITALIC_STAR_RE = re.compile(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])")
ITALIC_UNDERSCORE_RE = re.compile(r"(?<![\w])_(?=\S)(.+?)(?<=\S)_(?![\w])")
#: Placeholder for a protected span. NUL never occurs in an entry file.
_SLOT = "\x00{}\x00"
_SLOT_RE = re.compile("\x00(\\d+)\x00")
#: Characters a backslash makes literal outside math (CommonMark's punctuation subset).
ESCAPABLE = set("\\`*_{}[]()#+-.!|>~")


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def render(text: str, link_id: Callable[[str], str]) -> str:
    """HTML for a markdown body. `link_id(ID)` returns the markup for one `MD_####` token."""
    lines = parse.strip_html_comments(text).splitlines()
    return "\n".join(_blocks(lines, link_id))


def render_inline(text: str, link_id: Callable[[str], str]) -> str:
    """HTML for one run of inline markdown (a title, a list item, a paragraph)."""
    return _Inline(link_id).render(text)


# --- blocks ---------------------------------------------------------------


def _blocks(lines: list[str], link_id) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if FENCE_RE.match(line):
            i = _fence(lines, i, out)
            continue
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group("hashes"))
            out.append(f"<h{level}>{render_inline(heading.group('text'), link_id)}</h{level}>")
            i += 1
            continue
        if LIST_RE.match(line):
            i = _list(lines, i, out, link_id)
            continue
        if QUOTE_RE.match(line):
            quoted = []
            while i < len(lines) and lines[i].strip() and QUOTE_RE.match(lines[i]):
                quoted.append(QUOTE_RE.sub("", lines[i], count=1))
                i += 1
            out.append("<blockquote>" + "\n".join(_blocks(quoted, link_id)) + "</blockquote>")
            continue
        if line.strip().startswith("$$") and _opens_display_block(line):
            i = _display_block(lines, i, out, link_id)
            continue
        i = _paragraph(lines, i, out, link_id)
    return out


def _fence(lines: list[str], i: int, out: list[str]) -> int:
    marker = FENCE_RE.match(lines[i]).group(1)
    body = []
    j = i + 1
    while j < len(lines) and not lines[j].strip().startswith(marker):
        body.append(lines[j])
        j += 1
    if j == len(lines):
        raise MarkupError(f"a code fence opened with {marker} on line {i + 1} is never closed")
    out.append("<pre><code>" + html.escape("\n".join(body)) + "</code></pre>")
    return j + 1


def _opens_display_block(line: str) -> bool:
    """True when a line starting with `$$` opens a display block that runs past it."""
    return line.strip().count("$$") % 2 == 1


def _display_block(lines: list[str], i: int, out: list[str], link_id) -> int:
    """`$$` alone (or opening) on a line, closed on a later line: one display formula."""
    body = [lines[i]]
    j = i + 1
    while j < len(lines):
        body.append(lines[j])
        if lines[j].count("$$") % 2 == 1:
            break
        j += 1
    else:
        raise MarkupError(f"a display formula opened with $$ on line {i + 1} is never closed")
    out.append(f'<div class="math-display">{render_inline(chr(10).join(body), link_id)}</div>')
    return j + 1


def _starts_block(line: str) -> bool:
    """A line that ends a paragraph without a blank line before it."""
    return bool(FENCE_RE.match(line) or HEADING_RE.match(line) or QUOTE_RE.match(line)
                or _interrupting_item(line))


def _interrupting_item(line: str) -> bool:
    """A list item that may interrupt a paragraph: a bullet, or a numbered item starting at 1."""
    match = LIST_RE.match(line)
    if match is None:
        return False
    return match.group("number") is None or match.group("number") == "1"


def _paragraph(lines: list[str], i: int, out: list[str], link_id) -> int:
    body = [lines[i].strip()]
    j = i + 1
    while j < len(lines) and lines[j].strip() and not _starts_block(lines[j]):
        body.append(lines[j].strip())
        j += 1
    out.append(f"<p>{render_inline(chr(10).join(body), link_id)}</p>")
    return j


def _sibling(line: str, base: int, ordered: bool) -> re.Match | None:
    """The marker match when `line` is another item of the list at indentation `base`."""
    match = LIST_RE.match(line.expandtabs(4))
    if (match is not None and len(match.group("indent")) == base
            and (match.group("number") is not None) == ordered):
        return match
    return None


def _list(lines: list[str], i: int, out: list[str], link_id) -> int:
    first = LIST_RE.match(lines[i].expandtabs(4))
    base = len(first.group("indent"))
    ordered = first.group("number") is not None
    items: list[list[str]] = []
    content = base  # the current item's content column
    j = i
    while j < len(lines):
        line = lines[j].expandtabs(4)
        match = _sibling(line, base, ordered)
        if match is not None:
            items.append([line[match.end():]])
            content = match.end()
            j += 1
            continue
        if not line.strip():
            k = j
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k < len(lines) and indent_of(lines[k].expandtabs(4)) > base:
                items[-1].append("")  # a blank line inside the item (a loose item)
                j += 1
                continue
            if k < len(lines) and _sibling(lines[k], base, ordered) is not None:
                j = k
                continue
            break
        width = indent_of(line)
        if width > base:
            items[-1].append(line[min(width, content):])  # an indented continuation or a nested list
            j += 1
            continue
        if items[-1][-1].strip() and not _starts_block(line):
            items[-1].append(line.strip())  # a lazy continuation line
            j += 1
            continue
        break
    tag = "ol" if ordered else "ul"
    start = int(first.group("number")) if ordered else 1
    attrs = f' start="{start}"' if ordered and start != 1 else ""
    rendered = []
    for item in items:
        inner = _blocks(item, link_id)
        if "" not in item:
            # A tight item (no blank line inside) keeps its text out of paragraph tags.
            inner = [b[3:-4] if b.startswith("<p>") and b.endswith("</p>") else b for b in inner]
        rendered.append("<li>" + "\n".join(inner) + "</li>")
    out.append(f"<{tag}{attrs}>" + "".join(rendered) + f"</{tag}>")
    return j


# --- inline ---------------------------------------------------------------


class _Inline:
    """One inline run: protect code and math, then read the rest as markdown."""

    def __init__(self, link_id):
        self.link_id = link_id
        self.slots: list[str] = []

    def _keep(self, markup: str) -> str:
        self.slots.append(markup)
        return _SLOT.format(len(self.slots) - 1)

    def render(self, text: str) -> str:
        protected = self._protect(text)
        protected = LINK_RE.sub(self._link, protected)
        protected = BOLD_RE.sub(r"<strong>\1</strong>", protected)
        protected = ITALIC_STAR_RE.sub(r"<em>\1</em>", protected)
        protected = ITALIC_UNDERSCORE_RE.sub(r"<em>\1</em>", protected)
        # Slots nest (a link's text may hold math), so restore until none is left.
        while _SLOT_RE.search(protected):
            protected = _SLOT_RE.sub(lambda m: self.slots[int(m.group(1))], protected)
        return protected

    def _protect(self, text: str) -> str:
        """Escape the text, with code, math, escapes and entry IDs moved into slots."""
        out: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == "\\" and i + 1 < n and text[i + 1] == "$":
                out.append(self._keep('<span class="dollar">$</span>'))
                i += 2
            elif c == "\\" and i + 1 < n and text[i + 1] in ESCAPABLE:
                out.append(self._keep(html.escape(text[i + 1])))
                i += 2
            elif c == "`":
                end = text.find("`", i + 1)
                if end == -1:
                    out.append(html.escape(c))
                    i += 1
                else:
                    out.append(self._keep(f"<code>{html.escape(text[i + 1:end])}</code>"))
                    i = end + 1
            elif text.startswith("$$", i):
                end = _closing(text, i + 2, "$$")
                if end == -1:
                    raise MarkupError(f"unclosed $$ in: {_snippet(text, i)}")
                out.append(self._keep(html.escape(text[i:end + 2], quote=False)))
                i = end + 2
            elif c == "$":
                end = _closing(text, i + 1, "$")
                if end == -1:
                    raise MarkupError(f"unclosed $ in: {_snippet(text, i)}")
                out.append(self._keep(html.escape(text[i:end + 1], quote=False)))
                i = end + 1
            else:
                match = schema.ID_TOKEN_RE.match(text, i)
                if match and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] == "_")):
                    out.append(self._keep(self.link_id(match.group(0))))
                    i = match.end()
                else:
                    out.append(html.escape(c, quote=False))
                    i += 1
        return "".join(out)

    def _link(self, match: re.Match) -> str:
        url = html.unescape(match.group("url"))
        if not SAFE_URL_RE.match(url):
            raise MarkupError(f"link target {url!r} is neither a web address nor a relative path")
        text = match.group("text")
        return self._keep(f'<a href="{html.escape(url)}">{text}</a>')


def _closing(text: str, start: int, delimiter: str) -> int:
    """Index of the delimiter that closes a math span opened before `start`, or -1.

    Inside math a backslash escapes the next character (`\\$` is a dollar sign in
    the formula), and a single `$` never closes on the first half of a `$$`.
    """
    i = start
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text.startswith(delimiter, i):
            if delimiter == "$" and text.startswith("$$", i):
                return -1
            return i
        i += 1
    return -1


def _snippet(text: str, at: int, width: int = 60) -> str:
    return repr(text[max(0, at - 20):at + width])
