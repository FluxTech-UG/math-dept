# Triage: settling a filed request
<!-- role: runbook | status: current 2026-09-04 | cited-by: CLAUDE.md -->

The math-side half of `docs/protocol.md`, run from a session in `math-dept-private`.
Open with `git pull` in both repos and `make check`, then work the requests in
`inbox/` by priority, and within a priority by date. Priority `high` means a consumer
verdict is blocked on the answer.

Close-out and release are `docs/protocol.md`. Everything between intake and close-out
is here.

## 1. Statement fidelity, before any effort

Mandatory, and it comes before the ladder. A statement nobody checked is the cheapest
way to waste a whole session proving the wrong thing.

1. Write the statement with every quantifier and every hypothesis explicit, and every
   symbol defined in the statement or in the Hypotheses list.
2. Have a **different** agent informalize it back to prose, working from the formal
   statement alone.
3. Compare that prose against the request's own wording.
4. Record the comparison in `triage/MD_####.md`.

Run the same round trip on the Lean statement before any proof attempt, once the file
typechecks and before the first tactic. Three signals say the formalization slipped:

- the statement is false;
- the statement is suspiciously easy;
- the statement does not imply the downstream use the request describes.

Any of the three sends the statement back to step 1, not to the next rung.

## 2. Allocate the ID

`python -m mdept.new --request <stem> --candidate C2` allocates the next `MD_####`
across both repos and pre-fills provenance from the request's front matter. A
candidate that is ill-posed, or that duplicates an existing entry, gets no ID: it is
answered in the request's Outcome block as `declined: <reason>`, and a duplicate
names the ID it duplicates.

## 3. The cheap-first ladder

Budgets are written into the triage record before the stage starts, not after.

| Stage | What | Budget | Lands as |
|---|---|---|---|
| S0 | bibliography, extracts, and Mathlib search (`lean_leansearch`, `lean_loogle`, `exact?`, `apply?`, grep `.lake/packages/mathlib`) | 15 min | `cited` |
| S1 | numeric and symbolic counterexample search (`mdept.symbolic`, `mdept.search`, hypothesis boundary cases) | 30 min | `refuted` |
| S2 | finite instances in Lean (`decide`, `plausible`) | 30 min | a `special_case_of` entry, `proven-formal` |
| S3 | informal proof of 5 to 10 lines, every hypothesis used at a named step | 60 min | `proven-informal`, after a second-session check |
| S4 | Lean formalization: `sorry` skeleton, lemma DAG, leaves filled on compiler feedback | one session | `proven-formal` |

S4 is entered only for priority `high`, for usefulness at least 0.7, or on an explicit
request. A refutation at any stage ends the ladder immediately: nothing above it is
worth the budget. An entry that reaches the end of S3 without settling is `open`, and
`open` is an honest outcome that keeps its triage record.

An S1 hit that is numeric is a lead, not a verdict. Upgrade it to an exact witness
(int, `Fraction`, or sympy) before the entry claims `refuted` without a qualifier.

## 4. The triage record

Every stage attempted gets a row in `triage/MD_####.md`, whatever it showed: date,
stage, what was tried, what it showed, time spent, model. The record is the reason a
later session can tell "we tried and it resisted" from "nobody looked", and it is what
`settled_by.model` and the attempt count are read from at close-out.

The record is private and stays private. A released entry carries its outcome, not its
attempts.

## 5. Rules that keep the ladder honest

**Settled statements are frozen.** Once an entry is settled, its Statement and its
Hypotheses do not change. A better version of the statement is a new entry carrying
`revises`, so the old one keeps meaning what it meant when it was checked.

**A partial result is an entry, not a status.** Proving the theorem for finite
dimension, or under one extra hypothesis, creates its own entry linked to the target by
`special_case_of`. The target stays `open`.

**No agent judges its own output.** The formalizer, the informalizer and the reviewer
are three different contexts; the lead compares their outputs and decides. A context
that wrote a proof is the worst-placed reader of it.

**Adversarial review before any status change.** A fresh context runs the hostile
reviewer pass (`lean-review` skill): hypothesis creep against the source prose, a
non-vacuity witness, a helper lemma that restates the target, the axiom audit,
unexplained `maxHeartbeats`, coercion traps. It ends in ACCEPT, REJECT with reasons, or
UNCERTAIN. The lead reads the verdict before touching `status`.

**Escalate a rung only on a documented stuck report.** A stage that ran out of budget
reports what it tried and where it stopped, and that report is what buys the next rung.
Rerunning the same rung with a longer budget is how a session spends an afternoon on a
statement that S1 would have refuted in ten minutes.
