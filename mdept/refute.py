"""The refutation contract: a `Witness`, and the runner over `counterexamples/`.

Run: `python -m mdept.refute MD_0006` or `python -m mdept.refute --all [--json]`

A counterexample artifact is `counterexamples/MD_####_slug.py`. Its module
docstring states the informal claim; it defines `refute() -> Witness` and is
deterministic. The witness carries the exact point and the predicate the entry
stipulates, and `verify()` demands that the predicate evaluate to exactly False
there.

Exactness is the whole point. A float point is a numeric LEAD, not a
refutation: rounding can manufacture a violation that the real numbers do not
have. `verify()` refuses a float unless the witness declares `numeric=True`,
which downgrades what the ledger may claim.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from fractions import Fraction
from numbers import Integral, Rational
from pathlib import Path
from typing import Callable

from . import CheckError
from . import config

#: Types a witness point may carry when it claims to be exact.
EXACT_TYPES = (bool, int, str, Integral, Rational, Fraction)


@dataclass(frozen=True)
class Witness:
    """One point that satisfies an entry's hypotheses and violates its conclusion."""

    entry: str
    point: dict
    claim: Callable[..., bool]
    note: str = ""
    numeric: bool = False

    def verify(self) -> bool:
        """True when the claim evaluates to exactly False at this point."""
        if not self.numeric:
            for name, value in sorted(self.point.items()):
                self._require_exact(name, value)
        result = self.claim(**self.point)
        return _as_bool(result, self.entry) is False

    def _require_exact(self, name: str, value) -> None:
        if isinstance(value, (list, tuple)):
            for i, item in enumerate(value):
                self._require_exact(f"{name}[{i}]", item)
            return
        if isinstance(value, EXACT_TYPES):
            return
        if _is_sympy(value):
            return
        raise CheckError(
            f"I6 counterexample: {self.entry}: field 'point.{name}': "
            f"{type(value).__name__} is not exact. Use int, Fraction, or a sympy expression, "
            "or set numeric=True and accept that the ledger records a numeric lead."
        )


def _is_sympy(value) -> bool:
    return type(value).__module__.split(".")[0] == "sympy"


def _as_bool(value, entry: str) -> bool:
    if isinstance(value, bool):
        return value
    name = type(value).__name__
    if name in ("bool_", "BooleanTrue", "BooleanFalse"):
        return bool(value)
    raise CheckError(
        f"I6 counterexample: {entry}: field 'claim': the predicate returned "
        f"{value!r} ({name}); it must return a definite True or False at the witness point"
    )


def load(path: Path) -> Witness:
    """Import an artifact and call its `refute()`. Raises when the contract is broken."""
    path = Path(path).resolve()
    if not path.is_file():
        raise CheckError(f"I6 counterexample: {path}: field '<file>': does not exist")
    spec = importlib.util.spec_from_file_location(f"mdept_counterexample_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise CheckError(f"I6 counterexample: {path}: field '<module>': cannot be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "refute"):
        raise CheckError(f"I6 counterexample: {path}: field 'refute': the module defines no `refute()`")
    witness = module.refute()
    if not isinstance(witness, Witness):
        raise CheckError(
            f"I6 counterexample: {path}: field 'refute': returned {type(witness).__name__}, expected a Witness"
        )
    return witness


def run_all(directory: Path) -> dict:
    """Run every artifact in a directory. Returns {entry id: {file, verified, exact}}."""
    directory = Path(directory)
    report: dict[str, dict] = {}
    if not directory.is_dir():
        return report
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        witness = load(path)
        report[witness.entry] = {
            "file": str(path.relative_to(directory.parent)),
            "verified": witness.verify(),
            "exact": not witness.numeric,
        }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.refute", description=__doc__.splitlines()[0])
    parser.add_argument("entry", nargs="?", default=None, help="an entry ID, for example MD_0006")
    parser.add_argument("--all", action="store_true", help="run every artifact in counterexamples/")
    parser.add_argument("--root", default=None, help="repo root (default: nearest ancestor with ledger/)")
    parser.add_argument("--json", action="store_true", help="emit the machine view on stdout")
    args = parser.parse_args(argv)
    if not args.all and args.entry is None:
        parser.error("name an entry ID or pass --all")

    root = config.find_repo_root(args.root) if args.root is None else Path(args.root).resolve()
    directory = root / "counterexamples"
    try:
        report = run_all(directory)
    except CheckError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    if not args.all:
        if args.entry not in report:
            print(f"FAIL no counterexample artifact for {args.entry} in {directory}", file=sys.stderr)
            return 1
        report = {args.entry: report[args.entry]}

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    failed = [k for k, v in report.items() if not v["verified"]]
    for entry_id, record in sorted(report.items()):
        mark = "ok " if record["verified"] else "FAIL"
        exact = "exact" if record["exact"] else "numeric lead"
        if not args.json:
            print(f"{mark} {entry_id} {record['file']} ({exact})")
    if failed:
        print(f"FAIL witnesses did not verify: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # Dispatch to the canonical module: under `python -m`, this file runs as `__main__`
    # and its classes would be distinct from the `mdept.refute` ones that artifacts and
    # callers import, breaking isinstance checks.
    from mdept.refute import main as _main

    raise SystemExit(_main())
