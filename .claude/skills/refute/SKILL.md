---
name: refute
description: >
  Find and certify a counterexample to one math-dept ledger entry. Use when a
  session says "refute MD_0007", "find a counterexample", "is this actually
  true", when the triage ladder reaches stage S1, when a prove attempt reports
  that the statement looks false, or when a fresh conjecture is raced with both
  attempts running in parallel. Proving a statement is the prove skill.
---

# Refute one ledger entry

A refutation is a result: it ends the ladder for its entry, and when the Lean negation
closes it lands in `MathDept/Results/` beside the proofs. Run from the repo root. While
an entry is unreleased its Lean file is `MathDeptPrivate/Conjectures/MD_####.lean` in
`math-dept-private`; the namespace is `MathDept.MD_####` in both libraries, so a release
moves the module path and keeps the declaration name.

## Cheap first

1. The `python -m mdept.symbolic` helpers: `is_identity(lhs, rhs, **assumptions)`
   for a claimed identity, `inequality_counterexample(expr, var, domain)` for a
   bound, `rational_witness(expr, var, lo, hi)` when an exact rational point is
   plausible. Sympy settles more of these than expected, and settles them in the
   exact form the ledger needs.
2. Boundary cases of each hypothesis by hand: the empty case, the degenerate
   dimension, equality where the source assumes strictness, the tie. Most
   stipulations that are false are false right here.
3. `mdept.search.random_search(pred, sampler)` last. Sampling is the expensive
   rung and the least informative when it finds nothing.

## A numeric hit is a lead, not a witness

A float that violates the claim tells you where to look. Move to exact values in
that neighborhood (`int`, `fractions.Fraction`, a sympy expression) and re-check
there. `Witness.verify()` raises on a float unless `numeric=True`, which is the
mechanism holding this line.

Set `numeric=True` only for a claim genuinely about floating-point behaviour,
or when the exact upgrade failed after real effort; say which in `note`.

## Write the artifact

`counterexamples/MD_####_slug.py`, stem `^MD_[0-9]{4}_[a-z0-9_]+$`, deterministic:

```python
"""MD_0007: <the claim, as the ledger entry states it>."""
from fractions import Fraction
from mdept.refute import Witness

def refute() -> Witness:
    return Witness(
        entry="MD_0007",
        point={"x": Fraction(1, 3), "n": 2},
        claim=lambda x, n: <the stipulated predicate at that point>,
        note="<hypotheses this point satisfies; the conclusion it violates>",
    )
```

`python -m mdept.refute MD_####` must verify before anything else happens. A
witness that does not verify is not evidence, whatever the prose around it says.

## Certify in Lean when feasible

Add `theorem refuted : ¬ (...)` to the entry's Lean file, negating the frozen
`statement` type verbatim, and prove it from the witness (`decide`, `norm_num`,
an explicit instance). Then `git mv` the file into `MathDept/Results/`.

Do this only when no proof attempt is running on the same entry. In a race under
`math-orchestration` the entry's Lean file belongs to the prover, so the refuter's only
artifact is the counterexample script. The negation is then a separate follow-up the
lead assigns once the race has resolved and the file is free; it is the step that lifts
the entry from the weaker tier below to the strongest.

The ledger status word is `refuted` in every case: the status enum is closed
and carries no qualifier. What varies is the strength of the evidence behind it,
which the entry records:

- Strongest: an exact witness AND a Lean negation that compiles sorry-free with
  axioms within {`propext`, `Classical.choice`, `Quot.sound`} plus any
  allowlisted line. Set `formal.decl` and `formal.file`.
- Weaker: the witness verifies but the negation is not formalized yet. The Lean
  file stays in `MathDept/Conjectures/`, `formal.decl` stays null, and Current
  notes say what blocks the formalization.
- Weakest: the witness carries `numeric: true`. The generated views display this
  as "refuted (numeric)". Upgrading the point to exact values removes the
  qualifier, and is the first thing to try before reporting the entry settled.

## The statement stays frozen

Never edit Statement or Hypotheses to make the counterexample land: the value of the
witness is that it kills the statement as stipulated. A repaired version is a new entry
ID with `revises`, linked from this one, and that pair is the record consumers read.

## Close out under orchestration

As a `prover` agent in a wave under `math-orchestration`, the run ends at the artifact:
`counterexamples/MD_####_slug.py`, with `python -m mdept.refute MD_####` verifying.
Leave it in place and report the entry ID, the outcome (exact witness, numeric witness,
or none found), the artifact path, what was tried, the evidence tier it reaches, and
anything the lead must decide. Steps 1 to 5 below and the `git mv` into `Results/` are
the lead's, after the wave: set no `status` or other ledger field, run no `make regen`
or any part of it (`gen_root.py`, `mdept.index`, `repo-outline`), and make no commit. A
status the adversarial review has not seen is a status nobody checked, and each
generated view is derived from the whole tree, so regenerating or committing mid-wave
collides with entries the agent did not write.

## Close out: direct session

1. `python scripts/gen_root.py --write` (when a Lean file moved)
2. `python -m pytest`
3. `repo-outline --write`
4. Update `ledger/MD_####.md`: `status`, `evidence` (the counterexample path),
   `provenance.settled_by` with `how: counterexample`, and `formal.decl` and
   `formal.file` when the negation compiled.
5. `git commit -m "MD_####: refuted"`
