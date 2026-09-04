"""Random search for numeric leads.

A hit here is a LEAD, never a verdict. Floating point can violate an inequality
that holds over the reals, so a hit is handed to `mdept.symbolic` (or to hand
work) to be upgraded into an exact witness before any status changes.

numpy is imported lazily so the checker and the ledger tooling stay importable
on a machine that only installed the base dependencies.
"""

from __future__ import annotations

from typing import Callable


def random_search(pred: Callable[..., bool], sampler: Callable, n: int = 10_000, seed: int = 0):
    """Sample `n` points and return the first where `pred` is False, else None.

    `sampler(rng)` returns a point as a dict of keyword arguments; `pred(**point)`
    evaluates the stipulated claim there. `seed` is fixed so a lead is
    reproducible: an artifact that cannot be re-run is not evidence.
    """
    import numpy as np

    if n < 1:
        raise ValueError(f"n must be at least 1, got {n}")
    rng = np.random.default_rng(seed)
    for _ in range(n):
        point = sampler(rng)
        if not isinstance(point, dict):
            raise TypeError(f"sampler must return a dict of keyword arguments, got {type(point).__name__}")
        if not pred(**point):
            return point
    return None
