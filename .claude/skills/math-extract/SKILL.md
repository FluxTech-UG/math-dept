---
name: math-extract
description: >
  Extract a mathematical source (paper, book chapter, lecture notes, a Mathlib
  area) into an LLM-readable extract plus a bibliography entry for the math
  ledger. Use when a session says "extract this paper", "add [BibTag]", "read
  this source for the ledger", when an entry is about to be filed as status
  cited and no extract backs it, or when a bibliography tag is referenced and
  its extract is missing. Statements are extracted here and formalized by the
  prove skill, never both in one pass.
---

# Extract a mathematical source

Two files, both written from the source's actual full text:

- `sources/[BibTag]_extract.md` in the private sibling repo `math-dept-private`,
  which holds every extract.
- The public `bibliography.md`: an index entry, citations only, no paraphrase.

A PreToolUse hook confines writes to those two surfaces. Lean files, ledger
entries and counterexamples belong to other skills, and a write there exits 2:
the guard working, not a bug to route around.

## Work from the full text or stop

Read the source itself. An abstract or a recollection of the result produces an
extract that reads authoritative and states hypotheses the source does not have,
the failure mode this ledger exists to catch. When the full text is unreachable,
report that and file nothing. Budget the extract at 1,200 to 1,800 tokens.

## Extract skeleton

```markdown
# Source Extract: [Short Descriptive Title]

**Citation:** full citation, DOI or URL
**Bibliography tag:** [BibTag]
**Kind and trust:** book (citable) | forum (not citable as sole evidence)

---

## Core Contribution
## Statements used
### Thm 7.1.x (the source's own numbering)
- **Setting:** ...
- **Hypotheses:** H1 ... (exactly as the source states them)
- **Conclusion:** $...$
- **Proof strategy (5 to 10 lines):** numbered steps
## Generalizations the source itself notes
## Mathlib coverage
## Hooks
## Caveats and Limitations
## Relevance
```

**Statements used** carries every hypothesis verbatim, including ones the source
states in passing prose. The gap between those and what an application actually
satisfies is what a ledger entry is made of, so a dropped hypothesis erases the
entry before it exists.

**Mathlib coverage** cites full declaration names verbatim with the revision,
checked in `.lake/packages/mathlib` or the docs (`Matrix.PosSemidef`,
`LinearMap.finrank_range_add_finrank_ker`). When nothing covers it, write "none
found, searched YYYY-MM-DD"; a guessed declaration name is worse than none.

**Hooks** names each place an application's assumptions are weaker or stronger
than the theorem's, plus the ledger entry it seeded (`MD_0007`) or the candidate
it proposes. A hook with no ID and no candidate is an observation, not a hook.

## Trust tiers

`Kind` is one of paper, book, notes, mathlib, forum, draft. A `forum` or `draft`
source is never the sole evidence for a `cited` entry: extract it, mark it, and
name in Caveats what a citable source must confirm.

## Bibliography entry

```markdown
### [HornJohnson2013] Matrix Analysis, 2nd ed.
- **Authors:** Horn, R. A.; Johnson, C. R.
- **Source:** Cambridge University Press (2013). Ch. 7, Thm 7.1.x
- **Kind:** book
- **Used for:** kernel of a PSD sum is the intersection of kernels
- **Mathlib:** `Matrix.PosSemidef`
- **Ledger:** MD_0001, MD_0002
```

Index the tag in the Topic Index table at the top of `bibliography.md` in the
same edit: the validator fails on a tag indexed nowhere.

## Close out under orchestration

As a `math-extractor` agent in a wave under `math-orchestration`, the run ends at the two
files: the extract and the `bibliography.md` entry with its Topic Index row. Leave both
in place and report the BibTag, the outcome (extracted, or full text unreachable and
nothing filed), both paths, which statements were taken and what the source turned out
not to state, and anything the lead must decide. Every ledger entry a Hook seeds is the
lead's to allocate, and so are the generated views (`make regen`, `python -m mdept.index`)
and the commit; the write guard already holds the ledger half of that line. Each view is
derived from the whole tree, so regenerating or committing mid-wave collides with entries
the agent did not write.

## Close out: direct session

With no orchestration above the run, `make check` (the bibliography and index validators)
and the commits are yours: the extract commits in `math-dept-private`, the bibliography
edit commits here, one commit each, because a commit never spans two repos. A candidate a
Hook proposes becomes a ledger entry in its own pass, never in this one.
