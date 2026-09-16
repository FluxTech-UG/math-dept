"""`python -m mdept.query`: what it searches, how it ranks, and what it resolves.

The fixture pair is a family: four released entries in `good_public` and three
unreleased ones in `good_private`. Every query here runs over both, which is the
property that makes this command worth having over a grep of one directory.
"""

import shutil
from pathlib import Path

import pytest

from mdept import CheckError, ConfigError
from mdept import family as family_mod
from mdept import query

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASES = ("good_public", "good_private")


def stage(tmp_path: Path) -> Path:
    for base in BASES:
        shutil.copytree(FIXTURES / base, tmp_path / base,
                        ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


@pytest.fixture
def family(tmp_path):
    return family_mod.load_family(stage(tmp_path) / "good_private")


def ids(answer) -> list[str]:
    return [record["id"] for record in answer["entries"]]


# --- both ledgers, one answer ----------------------------------------------


def test_both_ledgers_are_searched(family):
    assert ids(query.search(family, [])) == [f"MD_000{n}" for n in range(1, 8)]


def test_terms_select_when_there_is_no_filter(family):
    """MD_0005 and MD_0006 are the two bounds; nothing else says "bound"."""
    answer = query.search(family, ["bound"])
    assert ids(answer) == ["MD_0005", "MD_0006"]
    assert [record["hits"] for record in answer["entries"]] == [4, 2], "ranked by hit count"


def test_a_term_matches_the_statement_body(family):
    """`2^n` appears in no title and no topic: only in three Statements."""
    answer = query.search(family, ["2^n"])
    assert ids(answer) == ["MD_0004", "MD_0005", "MD_0006"]
    assert all(record["hits"] > 0 for record in answer["entries"])


def test_a_filter_selects_and_terms_only_rank(family):
    """With a filter, an entry the filter admits is never hidden by the terms.

    A reader scanning a topic wants the whole topic, with the terms deciding
    what to read first. Dropping the zero-hit entries would make the filter
    silently narrower than it says.
    """
    answer = query.search(family, ["naturals"], topic="arithmetic")
    assert ids(answer) == ["MD_0001", "MD_0007", "MD_0002"]
    assert [record["hits"] for record in answer["entries"]] == [2, 1, 0]


def test_a_status_filter_is_checked_against_the_vocabulary(family):
    assert ids(query.search(family, [], status="refuted")) == ["MD_0002"]
    with pytest.raises(CheckError, match="is not one of"):
        query.search(family, [], status="disproven")


def test_a_consumer_filter_takes_raised_and_cited(family):
    assert ids(query.search(family, [], consumer="ToyRepo")) == ["MD_0005", "MD_0006", "MD_0007"]
    with pytest.raises(ConfigError, match="not a consumer"):
        query.search(family, [], consumer="NoSuchRepo")


# --- the record shape ------------------------------------------------------


def test_the_record_carries_what_the_human_view_prints(family):
    record = query.search(family, [], status="open")["entries"][0]
    assert record["id"] == "MD_0006"
    assert set(record) == {
        "id", "status", "title", "statement", "topics",
        "raised_by", "cited_by", "citation_words", "hits",
    }
    assert set(record["raised_by"]) == {"repo", "doc", "anchor"}
    assert record["citation_words"] == ["pending", "conjectured", "open"]
    assert record["cited_by"] == [
        "ToyRepo:docs/toy.md §1",
        'ToyRepo:"research/toy notes.md" §2',
    ]


def test_a_refuted_entry_asks_for_the_word_refuted(family):
    record = query.search(family, [], status="refuted")["entries"][0]
    assert record["citation_words"] == ["refuted"]


def test_a_settled_entry_asks_for_no_word(family):
    record = query.search(family, [], status="proven-formal")["entries"][0]
    assert record["citation_words"] == []


def test_one_line_cuts_a_long_statement_and_keeps_a_short_one():
    assert query.one_line("a  b\n c") == "a b c"
    assert query.one_line("x" * 200).endswith("…")
    assert len(query.one_line("x" * 200)) == query.STATEMENT_WIDTH


# --- resolve ---------------------------------------------------------------


def test_resolve_reports_the_entries_a_closed_candidate_became(family):
    answer = query.resolve(family, "MDR:2026-08-20-closed")
    assert answer["state"] == "closed"
    assert answer["candidates"]["C1"] == [{"id": "MD_0005", "status": "conjectured"}]
    assert answer["candidates"]["C2"] == [{"id": "MD_0006", "status": "open"}]


def test_resolve_reports_a_declined_candidate_with_its_reason(family):
    answer = query.resolve(family, "MDR:2026-08-20-closed")
    assert answer["candidates"]["C3"].startswith("declined: the statement leaves its index set")


def test_resolve_reports_pending_for_a_request_nobody_has_worked(family):
    answer = query.resolve(family, "MDR:2026-09-01-toy")
    assert answer["state"] == "new"
    assert answer["candidates"] == {"C1": "pending"}


def test_one_candidate_can_be_asked_for_on_its_own(family):
    answer = query.resolve(family, "MDR:2026-08-20-closed#C2")
    assert list(answer["candidates"]) == ["C2"]


def test_resolve_refuses_a_token_that_is_not_one(family):
    with pytest.raises(CheckError, match="is not MDR:"):
        query.resolve(family, "2026-08-20-closed")


def test_resolve_names_a_request_that_does_not_exist(family):
    with pytest.raises(CheckError, match="names no request"):
        query.resolve(family, "MDR:2026-01-01-nothing")


# --- the public ledger alone -----------------------------------------------


def test_the_public_ledger_alone_is_still_a_family(tmp_path, monkeypatch):
    """A public checkout with no private sibling answers over what it has.

    This is the open-source case: the repo has to be usable by someone who will
    never see the private side, and a query that refused to run without it would
    make the public ledger unreadable from outside.
    """
    monkeypatch.delenv("MATHDEPT_PRIVATE", raising=False)
    root = stage(tmp_path) / "good_public"
    family = family_mod.load_family(root)
    assert family.private is None and family.consumers == {}
    assert ids(query.search(family, [])) == [f"MD_000{n}" for n in range(1, 5)]
    with pytest.raises(ConfigError, match="needs the private repo"):
        family_mod.require_private(family, "mdept.view")


# --- a filter nobody can satisfy is a mistake, not an empty answer ---------


def test_an_unknown_topic_fails_rather_than_answering_nothing(family):
    """Zero entries for a mistyped topic reads as "the department holds nothing".

    That is the most expensive wrong answer this command can give, because the
    next step in the protocol is to file a request for something already settled.
    """
    with pytest.raises(CheckError, match="no entry carries the topic 'thermoacustics'"):
        query.search(family, [], topic="thermoacustics")
    assert query.search(family, [], topic="TOY")["entries"], "a known topic is case-insensitive"


def test_an_unknown_consumer_fails_even_with_the_public_ledger_alone(tmp_path, monkeypatch):
    """With no private repo there is no consumer list, so no name can be checked.

    Saying so beats filtering by a name that could never match: the reader who
    typed it is told the list is missing, not that their repo cites nothing.
    """
    monkeypatch.delenv("MATHDEPT_PRIVATE", raising=False)
    public = family_mod.load_family(stage(tmp_path) / "good_public")
    with pytest.raises(ConfigError, match="no consumer list on this machine"):
        query.search(public, [], consumer="ToyRepo")
