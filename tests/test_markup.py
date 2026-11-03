"""`mdept.markup`: the entry-body markdown, rendered with its math left intact for KaTeX."""

import pytest

from mdept import markup


def link(entry_id: str) -> str:
    return f'<a href="{entry_id}.html">{entry_id}</a>'


def render(text: str) -> str:
    return markup.render(text, link)


def test_math_is_kept_verbatim_while_the_text_around_it_is_markdown():
    html = render("Let $x_1 = a*b*c$ and **bold $y_2$**, *it* and _em_.")
    assert "$x_1 = a*b*c$" in html
    assert "<strong>bold $y_2$</strong>" in html and "<em>it</em>" in html and "<em>em</em>" in html


def test_display_math_on_its_own_lines_is_one_block_with_its_html_escaped():
    html = render("$$\n\\begin{aligned} a &= b \\\\ c &< d \\end{aligned}\n$$")
    assert html.startswith('<div class="math-display">$$')
    assert "a &amp;= b" in html and "c &amp;&lt; d" in html


def test_raw_html_in_a_body_is_escaped():
    assert "&lt;script&gt;" in render("A <script>alert(1)</script> line.")


def test_entry_ids_are_linked_outside_code_and_math():
    html = render("See MD_0007, `MD_0008` and $MD_0009$, not MD_0010_slug.")
    assert '<a href="MD_0007.html">MD_0007</a>' in html
    assert "<code>MD_0008</code>" in html and "$MD_0009$" in html and "MD_0010_slug" in html
    assert "MD_0010.html" not in html


def test_an_escaped_dollar_is_a_literal_kept_apart_from_the_formulas():
    assert '<span class="dollar">$</span>5' in render("It costs \\$5.")


def test_lists_nest_by_indentation_and_numbered_lists_keep_their_start():
    html = render("- **H1.** one\n  continued\n- two\n  - nested\n\n3. third\n4. fourth")
    assert "<ul><li><strong>H1.</strong> one\ncontinued</li><li>two\n<ul><li>nested</li></ul></li></ul>" in html
    assert '<ol start="3"><li>third</li><li>fourth</li></ol>' in html


def test_a_list_interrupts_a_paragraph():
    assert render("Then:\n- a\n- b") == "<p>Then:</p>\n<ul><li>a</li><li>b</li></ul>"


@pytest.mark.parametrize("text, message", [
    ("an unclosed $x formula", "unclosed \\$"),
    ("an unclosed $$ x display", "unclosed \\$\\$"),
    ("$$\nx = 1\n", "never closed"),
    ("```\ncode", "never closed"),
    ("[x](javascript:alert(1))", "neither a web address"),
])
def test_what_would_render_as_nonsense_is_an_error(text, message):
    with pytest.raises(markup.MarkupError, match=message):
        render(text)
