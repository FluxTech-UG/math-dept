"""The closed front-matter schema for a ledger entry.

Every key is required and every key set is closed: an unknown key is an error,
a missing key is an error, and a null is only accepted where the template shows
one. There is no defaulting layer. A field that should carry a value and does
not is a fact the ledger is missing, and the checker says so rather than
inventing it.

`validate_front` raises `CheckError` prefixed `I3 schema` so the caller does not
have to re-wrap it.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from . import CheckError

# --- vocabularies (closed) --------------------------------------------------

STATUSES = (
    "cited",
    "conjectured",
    "open",
    "proven-formal",
    "proven-informal",
    "refuted",
    "merged",
)
SETTLED_STATUSES = ("cited", "proven-formal", "proven-informal", "refuted")
UNSETTLED_STATUSES = ("conjectured", "open")
PROVEN_STATUSES = ("proven-formal", "proven-informal")

KINDS = ("theorem", "lemma", "proposition", "identity", "bound", "definition")
WHO = ("john", "claude", "both")
HOW = ("citation", "counterexample", "lean", "informal-proof")
EVIDENCE_KINDS = ("extract", "proof", "counterexample", "triage", "experiment")

#: Evidence surfaces that exist only in the private repo. A released entry
#: drops them, because a public path that does not resolve is a dead pointer.
PRIVATE_EVIDENCE_KINDS = ("extract", "triage")

SOURCE_KINDS = ("paper", "book", "notes", "mathlib", "forum", "draft")
#: A `cited` entry may only rest on one of these. Forum posts and drafts are
#: read, and may seed a conjecture, but they never carry a citation alone.
TRUSTED_SOURCE_KINDS = ("paper", "book", "notes", "mathlib")

RELATIONS = ("below_of", "above_of", "special_case_of", "generalizes")

#: The words a consumer line citing an entry must carry, by status (I15). A
#: settled-and-standing entry needs none: the citation is simply true. The
#: unsettled and the refuted need one, because a line that reads as established
#: is the failure mode, and it is invisible in the consumer's own document.
CITATION_WORDS = {
    "refuted": ("refuted",),
    "conjectured": ("pending", "conjectured", "open"),
    "open": ("pending", "conjectured", "open"),
}

# --- key sets (closed) ------------------------------------------------------

ENTRY_KEYS = (
    "id",
    "title",
    "status",
    "kind",
    "topics",
    "source",
    "formal",
    "evidence",
    "between",
    "provenance",
    "cited_by",
    "revises",
    "merged_into",
    "statement_hash",
)
FORMAL_KEYS = ("decl", "file")
BETWEEN_KEYS = RELATIONS
PROVENANCE_KEYS = ("raised_by", "stipulated_by", "settled_by", "connects")
RAISED_BY_KEYS = ("repo", "domain", "doc", "anchor", "application")
#: Only these survive a release. The rest describe the application and stay private.
RAISED_BY_PUBLIC_KEYS = ("repo", "domain")
STIPULATED_BY_KEYS = ("who", "date", "model", "request")
SETTLED_BY_KEYS = ("who", "date", "how", "checked_by", "model")
EVIDENCE_KEYS = ("kind", "path")

# --- token grammars ---------------------------------------------------------

ID_RE = re.compile(r"^MD_\d{4}$")
ID_TOKEN_RE = re.compile(r"\bMD_\d{4}\b")
REQUEST_STEM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$")
REQUEST_TOKEN_RE = re.compile(r"\bMDR:(\d{4}-\d{2}-\d{2}-[a-z0-9-]+)#(C\d+)\b")
#: The same token with the candidate optional, for reading what a document carries.
REQUEST_STEM_TOKEN_RE = re.compile(
    r"\bMDR:(?P<stem>\d{4}-\d{2}-\d{2}-[a-z0-9-]+)(?:#(?P<candidate>C\d+))?\b"
)
TOPIC_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BIB_TAG_RE = re.compile(r"^\[([A-Za-z0-9][A-Za-z0-9+._-]*)\]$")
DECL_RE = re.compile(r"^MathDept(Private)?\.MD_\d{4}\.[A-Za-z_][A-Za-z0-9_.']*$")
LEAN_FILE_RE = re.compile(r"^MathDept(Private)?/[A-Za-z0-9_/]+\.lean$")
COUNTEREXAMPLE_STEM_RE = re.compile(r"^MD_\d{4}_[a-z0-9_]+$")
#: One `cited_by` string: `Repo:path §locator`. The path may be double quoted,
#: which is the only way to write one that contains a space, and several repos in
#: this family have those (`Some Repo:"research/a spaced name.md" §2`).
#: Read it through `split_cited_by`, never by group name.
CITED_BY_RE = re.compile(
    r'^(?P<repo>[^:]+):(?:"(?P<quoted>[^"]+)"|(?P<path>\S+))(?:\s+(?P<loc>.+))?$'
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: The four body headings every entry carries, in order.
BODY_HEADINGS = ("Statement", "Hypotheses", "Why it was raised", "Current notes")

EM_DASH = "—"


def split_cited_by(citation: str) -> tuple[str, str, str | None] | None:
    """(repo, path, locator) from one `cited_by` string, or None when it is malformed."""
    match = CITED_BY_RE.match(str(citation))
    if match is None:
        return None
    path = match.group("quoted") or match.group("path")
    return match.group("repo").strip(), path, match.group("loc")


def cited_by_form(repo: str, path: str) -> str:
    """The `cited_by` string for this repo and path, quoted when it has to be."""
    return f'{repo}:"{path}"' if " " in str(path) else f"{repo}:{path}"


def citation_words(status: str) -> tuple[str, ...]:
    """The status words I15 requires on a line citing an entry at this status."""
    return CITATION_WORDS.get(status, ())


def _fail(path: Path, field: str, message: str) -> None:
    raise CheckError(f"I3 schema: {path}: field '{field}': {message}")


def _closed_mapping(value, keys, path: Path, field: str) -> dict:
    if not isinstance(value, dict):
        _fail(path, field, f"expected a mapping, got {type(value).__name__}")
    unknown = sorted(set(value) - set(keys))
    if unknown:
        _fail(path, field, f"unknown key(s) {unknown}; the schema is closed")
    missing = [k for k in keys if k not in value]
    if missing:
        _fail(path, field, f"missing key(s) {missing}; every key is required")
    return value


def _enum(value, allowed, path: Path, field: str) -> None:
    if value not in allowed:
        _fail(path, field, f"{value!r} is not one of {list(allowed)}")


def _iso_date(value, path: Path, field: str) -> None:
    if not isinstance(value, str) or not ISO_DATE_RE.match(value):
        _fail(path, field, f"expected an ISO date YYYY-MM-DD, got {value!r}")
    try:
        datetime.date.fromisoformat(value)
    except ValueError as exc:
        _fail(path, field, f"{value!r} is not a real calendar date ({exc})")


def _str_list(value, path: Path, field: str) -> list:
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        _fail(path, field, f"expected a list of strings, got {value!r}")
    return value


def _id_list(value, path: Path, field: str) -> list:
    for item in _str_list(value, path, field):
        if not ID_RE.match(item):
            _fail(path, field, f"{item!r} is not an ID of the form MD_0007")
    return value


def validate_front(front: dict, path: Path, kind: str = "public") -> None:
    """Validate one entry's front matter. `kind` is 'public' or 'private'."""
    _closed_mapping(front, ENTRY_KEYS, path, "<root>")

    if not isinstance(front["id"], str) or not ID_RE.match(front["id"]):
        _fail(path, "id", f"{front['id']!r} is not an ID of the form MD_0007")

    title = front["title"]
    if not isinstance(title, str) or not title.strip():
        _fail(path, "title", "must be a non-empty string")
    if "$" in title:
        _fail(path, "title", "carries LaTeX; the title is plain prose, the Statement holds the math")

    _enum(front["status"], STATUSES, path, "status")
    _enum(front["kind"], KINDS, path, "kind")

    for topic in _str_list(front["topics"], path, "topics"):
        if not TOPIC_RE.match(topic):
            _fail(path, "topics", f"{topic!r} is not lower-case-hyphenated")
    if not front["topics"]:
        _fail(path, "topics", "at least one topic is required; the Topic Index is built from these")

    source = front["source"]
    if source is not None and (not isinstance(source, str) or not BIB_TAG_RE.match(source)):
        _fail(path, "source", f"{source!r} is not a bibliography tag of the form [Tag]")

    formal = _closed_mapping(front["formal"], FORMAL_KEYS, path, "formal")
    if formal["decl"] is not None and not DECL_RE.match(str(formal["decl"])):
        _fail(path, "formal.decl", f"{formal['decl']!r} is not of the form MathDept.MD_0007.statement")
    if formal["file"] is not None and not LEAN_FILE_RE.match(str(formal["file"])):
        _fail(path, "formal.file", f"{formal['file']!r} is not a repo-relative path under MathDept*/")
    if (formal["decl"] is None) != (formal["file"] is None):
        _fail(path, "formal", "decl and file are set together or both null")

    if not isinstance(front["evidence"], list):
        _fail(path, "evidence", "expected a list of {kind, path} mappings")
    for i, item in enumerate(front["evidence"]):
        _closed_mapping(item, EVIDENCE_KEYS, path, f"evidence[{i}]")
        _enum(item["kind"], EVIDENCE_KINDS, path, f"evidence[{i}].kind")
        if not isinstance(item["path"], str) or not item["path"].strip():
            _fail(path, f"evidence[{i}].path", "must be a non-empty repo-relative path")
        if kind == "public" and item["kind"] in PRIVATE_EVIDENCE_KINDS:
            _fail(
                path,
                f"evidence[{i}].kind",
                f"{item['kind']!r} names a private-only surface; a released entry drops it",
            )

    between = _closed_mapping(front["between"], BETWEEN_KEYS, path, "between")
    for relation in BETWEEN_KEYS:
        _id_list(between[relation], path, f"between.{relation}")

    prov = _closed_mapping(front["provenance"], PROVENANCE_KEYS, path, "provenance")
    _validate_raised_by(prov["raised_by"], front["status"], path, kind)
    _validate_stipulated_by(prov["stipulated_by"], front["status"], path)
    _validate_settled_by(prov["settled_by"], path)
    _str_list(prov["connects"], path, "provenance.connects")

    for i, citation in enumerate(_str_list(front["cited_by"], path, "cited_by")):
        if split_cited_by(citation) is None:
            _fail(path, f"cited_by[{i}]",
                  f"{citation!r} is not of the form 'Repo:path/to/doc.md §n'; "
                  'a path containing a space is double quoted, as in Repo:"a doc.md" §2')

    for field in ("revises", "merged_into"):
        value = front[field]
        if value is not None and (not isinstance(value, str) or not ID_RE.match(value)):
            _fail(path, field, f"{value!r} is not null and not an ID of the form MD_0007")

    hashed = front["statement_hash"]
    if hashed is not None and (not isinstance(hashed, str) or not SHA256_RE.match(hashed)):
        _fail(path, "statement_hash", f"{hashed!r} is not null and not a lower-case sha256 hex digest")


def _validate_raised_by(raised_by, status: str, path: Path, kind: str) -> None:
    if raised_by is None:
        if status != "merged":
            _fail(path, "provenance.raised_by", f"required for status {status!r}; only 'merged' may omit it")
        return
    _closed_mapping(raised_by, RAISED_BY_KEYS, path, "provenance.raised_by")
    if not isinstance(raised_by["repo"], str) or not raised_by["repo"].strip():
        _fail(path, "provenance.raised_by.repo", "must name the repo that raised the statement")
    if not isinstance(raised_by["domain"], str) or not raised_by["domain"].strip():
        _fail(path, "provenance.raised_by.domain", "one neutral line describing the domain is required")
    if kind == "public":
        for field in ("doc", "anchor", "application"):
            if raised_by[field] is not None:
                _fail(
                    path,
                    f"provenance.raised_by.{field}",
                    "public provenance is abstract: repo and domain only, "
                    "the application's doc, anchor and rationale stay private",
                )
    else:
        for field in ("doc", "anchor", "application"):
            value = raised_by[field]
            if value is not None and (not isinstance(value, str) or not value.strip()):
                _fail(path, f"provenance.raised_by.{field}", "must be null or a non-empty string")


def _validate_stipulated_by(stipulated_by, status: str, path: Path) -> None:
    if stipulated_by is None:
        if status != "merged":
            _fail(path, "provenance.stipulated_by", f"required for status {status!r}")
        return
    _closed_mapping(stipulated_by, STIPULATED_BY_KEYS, path, "provenance.stipulated_by")
    _enum(stipulated_by["who"], WHO, path, "provenance.stipulated_by.who")
    _iso_date(stipulated_by["date"], path, "provenance.stipulated_by.date")
    model = stipulated_by["model"]
    if model is not None and (not isinstance(model, str) or not model.strip()):
        _fail(path, "provenance.stipulated_by.model", "must be null or a model identifier")
    request = stipulated_by["request"]
    if request is not None:
        if not isinstance(request, str) or not REQUEST_TOKEN_RE.fullmatch(request):
            _fail(
                path,
                "provenance.stipulated_by.request",
                f"{request!r} is not a request token of the form MDR:2026-09-04-three-basin#C1",
            )


def _validate_settled_by(settled_by, path: Path) -> None:
    if settled_by is None:
        return
    _closed_mapping(settled_by, SETTLED_BY_KEYS, path, "provenance.settled_by")
    _enum(settled_by["who"], WHO, path, "provenance.settled_by.who")
    _iso_date(settled_by["date"], path, "provenance.settled_by.date")
    _enum(settled_by["how"], HOW, path, "provenance.settled_by.how")
    if settled_by["checked_by"] is not None:
        _iso_date(settled_by["checked_by"], path, "provenance.settled_by.checked_by")
    model = settled_by["model"]
    if model is not None and (not isinstance(model, str) or not model.strip()):
        _fail(path, "provenance.settled_by.model", "must be null or a model identifier")
