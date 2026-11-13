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

from . import CheckError, ConfigError
from . import schema

#: Directories no scan descends into.
IGNORE_DIRS = frozenset(
    {".git", ".lake", "lake-packages", "__pycache__", ".pytest_cache", ".venv", "node_modules", "build", "dist"}
)

#: Generated or template markdown that carries placeholder IDs by design.
PLACEHOLDER_MD = ("ledger/TEMPLATE.md", "inbox/TEMPLATE.md")

#: The markdown under `ledger/` that is not an entry: the template and the generated views.
LEDGER_VIEW_NAMES = ("TEMPLATE.md", "INDEX.md", "CATALOG.md")
#: A topic file of the catalog once it is split past its budget (`mdept.catalog`).
CATALOG_TOPIC_RE = re.compile(r"^CATALOG-[a-z0-9]+(-[a-z0-9]+)*\.md$")


def is_ledger_view(name: str) -> bool:
    """True for a `ledger/` markdown file name that is the template or a generated view."""
    return name in LEDGER_VIEW_NAMES or CATALOG_TOPIC_RE.match(name) is not None

#: The closed key set of one `repos.yaml` consumer, and where its view lands.
CONSUMER_KEYS = ("path", "ignore", "view", "archived", "retired")
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
    """Every `ledger/MD_####.md` under `root`, sorted. The template and the views are not entries."""
    ledger = Path(root) / "ledger"
    if not ledger.is_dir():
        raise CheckError(f"I1 filename: {root}: field '<ledger>': no 'ledger/' directory")
    return sorted(p for p in ledger.glob("*.md") if not is_ledger_view(p.name))


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


# --- attempt records (private repo) -----------------------------------------

#: The attempts table's header: six cells, these two first and these two last.
ATTEMPTS_HEAD = ("Date", "Stage")
ATTEMPTS_TAIL = ("Time", "Model")
_SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")

#: The stage of a row recording an edit to an entry's Statement or Hypotheses, and
#: the stage of a statement round trip (`docs/triage.md`, section 1).
STATEMENT_STAGE = "statement"
FIDELITY_STAGE = "fidelity"


def table_cells(line: str) -> list[str] | None:
    """A markdown table line's cells, stripped, or None when the line is no table row."""
    body = line.strip()
    if not (body.startswith("|") and body.endswith("|")) or len(body) < 2:
        return None
    return [cell.strip() for cell in body[1:-1].split("|")]


def attempts_table(lines: list[str], where: str) -> tuple[int, int]:
    """(header index, index of the last line) of a record's one attempts table.

    The table is found by its header, wherever it sits: six cells with `Date` and
    `Stage` first and `Time` and `Model` last, then the separator line. Its last
    line is its last row, or the separator when it has none. A record without
    exactly one such table is refused, naming `where`.
    """
    heads = []
    for i, line in enumerate(lines[:-1]):
        cells = table_cells(line)
        if cells and len(cells) == 6 and tuple(cells[:2]) == ATTEMPTS_HEAD and tuple(cells[4:]) == ATTEMPTS_TAIL:
            sep = table_cells(lines[i + 1])
            if sep and len(sep) == 6 and all(_SEPARATOR_CELL_RE.match(c) for c in sep):
                heads.append(i)
    if len(heads) != 1:
        found = "no attempts table" if not heads else f"{len(heads)} attempts tables"
        raise CheckError(f"{where}: {found}; expected one table headed "
                         "`| Date | Stage | ... | ... | Time | Model |` with its separator line")
    end = heads[0] + 1
    while end + 1 < len(lines) and lines[end + 1].startswith("|"):
        end += 1
    return heads[0], end


def attempt_stages(path: Path, where: str) -> list[str]:
    """The Stage cell of every row of a record's attempts table, in table order."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    head, end = attempts_table(lines, where)
    return [table_cells(line)[1] for line in lines[head + 2:end + 1]]


def attempt_rows(path: Path, where: str) -> list[tuple[datetime.date, str]]:
    """(date, stage word) of every row of a record's attempts table, in table order.

    A Date cell that is not an ISO calendar date is refused, naming `where` and the cell.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    head, end = attempts_table(lines, where)
    rows = []
    for number, line in enumerate(lines[head + 2:end + 1], start=head + 3):
        cells = table_cells(line)
        if not schema.ISO_DATE_RE.match(cells[0]):
            raise CheckError(f"{where}:{number}: field 'Date': expected an ISO date YYYY-MM-DD, got {cells[0]!r}")
        try:
            day = datetime.date.fromisoformat(cells[0])
        except ValueError as exc:
            raise CheckError(f"{where}:{number}: field 'Date': {cells[0]!r} is not a real calendar date ({exc})") from exc
        rows.append((day, _stage_word(cells[1])))
    return rows


def _stage_word(stage: str) -> str:
    # Rows written before `mdept.row` held a stage to one word carry forms such as
    # `fidelity (steps 2 to 4)`; the first word is the stage.
    words = stage.split()
    return words[0] if words else ""


def stale_statement_row(stages: list[str]) -> int | None:
    """Index of the last `statement` row when no `fidelity` row follows it, else None.

    Table order is the order: rows carry dates only, and a day holds several rows.
    """
    words = [_stage_word(stage) for stage in stages]
    if STATEMENT_STAGE not in words:
        return None
    last = len(words) - 1 - words[::-1].index(STATEMENT_STAGE)
    return None if FIDELITY_STAGE in words[last + 1:] else last


def has_fidelity_row(stages: list[str]) -> bool:
    """True when some row of the table is a statement round trip."""
    return any(_stage_word(stage) == FIDELITY_STAGE for stage in stages)


def load_repos_yaml(path: Path) -> dict:
    """Load `repos.yaml`: a `public_sibling` path and the `consumers` map.

    A consumer's value is either a bare path, a mapping `{path, ignore, view,
    retired}`, or `{archived: <where>}` for a repo whose files are kept off-line.
    The bare form means `{path: <it>, ignore: [], view: 'docs/MATH.md', retired:
    false}`; `retired: true` marks a repo on disk that is read-only for good. The
    mapping's `path` is one path or a non-empty list of candidate paths, tried in
    order where the consumers are resolved (`family.read_consumers`). Every form
    comes back normalized with the same six keys: `paths` the candidates in order,
    `path` the first of them, `archived` None for a repo on disk, `retired` a
    bool, and for an archived one `path` None and `paths` empty, so no caller has
    to test which was written. An optional `baseline` list declares failures the
    consumers own (`_baseline_item`); it comes back as a list, empty when absent.
    """
    path = Path(path)
    if not path.is_file():
        raise CheckError(f"I7 raised-by: {path}: field '<repos.yaml>': file does not exist")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise CheckError(f"I7 raised-by: {path}: field '<repos.yaml>': expected a mapping")
    unknown = sorted(set(data) - {"public_sibling", "consumers", "baseline"})
    if unknown:
        raise CheckError(f"I7 raised-by: {path}: field '<repos.yaml>': unknown key(s) {unknown}")
    consumers = data.get("consumers") or {}
    if not isinstance(consumers, dict):
        raise CheckError(f"I7 raised-by: {path}: field 'consumers': expected a mapping of name to path")
    baseline = data.get("baseline") or []
    if not isinstance(baseline, list):
        raise ConfigError(f"{path}: field 'baseline': expected a list of items {list(BASELINE_KEYS)}")
    return {
        "public_sibling": data.get("public_sibling"),
        "consumers": {name: _consumer_entry(path, name, value) for name, value in consumers.items()},
        "baseline": [_baseline_item(path, i, item) for i, item in enumerate(baseline)],
    }


#: The closed key set of one `repos.yaml` baseline item, every key required.
BASELINE_KEYS = ("invariant", "file", "text", "reason", "since")
_INVARIANT_ID_RE = re.compile(r"^I\d+[ab]?$")


def _baseline_item(path: Path, index: int, item) -> dict:
    """One declared consumer-owned failure, normalized: every key a stripped string.

    `invariant` is an invariant ID (`I15`); `file` and `text` are literal
    substrings that pin the failure line without its line number; `reason` says
    in a sentence why the failure belongs to the consumer; `since` is the ISO
    date it was declared. `mdept.check` owns what the item means.
    """
    where = f"{path}: field 'baseline[{index}]'"
    if not isinstance(item, dict):
        raise ConfigError(f"{where}: expected a mapping of {list(BASELINE_KEYS)}, got {type(item).__name__}")
    unknown = sorted(set(item) - set(BASELINE_KEYS))
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {unknown}; an item carries {list(BASELINE_KEYS)}")
    normalized = {}
    for key in BASELINE_KEYS:
        value = item.get(key)
        if isinstance(value, datetime.date):
            value = value.isoformat()
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"{where}.{key}: required, a non-empty string; every item carries "
                              f"{list(BASELINE_KEYS)}")
        normalized[key] = value.strip()
    if not _INVARIANT_ID_RE.match(normalized["invariant"]):
        raise ConfigError(f"{where}.invariant: {normalized['invariant']!r} is not an invariant ID like I15")
    try:
        datetime.date.fromisoformat(normalized["since"])
    except ValueError:
        raise ConfigError(f"{where}.since: {normalized['since']!r} is not an ISO date") from None
    return normalized


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
    if "archived" in value:
        where = value["archived"]
        if not isinstance(where, str) or not where.strip():
            raise CheckError(
                f"I7 raised-by: {path}: field 'consumers.{name}.archived': "
                "expected a non-empty string saying where the archived repo is kept"
            )
        extra = sorted(set(value) - {"archived"})
        if extra:
            raise CheckError(
                f"I7 raised-by: {path}: field 'consumers.{name}': an archived consumer has no "
                f"tree on disk, so it takes no {extra}"
            )
        return {"path": None, "paths": [], "ignore": [], "view": DEFAULT_VIEW, "archived": where.strip(),
                "retired": False}
    if not value.get("path"):
        raise CheckError(
            f"I7 raised-by: {path}: field 'consumers.{name}.path': a consumer declares a path, "
            "or `archived` when its files are off-line"
        )
    candidates = value["path"] if isinstance(value["path"], list) else [value["path"]]
    if not all(isinstance(candidate, str) and candidate for candidate in candidates):
        raise CheckError(
            f"I7 raised-by: {path}: field 'consumers.{name}.path': expected a path or a non-empty "
            f"list of paths, got {value['path']!r}"
        )
    ignore = value.get("ignore") or []
    if not isinstance(ignore, list) or not all(isinstance(glob, str) for glob in ignore):
        raise CheckError(
            f"I7 raised-by: {path}: field 'consumers.{name}.ignore': expected a list of glob strings"
        )
    retired = value.get("retired", False)
    if not isinstance(retired, bool):
        raise CheckError(
            f"I7 raised-by: {path}: field 'consumers.{name}.retired': expected true or false, "
            f"got {retired!r}"
        )
    return {
        "path": candidates[0],
        "paths": list(candidates),
        "ignore": [str(glob) for glob in ignore],
        "view": str(value.get("view") or DEFAULT_VIEW),
        "archived": None,
        "retired": retired,
    }
