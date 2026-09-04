---
name: prove
description: >
  Attempt a Lean 4 + Mathlib proof of one math-dept ledger entry. Use when a
  session names an entry to prove ("prove MD_0007", "formalize this statement",
  "take the next conjecture"), when the triage ladder reaches stage S4, or when
  an entry at status conjectured or open needs a formal proof. Also use to
  record attempt notes on an entry that resisted a time-boxed attempt. Finding
  a counterexample is the refute skill; judging a finished proof is lean-review.
---

# Prove one ledger entry

The entry ID is the unit of work: one Lean file, one namespace, one commit
subject. Run from the repo root.

## Freeze the statement first

1. Read `ledger/MD_####.md`. Statement and Hypotheses are the contract; the
   `between` links name entries that may already supply pieces.
2. Write `MathDept/Conjectures/MD_####.lean` from the entry template: targeted
   imports (`import Mathlib.Data.Real.Basic` and friends; `import Mathlib` lives
   in `MathDept/Smoke.lean` alone, because a full import costs minutes on every
   compile cycle), `namespace MathDept.MD_####`, a module docstring carrying the
   informal statement, one `theorem statement` whose body is `sorry`.
3. `lake build` exits 0 before any proof attempt. The green build freezes the
   type: what compiles is what gets proved. A statement that needs a different
   hypothesis is a NEW entry ID carrying `revises`, never an edit to this file.
   If you find yourself reasoning that one extra hypothesis would be harmless
   here, that is exactly the move this rule forbids.

While an entry is unreleased its Lean file is `MathDeptPrivate/Conjectures/MD_####.lean`
in `math-dept-private`. The namespace is `MathDept.MD_####` in both libraries, so a
release moves the module path and keeps the declaration name.

## Search before you prove

- Order: `lean_leansearch` and `lean_loogle` for candidates, then `exact?` and
  `apply?` against the live goal, then grep `.lake/packages/mathlib`.
- Hover every lemma name (`lean_goal`, `lean_diagnostic_messages`) before typing
  it into a proof. Invented Mathlib names are the top failure mode of this work,
  and they fail late, after a long build.
- Lean 3 syntax (`begin ... end`, `λ x, ...`, `from`) is an error, not a
  dialect. Write Lean 4: `fun x => ...`, `by`, term mode.

## Shape the proof

- Recipe first: state the proof as numbered prose steps in the docstring, turn
  each step into a named lemma above `statement` with a `sorry` body, then fill
  the leaves. A monolithic tactic block hides which step is the hard one.
- Split abstract from concrete: the general lemma over a typeclass, then the
  instance that applies it. Each half is separately debuggable.
- Gaps stay `sorry`. Closing a gap by adding a hypothesis silently changes the
  theorem, and `lean-review` rejects it as hypothesis creep.
- No helper lemma that restates the target in different notation.

## Tactic cascade on a leaf

`rfl → simp → ring → linarith → nlinarith → omega → positivity → exact? →
apply? → aesop`. Cheap first: `aesop` and `grind` time out and teach you nothing
when they do. A `maxHeartbeats` bump carries a one-line reason in the docstring.

## Budget

Default 40 turns. Stop and report when the goal state has not changed across 3
compile cycles: a stalled proof needs a different decomposition or a different
rung, never a longer budget on the same approach.

## Close out under orchestration

As a `prover` agent in a wave under `math-orchestration`, the run ends at the artifact:
the entry's Lean file, carrying the stuck-path attempt notes when the proof stalled.
Leave it where it sits and report the entry ID, the outcome (proven, stuck, or looks
false), the artifact path, what was tried and where progress stopped, and anything the
lead must decide.

Everything shared is the lead's, after the wave: `status` and every other ledger field,
the `git mv` into `Results/`, the commit, and `make regen` with its three parts
(`python scripts/gen_root.py --write`, `python -m mdept.index`, `repo-outline --write`
for `docs/MAP.md`). A status the adversarial review has not seen is a status nobody
checked, and each generated view is derived from the whole tree, so regenerating or
committing mid-wave collides with entries the agent did not write.

## Close out: proven, direct session

With no orchestration above the run, this close-out is yours.

1. Remove every `sorry`; `lake build` green.
2. `git mv MathDept/Conjectures/MD_####.lean MathDept/Results/MD_####.lean`
3. `python scripts/gen_root.py --write`
4. `python -m pytest`
5. `repo-outline --write`
6. Update `ledger/MD_####.md`: `status`, `formal.decl`, `formal.file`,
   `evidence`, `provenance.settled_by`, and `statement_hash` from the audit's
   pretty-printed type.
7. `git commit -m "MD_####: proven"`

## Close out: stuck

Leave the file in `Conjectures/`, in both modes. Append to the module docstring what
was tried, which lemma names were searched and rejected, and the goal state where
progress stopped. A direct session commits that as `MD_####: attempt notes`. The next
attempt reads the record cold, so write it for someone with no memory of this session.

## When it looks false

A goal that resists every decomposition, a hypothesis that never gets used, or a
boundary case that will not close: stop and switch to the `refute` skill. A
counterexample is a result, and finding it on turn 6 is cheaper than on turn 39.
