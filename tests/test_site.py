"""`python -m mdept.site`: the reading site, one page per entry plus the index.

The fixture pair is the family: the public build reads `good_public` alone, the private
build reads both ledgers from `good_private`. Every case builds into a temporary folder
and reads the HTML back; `--check` (the `make check` line) is exercised on a broken body
and on this repo's own ledger.
"""

import re
import shutil
from pathlib import Path

import pytest

from mdept import CheckError, ConfigError, site

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent
BASES = ("good_public", "good_private")

GISCUS_FILLED = """[giscus]
repo = "FluxTech-UG/math-dept"
repo_id = "R_kgDOtest"
category = "Entries"
category_id = "DIC_kwDOtest"
"""


@pytest.fixture
def family(tmp_path):
    for base in BASES:
        shutil.copytree(FIXTURES / base, tmp_path / base, ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def settings(tmp_path, giscus: str | None = None) -> site.SiteConfig:
    text = (REPO_ROOT / site.CONFIG_NAME).read_text(encoding="utf-8")
    if giscus is not None:
        text = text[:text.index("[giscus]")] + giscus
    path = tmp_path / "site.toml"
    path.write_text(text, encoding="utf-8")
    return site.load_config(path)


def build(root: Path, tmp_path: Path, cfg=None, name="out") -> Path:
    out = tmp_path / name
    site.build(root, out, cfg or settings(tmp_path))
    return out


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def set_plain_words(entry: Path, text: str | None, checked: str | None = None) -> None:
    """Replace the text of the entry's `## In plain words` section; None removes the section."""
    body = entry.read_text(encoding="utf-8")
    start, end = body.index("\n## In plain words\n"), body.index("\n## Why it was raised")
    section = "" if text is None else f"\n## In plain words\n\n{text}\n"
    entry.write_text(body[:start] + section + body[end:], encoding="utf-8")
    if checked is not None:
        edit(entry, "\nrevises:", f"\nplain_words_checked: '{checked}'\nrevises:")


# --- pages ----------------------------------------------------------------


def test_the_public_build_writes_a_page_per_entry_and_the_index(family, tmp_path):
    out = build(family / "good_public", tmp_path)
    assert sorted(p.name for p in out.glob("*.html")) == [
        "MD_0001.html", "MD_0002.html", "MD_0003.html", "MD_0004.html", "index.html"]
    page = (out / "MD_0002.html").read_text(encoding="utf-8")
    assert "$$ \\forall n \\in \\mathbb{Z},\\; n^2 &gt; n $$" in page
    assert f"katex@{site.KATEX_VERSION}/dist/katex.min.js" in page
    assert '<span class="badge st-refuted">refuted</span>' in page
    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'data-status-chip="refuted"' in index and '<option value="toy">toy (' in index


def test_an_entry_without_plain_words_fails_the_build(family, tmp_path):
    set_plain_words(family / "good_public/ledger/MD_0002.md", None)
    with pytest.raises(CheckError, match="In plain words"):
        build(family / "good_public", tmp_path)


def test_an_unchecked_plain_words_section_is_badged_unreviewed(family, tmp_path):
    set_plain_words(family / "good_public/ledger/MD_0002.md", "Squaring does not always grow $n$.")
    page = (build(family / "good_public", tmp_path) / "MD_0002.html").read_text(encoding="utf-8")
    assert 'class="badge pw-unreviewed">unreviewed' in page
    assert "Squaring does not always grow $n$." in page and "Plain words pending" not in page


def test_a_checked_plain_words_section_carries_its_review_date(family, tmp_path):
    set_plain_words(family / "good_public/ledger/MD_0002.md", "Squaring does not always grow.", "2026-11-03")
    out = build(family / "good_public", tmp_path)
    assert 'pw-reviewed">reviewed 2026-11-03' in (out / "MD_0002.html").read_text(encoding="utf-8")
    assert 'pw-reviewed">reviewed 2026-11-03' in (out / "index.html").read_text(encoding="utf-8")


def test_a_review_date_without_a_section_fails(family, tmp_path):
    set_plain_words(family / "good_public/ledger/MD_0002.md", None, "2026-11-03")
    with pytest.raises(CheckError, match="plain_words_checked"):
        build(family / "good_public", tmp_path)


def test_aka_names_reach_the_page_and_the_index_search(family, tmp_path):
    edit(family / "good_public/ledger/MD_0002.md", "\nrevises:", "\naka: [square exceeds the integer]\nrevises:")
    out = build(family / "good_public", tmp_path)
    assert "Also known as: square exceeds the integer" in (out / "MD_0002.html").read_text(encoding="utf-8")
    assert "square exceeds the integer" in (out / "index.html").read_text(encoding="utf-8")


# --- the graph ------------------------------------------------------------


def test_the_graph_draws_a_mirrored_pair_once_from_each_side(family, tmp_path):
    """MD_0005 above_of MD_0006 and MD_0006 below_of MD_0005 are one fact, drawn as one edge."""
    out = build(family / "good_private", tmp_path)
    five = (out / "MD_0005.html").read_text(encoding="utf-8")
    six = (out / "MD_0006.html").read_text(encoding="utf-8")
    assert five.count('class="edge"') == 1 and ">implies</text>" in five and 'href="MD_0006.html"' in five
    assert six.count('class="edge"') == 1 and ">implied by</text>" in six and 'href="MD_0005.html"' in six


def test_a_counterexample_is_a_refuted_by_edge_to_the_script(family, tmp_path):
    page = (build(family / "good_public", tmp_path) / "MD_0002.html").read_text(encoding="utf-8")
    assert ">refuted by</text>" in page and "MD_0002_toy.py" in page
    assert "github.com/FluxTech-UG/math-dept/blob/main/counterexamples/MD_0002_toy.py" in page


def test_the_public_build_names_an_unreleased_neighbour_without_a_link(family, tmp_path):
    edit(family / "good_public/ledger/MD_0004.md", "revises: null", "revises: MD_0007")
    page = (build(family / "good_public", tmp_path) / "MD_0004.html").read_text(encoding="utf-8")
    assert "MD_0007 <tspan" in page and "unreleased" in page and 'href="MD_0007.html"' not in page


def test_the_private_build_refuses_an_id_in_neither_ledger(family, tmp_path):
    edit(family / "good_private/ledger/MD_0005.md", "revises: null", "revises: MD_0099")
    with pytest.raises(CheckError, match="MD_0099 resolves to no entry"):
        build(family / "good_private", tmp_path)


def test_an_entry_with_no_links_says_so(family, tmp_path):
    page = (build(family / "good_public", tmp_path) / "MD_0003.html").read_text(encoding="utf-8")
    assert "<svg" not in page and "links to none" in page


# --- the two builds and the comment routes ----------------------------------


def test_the_private_build_shows_both_ledgers_and_marks_the_unreleased(family, tmp_path):
    out = build(family / "good_private", tmp_path)
    assert sorted(p.stem for p in out.glob("MD_*.html")) == [f"MD_000{n}" for n in range(1, 8)]
    five = (out / "MD_0005.html").read_text(encoding="utf-8")
    assert 'class="badge unreleased"' in five
    assert "github.com/FluxTech-UG/math-dept-private/blob/main/ledger/MD_0005.md" in five
    assert 'class="badge unreleased"' not in (out / "MD_0001.html").read_text(encoding="utf-8")


def test_every_page_carries_the_prefilled_private_issue_link(family, tmp_path):
    for root in ("good_public", "good_private"):
        page = (build(family / root, tmp_path, name=f"out-{root}") / "MD_0001.html").read_text(encoding="utf-8")
        assert "https://github.com/FluxTech-UG/math-dept-private/issues/new?title=MD_0001%3A%20" in page
        assert "labels=comment" in page and "body=Entry%3A%20MD_0001" in page


def test_the_public_build_names_citing_repos_only_and_drops_the_request(family, tmp_path):
    """A consumer's document path, its anchor and the request token stay in the private view."""
    entry = family / "good_public/ledger/MD_0001.md"
    edit(entry, "cited_by: []", "cited_by: ['Repo:docs/a.md §2', 'Repo:docs/b.md §3']")
    edit(entry, "request: null", "request: 'MDR:2026-09-04-three-basin#C1'")
    public = (build(family / "good_public", tmp_path, name="pub") / "MD_0001.html").read_text(encoding="utf-8")
    private = (build(family / "good_private", tmp_path, name="priv") / "MD_0001.html").read_text(encoding="utf-8")
    for detail in ("docs/a.md", "§2", "MDR:2026-09-04-three-basin#C1"):
        assert detail not in public, detail
        assert detail in private, detail
    assert public.count("<li><code>Repo</code></li>") == 1


def by_repo_groups(index: str) -> list[tuple[str, str, list[str]]]:
    """(anchor, heading, entry IDs) for each group of the index's by-repo section, in page order."""
    start = index.index('<section id="by-repo">')
    section = index[start:index.index("</section>", start)]
    groups = re.findall(r'<h3 id="([^"]+)">(.*?)</h3>(.*?)(?=<h3 |\Z)', section, re.S)
    return [(anchor, heading, re.findall(r'href="(MD_\d{4})\.html"', body)) for anchor, heading, body in groups]


def test_the_index_groups_the_entries_by_the_repo_that_cites_them(family, tmp_path):
    """John, 2026-11-04: "sort by connection to repos". One group per citing repo, largest first and
    then by name, an entry under every repo that cites it, the uncited last; the public build names
    the repo and never the document."""
    ledger = family / "good_public/ledger"
    edit(ledger / "MD_0001.md", "cited_by: []", "cited_by: ['Beta:docs/a.md §2', 'Alpha:docs/b.md §3']")
    edit(ledger / "MD_0002.md", "cited_by: []", "cited_by: ['Beta:docs/c.md §4', 'Beta:docs/d.md']")
    edit(ledger / "MD_0003.md", "cited_by: []", "cited_by: ['Gamma:docs/e.md §5']")
    index = (build(family / "good_public", tmp_path) / "index.html").read_text(encoding="utf-8")
    assert '<a href="#by-topic">by topic</a>' in index and '<a href="#by-repo">by repo</a>' in index
    groups = by_repo_groups(index)
    assert [(anchor, ids) for anchor, _, ids in groups] == [
        ("repo-beta", ["MD_0001", "MD_0002"]), ("repo-alpha", ["MD_0001"]), ("repo-gamma", ["MD_0003"]),
        ("uncited", ["MD_0004"])]
    assert [heading.split(" <")[0] for _, heading, _ in groups[:3]] == ["Beta", "Alpha", "Gamma"]
    section = index[index.index('<section id="by-repo">'):]
    section = section[:section.index("</section>")]
    for detail in ("docs/", "§2", ".md"):
        assert detail not in section, detail


def test_the_private_index_groups_the_unreleased_entries_too(family, tmp_path):
    index = (build(family / "good_private", tmp_path) / "index.html").read_text(encoding="utf-8")
    groups = by_repo_groups(index)
    assert [(anchor, ids) for anchor, _, ids in groups] == [
        ("repo-toyrepo", ["MD_0005", "MD_0006"]),
        ("uncited", ["MD_0001", "MD_0002", "MD_0003", "MD_0004", "MD_0007"])]
    toy = index[index.index('<h3 id="repo-toyrepo">'):index.index('<h3 id="uncited">')]
    assert toy.count('class="badge unreleased"') == 2


def test_a_merged_entry_shows_where_it_merged_instead_of_empty_provenance(family, tmp_path):
    """`merged` may omit raised_by and stipulated_by (the schema); the page points at the survivor."""
    entry = family / "good_public/ledger/MD_0003.md"
    edit(entry, "status: cited", "status: merged")
    edit(entry, "merged_into: null", "merged_into: MD_0001")
    edit(entry, "  raised_by:\n    repo: math-dept\n    domain: the toy source's own setting\n"
         "    doc: null\n    anchor: null\n    application: null\n", "  raised_by: null\n")
    edit(entry, "  stipulated_by:\n    who: claude\n    date: 2026-09-01\n    model: null\n    request: null\n",
         "  stipulated_by: null\n")
    page = (build(family / "good_public", tmp_path) / "MD_0003.html").read_text(encoding="utf-8")
    assert "raised by</dt><dd>None" not in page and "<dt>stipulated</dt>" not in page
    assert 'Merged into <a class="idref" href="MD_0001.html">MD_0001</a>' in page


def test_giscus_waits_for_its_values(family, tmp_path):
    page = (build(family / "good_public", tmp_path) / "MD_0001.html").read_text(encoding="utf-8")
    assert "Public discussion is not open yet." in page and "giscus.app" not in page
    assert "when the site is published" not in page


def test_giscus_appears_once_filled_and_on_the_public_build_only(family, tmp_path):
    cfg = settings(tmp_path, GISCUS_FILLED)
    public = (build(family / "good_public", tmp_path, cfg, "pub") / "MD_0001.html").read_text(encoding="utf-8")
    assert 'src="https://giscus.app/client.js"' in public and 'data-term="MD_0001"' in public
    assert 'data-mapping="specific"' in public and 'data-repo-id="R_kgDOtest"' in public
    private = (build(family / "good_private", tmp_path, cfg, "priv") / "MD_0001.html").read_text(encoding="utf-8")
    assert "giscus" not in private


def test_a_half_filled_giscus_table_is_refused(tmp_path):
    with pytest.raises(ConfigError, match="half filled"):
        settings(tmp_path, GISCUS_FILLED.replace('"Entries"', '"FILL the category"'))


# --- figures, the output folder, and the check ------------------------------


def test_a_figure_is_copied_and_shown(family, tmp_path):
    figures = family / "good_public/figures"
    figures.mkdir()
    (figures / "MD_0002.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>\n', encoding="utf-8")
    out = build(family / "good_public", tmp_path)
    assert (out / "figures/MD_0002.svg").is_file()
    assert '<img src="figures/MD_0002.svg"' in (out / "MD_0002.html").read_text(encoding="utf-8")
    assert "<img" not in (out / "MD_0001.html").read_text(encoding="utf-8")


def test_a_figure_that_is_not_svg_fails(family, tmp_path):
    (family / "good_public/figures").mkdir()
    (family / "good_public/figures/MD_0002.svg").write_text("PNG", encoding="utf-8")
    with pytest.raises(CheckError, match="not an SVG"):
        build(family / "good_public", tmp_path)


def test_the_build_never_clears_a_folder_it_did_not_write(family, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "notes.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ConfigError, match="no earlier site build wrote"):
        site.build(family / "good_public", out, settings(tmp_path))
    assert (out / "notes.txt").is_file()


def test_the_build_is_deterministic(family, tmp_path):
    first = build(family / "good_private", tmp_path, name="a")
    second = build(family / "good_private", tmp_path, name="b")
    for page in sorted(first.iterdir()):
        assert page.read_bytes() == (second / page.name).read_bytes(), page.name


def test_check_fails_on_an_unclosed_formula_and_names_where(family, tmp_path, capsys):
    edit(family / "good_public/ledger/MD_0002.md", "- **H1.** $n$ ranges", "- **H1.** $n ranges")
    code = site.main(["--repo", str(family / "good_public"), "--config", str(tmp_path / "missing.toml"),
                      "--check"])
    assert code == 1 and "missing.toml is missing" in capsys.readouterr().err
    settings(tmp_path)
    code = site.main(["--repo", str(family / "good_public"), "--config", str(tmp_path / "site.toml"), "--check"])
    err = capsys.readouterr().err
    assert code == 1 and "MD_0002.md" in err and "## Hypotheses" in err and "unclosed $" in err


def test_a_link_to_a_file_the_build_did_not_write_fails(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "index.html").write_text('<html><body><a href="MD_0042.html">x</a></body></html>', encoding="utf-8")
    with pytest.raises(CheckError, match="MD_0042.html names no file"):
        site._verify(out)


def test_this_repo_builds_clean(capsys):
    """The `make check` line: every entry of this ledger renders, with the committed settings."""
    assert site.main(["--repo", str(REPO_ROOT), "--check"]) == 0
    assert "[public build]" in capsys.readouterr().out


def test_the_conventions_make_check_row_names_every_recipe_line():
    """docs/CONVENTIONS.md's `make check` row lists every line the Makefile's `check:` target runs."""
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8").splitlines()
    recipe = []
    for line in makefile[makefile.index("check:") + 1:]:
        if not line.startswith("\t"):
            break
        recipe.append(line.strip())
    assert recipe, "the Makefile's check: target runs nothing"
    conventions = (REPO_ROOT / "docs/CONVENTIONS.md").read_text(encoding="utf-8").splitlines()
    rows = [line for line in conventions if line.startswith("| `make check` |")]
    assert len(rows) == 1, f"docs/CONVENTIONS.md has {len(rows)} `make check` rows, not one"
    missing = [command for command in recipe if f"`{command}`" not in rows[0]]
    assert not missing, f"docs/CONVENTIONS.md's `make check` row lacks {missing}"
