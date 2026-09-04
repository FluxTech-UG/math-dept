# math-dept

A ledger of the mathematical statements that sit between a published result and an
application of it, each one proven, conjectured, or refuted, with provenance. Proofs are
Lean 4 + Mathlib. Validation and refutation are Python.

## The problem

Applying a published theorem quietly stipulates statements in between the theorem and
the application. The source proves a bound for continuous fields and the application
uses it on a finite grid. The source assumes a hypothesis the application only nearly
satisfies. Two quantities are assumed to keep their order under an operation nobody
checked. Each of those is a real mathematical claim, and each is usually never written
down, let alone proved.

This repo writes them down. One statement per entry, with a permanent ID such as
`MD_0007`. Every entry is then pushed toward a verdict: cited from the literature,
proved in Lean, proved informally and reviewed, refuted by an explicit counterexample,
or recorded as open after a budgeted attempt. The outcome is recorded with provenance,
so a reader can reconstruct where the statement came from, who settled it, and how.

## Status vocabulary

| Status | Meaning | Required evidence |
|---|---|---|
| `cited` | A published result, taken as it stands | A bibliography tag of kind paper, book, notes, or mathlib |
| `conjectured` | Stipulated, not yet worked | Provenance: who raised it and who stipulated it |
| `open` | Worked to budget, still undecided | An attempt record naming what was tried and for how long |
| `proven-formal` | A Lean proof, sorry-free, standard axioms | A declaration under `MathDept/Results/` that passes the axiom audit |
| `proven-informal` | A written proof, reviewed in a later session | `proofs/MD_0007.md` with a Formalization blockers section, checked on a strictly later date |
| `refuted` | An instance satisfies the hypotheses and violates the conclusion | `counterexamples/MD_0007_slug.py` whose witness verifies exactly |
| `merged` | A duplicate of another entry | `merged_into` resolving to a live entry |

A settled entry's Statement and Hypotheses are frozen. Restating either is a new entry
that `revises` the old one, so a citation to an ID always means one definite thing.

## What an entry looks like

`ledger/MD_0007.md` opens with machine-checked front matter (excerpt; the full key set is
in `ledger/TEMPLATE.md` and `docs/CONVENTIONS.md`):

```yaml
---
id: MD_0007
title: Rank bound for a sum of positive semidefinite matrices
status: proven-formal
kind: lemma
topics: [linear-algebra]
formal:
  decl: MathDept.MD_0007.statement
  file: MathDept/Results/MD_0007.lean
evidence:
  - {kind: proof, path: proofs/MD_0007.md}
between:
  special_case_of: [MD_0003]
provenance:
  raised_by: {repo: <consumer>, domain: "one neutral line naming the area"}
  stipulated_by: {who: claude, date: 2026-09-04, model: claude-fable-5-1}
  settled_by: {who: both, date: 2026-09-05, how: lean, checked_by: null, model: claude-fable-5-1}
statement_hash: "sha256 of the audited Lean type"
---
```

The body is always the same four headings: **Statement** (LaTeX, every quantifier
explicit), **Hypotheses** (numbered H1, H2, ...), **Why it was raised** (two to five
lines), **Current notes** (the current state, with dated attempts kept elsewhere).

## Layout

```
math-dept/
  ledger/MD_0007.md        one statement per file; INDEX.md and ledger.json are generated
  bibliography.md          topic-indexed citations, with a trust Kind on every source
  proofs/                  informal proofs, each naming its formalization blockers
  counterexamples/         MD_0007_slug.py, each defining refute() -> Witness
  MathDept/                Lean: Defs/, Results/, Conjectures/, Citations.lean, Smoke.lean
  mdept/                   the Python package: schema, parse, check, index, audit, refute
  scripts/                 AxiomAudit.lean and the generated-root writer
  audit/                   the axiom allowlist and the cached audit JSON
  docs/                    protocol.md, triage.md, CONVENTIONS.md, MAP.md
  tests/                   pytest: the one command that runs every guard
```

## The Lean side

The repo root is a Lake package. Mathlib is pinned by release tag in `lakefile.toml`, and
`lean-toolchain` is Mathlib's own file at that same tag, so a checkout builds against
exactly one Mathlib revision.

Each entry gets one file, `MathDept/<state>/MD_0007.lean`, with its declarations in
`namespace MathDept.MD_0007`. Consumers cite `MathDept.MD_0007.statement`, and because
the namespace is the ID, that name survives every move between directories.

The directory encodes the state of the work. `Conjectures/` is the only place `sorry` may
appear, and even there the statement must typecheck. `Results/`, `Defs/`, and
`Smoke.lean` are audited by `scripts/AxiomAudit.lean`, which emits one JSON line per
declaration (module, axioms, pretty-printed type) and then fails if any audited
declaration depends on an axiom outside {`propext`, `Classical.choice`, `Quot.sound`}
plus the per-declaration lines in `audit/axiom-allowlist.txt`. That catches a `sorryAx`
arriving through an import, which a text search cannot see, and it refuses
`native_decide`, whose generated axiom is refused unless explicitly allowed.
The audited type is what the ledger hashes to keep a settled statement frozen.

## The Python side

`mdept` is the validator and the refutation toolkit.

**Validator.** `python -m mdept.check` runs twenty invariants over the ledger: filename
matches ID, IDs unique, front-matter schema exact with closed enumerations, status
matched to the evidence it requires, formal pointers resolving in the audit JSON with a
matching statement hash, counterexamples that load and verify, links that resolve with no
self-links and no links into merged entries, no contradiction (a refuted statement cannot
be implied by a proven one), generated views fresh, dates monotone, no em dashes, and
`sorry` fenced to `Conjectures/`. Each failure names the offending path and field.

**Refutation toolkit.** A counterexample is a Python file that defines
`refute() -> Witness`. A `Witness` carries the entry ID, the exact point, and the claim as
a callable; `verify()` requires the claim to evaluate to exactly `False` at that point,
and refuses a float in a witness not marked `numeric`. `mdept.symbolic` wraps sympy for
identity checks and inequality counterexamples; `mdept.search` runs randomized search over
a sampler. A numeric hit is a lead, not a verdict: it is upgraded to an exact witness
before the entry becomes `refuted`.

## Quick start

```bash
pip install -e ".[test]"     # Python side: validator, toolkit, tests
lake exe cache get           # Mathlib binaries for the pinned tag
lake build                   # ~1-3 minutes with the cache
python -m pytest -v          # every guard; Lean tests skip loudly without lake
make check                   # the ledger validator
```

## Citing an entry

Cite by ID: `MD_0007`. Only `proven-formal`, `proven-informal`, and `cited` entries count
as results. A `conjectured` or `open` entry is citable only as what it is, written out:
"conjectured, MD_0007". A `refuted` entry is cited to record that a line of reasoning is
closed, and any text citing it says "refuted" in the same line.

`ledger/INDEX.md` is generated from the entries: grep the ID there for its status, its
kind, its formal declaration, and its links to neighboring statements.

## Credit

Credit is recorded per entry, in `provenance.stipulated_by` and `provenance.settled_by`.
Each carries who (a person, a model, or both), the date, and the model that did the work.
That is why provenance is a required field rather than a courtesy: much of this ledger is
settled in collaboration between a human and a language model, and the repo is meant to
let anyone reconstruct, from the files alone, which statements came from where and who
put each verdict on the board.

## License

Apache-2.0. See `LICENSE`.
