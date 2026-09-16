"""Read the markdown surfaces: ledger entries, bibliography, requests, role lines.

Parsing raises on malformed input rather than returning a partial object. A file
that cannot be parsed is reported with its path; the caller never has to guess
whether an empty result means "absent" or "broken".
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import CheckError
from . import schema

#: Directories no scan descends into.
IGNORE_DIRS = frozenset(
    {".git", ".lake", "lake-packages", "__pycache__", ".pytest_cache", ".venv", "node_modules", "build", "dist"}
)

#: Generated or template markdown that carries placeholder IDs by design.
PLACEHOLDER_MD = ("ledger/TEMPLATE.md", "inbox/TEMPLATE.md")

#: The closed key set of one `repos.yaml` consumer, and where its view lands.
CONSUMER_KEYS = ("path", "ignore", "view")
DEFAULT_VIEW = "docs/MATH.md"

FRONT_MATTER_RE = re.compile(r"\A---\r?\n(?P<front>.*?)\r?\n---\r?\n(?P<body>.*)\Z", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)
ROLE_LINE_RE = re.compile(
    r"^<!--\s*role:\s*(?P<role>[a-z]+)\s*\|\s*status:\s*current\s+(?P<date>\d{4}-\d{2}-\d{2})\s*(?P<rest>\|.*)?-->\s*$"
)
BIB_HEADING_RE = re.compile(r"^###\s+\[(?P<tag>[A-Za-z0-9][A-Za-z0-9+._-]*)\]\s*(?P<title>.*?)\s*$")
BIB_FIELD_RE = re.compile(r"^-\s+\*\*(?P<key>[^:*]+):\*\*\s*(?P<value>.*?)\s*$")

ROLES = ("contract", "mechanism", "record", "plan", "runbook", "generated", "human")


# --- front matter -----------------------------------------------------------


def split_front_matter(text: str, path: Path) -> tuple[str, str]:
    """Return (front matter source, body). Raises when the fence is absent."""
    match = FRONT_MATTER_RE.match(text)
    if match is None:
        raise CheckError(f"I3 schema: {path}: field '<front matter>': no leading '---' YAML front matter block")
    return match.group("front"), match.group("body")


def load_front_matter(path: Path) -> tuple[dict, str, str]:
    """Return (front mapping, front source, body) for a markdown file."""
    text = Path(path).read_text(encoding="utf-8")
    front_text, body = split_front_matter(text, path)
    try:
        front = yaml.safe_load(front_text)
    except yaml.YAMLError as exc:
        raise CheckError(f"I3 schema: {path}: field '<front matter>': invalid YAML ({exc})") from exc
    if not isinstance(front, dict):
        raise CheckError(f"I3 schema: {path}: field '<front matter>': expected a mapping, got {type(front).__name__}")
    return normalize_dates(front), front_text, body


def normalize_dates(node):
    """Render YAML's own date type back to an ISO string, recursively.

    An unquoted `2026-09-04` in front matter is loaded by PyYAML as a
    `datetime.date`, so the schema would see an object where it expects a
    string and the generated JSON would not serialize. Normalizing here keeps
    the authored form in the template plain and unquoted, which is what an
    author writing by hand does anyway. A `datetime.datetime` is deliberately
    left alone: a timestamp is not a ledger date, and the schema says so.
    """
    if isinstance(node, dict):
        return {key: normalize_dates(value) for key, value in node.items()}
    if isinstance(node, list):
        return [normalize_dates(value) for value in node]
    if isinstance(node, datetime.date) and not isinstance(node, datetime.datetime):
        return node.isoformat()
    return node


# --- ledger entries ---------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    """One ledger entry: its path, its front matter, and its body."""

    path: Path
    root: Path
    front: dict
    front_text: str
    body: str

    @property
    def id(self) -> str:
        return self.front["id"]

    @property
    def status(self) -> str:
        return self.front["status"]

    @property
    def kind(self) -> str:
        return self.front["kind"]

    @property
    def title(self) -> str:
        return self.front["title"]

    @property
    def rel(self) -> str:
        return str(self.path.relative_to(self.root))

    def at(self, dotted: str):
        """Nested lookup by dotted path, returning None at the first null."""
        node = self.front
        for part in dotted.split("."):
            if not isinstance(node, dict) or node.get(part) is None:
                return None
            node = node[part]
        return node

    def linked_ids(self) -> dict[str, list[str]]:
        """Every outgoing MD_#### link, grouped by the field that carries it."""
        links: dict[str, list[str]] = {}
        between = self.front.get("between") or {}
        for relation in schema.RELATIONS:
            values = between.get(relation) or []
            if values:
                links[f"between.{relation}"] = list(values)
        for single in ("revises", "merged_into"):
            value = self.front.get(single)
            if value:
                links[single] = [value]
        connects = ((self.front.get("provenance") or {}).get("connects")) or []
        tokens = [t for c in connects for t in schema.ID_TOKEN_RE.findall(str(c))]
        if tokens:
            links["provenance.connects"] = tokens
        return links

    def sections(self) -> dict[str, str]:
        return body_sections(self.body)


def entry_paths(root: Path) -> list[Path]:
    """Every `ledger/MD_####.md` under `root`, sorted. TEMPLATE.md is not an entry."""
    ledger = Path(root) / "ledger"
    if not ledger.is_dir():
        raise CheckError(f"I1 filename: {root}: field '<ledger>': no 'ledger/' directory")
    return sorted(p for p in ledger.glob("*.md") if p.name not in ("TEMPLATE.md", "INDEX.md"))


def load_entries(root: Path) -> list[Entry]:
    """Load every entry under `root/ledger/`, sorted by filename."""
    root = Path(root).resolve()
    entries = []
    for path in entry_paths(root):
        front, front_text, body = load_front_matter(path)
        entries.append(Entry(path=path, root=root, front=front, front_text=front_text, body=body))
    return entries


def body_sections(body: str) -> dict[str, str]:
    """Split a body into `## Heading` -> text. Deeper headings stay in the section."""
    sections: dict[str, str] = {}
    matches = [m for m in HEADING_RE.finditer(body) if len(m.group(1)) == 2]
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[match.group(2)] = body[match.end() : end].strip()
    return sections


# --- bibliography -----------------------------------------------------------


@dataclass(frozen=True)
class BibEntry:
    tag: str
    title: str
    fields: dict
    line: int

    @property
    def source_kind(self) -> str | None:
        return (self.fields.get("Kind") or "").strip() or None


def parse_bibliography(path: Path) -> dict[str, BibEntry]:
    """Tag -> entry, from `### [Tag] Title` blocks. HTML comments are not entries."""
    path = Path(path)
    if not path.is_file():
        raise CheckError(f"I10 cited source: {path}: field '<bibliography>': file does not exist")
    text = strip_html_comments(path.read_text(encoding="utf-8"))
    entries: dict[str, BibEntry] = {}
    current: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        heading = BIB_HEADING_RE.match(line)
        if heading:
            tag = heading.group("tag")
            if tag in entries:
                raise CheckError(
                    f"I11 tag sync: {path}: field '[{tag}]': tag appears twice "
                    f"(lines {entries[tag].line} and {number})"
                )
            entries[tag] = BibEntry(tag=tag, title=heading.group("title"), fields={}, line=number)
            current = tag
            continue
        if line.startswith("#"):
            current = None
            continue
        field_match = BIB_FIELD_RE.match(line)
        if field_match and current is not None:
            entries[current].fields[field_match.group("key").strip()] = field_match.group("value")
    return entries


# --- requests (private repo) ------------------------------------------------


@dataclass(frozen=True)
class Request:
    path: Path
    root: Path
    front: dict
    body: str
    closed: bool

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def state(self) -> str:
        return self.front.get("state")

    @property
    def rel(self) -> str:
        return str(self.path.relative_to(self.root))

    def candidates(self) -> list[str]:
        """The `### C<n>` headings this request offers."""
        return [m.group(2).split()[0] for m in HEADING_RE.finditer(self.body)
                if len(m.group(1)) == 3 and re.match(r"^C\d+\b", m.group(2))]

    def outcome(self) -> str:
        return body_sections(self.body).get("Outcome", "")

    def outcome_line(self, candidate: str) -> str | None:
        """The Outcome line for one candidate, or None when it has none."""
        for line in self.outcome().splitlines():
            stripped = line.strip().lstrip("-*").strip()
            if stripped.startswith(candidate) and (
                len(stripped) == len(candidate) or not stripped[len(candidate)].isdigit()
            ):
                return line
        return None


def load_requests(root: Path) -> list[Request]:
    """Every request in `inbox/` and `inbox/done/`. Empty when there is no inbox."""
    root = Path(root).resolve()
    inbox = root / "inbox"
    if not inbox.is_dir():
        return []
    requests = []
    for path in sorted(list(inbox.glob("*.md")) + list((inbox / "done").glob("*.md"))):
        if path.name == "TEMPLATE.md":
            continue
        front, _, body = load_front_matter(path)
        requests.append(
            Request(path=path, root=root, front=front, body=body, closed=path.parent.name == "done")
        )
    return requests


# --- generic helpers --------------------------------------------------------


def strip_html_comments(text: str) -> str:
    return HTML_COMMENT_RE.sub("", text)


def iter_markdown(root: Path, exclude: tuple[str, ...] = ()) -> list[Path]:
    """Every .md file under `root`, sorted, skipping IGNORE_DIRS and `exclude` prefixes."""
    root = Path(root).resolve()
    found = []
    for path in sorted(root.rglob("*.md")):
        if any(part in IGNORE_DIRS for part in path.relative_to(root).parts):
            continue
        rel = str(path.relative_to(root))
        if any(rel == prefix or rel.startswith(prefix.rstrip("/") + "/") for prefix in exclude):
            continue
        found.append(path)
    return found


def id_tokens(text: str) -> set[str]:
    """Every MD_#### token, with HTML comments removed first."""
    return set(schema.ID_TOKEN_RE.findall(strip_html_comments(text)))


def request_tokens(text: str) -> set[tuple[str, str]]:
    """Every (request stem, candidate) pair from MDR: tokens."""
    return set(schema.REQUEST_TOKEN_RE.findall(strip_html_comments(text)))


def request_stem_tokens(text: str) -> list[tuple[int, str, str | None]]:
    """Every MDR: token with its line and candidate, the candidate optional.

    `request_tokens` reads the citing form a consumer commits to, `MDR:<stem>#C2`,
    which is the one I12 resolves. This reads the looser thing a document may
    actually carry, a bare `MDR:<stem>` naming the whole request, because the
    generated consumer view has to report what is written rather than only what
    is well formed.
    """
    found = []
    for number, line in enumerate(strip_html_comments(text).splitlines(), start=1):
        for match in schema.REQUEST_STEM_TOKEN_RE.finditer(line):
            found.append((number, match.group("stem"), match.group("candidate")))
    return found


def parse_role_line(path: Path) -> tuple[str, str]:
    """Return (role, status date) from line 2 of a doc. Raises when it is absent."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise CheckError(f"I19 attempt record: {path}: field '<role line>': file has no line 2")
    match = ROLE_LINE_RE.match(lines[1].strip())
    if match is None:
        raise CheckError(
            f"I19 attempt record: {path}: field '<role line>': line 2 is not a role line "
            "'<!-- role: ... | status: current YYYY-MM-DD | ... -->'"
        )
    role = match.group("role")
    if role not in ROLES:
        raise CheckError(f"I19 attempt record: {path}: field '<role line>': role {role!r} is not one of {list(ROLES)}")
    return role, match.group("date")


def load_repos_yaml(path: Path) -> dict:
    """Load `repos.yaml`: a `public_sibling` path and the `consumers` map.

    A consumer's value is either a bare path or a mapping `{path, ignore, view}`.
    The bare form means `{path: <it>, ignore: [], view: 'docs/MATH.md'}`, so both
    forms come back normalized and no caller has to test which was written.
    """
    path = Path(path)
    if not path.is_file():
        raise CheckError(f"I7 raised-by: {path}: field '<repos.yaml>': file does not exist")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise CheckError(f"I7 raised-by: {path}: field '<repos.yaml>': expected a mapping")
    unknown = sorted(set(data) - {"public_sibling", "consumers"})
    if unknown:
        raise CheckError(f"I7 raised-by: {path}: field '<repos.yaml>': unknown key(s) {unknown}")
    consumers = data.get("consumers") or {}
    if not isinstance(consumers, dict):
        raise CheckError(f"I7 raised-by: {path}: field 'consumers': expected a mapping of name to path")
    return {
        "public_sibling": data.get("public_sibling"),
        "consumers": {name: _consumer_entry(path, name, value) for name, value in consumers.items()},
    }


def _consumer_entry(path: Path, name: str, value) -> dict:
    if isinstance(value, str):
        value = {"path": value}
    if not isinstance(value, dict):
        raise CheckError(
            f"I7 raised-by: {path}: field 'consumers.{name}': expected a path or a mapping "
            f"of {list(CONSUMER_KEYS)}, got {type(value).__name__}"
        )
    unknown = sorted(set(value) - set(CONSUMER_KEYS))
    if unknown:
        raise CheckError(f"I7 raised-by: {path}: field 'consumers.{name}': unknown key(s) {unknown}")
    if not value.get("path"):
        raise CheckError(f"I7 raised-by: {path}: field 'consumers.{name}.path': a consumer declares a path")
    ignore = value.get("ignore") or []
    if not isinstance(ignore, list) or not all(isinstance(glob, str) for glob in ignore):
        raise CheckError(
            f"I7 raised-by: {path}: field 'consumers.{name}.ignore': expected a list of glob strings"
        )
    return {
        "path": str(value["path"]),
        "ignore": [str(glob) for glob in ignore],
        "view": str(value.get("view") or DEFAULT_VIEW),
    }
