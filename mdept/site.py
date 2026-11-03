"""The reading site: one HTML page per ledger entry, and an index, built from the ledger.

Run:

    python -m mdept.site --repo . --out build/site
    python -m mdept.site --repo . --check

The ledger is written for the validator and for an agent that already knows an ID;
this is its human face. Each entry page carries the Statement and Hypotheses (LaTeX
rendered by KaTeX from a pinned CDN build), the status, the `In plain words` section
with its review badge, the entry's neighbourhood graph as inline SVG, links to its
source, proof, counterexample and Lean files, where it is cited, its figure when one
was drawn, and the comment routes. The index counts entries by status and filters the
full table by status, topic and text. Plain HTML and one stylesheet, no build step.

Two builds, chosen by the repo `--repo` names:

- The public build (from `math-dept`) shows the public ledger only. An ID it holds no
  entry for is unreleased (`family.held`), and its pages name it as such without a link.
  Its provenance is abstract: the repos that cite an entry by name, never a consumer's
  document path, anchor or request token.
- The private build (from `math-dept-private`) shows both ledgers, read through
  `family.load_family`: the private `ledger.json` lists only the private entries. It
  adds the private provenance fields and marks every unreleased entry.

Both builds read the settings in `site.toml` at the root of the public checkout this
package was installed from (`config.package_root`), so the GitHub coordinates, the
comment label and the giscus values have one home.

`--check` builds into a temporary directory and fails on anything a reader would meet
as a broken page: a body the markup cannot render (an unclosed `$`), a missing
Statement or Hypotheses, a `plain_words_checked` date with no section to have checked,
a figure that is not SVG, an unbalanced tag, or a link inside the site to a file the
build did not write. The output carries no timestamp, so two builds of one ledger are
byte-identical.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
import tempfile
import tomllib
import urllib.parse
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from . import CheckError, ConfigError, MDeptError
from . import config, markup, parse, schema
from . import family as family_mod
from .figures import FIGURES_DIR, figure_path

CONFIG_NAME = "site.toml"
#: A giscus value still to be filled starts with this word.
PLACEHOLDER = "FILL"
GISCUS_KEYS = ("repo", "repo_id", "category", "category_id")
GITHUB_KEYS = ("owner", "public_repo", "private_repo", "branch")
COMMENT_KEYS = ("label",)

KATEX_VERSION = "0.16.11"
KATEX_BASE = f"https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist"
GISCUS_CLIENT = "https://giscus.app/client.js"

STYLESHEET = "site.css"
INDEX_PAGE = "index.html"
#: The file that marks a directory as a build output, so `--out` never clears a stranger's folder.
MARKER = ".mdept-site"
#: The issue title carries the entry ID and the start of its title, cut at a word boundary.
ISSUE_TITLE_WIDTH = 60

#: How each link field reads from the entry that carries it (first) and from the entry it
#: names (second). The graph draws every edge from the page's own entry, in these words.
RELATION_WORDS = {
    "between.below_of": ("implied by", "implies"),
    "between.above_of": ("implies", "implied by"),
    "between.special_case_of": ("special case of", "generalizes"),
    "between.generalizes": ("generalizes", "special case of"),
    "revises": ("revises", "revised by"),
    "merged_into": ("merged into", "merged from"),
}
REFUTED_BY = "refuted by"

#: The order the body sections appear in on a page; any other heading follows these.
SECTION_ORDER = ("Statement", "Hypotheses", schema.PLAIN_WORDS_HEADING)
#: Sections every entry carries before the page can be built (I3 requires them too).
REQUIRED_SECTIONS = ("Statement", "Hypotheses")


# --- settings -------------------------------------------------------------


@dataclass(frozen=True)
class SiteConfig:
    """The settings in `site.toml`. `giscus` is None until every value is filled."""

    owner: str
    public_repo: str
    private_repo: str
    branch: str
    comment_label: str
    giscus: dict | None

    def blob_url(self, private: bool, rel: str) -> str:
        repo = self.private_repo if private else self.public_repo
        return f"https://github.com/{self.owner}/{repo}/blob/{self.branch}/{urllib.parse.quote(rel)}"

    @property
    def issue_repo(self) -> str:
        """The private repo as `owner/name`, the form `gh --repo` takes."""
        return f"{self.owner}/{self.private_repo}"

    @property
    def new_issue_url(self) -> str:
        return f"https://github.com/{self.issue_repo}/issues/new"


def default_config_path() -> Path:
    return config.package_root() / CONFIG_NAME


def _table(data: dict, name: str, keys: tuple[str, ...], path: Path) -> dict:
    table = data.get(name)
    if not isinstance(table, dict):
        raise ConfigError(f"{path}: the [{name}] table is missing")
    unknown = sorted(set(table) - set(keys))
    missing = [k for k in keys if k not in table]
    if unknown or missing:
        raise ConfigError(f"{path}: [{name}] takes exactly {list(keys)}; "
                          f"missing {missing}, unknown {unknown}")
    for key in keys:
        if not isinstance(table[key], str) or not table[key].strip():
            raise ConfigError(f"{path}: [{name}] {key} must be a non-empty string")
    return table


def load_config(path: Path | None = None) -> SiteConfig:
    """Read and validate `site.toml`. A half-filled giscus table is an error."""
    path = Path(path) if path is not None else default_config_path()
    if not path.is_file():
        raise ConfigError(f"{path} is missing; the site settings live in the public repo's {CONFIG_NAME}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    unknown = sorted(set(data) - {"github", "comments", "giscus"})
    if unknown:
        raise ConfigError(f"{path}: unknown tables {unknown}")
    github = _table(data, "github", GITHUB_KEYS, path)
    comments = _table(data, "comments", COMMENT_KEYS, path)
    giscus = _table(data, "giscus", GISCUS_KEYS, path)
    filled = [k for k in GISCUS_KEYS if not giscus[k].startswith(PLACEHOLDER)]
    if filled and len(filled) != len(GISCUS_KEYS):
        pending = [k for k in GISCUS_KEYS if k not in filled]
        raise ConfigError(f"{path}: [giscus] is half filled: {filled} set, {pending} still {PLACEHOLDER}; "
                          "fill all four from giscus.app or none")
    return SiteConfig(
        owner=github["owner"], public_repo=github["public_repo"],
        private_repo=github["private_repo"], branch=github["branch"],
        comment_label=comments["label"], giscus=dict(giscus) if filled else None,
    )


# --- the ledger as the site sees it ---------------------------------------


@dataclass
class Ledger:
    """The entries one build shows, and how an ID resolves in it."""

    kind: str
    entries: list
    private_ids: frozenset
    roots: dict  # "public" / "private" -> Path
    resolve: object = field(repr=False)
    incoming: dict = field(default_factory=dict, repr=False)

    @property
    def private(self) -> bool:
        return self.kind == "private"

    def is_private_entry(self, entry) -> bool:
        return entry.id in self.private_ids

    def held(self, entry_id: str) -> bool:
        return family_mod.held(self.private, self.resolve, entry_id)

    def root_of(self, entry) -> Path:
        return self.roots["private" if self.is_private_entry(entry) else "public"]


def load_ledger(root: Path) -> Ledger:
    root = Path(root).resolve()
    kind = config.repo_kind(root)
    if kind == "public":
        entries = parse.load_entries(root)
        own = {e.id: e for e in entries}
        ledger = Ledger(kind=kind, entries=entries, private_ids=frozenset(), roots={"public": root},
                        resolve=family_mod.resolver(False, own, None))
    else:
        family = family_mod.load_family(root)
        if family.public is None:
            raise ConfigError(f"{root}: the private build shows both ledgers and no public sibling "
                              f"was found; set {config.PUBLIC_ENV} or repos.yaml public_sibling")
        public = family.public.entries()
        private = family.private.entries()
        both = {e.id for e in public} & {e.id for e in private}
        if both:
            raise CheckError(f"site: {root}: field '<ledger>': {sorted(both)} sit in both ledgers; "
                             "a released entry leaves the private ledger")
        entries = sorted(public + private, key=lambda e: e.id)
        by_id = {e.id: e for e in entries}
        ledger = Ledger(kind=kind, entries=entries, private_ids=frozenset(e.id for e in private),
                        roots={"public": family.public.root, "private": family.private.root},
                        resolve=family_mod.resolver(True, by_id, lambda: by_id))
    for entry in ledger.entries:
        for fieldname, targets in _links(entry).items():
            for target in targets:
                ledger.incoming.setdefault(target, []).append((entry.id, fieldname))
    return ledger


def _links(entry) -> dict[str, list[str]]:
    """The entry's link fields the graph draws (`provenance.connects` is prose, not an edge)."""
    return {name: ids for name, ids in entry.linked_ids().items() if name in RELATION_WORDS}


@dataclass(frozen=True)
class Neighbour:
    relation: str
    label: str
    href: str | None
    css: str


def neighbourhood(ledger: Ledger, entry, cfg: SiteConfig) -> list[Neighbour]:
    """Every entry one link away, and every counterexample script, in the page entry's words."""
    seen: dict[tuple[str, str], Neighbour] = {}

    def add(target: str, relation: str) -> None:
        node = ledger.resolve(target)
        if node is not None:
            item = Neighbour(relation, f"{target} {node.status}", f"{target}.html", f"st-{node.status}")
        elif ledger.held(target):
            item = Neighbour(relation, f"{target} unreleased", None, "held")
        else:
            raise CheckError(f"site: {entry.rel}: field '{relation}': {target} resolves to no entry")
        seen.setdefault((target, relation), item)

    for fieldname, targets in _links(entry).items():
        for target in targets:
            add(target, RELATION_WORDS[fieldname][0])
    for source, fieldname in ledger.incoming.get(entry.id, []):
        add(source, RELATION_WORDS[fieldname][1])
    ordered = sorted(seen.values(), key=lambda n: (n.relation, n.label))
    for item in entry.front.get("evidence") or []:
        if item["kind"] == "counterexample":
            href = cfg.blob_url(ledger.is_private_entry(entry), item["path"])
            ordered.append(Neighbour(REFUTED_BY, Path(item["path"]).name, href, "script"))
    return ordered


def plain_words_state(entry) -> tuple[str, str | None]:
    """('pending', None), ('unreviewed', None) or ('reviewed', date) for the plain-words section."""
    text = entry.sections().get(schema.PLAIN_WORDS_HEADING, "").strip()
    checked = entry.front.get("plain_words_checked")
    if not text:
        if checked is not None:
            raise CheckError(f"site: {entry.rel}: field 'plain_words_checked': {checked} names a review "
                             f"of a '## {schema.PLAIN_WORDS_HEADING}' section the entry does not carry")
        return "pending", None
    if checked is None:
        return "unreviewed", None
    return "reviewed", checked


# --- the graph ------------------------------------------------------------

GRAPH_WIDTH = 480
NODE_HEIGHT = 42
ROW = 52
CENTRE_WIDTH = 150
SIDE_X = 236
SIDE_WIDTH = GRAPH_WIDTH - SIDE_X - 4
#: The width of one character of a node's ID line, for cutting a long script name to fit.
NODE_CHAR_WIDTH = 7.6


def graph_svg(entry, neighbours: list[Neighbour]) -> str:
    """The neighbourhood as inline SVG: the entry on the left, one row per neighbour on the right."""
    rows = len(neighbours)
    height = max(rows * ROW, NODE_HEIGHT) + 8
    cy = height / 2
    parts = [
        f'<svg class="graph" viewBox="0 0 {GRAPH_WIDTH} {height}" role="img" '
        f'aria-labelledby="graph-title-{entry.id}" xmlns="http://www.w3.org/2000/svg">',
        f'<title id="graph-title-{entry.id}">{entry.id} and the entries and scripts linked to it</title>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" '
        'class="arrowhead"/></marker></defs>',
    ]
    for k, item in enumerate(neighbours):
        ny = 4 + k * ROW + NODE_HEIGHT / 2
        parts.append(f'<line class="edge" x1="{4 + CENTRE_WIDTH}" y1="{cy:g}" x2="{SIDE_X - 2}" '
                     f'y2="{ny:g}" marker-end="url(#arrow)"/>')
    parts.append(_node(4, cy - NODE_HEIGHT / 2, CENTRE_WIDTH, entry.status, entry.id, "",
                       f"st-{entry.status} self", None))
    for k, item in enumerate(neighbours):
        ident, _, rest = item.label.partition(" ")
        parts.append(_node(SIDE_X, 4 + k * ROW, SIDE_WIDTH, item.relation, ident, rest,
                           item.css, item.href))
    parts.append("</svg>")
    return "\n".join(parts)


def _fit(text: str, width: float) -> str:
    """`text` cut to what a node of `width` holds at the graph's font size, marked when cut."""
    room = int((width - 16) / NODE_CHAR_WIDTH)
    return text if len(text) <= room else text[:room - 3] + "..."


def _node(x: float, y: float, width: float, relation: str, ident: str, detail: str,
          css: str, href: str | None) -> str:
    """One box: a small upper line (the relation, or the page entry's status), the ID below it."""
    text_x = x + 8
    label = html.escape(_fit(ident, width)) + (
        f' <tspan class="detail">{html.escape(detail)}</tspan>' if detail else "")
    body = (f'<g class="node {css}"><title>{html.escape(" ".join(filter(None, (relation, ident, detail))))}'
            f'</title><rect x="{x:g}" y="{y:g}" width="{width:g}" height="{NODE_HEIGHT}" rx="6"/>'
            f'<text class="rel" x="{text_x:g}" y="{y + 15:g}">{html.escape(relation)}</text>'
            f'<text class="id" x="{text_x:g}" y="{y + 33:g}">{label}</text></g>')
    if href is None:
        return body
    return f'<a href="{html.escape(href)}">{body}</a>'


# --- pages ----------------------------------------------------------------


def _id_link(ledger: Ledger, entry_id: str) -> str:
    if ledger.resolve(entry_id) is not None:
        return f'<a class="idref" href="{entry_id}.html">{entry_id}</a>'
    if ledger.held(entry_id):
        return f'<span class="idref held" title="{html.escape(family_mod.HELD)}">{entry_id}</span>'
    raise CheckError(f"site: field '<MD token>': {entry_id} resolves to no entry")


def _render_section(ledger: Ledger, entry, name: str, text: str) -> str:
    try:
        return markup.render(text, lambda token: _id_link(ledger, token))
    except markup.MarkupError as exc:
        raise CheckError(f"site: {entry.rel}: field '## {name}': {exc}") from exc
    except CheckError as exc:
        raise CheckError(f"{exc} (in {entry.rel}, ## {name})") from exc


def _head(title: str, math: bool) -> list[str]:
    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(title)}</title>",
        f'<link rel="stylesheet" href="{STYLESHEET}">',
    ]
    if math:
        lines += [
            f'<link rel="stylesheet" href="{KATEX_BASE}/katex.min.css">',
            f'<script defer src="{KATEX_BASE}/katex.min.js"></script>',
            f'<script defer src="{KATEX_BASE}/contrib/auto-render.min.js"></script>',
        ]
    lines.append("</head>")
    return lines


MATH_SCRIPT = """<script>
document.addEventListener("DOMContentLoaded", function () {
  if (!window.renderMathInElement) return;
  renderMathInElement(document.querySelector("main"), {
    delimiters: [
      {left: "$$", right: "$$", display: true},
      {left: "\\\\[", right: "\\\\]", display: true},
      {left: "$", right: "$", display: false},
      {left: "\\\\(", right: "\\\\)", display: false}
    ],
    throwOnError: false
  });
});
</script>"""


def _site_name(ledger: Ledger) -> str:
    return "math-dept, private view" if ledger.private else "math-dept"


def _banner(ledger: Ledger) -> str:
    note = "both ledgers, unreleased entries included" if ledger.private else "the public ledger"
    return (f'<header class="top"><a class="home" href="{INDEX_PAGE}">{_site_name(ledger)}</a>'
            f'<span class="scope">{note}</span></header>')


FOOTER = ('<footer>Generated by <code>python -m mdept.site</code> from the ledger entries; '
          "every page is rebuilt from the source, so edit the entry, never the page.</footer>")


def _badge(status: str) -> str:
    return f'<span class="badge st-{status}">{html.escape(status)}</span>'


def _plain_words_badge(state: str, date: str | None) -> str:
    if state == "reviewed":
        return f'<span class="badge pw-reviewed">reviewed {html.escape(date)}</span>'
    return f'<span class="badge pw-{state}">{"unreviewed" if state == "unreviewed" else "pending"}</span>'


def _issue_link(cfg: SiteConfig, entry) -> str:
    short = entry.title if len(entry.title) <= ISSUE_TITLE_WIDTH else (
        entry.title[:ISSUE_TITLE_WIDTH].rsplit(" ", 1)[0] + "...")
    body = (f"Entry: {entry.id} ({entry.title})\n"
            f"Status when this comment was written: {entry.status}\n\n"
            "Comment:\n\n")
    query = urllib.parse.urlencode(
        {"title": f"{entry.id}: {short}", "labels": cfg.comment_label, "body": body},
        quote_via=urllib.parse.quote)
    return f"{cfg.new_issue_url}?{query}"


def _giscus(cfg: SiteConfig, entry) -> str:
    g = cfg.giscus
    attrs = {
        "src": GISCUS_CLIENT, "data-repo": g["repo"], "data-repo-id": g["repo_id"],
        "data-category": g["category"], "data-category-id": g["category_id"],
        "data-mapping": "specific", "data-term": entry.id, "data-strict": "1",
        "data-reactions-enabled": "0", "data-emit-metadata": "0", "data-input-position": "bottom",
        "data-theme": "preferred_color_scheme", "data-lang": "en", "data-loading": "lazy",
        "crossorigin": "anonymous",
    }
    rendered = " ".join(f'{k}="{html.escape(v)}"' for k, v in attrs.items())
    return f'<div class="giscus"></div>\n<script {rendered} async></script>'


def _comments(ledger: Ledger, cfg: SiteConfig, entry) -> list[str]:
    lines = ['<section id="comments"><h2>Comments</h2>',
             f'<p><a class="button" href="{html.escape(_issue_link(cfg, entry))}">Leave a note for the '
             f"maintainers</a> opens a new issue in the private tracker "
             f"({html.escape(cfg.issue_repo)}), prefilled with this entry. It needs access to that "
             "repo; the notes are filed into the department's working queue.</p>"]
    if not ledger.private:
        if cfg.giscus is None:
            lines.append('<p class="pending-discussion">Public discussion is not open yet.</p>')
        else:
            lines.append(_giscus(cfg, entry))
    lines.append("</section>")
    return lines


def _files(ledger: Ledger, cfg: SiteConfig, entry) -> list[str]:
    private = ledger.is_private_entry(entry)
    rows = [("entry source", entry.rel)]
    formal = entry.front.get("formal") or {}
    if formal.get("file"):
        rows.append((f"Lean, {formal['decl']}", formal["file"]))
    for item in entry.front.get("evidence") or []:
        rows.append((item["kind"], item["path"]))
    out = ['<section id="files"><h2>Files</h2><ul class="files">']
    for label, rel in rows:
        out.append(f'<li><span class="file-kind">{html.escape(label)}</span> '
                   f'<a href="{html.escape(cfg.blob_url(private, rel))}"><code>{html.escape(rel)}</code></a></li>')
    source = entry.front.get("source")
    if source:
        out.append(f'<li><span class="file-kind">source</span> {html.escape(source)}, see '
                   f'<a href="{html.escape(cfg.blob_url(False, "bibliography.md"))}">the bibliography</a></li>')
    out.append("</ul></section>")
    return out


def _provenance(ledger: Ledger, entry) -> list[str]:
    """Who raised, stipulated and settled the entry. The public build leaves out the application's
    document, anchor and rationale and the request token: those stay in the private view.

    A `merged` entry may omit raised_by and stipulated_by (the schema), so its section points at
    the entry it merged into, which carries them, and keeps only the settled row of the merge."""
    prov = entry.front["provenance"]
    out = ['<section id="provenance"><h2>Provenance</h2>']
    rows = []
    if entry.status == "merged":
        target = entry.front["merged_into"]
        if target is None:
            raise CheckError(f"site: {entry.rel}: field 'merged_into': a merged entry names the entry "
                             "it merged into")
        out.append(f"<p>Merged into {_id_link(ledger, target)}, which carries the provenance.</p>")
    else:
        raised = prov["raised_by"]
        rows.append(("raised by", f"{raised['repo']}: {raised['domain']}"))
        if ledger.private:
            for key in ("doc", "anchor", "application"):
                if raised[key]:
                    rows.append((key, str(raised[key])))
        shown = schema.STIPULATED_BY_KEYS if ledger.private else tuple(
            k for k in schema.STIPULATED_BY_KEYS if k != "request")
        rows.append(("stipulated", _credit(prov["stipulated_by"], shown)))
    settled = prov["settled_by"]
    if settled:
        rows.append(("settled", _credit(settled, ("who", "date", "how", "checked_by", "model"))))
    if not rows:
        out.append("</section>")
        return out
    out.append('<dl class="prov">')
    for key, value in rows:
        out.append(f"<dt>{html.escape(key)}</dt><dd>{html.escape(value)}</dd>")
    out.append("</dl></section>")
    return out


def _credit(record: dict, keys: tuple[str, ...]) -> str:
    return ", ".join(f"{k.replace('_', ' ')} {record[k]}" for k in keys if record.get(k))


def _cited_by(ledger: Ledger, entry) -> list[str]:
    """The consumer documents that cite the entry. The public build names the citing repos only,
    once each: a consumer's document path and anchor stay in the private view."""
    cited = entry.front["cited_by"]
    out = ['<section id="cited"><h2>Cited by</h2>']
    if not cited:
        out.append("<p>No consumer document cites this entry yet.</p>")
    else:
        if not ledger.private:
            repos = []
            for citation in cited:
                parts = schema.split_cited_by(citation)
                if parts is None:
                    raise CheckError(f"site: {entry.rel}: field 'cited_by': {citation!r} is not of the "
                                     "form 'Repo:path §n'")
                repos.append(parts[0])
            cited = list(dict.fromkeys(repos))
        out.append("<ul>" + "".join(f"<li><code>{html.escape(c)}</code></li>" for c in cited) + "</ul>")
    out.append("</section>")
    return out


def figure_source(ledger: Ledger, entry) -> Path | None:
    path = figure_path(ledger.root_of(entry), entry.id)
    if not path.is_file():
        return None
    head = path.read_text(encoding="utf-8")[:200].lstrip()
    if not (head.startswith("<?xml") or head.startswith("<svg")):
        raise CheckError(f"site: {path}: field '<figure>': not an SVG file")
    return path


def render_entry(ledger: Ledger, cfg: SiteConfig, entry) -> str:
    sections = entry.sections()
    for name in REQUIRED_SECTIONS:
        if not sections.get(name, "").strip():
            raise CheckError(f"site: {entry.rel}: field '## {name}': the section is missing or empty")
    state, date = plain_words_state(entry)
    title = f"{entry.id}: {entry.title}"
    out = _head(f"{title} | {_site_name(ledger)}", math=True)
    out += ["<body>", _banner(ledger), "<main>",
            f'<p class="crumbs"><a href="{INDEX_PAGE}">All entries</a></p>',
            f'<h1><span class="id">{entry.id}</span> {html.escape(entry.title)}</h1>']
    meta = [_badge(entry.status), html.escape(entry.kind)]
    if ledger.private and ledger.is_private_entry(entry):
        meta.append('<span class="badge unreleased">unreleased</span>')
    topics = " ".join(f'<a class="topic" href="{INDEX_PAGE}?topic={html.escape(t)}">{html.escape(t)}</a>'
                      for t in entry.front.get("topics") or [])
    out.append(f'<p class="meta">{" ".join(meta)} <span class="topics">{topics}</span></p>')
    aka = entry.front.get("aka") or []
    if aka:
        out.append('<p class="aka">Also known as: ' + "; ".join(html.escape(a) for a in aka) + "</p>")

    for name in ("Statement", "Hypotheses"):
        out.append(f'<section id="{_slug(name)}"><h2>{name}</h2>'
                   f"{_render_section(ledger, entry, name, sections[name])}</section>")
    heading = schema.PLAIN_WORDS_HEADING
    out.append(f'<section id="plain-words"><h2>{heading} {_plain_words_badge(state, date)}</h2>')
    if state == "pending":
        out.append('<p class="placeholder">Plain words pending: the paragraph for readers who skip the '
                   "Statement has not been written for this entry yet.</p>")
    else:
        out.append(_render_section(ledger, entry, heading, sections[heading]))
        if state == "unreviewed":
            out.append('<p class="note">Drafted by an agent and not yet reviewed; the Statement is '
                       "the authority.</p>")
    out.append("</section>")

    if figure_source(ledger, entry) is not None:
        out.append(f'<figure><img src="{FIGURES_DIR}/{entry.id}.svg" alt="Figure for {entry.id}, drawn by '
                   f'its counterexample script"><figcaption>Drawn by the counterexample script listed '
                   "under Files.</figcaption></figure>")

    neighbours = neighbourhood(ledger, entry, cfg)
    out.append('<section id="graph"><h2>Neighbourhood</h2>')
    out.append(graph_svg(entry, neighbours) if neighbours else
               "<p>No other entry links to this one, and it links to none.</p>")
    out.append("</section>")

    for name, text in sections.items():
        if name in SECTION_ORDER:
            continue
        out.append(f'<section id="{_slug(name)}"><h2>{html.escape(name)}</h2>'
                   f"{_render_section(ledger, entry, name, text)}</section>")
    out += _files(ledger, cfg, entry)
    out += _provenance(ledger, entry)
    out += _cited_by(ledger, entry)
    out += _comments(ledger, cfg, entry)
    out += ["</main>", FOOTER, MATH_SCRIPT, "</body>", "</html>"]
    return "\n".join(out) + "\n"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# --- the index ------------------------------------------------------------


INDEX_SCRIPT = """<script>
(function () {
  var rows = Array.prototype.slice.call(document.querySelectorAll("#entries tbody tr"));
  var status = document.getElementById("f-status"), topic = document.getElementById("f-topic");
  var text = document.getElementById("f-text"), shown = document.getElementById("shown");
  var params = new URLSearchParams(window.location.search);
  if (params.get("status")) status.value = params.get("status");
  if (params.get("topic")) topic.value = params.get("topic");
  function apply() {
    var s = status.value, t = topic.value, q = text.value.trim().toLowerCase(), n = 0;
    rows.forEach(function (row) {
      var ok = (!s || row.dataset.status === s) &&
               (!t || (" " + row.dataset.topics + " ").indexOf(" " + t + " ") >= 0) &&
               (!q || row.dataset.text.indexOf(q) >= 0);
      row.hidden = !ok;
      if (ok) n += 1;
    });
    shown.textContent = n + " of " + rows.length + " entries";
  }
  document.querySelectorAll("[data-status-chip]").forEach(function (chip) {
    chip.addEventListener("click", function () {
      status.value = status.value === chip.dataset.statusChip ? "" : chip.dataset.statusChip;
      apply();
    });
  });
  [status, topic].forEach(function (el) { el.addEventListener("change", apply); });
  text.addEventListener("input", apply);
  apply();
})();
</script>"""


def render_index(ledger: Ledger, cfg: SiteConfig) -> str:
    entries = ledger.entries
    counts = {s: sum(1 for e in entries if e.status == s) for s in schema.STATUSES}
    topics: dict[str, int] = {}
    for entry in entries:
        for topic in entry.front.get("topics") or []:
            topics[topic] = topics.get(topic, 0) + 1
    out = _head(_site_name(ledger), math=False)
    out += ['<body class="index">', _banner(ledger), "<main>", f"<h1>{_site_name(ledger)}</h1>"]
    out.append("<p>Each entry is one mathematical statement that sits between a published result and an "
               "application of it, with its status and how it was settled. Open an entry for its "
               "statement, a paragraph in plain words, and the entries it links to. The status words "
               f'are defined in the <a href="{html.escape(cfg.blob_url(False, "README.md"))}">README</a>.</p>')
    out.append('<div class="chips">' + "".join(
        f'<button type="button" class="badge st-{s}" data-status-chip="{s}">{s} {n}</button>'
        for s, n in counts.items() if n) + "</div>")
    options = "".join(f'<option value="{s}">{s} ({n})</option>' for s, n in counts.items() if n)
    topic_options = "".join(f'<option value="{html.escape(t)}">{html.escape(t)} ({n})</option>'
                            for t, n in sorted(topics.items()))
    out.append('<form class="filters" onsubmit="return false">'
               f'<label>Status <select id="f-status"><option value="">all</option>{options}</select></label>'
               f'<label>Topic <select id="f-topic"><option value="">all</option>{topic_options}</select></label>'
               '<label>Text <input id="f-text" type="search" placeholder="ID, title or name"></label>'
               f'</form><p id="shown" class="shown">{len(entries)} entries</p>')
    out.append('<table id="entries"><thead><tr><th>ID</th><th>Entry</th><th>Status</th>'
               "<th>Topics</th><th>Plain words</th></tr></thead><tbody>")
    for entry in entries:
        aka = entry.front.get("aka") or []
        state, date = plain_words_state(entry)
        searchable = " ".join([entry.id, entry.title, *aka]).lower()
        unreleased = (' <span class="badge unreleased">unreleased</span>'
                      if ledger.private and ledger.is_private_entry(entry) else "")
        aka_line = (f'<div class="aka">{"; ".join(html.escape(a) for a in aka)}</div>' if aka else "")
        entry_topics = entry.front.get("topics") or []
        out.append(
            f'<tr data-status="{entry.status}" data-topics="{html.escape(" ".join(entry_topics))}" '
            f'data-text="{html.escape(searchable)}">'
            f'<td class="id"><a href="{entry.id}.html">{entry.id}</a>{unreleased}</td>'
            f'<td><a href="{entry.id}.html">{html.escape(entry.title)}</a>{aka_line}</td>'
            f"<td>{_badge(entry.status)}</td>"
            f'<td class="topics">{html.escape(", ".join(entry_topics))}</td>'
            f'<td data-label="plain words">{_plain_words_badge(state, date)}</td></tr>')
    out.append("</tbody></table>")
    out += ["</main>", FOOTER, INDEX_SCRIPT, "</body>", "</html>"]
    return "\n".join(out) + "\n"


# --- the stylesheet -------------------------------------------------------

STYLESHEET_TEXT = """:root {
  --bg: #fbfbf9; --fg: #1d1f21; --muted: #5f6368; --rule: #d9d9d4; --card: #ffffff;
  --link: #1f5fa8; --code-bg: #f0f0ec;
  --proven-formal: #1e7a3c; --proven-informal: #4b8b2a; --cited: #2a62a8;
  --conjectured: #a86b00; --open: #8a5a00; --refuted: #b3261e; --merged: #6b6b6b;
  --held: #7a7a7a; --script: #6a4c9c; --unreviewed: #a86b00; --pending: #6b6b6b; --reviewed: #1e7a3c;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #15171a; --fg: #e6e6e3; --muted: #a0a4a8; --rule: #33363b; --card: #1d2024;
    --link: #8ab8f0; --code-bg: #24272c;
    --proven-formal: #5cc77f; --proven-informal: #9ccf6a; --cited: #7fb0f0;
    --conjectured: #e0a841; --open: #d9a050; --refuted: #f08a80; --merged: #a0a0a0;
    --held: #9a9a9a; --script: #b89ae6; --unreviewed: #e0a841; --pending: #a0a0a0; --reviewed: #5cc77f;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
a { color: var(--link); }
code { background: var(--code-bg); padding: 0 .25em; border-radius: 3px; font-size: .92em;
  overflow-wrap: anywhere; }
pre { background: var(--code-bg); padding: .75em; overflow-x: auto; }
header.top { display: flex; flex-wrap: wrap; gap: .25em 1em; align-items: baseline;
  padding: .6em 16px; border-bottom: 1px solid var(--rule); }
header.top .home { font-weight: 600; text-decoration: none; }
header.top .scope { color: var(--muted); font-size: .9em; }
main { max-width: 52rem; margin: 0 auto; padding: 0 16px 2em; }
body.index main { max-width: 72rem; }
footer { max-width: 52rem; margin: 0 auto; padding: 1em 16px 2em; color: var(--muted);
  font-size: .85em; border-top: 1px solid var(--rule); }
h1 { font-size: 1.45em; line-height: 1.3; margin: .4em 0; }
h1 .id { color: var(--muted); font-weight: 500; margin-right: .3em; }
h2 { font-size: 1.1em; margin: 1.6em 0 .4em; padding-bottom: .2em; border-bottom: 1px solid var(--rule); }
section { overflow-x: auto; }
.crumbs { margin: .8em 0 0; font-size: .9em; }
.meta { display: flex; flex-wrap: wrap; gap: .4em; align-items: center; color: var(--muted); }
.topic { font-size: .85em; margin-right: .4em; }
.aka { color: var(--muted); font-size: .92em; }
.badge { display: inline-block; font-size: .78em; font-weight: 600; line-height: 1.4;
  padding: .05em .55em; border-radius: 999px; border: 1px solid currentColor; white-space: nowrap;
  background: transparent; }
.st-proven-formal { color: var(--proven-formal); } .st-proven-informal { color: var(--proven-informal); }
.st-cited { color: var(--cited); } .st-conjectured { color: var(--conjectured); }
.st-open { color: var(--open); } .st-refuted { color: var(--refuted); } .st-merged { color: var(--merged); }
.unreleased, .held { color: var(--held); }
.pw-unreviewed { color: var(--unreviewed); } .pw-pending { color: var(--pending); }
.pw-reviewed { color: var(--reviewed); }
.placeholder, .note, .pending-discussion { color: var(--muted); font-style: italic; }
.math-display { overflow-x: auto; }
span.idref.held { border-bottom: 1px dotted var(--held); }
figure { margin: 1.4em 0; } figure img { max-width: 100%; height: auto; background: #fff; }
figcaption { color: var(--muted); font-size: .88em; }
svg.graph { width: 100%; max-width: 480px; height: auto; display: block; }
svg.graph .edge { stroke: var(--muted); stroke-width: 1.4; fill: none; }
svg.graph .arrowhead { fill: var(--muted); }
svg.graph .node rect { fill: var(--card); stroke: currentColor; stroke-width: 1.5; }
svg.graph .node.self rect { stroke-width: 2.5; }
svg.graph .node.held rect { stroke-dasharray: 4 3; }
svg.graph .node.script { color: var(--script); }
svg.graph text { fill: var(--fg); font-size: 13px; }
svg.graph text.rel { fill: var(--muted); font-size: 11px; }
svg.graph text.id { font-weight: 600; }
svg.graph tspan.detail { fill: currentColor; font-weight: 500; font-size: 11px; }
svg.graph a:hover rect { stroke-width: 2.5; }
ul.files { padding-left: 1.1em; } .file-kind { color: var(--muted); font-size: .9em; }
dl.prov { display: grid; grid-template-columns: max-content 1fr; gap: .2em 1em; }
dl.prov dt { color: var(--muted); } dl.prov dd { margin: 0; overflow-wrap: anywhere; }
a.button { font-weight: 600; }
.chips { display: flex; flex-wrap: wrap; gap: .4em; margin: 1em 0; }
.chips button { cursor: pointer; font: inherit; font-size: .85em; }
.filters { display: flex; flex-wrap: wrap; gap: .6em 1.2em; margin: .5em 0; }
.filters label { font-size: .9em; color: var(--muted); }
.filters select, .filters input { font: inherit; font-size: .95em; margin-left: .3em; max-width: 14em; }
.shown { color: var(--muted); font-size: .88em; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; vertical-align: top; padding: .45em .5em; border-bottom: 1px solid var(--rule); }
th { font-size: .85em; color: var(--muted); font-weight: 600; }
td.id .badge { display: block; width: max-content; margin-top: .3em; }
td.id { white-space: nowrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .9em; }
td.topics { color: var(--muted); font-size: .85em; }
@media (max-width: 640px) {
  table, tbody, tr, td { display: block; width: 100%; }
  thead { display: none; }
  tr { border-bottom: 1px solid var(--rule); padding: .4em 0; }
  td { border: 0; padding: .1em 0; }
  td[data-label]::before { content: attr(data-label) ": "; color: var(--muted); font-size: .85em; }
}
"""


# --- the build and its check ----------------------------------------------


class _TagBalance(HTMLParser):
    """Records the first unbalanced tag and every internal link target."""

    VOID = {"meta", "link", "br", "img", "input", "hr", "path"}

    def __init__(self):
        super().__init__()
        self.stack: list[str] = []
        self.problem: str | None = None
        self.targets: list[str] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.targets.append(value)
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.targets.append(value)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.problem = self.problem or f"</{tag}> closes {self.stack[-1] if self.stack else 'nothing'}"
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()


def _verify(out: Path) -> None:
    """Every page balanced, every link inside the site pointing at a file the build wrote."""
    for page in sorted(out.glob("*.html")):
        parser = _TagBalance()
        parser.feed(page.read_text(encoding="utf-8"))
        parser.close()
        if parser.problem or parser.stack:
            raise CheckError(f"site: {page.name}: field '<html>': "
                             f"{parser.problem or 'unclosed ' + ', '.join(parser.stack)}")
        for target in parser.targets:
            parsed = urllib.parse.urlparse(target)
            if parsed.scheme or target.startswith("#") or target.startswith("//"):
                continue
            if not (out / parsed.path).is_file():
                raise CheckError(f"site: {page.name}: field '<link>': {target} names no file the build wrote")


def build(root: Path, out: Path, cfg: SiteConfig) -> dict:
    """Write the site into `out` (which is cleared first only if an earlier build made it)."""
    out = Path(out)
    if out.exists():
        if any(out.iterdir()) and not (out / MARKER).is_file():
            raise ConfigError(f"{out} holds files no earlier site build wrote; choose an empty directory")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    ledger = load_ledger(root)
    figures = 0
    for entry in ledger.entries:
        (out / f"{entry.id}.html").write_text(render_entry(ledger, cfg, entry), encoding="utf-8")
        figure = figure_source(ledger, entry)
        if figure is not None:
            (out / FIGURES_DIR).mkdir(exist_ok=True)
            shutil.copyfile(figure, out / FIGURES_DIR / figure.name)
            figures += 1
    (out / INDEX_PAGE).write_text(render_index(ledger, cfg), encoding="utf-8")
    (out / STYLESHEET).write_text(STYLESHEET_TEXT, encoding="utf-8")
    (out / MARKER).write_text("written by python -m mdept.site; the next build clears this directory\n",
                              encoding="utf-8")
    _verify(out)
    return {"kind": ledger.kind, "entries": len(ledger.entries), "figures": figures}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.site", description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=None,
                        help="the repo to build from (default: nearest ancestor with ledger/)")
    parser.add_argument("--config", default=None,
                        help=f"the settings file (default: {CONFIG_NAME} in the public checkout)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--out", help="write the site into this directory")
    mode.add_argument("--check", action="store_true",
                      help="build into a temporary directory and fail on any broken page")
    args = parser.parse_args(argv)
    try:
        root = config.find_repo_root(args.repo)
        cfg = load_config(args.config)
        if args.check:
            with tempfile.TemporaryDirectory() as tmp:
                report = build(root, Path(tmp) / "site", cfg)
        else:
            report = build(root, Path(args.out), cfg)
    except MDeptError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    where = "checked" if args.check else f"written to {args.out}"
    print(f"ok site {where}: {report['entries']} entry pages, the index, "
          f"{report['figures']} figures [{report['kind']} build]")
    return 0


if __name__ == "__main__":
    # Dispatch to the canonical module, as `mdept.check` does, so classes are not duplicated.
    from mdept.site import main as _main

    raise SystemExit(_main())
