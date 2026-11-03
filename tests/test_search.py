"""The ranked search and the entry card: `python -m mdept.query "<words>"` and `mdept.card`.

The fixture pair is a family of seven toy entries. The ranked search is BM25
over weighted fields, with synonyms from `good_public/ledger/SYNONYMS.yaml`
and a floor below which nothing is offered. The card is the one rendering of
an entry that the query hits, the single-ID view and the consumer view share.
"""

import shutil
from pathlib import Path

import pytest

from mdept import CheckError, ConfigError
from mdept import card, query, view, words
from mdept import family as family_mod

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASES = ("good_public", "good_private")


def stage(tmp_path: Path) -> Path:
    for base in BASES:
        shutil.copytree(FIXTURES / base, tmp_path / base,
                        ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


@pytest.fixture
def root(tmp_path):
    return stage(tmp_path)


def load(root: Path):
    return family_mod.load_family(root / "good_private")


def hit_ids(answer) -> list[str]:
    return [hit["id"] for hit in answer["hits"]]


# --- the tokenizer ----------------------------------------------------------------


def test_latex_macros_read_as_words():
    assert words.tokens(r"$\nu \le \alpha$") == ["nu", "most", "alpha"]
    assert words.tokens(r"$\text{Let } \mathbb{R}^2 \ni x$") == ["2", "ni"]
    assert words.tokens(r"$\nabla G$") == ["nabla", "gradient"]
    assert words.tokens("Poincaré Fréchet Hölder") == words.tokens("Poincare Frechet Holder")


def test_an_entry_id_stays_one_token_and_plurals_fold():
    assert words.tokens("MD_0007 eigenvalues and bounds of series") == [
        "md_0007", "eigenvalue", "bound", "series"]


def test_ing_and_ed_endings_fold_to_one_root():
    assert {words.stem(w) for w in ("conditioning", "conditioned", "conditions")} == {"condition"}
    assert words.stem("mapping") == words.stem("mapped") == "map"
    assert words.stem("need") == "need" and words.stem("series") == "series"


def test_a_synonym_phrase_becomes_one_group_with_two_alternatives():
    pairs = [(("floquet", "matrix"), ("monodromy",))]
    assert words.expand(["floquet", "matrix", "eigenvalue"], pairs) == [
        [("floquet", "matrix"), ("monodromy",)],
        [("eigenvalue",)],
    ]


def test_a_synonym_phrase_without_a_search_word_fails(tmp_path):
    path = tmp_path / "SYNONYMS.yaml"
    path.write_text("pairs:\n  - {consumer: a b c, ledger: monodromy}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="no search word"):
        words.load_synonyms(path)


def test_a_synonym_list_with_a_repeated_phrase_fails(tmp_path):
    path = tmp_path / "SYNONYMS.yaml"
    path.write_text("pairs:\n  - {consumer: period map, ledger: monodromy}\n"
                    "  - {consumer: Period Maps, ledger: flow map}\n",
                    encoding="utf-8")
    with pytest.raises(ConfigError, match="repeats"):
        words.load_synonyms(path)


def test_a_missing_synonym_list_fails(root):
    (root / "good_public" / "ledger" / "SYNONYMS.yaml").unlink()
    with pytest.raises(ConfigError, match="synonym list is missing"):
        query.rank(load(root), ["adding zero"])


# --- ranking ------------------------------------------------------------------------


def test_the_ranked_search_finds_the_entry_from_its_title_words(root):
    answer = query.rank(load(root), ["adding zero on the left"])
    assert hit_ids(answer)[0] == "MD_0007"
    assert set(hit_ids(answer)[:2]) == {"MD_0001", "MD_0007"}


def test_an_aka_hit_outranks_a_notes_hit_the_count_ranking_put_first(root):
    """Two plain mentions in the notes beat one name in `aka` by raw count; BM25 weighs `aka` 3."""
    private = root / "good_private" / "ledger"
    edit(private / "MD_0005.md", "cited_by: [", "aka: [exponential dominates]\ncited_by: [")
    edit(private / "MD_0006.md", "Worked to budget at S1",
         "An exponential is mentioned here, and exponential again. Worked to budget at S1")
    family = load(root)
    counted = query.search(family, ["exponential"])
    assert [r["id"] for r in counted["entries"]][0] == "MD_0006", "the count ranking puts the notes first"
    assert hit_ids(query.rank(family, ["exponential"]))[0] == "MD_0005"


def test_phrasings_and_plain_words_are_searched(root):
    private = root / "good_private" / "ledger"
    edit(private / "MD_0006.md", "cited_by: [",
         "phrasings: [is n always strictly below two to the n, does the strict bound hold for "
         "every natural, can n reach two to the n]\ncited_by: [")
    edit(private / "MD_0007.md", "## Why it was raised",
         "## In plain words\n\nPutting nothing in front of a number leaves the number alone.\n\n"
         "## Why it was raised")
    family = load(root)
    assert hit_ids(query.rank(family, ["strictly below two to the n"]))[0] == "MD_0006"
    assert hit_ids(query.rank(family, ["putting nothing in front leaves it alone"]))[0] == "MD_0007"


def test_a_consumer_phrase_reaches_the_ledger_phrase_through_the_synonyms(root):
    family = load(root)
    answer = query.rank(family, ["additive identity on the naturals"])
    assert set(hit_ids(answer)[:2]) == {"MD_0001", "MD_0007"}
    assert answer["query"]["groups"][0] == [["additive", "identity"], ["adding", "zero"]]


def test_nothing_clears_the_floor_for_words_the_ledger_never_uses(root):
    answer = query.rank(load(root), ["banana spaceship turbulence"])
    assert answer["hits"] == []
    lines = query.render_rank(answer)
    assert any(line.startswith("nothing above the floor") for line in lines)


def test_a_query_of_stopwords_only_is_refused(root):
    with pytest.raises(CheckError, match="no search word"):
        query.rank(load(root), ["the of and"])


def test_the_top_k_cap_holds(root):
    family = load(root)
    assert query.rank(family, ["adding zero naturals"])["above_floor"] >= 2
    answer = query.rank(family, ["adding zero naturals"], k=1)
    assert len(answer["hits"]) == 1


def test_scores_are_shares_in_zero_one_and_sorted(root):
    answer = query.rank(load(root), ["toy bound naturals"])
    scores = [hit["score"] for hit in answer["hits"]]
    assert scores == sorted(scores, reverse=True)
    assert all(query.SCORE_FLOOR <= s <= 1 for s in scores)


def test_a_filter_restricts_the_ranked_search(root):
    answer = query.rank(load(root), ["toy bound naturals"], status="open")
    assert hit_ids(answer) == ["MD_0006"]
    with pytest.raises(CheckError, match="is not one of"):
        query.rank(load(root), ["toy"], status="disproven")


def test_the_cli_prints_cards_and_the_floor_line(root, capsys):
    assert query.main(["--root", str(root / "good_private"), "adding zero on the left"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("floor ")
    assert "MD_0007  proven-formal  Adding zero on the left changes nothing" in out
    assert "  statement    \\forall n \\in \\mathbb{N}, 0 + n = n" in out


def test_the_cli_exact_mode_is_the_substring_search(root, capsys):
    assert query.main(["--root", str(root / "good_private"), "--exact", "2^n"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "3 entries: terms 2^n"


# --- the card -----------------------------------------------------------------------


def test_the_card_carries_statement_hypotheses_links_and_citations(root):
    family = load(root)
    found = card.card(family.by_id()["MD_0006"], family)
    assert found["statement"] == "\\forall n \\in \\mathbb{N}, n < 2^n"
    assert found["hypotheses"] == ["H1. n ranges over the naturals."]
    assert found["cite_with"] == ["pending", "conjectured", "open"]
    assert found["links"] == [
        {"direction": "out", "kind": "below_of", "id": "MD_0005", "status": "conjectured",
         "title": "The toy bound on the naturals"},
        {"direction": "in", "kind": "above_of", "id": "MD_0005", "status": "conjectured",
         "title": "The toy bound on the naturals"},
    ]
    assert found["cited_by"] == ["ToyRepo:docs/toy.md §1", 'ToyRepo:"research/toy notes.md" §2']


def test_the_card_names_the_lean_declaration_and_the_settling_files(root):
    family = load(root)
    formal = card.card(family.by_id()["MD_0001"], family)
    assert formal["decl"] == "MathDept.MD_0001.statement"
    assert formal["files"] == [{"kind": "lean", "path": "MathDept/Results/MD_0001.lean"}]
    refuted = card.card(family.by_id()["MD_0002"], family)
    assert {"kind": "counterexample", "path": "counterexamples/MD_0002_toy.py"} in refuted["files"]
    lines = card.render_entry(refuted)
    assert "  files        refuted: counterexample counterexamples/MD_0002_toy.py" in lines


def test_the_text_card_prints_one_line_per_hypothesis_and_per_link(root):
    family = load(root)
    lines = card.render_entry(card.card(family.by_id()["MD_0006"], family))
    assert lines[0] == "MD_0006  open  The strict form of the toy bound"
    assert "  H1           n ranges over the naturals." in lines
    assert "  link         below_of MD_0005 (conjectured) The toy bound on the naturals" in lines
    assert "  link         MD_0005 above_of this (conjectured) The toy bound on the naturals" in lines
    assert "  cite with    one of pending, conjectured, open" in lines


def test_a_width_cuts_the_statement_on_a_hit_card(root):
    family = load(root)
    lines = card.render_entry(card.card(family.by_id()["MD_0006"], family), width=10)
    assert "  statement    \\forall n…" in lines


def test_a_link_to_an_id_neither_ledger_holds_prints_as_held(tmp_path, monkeypatch):
    monkeypatch.delenv("MATHDEPT_PRIVATE", raising=False)
    root = stage(tmp_path)
    edit(root / "good_public" / "ledger" / "MD_0004.md", "revises: null", "revises: MD_0006")
    public = family_mod.load_family(root / "good_public")
    shutil.rmtree(root / "good_private")
    found = card.card(public.by_id()["MD_0004"], public)
    assert found["links"] == [{"direction": "out", "kind": "revises", "id": "MD_0006",
                               "status": family_mod.HELD, "title": None}]


def test_a_link_to_an_id_in_neither_ledger_fails_from_the_private_side(root):
    """The private side resolves through both ledgers, so nothing is held from there."""
    edit(root / "good_private" / "ledger" / "MD_0006.md", "revises: null", "revises: MD_0099")
    family = load(root)
    with pytest.raises(CheckError, match="I8 links: .*MD_0099"):
        card.card(family.by_id()["MD_0006"], family)


def test_the_consumer_view_renders_the_card(root):
    family = load(root)
    text, _path, _payload = view.generate(family, "ToyRepo")
    assert "- **Statement.** \\forall n \\in \\mathbb{N}, n \\le 2^n" in text
    assert "- **Hypotheses.**\n  - H1. n ranges over the naturals." in text
    assert "- **Linked.** above_of MD_0006 (open) The strict form of the toy bound" in text
    assert "python -m mdept.query" in text.split("## Raised here")[0]


# --- the repo's own synonym list ------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_every_ledger_phrase_of_the_repo_synonym_list_is_ledger_vocabulary():
    """A ledger phrase no entry uses would expand a query into words that match nothing.

    Several phrases are the vocabulary of unreleased entries, so the check reads both
    ledgers and skips, saying why, on a public checkout with no private sibling.
    """
    family = family_mod.load_family(REPO_ROOT)
    if family.private is None:
        pytest.skip("the synonym list names the vocabulary of both ledgers; no private ledger on this machine")
    ranker = query.Ranker(family.entries())
    pairs = words.load_synonyms(REPO_ROOT / words.SYNONYMS_PATH)
    unused = [" ".join(ledger) for _consumer, ledger in pairs
              if any(ranker.df.get(token, 0) == 0 for token in ledger)]
    assert unused == [], f"ledger phrases no entry uses: {unused}"
