"""`ledger/CATALOG.md` and `ledger/EDGES.tsv`: the catalog under its budget, the edge list, both drift-checked.

The fixture pair is a family. Its entries all file under the topic `toy`, so a
test that needs a second primary topic rewrites one staged entry's topics.
"""

import shutil
from pathlib import Path

import pytest

from mdept import CheckError
from mdept import catalog, graph, index
from mdept import family as family_mod

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASES = ("good_public", "good_private")


def stage(tmp_path: Path) -> Path:
    for base in BASES:
        shutil.copytree(FIXTURES / base, tmp_path / base,
                        ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def retopic(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def public_entries(root: Path):
    return family_mod.locate(root / "good_public").public.entries()


# --- the views are part of the generated set ---------------------------------


def test_render_writes_the_catalog_and_the_edge_list(tmp_path):
    root = stage(tmp_path) / "good_public"
    rendered = index.render(root)
    assert catalog.CATALOG_PATH in rendered
    assert index.EDGES_PATH in rendered


def test_the_index_check_fails_while_the_catalog_is_missing(tmp_path):
    root = stage(tmp_path) / "good_public"
    (root / catalog.CATALOG_PATH).unlink(missing_ok=True)
    assert index.main(["--root", str(root), "--check"]) == 1


# --- one line per entry -------------------------------------------------------


def test_a_line_carries_id_status_title_and_the_statement_without_dollars(tmp_path):
    root = stage(tmp_path)
    entry = {e.id: e for e in public_entries(root)}["MD_0001"]
    assert catalog.line(entry) == (
        "- MD_0001 proven-formal: Adding zero on the naturals changes nothing | "
        "\\forall n \\in \\mathbb{N}, n + 0 = n"
    )


def test_a_line_carries_the_informal_names_when_the_entry_has_them(tmp_path):
    root = stage(tmp_path)
    path = root / "good_public" / "ledger" / "MD_0001.md"
    retopic(path, "cited_by: []", "cited_by: []\naka: [zero is a right identity, n plus zero]")
    entry = {e.id: e for e in public_entries(root)}["MD_0001"]
    assert " | aka zero is a right identity; n plus zero | " in catalog.line(entry)


def test_a_long_statement_is_cut_to_the_catalog_width(tmp_path):
    root = stage(tmp_path)
    path = root / "good_public" / "ledger" / "MD_0001.md"
    retopic(path, "$$ \\forall n", "$$ " + "x + " * 200 + "\\forall n")
    entry = {e.id: e for e in public_entries(root)}["MD_0001"]
    statement = catalog.line(entry).split(" | ")[-1]
    assert len(statement) == catalog.CATALOG_STATEMENT_WIDTH and statement.endswith("…")


# --- the budget -----------------------------------------------------------------


def test_under_the_budget_the_catalog_is_one_file_with_a_heading_per_topic(tmp_path):
    root = stage(tmp_path)
    retopic(root / "good_public" / "ledger" / "MD_0002.md", "topics: [toy, arithmetic]",
            "topics: [arithmetic, toy]")
    files = catalog.render(public_entries(root), "the public ledger")
    assert list(files) == [catalog.CATALOG_PATH]
    text = files[catalog.CATALOG_PATH]
    assert text.startswith("# Ledger catalog\n")
    assert "\n## arithmetic\n\n- MD_0002 refuted:" in text
    assert "\n## toy\n\n- MD_0001 proven-formal:" in text
    assert catalog.token_count(text) == -(-len(text) // catalog.CHARS_PER_TOKEN)


def test_past_the_budget_the_catalog_splits_by_primary_topic(tmp_path):
    root = stage(tmp_path)
    retopic(root / "good_public" / "ledger" / "MD_0002.md", "topics: [toy, arithmetic]",
            "topics: [arithmetic, toy]")
    for n in (1, 3, 4):
        retopic(root / "good_public" / "ledger" / f"MD_000{n}.md", "## Statement\n\n",
                "## Statement\n\n" + "a long opening clause, " * 10)
    entries = public_entries(root)
    single = catalog.render(entries, "the public ledger")[catalog.CATALOG_PATH]
    titled = catalog._contents(catalog._by_topic(entries), "the public ledger", titles=True)
    assert catalog.token_count(titled) < catalog.token_count(single)
    files = catalog.render(entries, "the public ledger", budget=catalog.token_count(titled))
    assert sorted(files) == sorted([
        catalog.CATALOG_PATH, "ledger/CATALOG-arithmetic.md", "ledger/CATALOG-toy.md",
    ])
    contents = files[catalog.CATALOG_PATH]
    assert "## [arithmetic](CATALOG-arithmetic.md)\n\n1 entry; also toy.\n\n- MD_0002 refuted: Every integer exceeds its own square\n" in contents
    assert "## [toy](CATALOG-toy.md)\n\n3 entries; also arithmetic.\n" in contents
    assert all(" | " not in ln for ln in contents.splitlines() if ln.startswith("- MD_")), \
        "an entry line in the contents file carries the title only"
    assert "MD_0002 refuted:" in files["ledger/CATALOG-arithmetic.md"]
    assert "MD_0002" not in files["ledger/CATALOG-toy.md"]


def test_a_contents_file_past_the_budget_drops_the_titles(tmp_path):
    root = stage(tmp_path)
    retopic(root / "good_public" / "ledger" / "MD_0002.md", "topics: [toy, arithmetic]",
            "topics: [arithmetic, toy]")
    entries = public_entries(root)
    topics_only = catalog._contents(catalog._by_topic(entries), "the public ledger", titles=False)
    files = catalog.render(entries, "the public ledger", budget=catalog.token_count(topics_only))
    assert files[catalog.CATALOG_PATH] == topics_only
    assert "- MD_" not in topics_only


def test_a_topic_file_past_the_budget_fails_and_names_itself(tmp_path):
    root = stage(tmp_path)
    with pytest.raises(CheckError, match="CATALOG-toy.md .*past the catalog budget of 50"):
        catalog.render(public_entries(root), "the public ledger", budget=50)


def test_the_private_catalog_covers_both_ledgers(tmp_path):
    root = stage(tmp_path)
    text = index.render(root / "good_private")[catalog.CATALOG_PATH]
    listed = [ln.split()[1] for ln in text.splitlines() if ln.startswith("- MD_")]
    assert listed == [f"MD_000{n}" for n in range(1, 8)]
    public = index.render(root / "good_public")[catalog.CATALOG_PATH]
    assert [ln.split()[1] for ln in public.splitlines() if ln.startswith("- MD_")] == [
        f"MD_000{n}" for n in range(1, 5)]


def test_the_citation_rule_in_the_preamble_follows_the_schema(tmp_path):
    text = index.render(stage(tmp_path) / "good_public")[catalog.CATALOG_PATH]
    assert "Cite an entry by its ID. A line citing a refuted entry carries `refuted`;" in text
    assert "a line citing a conjectured or open entry carries one of `pending`, `conjectured`, `open`." in text


# --- a stale split leaves no file behind ---------------------------------------


def test_a_stray_topic_file_fails_the_check_and_regen_removes_it(tmp_path):
    root = stage(tmp_path) / "good_public"
    index.write(root)
    stray = root / "ledger" / "CATALOG-retired-topic.md"
    stray.write_text("# Ledger catalog: retired-topic\n", encoding="utf-8")
    assert index.main(["--root", str(root), "--check"]) == 1
    assert "ledger/CATALOG-retired-topic.md" in index.drift(root)
    index.write(root)
    assert not stray.exists()
    assert index.drift(root) == []


def test_a_catalog_file_is_not_read_as_an_entry(tmp_path):
    root = stage(tmp_path) / "good_public"
    index.write(root)
    (root / "ledger" / "CATALOG-toy.md").write_text("stray\n", encoding="utf-8")
    assert [e.id for e in family_mod.locate(root).public.entries()] == [
        f"MD_000{n}" for n in range(1, 5)]


# --- the edge list ---------------------------------------------------------------


def test_edges_cover_link_fields_and_citations(tmp_path):
    root = stage(tmp_path)
    entries = family_mod.locate(root / "good_private").private.entries()
    rows = graph.edges(entries)
    assert ("MD_0005", "above_of", "MD_0006") in rows
    assert ("MD_0006", "below_of", "MD_0005") in rows
    assert ("MD_0006", "cited_by", 'ToyRepo:"research/toy notes.md" §2') in rows
    assert ("MD_0005", "cited_by", "ToyRepo:src/toy.py") in rows


def test_the_edge_file_is_a_header_and_one_tab_separated_row_per_edge(tmp_path):
    root = stage(tmp_path) / "good_private"
    text = index.render(root)[index.EDGES_PATH]
    lines = text.splitlines()
    assert lines[0] == "source\tkind\ttarget"
    assert "MD_0005\tabove_of\tMD_0006" in lines
    assert all(len(ln.split("\t")) == 3 for ln in lines)


def test_neighbours_read_both_directions(tmp_path):
    root = stage(tmp_path)
    rows = graph.edges(family_mod.locate(root / "good_private").private.entries())
    assert graph.neighbours(rows, "MD_0005") == [
        ("out", "above_of", "MD_0006"),
        ("in", "below_of", "MD_0006"),
    ]


def test_an_edge_field_with_a_tab_fails():
    with pytest.raises(CheckError, match="tab or a line break"):
        graph.render_tsv([("MD_0001", "cited_by", "Repo:a\tb.md")])
