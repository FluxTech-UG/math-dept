# Protocol: file a request, settle it, release it
<!-- role: runbook | status: current 2026-09-17 | cited-by: CLAUDE.md -->

One loop with two halves. A session in a consumer repo files a request into the
private inbox; a session in `math-dept-private` settles it and releases what belongs
in public. This file is the single home of that loop. The `math-consult`, `prove` and
`refute` skills point here rather than restating it, and `docs/triage.md` owns the
math-side ladder.

## Consumer side

Trigger: a session is about to rely on a published theorem, bound or identity in a
verdict, an assertion or a design section.

### 0. Resolve first

```
python -m mdept.query "<the statement in your own words>"
python -m mdept.query --topic TOPIC --status open
```

Both ledgers are searched, released and unreleased together, from whatever directory
you are in. An entry that already covers the statement is cited by its `MD_####` ID,
and the flow stops there. `python -m mdept.query MD_0007` prints that entry, the words
a citing line must carry, and where it is already cited.

In the same pass, resolve every pending `MDR:` token in this repo:

```
python -m mdept.query --resolve MDR:2026-09-04-three-basin
```

It reports each candidate as `pending`, as `declined: <reason>`, or as the IDs and
statuses it became. Replace a resolved token with those IDs. This is how a consumer
learns outcomes: notification is passive by design, and step 0 is the only thing that
delivers it.

A repo with entries of its own keeps a generated local view, so the answer is in the
repo that needs it:

```
python -m mdept.view --consumer NAME --write
```

It writes that repo's `docs/MATH.md`: what the repo raised, every citation with the
line it sits on, and every `MDR:` token with what it became. `--check` fails on drift
and belongs in the consumer's own test suite.

### 1. State the applied result as used

Write the statement the application actually leans on, with the hypotheses the
application actually satisfies. The gap between those hypotheses and the source's
hypotheses is the hook: it is where the stipulated statements come from.

### 2. Generate 3 to 5 candidates

Sample them with the `verbalized-sampling` skill across these relations: below-of,
above-of, special-case-of, generalizes, discrete or finite version, weakened
hypothesis. Each candidate carries a plausibility, a usefulness with one line of why,
and the cheapest test that would settle it (a ladder stage from `docs/triage.md`).

### 3. File one request

Copy `math-dept-private/inbox/TEMPLATE.md` to
`math-dept-private/inbox/YYYY-MM-DD-<slug>.md`, fill it, and commit that single file
in that repo with the message `inbox: <slug>`.

That file is the only write a foreign session may make in either math repo: never an
existing request, never a ledger entry, never `sources/`, never a Lean file. The
public repo accepts no foreign writes at all.

### 4. Cite provisionally

In the consumer's own doc, cite as `MDR:2026-09-04-three-basin#C2 (pending)`. A
pending candidate records exposure; it licenses nothing. No verdict, number or design
decision may depend on one.

Every file that names an entry is a citation, code as much as prose, and each one is
listed in that entry's `cited_by` as `<repo>:<path>`. I21 fails on a mention the ledger
does not know about, because an unlisted reliance is the one a refutation never
reaches; I15 requires the status word on the citing line itself. A generated file is
skipped: the citation belongs in the source it was generated from.

### 5. Commit in the consumer repo separately

The request commit lives in `math-dept-private`. The consumer's own changes commit in
the consumer repo. One commit never spans both.

## Math side

Fidelity checking, ID allocation, the cheap-first ladder and the triage record are
`docs/triage.md`. What follows is what happens once a candidate is settled.

### Close-out

1. Set the entry's `status`, its `evidence` list, and `provenance.settled_by` (who,
   date, how, checked_by, model).
2. Append the Outcome block to the request, one line per candidate, each mapping
   `C<n>` to a ledger ID or to `declined: <reason>`. That block is what
   `mdept.query --resolve` reads back to the consumer.
3. Set the request's `state: closed` and `git mv` it into `inbox/done/`.
4. `make regen && make check`.
5. Commit.
6. Report which consumers need `python -m mdept.view --consumer NAME --write`. The view
   lives in their repo, so a session there rewrites it: writes stay inside one repo.

A refuted stipulation reaches the consumer at its next step 0, which drops the
reliance. When what was refuted is the applied published result itself, the consumer
records the exposure in its own register, citing the ID.

### Release

`python -m mdept.release MD_0007` promotes one settled entry from private to public:

- moves the entry, its Lean file, its informal proof and its counterexample script
  into this repo, keeping the directory-for-status split (`Results/` stays
  `Results/`);
- abstracts provenance: keeps `raised_by.repo`, adds a one-line neutral `domain`,
  drops `doc`, `anchor` and `application`. `stipulated_by` and `settled_by` cross
  intact, because they are the credit trail;
- regenerates both Lean roots, using the public repo's `scripts/gen_root.py` (the one
  copy; the private repo has none) for each, and both ledger indexes;
- runs both repos' checks with `MATHDEPT_REQUIRE_LEAN=1`.

IDs and Lean declaration names are stable across a release. A consumer cites
`MathDept.MD_0007.statement` before and after; only the module path moves.

## Status vocabulary

| Status | Meaning | Required evidence |
|---|---|---|
| `cited` | published result taken as-is | `source: [BibTag]` of Kind paper, book, notes or mathlib; extract exists (private-side check); a Mathlib source also sets `formal.decl` and is `#check`ed in `MathDept/Citations.lean` |
| `conjectured` | stipulated, not yet worked | `provenance.raised_by` and `provenance.stipulated_by`; `settled_by: null` |
| `open` | worked to budget, undecided | `triage/MD_####.md` exists (private); `settled_by: null` |
| `proven-formal` | Lean proof, sorry-free, standard axioms | `formal.decl` and `formal.file`; the audit JSON lists the declaration under a `Results` module with axioms within {`propext`, `Classical.choice`, `Quot.sound`} plus its per-declaration allowlist lines; `settled_by.how: lean` |
| `proven-informal` | written proof, reviewed in a second session | `proofs/MD_####.md` with a "Formalization blockers" section; `settled_by.how: informal-proof`; `settled_by.checked_by` strictly later than `settled_by.date` |
| `refuted` | an explicit instance satisfies the hypotheses and violates the conclusion | `counterexamples/MD_####_slug.py` whose witness verifies; `settled_by.how: counterexample` |
| `merged` | duplicate | `merged_into` resolves to a non-merged entry |

Three rules ride on this table. Every status except `merged` requires
`provenance.raised_by`. A settled entry's Statement and Hypotheses are frozen: a
change is a new entry with `revises`. A partial result is a separate entry linked by
`special_case_of`, never a status of its own.

A witness carrying `numeric: true` keeps the status word `refuted` and displays as
"refuted (numeric)" in the generated views. Upgrading it to an exact witness is what
removes the qualifier.
