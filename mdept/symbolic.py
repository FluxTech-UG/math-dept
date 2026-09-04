"""Sympy helpers for stage S1: settle a claim exactly before anyone opens Lean.

Every function returns an exact object or None. None means "this method found
nothing", never "the claim is true": a failed search is not a proof, and the
caller must not read it as one.
"""

from __future__ import annotations

import sympy as sp


def is_identity(lhs, rhs, **assumptions) -> bool:
    """True when lhs - rhs simplifies to zero under the given symbol assumptions.

    `assumptions` maps a symbol name to sympy assumption keywords, so
    `is_identity(sp.sqrt(x**2), x, x=dict(nonnegative=True))` is True while the
    unassumed form is not.
    """
    lhs, rhs = sp.sympify(lhs), sp.sympify(rhs)
    if assumptions:
        substitution = {}
        for symbol in (lhs.free_symbols | rhs.free_symbols):
            keywords = assumptions.get(symbol.name)
            if keywords:
                substitution[symbol] = sp.Symbol(symbol.name, **keywords)
        lhs, rhs = lhs.subs(substitution), rhs.subs(substitution)
    return sp.simplify(sp.expand(lhs - rhs)) == 0


def inequality_counterexample(expr, var, domain):
    """An exact point in `domain` where the relational `expr` fails, or None.

    `domain` is a sympy Set or an (lo, hi) pair read as a closed interval.
    """
    var = sp.sympify(var)
    interval = domain if isinstance(domain, sp.Set) else sp.Interval(sp.sympify(domain[0]), sp.sympify(domain[1]))
    failing = sp.solveset(sp.Not(sp.sympify(expr)), var, interval)
    if failing == sp.EmptySet:
        return None
    return _sample(failing)


def _sample(region):
    """One exact representative of a solution set, or None when none is extractable."""
    if isinstance(region, sp.FiniteSet):
        return sorted(region.args, key=sp.default_sort_key)[0]
    if isinstance(region, sp.Interval):
        lo, hi = region.start, region.end
        if lo.is_finite and hi.is_finite:
            midpoint = sp.Rational(lo + hi, 2) if (lo + hi).is_rational else (lo + hi) / 2
            if midpoint in region:
                return midpoint
            for candidate in (lo, hi):
                if candidate in region:
                    return candidate
            return None
        if lo.is_finite:
            return lo + 1 if (lo + 1) in region else None
        if hi.is_finite:
            return hi - 1 if (hi - 1) in region else None
        return sp.Integer(0)
    if isinstance(region, sp.Union):
        for piece in region.args:
            found = _sample(piece)
            if found is not None:
                return found
    return None


def rational_witness(expr, var, lo, hi, steps: int = 200):
    """Scan `steps` rationals across [lo, hi] for the first exact failure of `expr`.

    Rationals, not floats, so a hit is a certified counterexample and not a
    rounding artifact.
    """
    expr = sp.sympify(expr)
    var = sp.sympify(var)
    lo, hi = sp.Rational(lo), sp.Rational(hi)
    if steps < 1:
        raise ValueError(f"steps must be at least 1, got {steps}")
    for k in range(steps + 1):
        point = lo + (hi - lo) * sp.Rational(k, steps)
        value = expr.subs(var, point)
        truth = sp.simplify(value)
        if truth == sp.false:
            return point
    return None
