---
name: lean-review
description: >
  Hostile review of a finished Lean formalization before its ledger entry
  changes status. Use when a prove or refute attempt reports done, when a
  session says "review MD_0007", "check this proof", "is this formalization
  honest", before any entry is set to proven-formal or refuted, and before a
  release. Run this in a fresh context that did not write the proof under
  review; a context reviewing its own work confirms it.
---

# Review one formalization as a hostile reviewer

Your job is to find the reason to REJECT. A formalization that survives a
genuine attempt to break it is worth the status change; one that was never
attacked is an untested claim with a green build.

Read into context: the ledger entry (Statement, Hypotheses, `provenance`), the
Lean file, and the extract's Statements-used section for the cited source. Do
not read other entries or the proof author's session notes.

## Checklist

Work every item and record evidence for each. An item you cannot check is a
FAIL, not a pass.

1. **Hypothesis creep.** Compare each binder in the Lean `statement` against the
   entry's Hypotheses and the source prose. Any hypothesis present in Lean and
   absent upstream is a REJECT: it means a gap got closed by assumption. Run
   `lean_minimal_hypotheses` and report every hypothesis it says is unused, each
   of which is either a misformalization or a weaker theorem worth its own ID.
2. **Non-vacuity.** Produce a concrete instance satisfying every hypothesis, and
   check it (`#eval`, `decide`, `norm_num`, an explicit term). A statement no
   object satisfies is true and worthless, and it typechecks exactly like a real
   one.
3. **Circular helpers.** Read every lemma above `statement`. A helper that
   restates the target in different notation, or that is discharged by the same
   fact it is meant to supply, is a REJECT.
4. **Axiom gate.** `#print axioms MathDept.MD_####.statement`, or `lean_verify`
   on the file. Axioms must lie within {`propext`, `Classical.choice`,
   `Quot.sound`} plus the declaration's own line in `audit/axiom-allowlist.txt`.
   A `sorryAx` reaching a Result through an imported conjecture is invisible to
   a grep and shows up only here.
5. **Unexplained `maxHeartbeats`.** Every bump needs a one-line reason in the
   docstring. An unexplained bump usually marks a proof that almost does not
   work, which is where the interesting bug lives.
6. **Coercion traps.** ℝ against ℝ≥0 (a subtraction that truncates at zero
   instead of going negative), ℕ subtraction (`2 - 3 = 0`), ℤ against ℕ
   division, an `↑` that silently changed which inequality is being asserted.
   Check every arithmetic step that crosses a numeric type.
7. **Statement round trip.** Have a different context informalize the Lean
   `statement` back into prose with no sight of the entry, then compare that
   prose against the entry's Statement. A difference in quantifier order, scope,
   or strictness is the finding. This is the check that catches a proof of the
   wrong theorem, so it does not get skipped because the Lean "obviously" says
   the right thing.

## Report

Evidence first, verdict last, in this order:

```
MD_0007  MathDept.Results.MD_0007.statement
1 hypothesis creep   PASS  binders match H1-H3; lean_minimal_hypotheses: none unused
2 non-vacuity        PASS  n = 3, x = 1/2 satisfies H1-H3; norm_num closes
3 circular helpers   PASS  aux_bound is strictly weaker than the target
4 axiom gate         FAIL  native_decide axiom, no allowlist line
5 maxHeartbeats      PASS  none set
6 coercion traps     PASS  single ℝ ambient, no ↑ in the proof
7 round trip         PASS  informalization matches the entry, quantifiers included

VERDICT: REJECT
- item 4: native_decide moves trust to the compiler. Either prove it by kernel
  reduction or add the allowlist line with a recorded reason.
```

## Close out

The artifact is the verdict, and it is the same artifact in both modes: the item table
above, then one word. ACCEPT stands alone; REJECT lists the failing items and what would
fix each; UNCERTAIN names exactly what a decision needs and who can supply it. This pass
changes no `status` and no other ledger field, in either mode. The lead reads the verdict
and sets the status.

As a `prover` agent in a wave under `math-orchestration`, report the entry ID, the
verdict, the path of the file reviewed, the evidence for each item, and anything the lead
must decide. Change no files: a reviewer that edits the proof it is judging has become
its author, and the review is gone. The commit and the generated views are the lead's,
after the wave.

With no orchestration above the run, the verdict goes back to the session that asked for
it, and that session decides the status after reading it.
