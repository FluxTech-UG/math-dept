---
name: math-rounds
description: >
  Start a math run on everything open: new inbound requests, written proofs whose
  later-day check is due, and old statements still unsettled. Reads the worklist from
  `mdept.inbox_status`, puts it to John with the parked statements and their cost, then
  hands the run to math-orchestration with spend recorded per entry. Use when a session
  in the math repos is told "math rounds", "pick up loose ends" or "work what is open",
  because it decides what to work, in what order, and what not to send an agent to.
  Working one named entry is prove or refute; the run itself is math-orchestration.
---

# Math rounds: the entry point of a math run

A round works what is open, in a fixed order, after John has seen the worklist and
said yes. It runs from `math-dept-private`. The run itself is `math-orchestration`'s;
load it too. This skill adds the worklist, the parking rule and the spend record.

## 1. Pull, check, read the worklist

Pull both math repos (`math-dept` and `math-dept-private`, each by the family's
three-call mirror pull), then `make check` in `math-dept-private`. Its failures head
queue 1, since rows and statuses written on a red tree cannot be verified.

Then `python -m mdept.inbox_status`. Its first line is the round's measure, with
`math-orchestration`'s target (`new`, `closable_open`, `check_fails` at zero). The
other counts are not driven to zero: a proof written today owes its check tomorrow,
and `stuck` is a valid end for an entry.

```
new=<n> closable_open=<n> entries_without_current_fidelity=<n> check_fails=<n> later_day_owed=<n> unsettled=<n> parked=<n>
```

Detail lines follow, one per non-empty count, for example:

```
later_day_owed: MD_0007 (check from 2026-11-14, settle --date 2026-11-13), ...
unsettled: MD_0008 (conjectured, last attempt 2026-11-22, 2 attempt days, 95 min, 410k tokens), ...
parked: MD_0009 (open, 3 attempt days since 2026-10-02, last 2026-11-22, 140 min, 600k tokens), ...
```

## 2. Three queues, worked in this order

1. **New inbound and cheap repairs:** check failures, then `new` requests,
   `closable_open` and entries without a current fidelity row. They are small and they
   block the others.
2. **Follow-ups due:** each `later_day_owed` entry gets its later-day check of the
   written proof by a fresh context, run no earlier than the "check from" day and
   recorded as a row of stage `later-day-check` (that exact word clears the entry from
   the list). On acceptance the lead settles it with `python -m mdept.settle MD_####
   --status proven-informal --by <who> --model <model> --date <the line's settle date>
   --checked-by <today>`.
3. **Old and unsettled:** `unsettled` entries, oldest last attempt first, so nothing
   waits forever behind fresher work.

`parked` entries are outside all three queues (section 4).

## 3. Put the worklist to John before any agent is spawned

One message, before the first spawn, holding:

- the three queues in the proposed order, with the width (how many agents at once) for
  each wave;
- the parked list: each statement, its total cost (attempt days, minutes, tokens from
  its `parked:` line) and what its last attempt said it would need (the `showed` field
  of its latest `decision` row, or of its latest attempt row when it has none).

Name every statement by what it says, with its id in the same sentence ("the bound on
the second moment of the step count, MD_0007"), never by id alone: John reads the list
cold. He answers yes or with cuts. For each parked statement he picks one of: another
route, a weaker statement, leave it open.

A parked entry is un-parked only by John's word, recorded as a row before any agent is
sent to it:

```
python -m mdept.row MD_0009 --stage unpark --tried "<the route John chose>" --showed "un-parked on John's word" --time "0 min" --model <model>
```

## 4. Parking: when no agent is sent

The command computes it, and the rule is stated here so the lead knows why an entry
sits where it does. An attempt day is a date with at least one triage row of stage
`S1`, `S3` or `S4` (those words exactly) after the entry's last `statement` or `unpark`
row; a joined stage such as `S1+S3` counts when every part is one of them. A row staged
`S3-fix` or `S3-review` does not count, so an attempt row carries the bare rung word. An `open` or `conjectured` entry with three or more attempt days is
parked, and with fewer it is unsettled: no agent goes to a parked entry without John's
word. Three days of resistance means the statement or the route needs a decision, not
more spend.

An entry waiting on its later-day check is in neither list, whatever its attempt days:
its newest `decision` row's `showed` field starts with `proof-owed` and no `S1`, `S3`,
`S4`, `statement` or `unpark` row follows it. The command tells that case apart by the
verdict word alone, so the word is written as one of the four in section 5, exactly.

## 5. What this round adds to the math-orchestration run

- **The goal contract's items are the entries John said yes to.** Parked entries and
  the unsettled ones he cut are listed in the contract as outside the run.
- **Spend is recorded as the run goes.** When the lead fills an agent's `TIME` line it
  writes the minutes and the tokens from that agent's completion notification, in
  exactly this form: `6 min, 124k tokens`, which is what the `TIME` replacement in
  `math-orchestration`'s batch recipe writes in a round. The worklist's totals are
  summed from these fields, so a time written any other way drops out of the cost John
  sees.
- **Every entry the run touched ends with the lead's `decision` row**, whose `showed`
  field opens with one of four words:
  - `settled`: the status changed to a settled one;
  - `proof-owed`: written proof, first review accepted, later-day check owed;
  - `repaired`: statement edited, with its fresh fidelity row;
  - `stuck`: followed by the step that stalled and what the next attempt would need.
    This is the text John reads when the entry comes up parked.

```
python -m mdept.row MD_0008 --stage decision --tried "S3 written proof and first review" --showed "proof-owed: review accepted, later-day check from 2026-11-23" --time "4 min, 30k tokens" --model <model>
```

## 6. Close

The closing summary to John gives, for each statement worked (named by what it says,
id beside it), its verdict word and the run's spend on it (minutes, tokens), then the
parked list as `python -m mdept.inbox_status` prints it after the run's last commit.
