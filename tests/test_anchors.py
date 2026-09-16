"""The anchor grammar: one case per form, plus the two ways an anchor is broken.

Every form is read off the anchor's own syntax, so these cases are also the
readable statement of what an author may write in `raised_by.anchor`.
"""

import pytest

from mdept import anchors

BACKLOG = """# Improvements

- **A8. The two-parameter gain term is implemented on the linear tiers**
  Some prose about the item.
- **A8(c). The cross-gain bank cannot follow a substitution of the six.**
  More prose.
- **A9. The next item.**
"""

DESIGN = """# Design

## 21. Real-fluid thermodynamics

### 21.1 Where the parameterisation contradicts itself

### 21.3 The gain term for a two-parameter medium

### 21.30 A decoy that must not match 21.3
"""

PLAN = """# Plan

## 5. Open items

19. The item before.
20. The closure's sign on the bed is one unsupplied number.
21. The item after.

## 6. Later items

20. A different item 20, under a different heading.
"""

PAPER = r"""\begin{theorem}\label{eq:gen-carnot-control}
The bound as printed.
\end{theorem}
"""

PROSE = """# A document with no ID space

What the basilica cannot control for is the thing this section is about.
"""


@pytest.mark.parametrize(
    "anchor,form",
    [
        ("A8", "item"),
        ("A8(c)", "item"),
        ("D4", "item"),
        ("T1", "item"),
        ("§21.3", "heading"),
        ("§5 item 20", "heading-item"),
        ("label:eq:gen-carnot-control", "label"),
        ('text:"What the basilica cannot control for"', "text"),
        ("A heading that reads like prose", "unknown"),
        ("", "unknown"),
        ("§", "unknown"),
    ],
)
def test_the_form_is_read_off_the_syntax(anchor, form):
    assert anchors.classify(anchor) == form


def test_an_item_id_resolves_at_its_own_line():
    hit = anchors.resolve("A8", BACKLOG)
    assert (hit.form, hit.line) == ("item", 3)


def test_an_item_id_does_not_match_a_sub_item():
    """`A8` and `A8(c)` are two items, and `A8` names exactly one of them.

    The sub-item's line opens with `A8(`, so a resolver that accepted the ID
    followed by any character at all would find two lines for one anchor and
    could not say which raised the statement.
    """
    assert [hit.line for hit in anchors.matches("A8", BACKLOG)] == [3]
    assert [hit.line for hit in anchors.matches("A8(c)", BACKLOG)] == [5]


def test_a_repeated_item_id_is_ambiguous_rather_than_resolved():
    doubled = BACKLOG + "\n- **A8. The same ID, written twice.**\n"
    assert [hit.line for hit in anchors.matches("A8", doubled)] == [3, 9]
    assert anchors.resolve("A8", doubled) is None


def test_a_numbered_heading_resolves_and_does_not_prefix_match():
    hit = anchors.resolve("§21.3", DESIGN)
    assert hit.line == 7 and hit.text.endswith("two-parameter medium")
    assert anchors.resolve("§21.5", DESIGN) is None
    assert anchors.resolve("§21", DESIGN).line == 3, "the parent heading, not its children"


def test_a_numbered_item_is_scoped_to_its_heading():
    hit = anchors.resolve("§5 item 20", PLAN)
    assert hit.line == 6 and "unsupplied number" in hit.text
    other = anchors.resolve("§6 item 20", PLAN)
    assert other.line == 11


def test_a_latex_label_resolves():
    hit = anchors.resolve("label:eq:gen-carnot-control", PAPER)
    assert (hit.form, hit.line) == ("label", 1)
    assert anchors.resolve("label:eq:absent", PAPER) is None


def test_a_text_anchor_resolves_on_the_literal():
    hit = anchors.resolve('text:"What the basilica cannot control for"', PROSE)
    assert (hit.form, hit.line) == ("text", 3)
    assert anchors.resolve('text:"a phrase that is not there"', PROSE) is None


def test_a_text_anchor_takes_its_first_occurrence():
    """Uniqueness is required of every form but this one: a phrase repeated in
    prose is one phrase, and demanding it appear once would rule out the only
    form available to a document with no ID space."""
    repeated = PROSE + "\nWhat the basilica cannot control for, again.\n"
    assert anchors.resolve('text:"What the basilica cannot control for"', repeated).line == 3


def test_an_unknown_form_resolves_nowhere_and_never_raises():
    assert anchors.matches("just some words", PROSE) == []
    assert anchors.resolve("just some words", PROSE) is None


@pytest.mark.parametrize(
    "line,text",
    [
        ("- **A8. Title**", "A8. Title**"),
        ("## D4. Title", "D4. Title"),
        ("### § 21.3 Title", "21.3 Title"),
        ("  20. An item", "An item"),
        ("> - `MD_0007` quoted", "MD_0007` quoted"),
    ],
)
def test_markup_is_stripped_before_a_line_is_read(line, text):
    assert anchors.line_text(line) == text
