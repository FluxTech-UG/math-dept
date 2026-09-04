---
id: MD_0000
title: Short imperative title, no LaTeX
status: conjectured            # cited | conjectured | open | proven-formal | proven-informal | refuted | merged
kind: lemma                    # theorem | lemma | proposition | identity | bound | definition
topics: [linear-algebra, fisher]
source: null                   # "[BibTag]" when status is cited, else null
formal:
  decl: null                   # e.g. MathDept.MD_0002.statement
  file: null                   # e.g. MathDept/Results/MD_0002.lean (or MathDeptPrivate/...)
evidence: []                   # list of {kind: extract|proof|counterexample|triage|experiment, path: ...}
between:
  below_of: []                 # entries that imply this one (this is the weaker statement)
  above_of: []                 # entries this one implies (this is the stronger statement)
  special_case_of: []          # same shape, narrower hypotheses
  generalizes: []              # same shape, wider hypotheses
provenance:
  raised_by:
    repo: math-dept            # a key of repos.yaml (private) or a free repo name (public)
    domain: one neutral line naming the mathematical domain
    doc: null                  # PRIVATE only: repo-relative path to the applying document
    anchor: null               # PRIVATE only: a heading or token that occurs literally in doc
    application: null          # PRIVATE only: what needs this, and what changes if it is false
  stipulated_by:
    who: claude                # john | claude | both
    date: 2026-09-04
    model: null                # optional model identifier for the credit trail
    request: null              # "MDR:2026-09-04-three-basin#C1", or null when born here
  settled_by: null             # {who, date, how: citation|counterexample|lean|informal-proof, checked_by, model}
  connects: []                 # free strings or MD_0007 tokens
cited_by: []                   # "Repo:path/to/doc.md §n"; the doc must literally contain this ID
revises: null
merged_into: null
statement_hash: null           # sha256 of the audit's pretty-printed Lean type, once formal.decl exists
---

## Statement

$$ ... $$

Every quantifier explicit. Every symbol defined here or in Hypotheses.

## Hypotheses

- **H1.** ...

## Why it was raised

Two to five lines. Public entries stay abstract: no application internals.

## Current notes

Current state only. Dated attempts belong in the private `triage/MD_0000.md`.
