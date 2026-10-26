"""MD_0084 (a): the curve sigma(r) = kappa r - l r^2 + m r^3 has a fold (a critical point at
r > 0) iff l^2 > 3 m kappa.

The parenthetical defines a fold as a critical point at r > 0, that is a zero of
sigma'(r) = kappa - 2 l r + 3 m r^2 with r > 0. At the boundary l^2 = 3 m kappa the
derivative is a perfect square, sigma'(r) = 3m (r - l/(3m))^2, with a double zero at
r = l/(3m) > 0. So a critical point at r > 0 exists while l^2 > 3 m kappa is false, and
the "only if" direction fails. The point is a degenerate critical point (an inflection,
sigma' does not change sign), not a turning point, so clause (a) holds once "fold" means
a critical point where sigma' changes sign, equivalently a nondegenerate one.

Witness: kappa = 3, l = 3, m = 1, r = 1. Then sigma'(1) = 3 - 6 + 3 = 0 and
l^2 = 9 = 3 m kappa.
"""
from fractions import Fraction

from mdept.refute import Witness


def _claim(kappa, l, m, r):
    """(a) with fold := critical point at r > 0, evaluated at one exhibited critical point.

    The iff says: if there is r > 0 with sigma'(r) = 0, then l^2 > 3 m kappa. At the
    point the antecedent is checked to hold, so the claim reduces to l^2 > 3 m kappa.
    """
    if not (kappa >= 0 and l > 0 and m > 0):
        raise AssertionError("hypotheses kappa >= 0, l > 0, m > 0 fail")
    dsigma = kappa - 2 * l * r + 3 * m * r * r
    if not (r > 0 and dsigma == 0):
        raise AssertionError("r is not a critical point at r > 0")
    return l * l > 3 * m * kappa


def refute() -> Witness:
    return Witness(
        entry="MD_0084",
        point={"kappa": Fraction(3), "l": Fraction(3), "m": Fraction(1), "r": Fraction(1)},
        claim=_claim,
        note=(
            "kappa = 3 >= 0, l = 3 > 0, m = 1 > 0; sigma'(r) = 3 (r - 1)^2 vanishes at r = 1 > 0, "
            "so a critical point at r > 0 exists, but l^2 = 9 = 3 m kappa, so l^2 > 3 m kappa "
            "is false. Clause (a) fails only on the boundary l^2 = 3 m kappa; it holds with "
            "'fold' read as a sign-changing (nondegenerate) critical point."
        ),
    )
