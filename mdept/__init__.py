"""Tooling for the math-dept ledger of stipulated mathematical statements.

The package is `mdept`, not `mathdept`: the macOS filesystem is case-insensitive
and `mathdept` would collide with the Lean library directory `MathDept/`.

Modules, each also runnable as `python -m mdept.<module>`:

- `config`  repo-root and sibling-repo resolution
- `schema`  the closed front-matter key set, the enumerations, and their validator
- `parse`   markdown front matter, ledger entries, bibliography, role lines
- `check`   invariants I1 to I20 over a ledger tree
- `index`   the generated views `ledger/INDEX.md` and `ledger.json`
- `new`     allocate the next ID and write an entry from the template
- `release` move an entry from the private sibling into the public repo
- `audit`   the `sorry` fence, the Lean axiom audit, the counterexample sweep
- `refute`  the `Witness` contract and the counterexample runner
- `symbolic` sympy helpers for identity and inequality refutation
- `search`  random search over a sampler, producing numeric leads

Nothing here calls Lean. The Lean side writes `audit/latest.json`; the checker
reads it.
"""

__version__ = "0.1.0"


class MDeptError(Exception):
    """Base class for every error this package raises."""


class ConfigError(MDeptError):
    """A path, repo, or environment variable could not be resolved."""


class CheckError(MDeptError):
    """A ledger invariant failed. The message names the invariant, path, and field."""


__all__ = ["MDeptError", "ConfigError", "CheckError", "__version__"]
