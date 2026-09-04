# math-dept

A public ledger of the mathematical statements that sit between a published result
and an application of it. Applying a theorem quietly stipulates a few statements in
between: a hypothesis the application only nearly satisfies, a discrete version of a
continuous claim, an ordering nobody proved. Each such stipulation becomes one entry
here, and each entry is proven, conjectured, or refuted, with provenance. Proofs are
Lean 4 + Mathlib; validation and refutation are Python (the `mdept` package). The repo
is consumed by reading and citation. It imports nothing: no consumer code, no
simulation, no application internals.

These house rules are self-contained and this file `@import`s nothing. The repo is
public, so a session that has never seen the wider family conventions must be able to
work here from this file alone.

## Place in the family

Consumers cite entries by ID and read them. They never import this repo, and it never
reaches back into them.

A private sibling, `math-dept-private`, holds the source extracts, the request inbox,
the triage records, and unreleased entries with their Lean modules. It depends on this
package (a Lake `require` by path, plus an editable install of `mdept`); the dependency
never runs the other way, so nothing public is allowed to reference anything private.
Releasing an entry moves its files from private to public without renaming anything:
the ID and the Lean declaration name are the same before and after, so an outside
citation keeps resolving.

Point at another repo's axioms, definitions, and results by reference; never copy them
into an entry. A copied axiom drifts from its source the moment the source is edited,
and the drift is silent. An entry that needs an external definition names it and states
the hypotheses it actually uses.

## Where to look

| Path | What it holds |
|---|---|
| `docs/protocol.md` | The flow end to end, both sides: how a request is filed and how it is worked. |
| `docs/triage.md` | The math-side ladder (cheap stages first), its budgets, and close-out. |
| `docs/CONVENTIONS.md` | The repo contract: front-matter schema, the invariants, the generated views. |
| `ledger/INDEX.md` | Generated. Grep the ID here first; it is the fastest route to an entry. |
| `ledger/TEMPLATE.md` | The entry template: closed key set plus the four body headings. |
| `bibliography.md` | Citations only, topic-indexed. Nothing is paraphrased here. |
| `counterexamples/` | `MD_0007_slug.py` files, each defining `refute() -> Witness`. |
| `proofs/` | Informal proofs, each with a Formalization blockers section. |
| `MathDept/` | Lean: `Defs/` (shared definitions), `Results/` (settled), `Conjectures/` (`sorry` allowed), `Smoke.lean`. |
| `.claude/skills/{prove,refute,math-extract,lean-review}/` | The working procedures for each job. |
| `docs/MAP.md` | Generated file map (`repo-outline`). Read it to find a symbol. |

## Writes stay inside this repo

A session working here edits files here and nowhere else. When work in this repo raises
something a consumer needs to change, say so in the report and let a session in that
repo make the change.

Requests for the math side are filed as a new file in the private repo's `inbox/`, by
the consumer session that needs the statement, never from here. That single inbox file
is the only write any foreign session makes into either math repo.

## Ledger discipline

- **One statement per entry**, and the filename is the ID: `ledger/MD_0007.md`.
- **IDs are permanent and never reused.** Entry files are never deleted or renamed. A
  duplicate becomes `status: merged` with `merged_into`; a restated theorem is a new
  entry with `revises`. Outside citations name IDs, so an ID has to resolve forever.
- **A settled entry's Statement and Hypotheses are frozen.** A change of either is a new
  entry with `revises` pointing back. The freeze is what makes a citation mean one
  definite thing, and the Lean type is hashed into `statement_hash` to enforce it.
- **Partial results are their own entry**, linked by `special_case_of`. A partial result
  is never expressed as a status.
- **Attempts live in the private repo's `triage/MD_0007.md`**, dated, one record per
  stage. The entry body states the current state only.

## Statement fidelity comes before any proof effort

Write the statement with every quantifier and every hypothesis explicit, then round trip
it before spending anything on a proof: a different context (a different agent, not the
one that wrote the formalization) informalizes the formal statement back into prose, and
the two prose versions are compared. Do this for the ledger statement, and again for the
Lean statement before the first proof attempt. An hour spent proving the wrong statement
does not just waste the hour, it produces a confident wrong entry that others cite.

Three signals mean the formalization is probably wrong, not the mathematics: the
statement is **false**, the statement is **suspiciously easy**, or the statement **does
not imply the downstream use**. On any of them, re-examine the statement before touching
the proof.

## `sorry` lives only under `MathDept/Conjectures/`

The directory encodes the state of the work. `Conjectures/` may carry `sorry`, and its
statements must still typecheck. `MathDept/Results/`, `MathDept/Defs/`, and
`MathDept/Smoke.lean` are audited: every declaration's axioms must lie within
{`propext`, `Classical.choice`, `Quot.sound`} plus the per-declaration lines in
`audit/axiom-allowlist.txt`.

The audit is the real fence, and the `sorry` grep is only the cheap first pass: a
`sorryAx` that reaches a Result through an imported conjecture is invisible to grep and
fails the audit. A `native_decide` proof is refused unless that declaration has an
allowlist line, because it moves the trust from the kernel to the compiler and that
trade should be a recorded decision. On the pinned toolchain it surfaces as a
generated per-declaration axiom, so copy the axiom name from what `make lean`
reports rather than guessing it.

## Provenance is required on every non-merged entry

Public provenance is abstract. `raised_by` carries a `repo` name and one neutral `domain`
line naming the mathematical area. The application's document, its anchor, and the
rationale for needing the statement stay in the private repo, which is what lets released
entries be public at all.

`stipulated_by` and `settled_by` are public and carry who (john, claude, or both), the
date, and the model. That credit trail is the reason provenance is a required field
rather than a courtesy: the ledger is meant to reconstruct who and what settled each
statement, years later, from the repo alone.

## Trust tiers: `forum` and `draft` are never the source of a `cited` entry

Every bibliography entry declares a `Kind`: paper, book, notes, mathlib, forum, or draft.
A `cited` entry is a published result taken as-is, with no proof of our own behind it,
so it must rest on a paper, book, notes, or mathlib source. A forum answer or an
unpublished draft can inform an entry, appear in its notes, or seed a conjecture. It can
never be the evidence that settles one.

## Prose

- **No em dashes.** Use a period, a comma, a colon, or parentheses. Invariant I17 greps
  every `.md` for U+2014 and fails the check.
- **LaTeX readable as source.** Inline `$...$` and display `$$...$$`, with every symbol
  defined in the Statement or Hypotheses of the same entry.
- **Living documents.** Every file states what is. When an approach changes, rewrite the
  passage and delete what it replaced; git holds the history.

## Commands

| Command | What it runs |
|---|---|
| `make check` | The validator, the generated-view drift guards, and the `sorry` fence. Counterexamples and the Lean audit are their own targets. |
| `make regen` | Rewrites the generated views: `ledger/INDEX.md`, `ledger.json`, `MathDept.lean`, `docs/MAP.md`. |
| `make lean` | `lake build`, then the axiom audit, cached to `audit/latest.json`. |
| `make counterexamples` | Loads and verifies every script in `counterexamples/`. |
| `make test` | The pytest suite, which is the one command that covers all guards. |

Underneath those:

- `python -m mdept.check [--run-counterexamples] [--family] [--lean]` validates the
  ledger. `--lean` reads the cached audit JSON and fails if it is stale against the Lean
  sources. `--family` resolves sibling repos through the private repo's `repos.yaml`, so
  it belongs to a session in `math-dept-private`.
- `python -m mdept.index --check` regenerates the views in memory and fails on drift.
- `python -m mdept.audit all --json` is the contract the validator consumes: sorry scan,
  per-declaration axioms and pretty-printed types, counterexample results.
- `python -m mdept.refute --all` verifies every counterexample witness.
- `python -m mdept.new` allocates the next ID with provenance pre-filled.
- `python -m mdept.release MD_0007` moves a settled entry from private to public and
  abstracts its provenance.
- `python scripts/gen_root.py --write` regenerates `MathDept.lean` after adding or moving
  a module; `repo-outline --write` regenerates `docs/MAP.md` after adding or moving a
  symbol. Both have `--check` guards that fail while stale.
- `python -m pytest -v` runs everything. Lean-dependent tests skip loudly without `lake`
  unless `MATHDEPT_REQUIRE_LEAN=1`.
- Lean directly: `lake build`, then `lake env lean scripts/AxiomAudit.lean`.

## Git

This repo owns its own `.git`, and git operations here scope to it.

- `git pull` on `main` is the first action of a session here, before reading deeply or
  editing, so every change starts from the current remote state.
- Commit to `main` when working solo. A branch and a pull request are for a collaborator's
  review, not a solo ritual.
- Commit generated views in the same commit as the change that caused them, so any
  checkout passes `make check`.
- Push before ending the session.
