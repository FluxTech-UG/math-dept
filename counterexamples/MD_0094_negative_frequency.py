"""MD_0094: for every real omega, |K(i omega) - K_N(i omega)| <= omega sum_{k>N} w_k (1/a_k + 1/b_k).

At omega < 0 the right side is negative (every tail weight of the disc is positive) and the
left side is an absolute value, so the bound fails for every N and every Pr, alpha > 0. The
point below is the disc (R = 1, w_k = 4/j_{2,k}^2, a_k = nu j_{2,k}^2, b_k = alpha j_{2,k}^2),
Pr = 2, alpha = 1, N = 1, omega = -1. The bound holds with |omega| (proofs/MD_0094.md).
"""
from fractions import Fraction

import mpmath as mp

from mdept.refute import Witness


def _claim(omega, N, Pr, alpha):
    mp.mp.dps = 40
    Pr, alpha, omega = mp.mpf(Pr.numerator) / Pr.denominator, mp.mpf(alpha), mp.mpf(omega)
    nu = Pr * alpha
    s = 1j * omega
    j = [mp.besseljzero(2, k) for k in range(1, N + 1)]
    w = [4 / jk**2 for jk in j]
    # K from MD_0090's definition 1 + K = g/((1-f_v)(1-f_k)), MD_0011's g, disc f = 2J1/(eta J0)
    f = lambda d: (lambda eta: 2 * mp.besselj(1, eta) / (eta * mp.besselj(0, eta)))(mp.sqrt(-s / d))
    fv, fk = f(nu), f(alpha)
    K = ((1 - fk) - Pr * (1 - fv)) / (1 - Pr) / ((1 - fv) * (1 - fk)) - 1
    rN = mp.mpf(1) / 3 - sum(w)                                   # sum_k 4/j^2 = 1/3
    KN = sum(wk * nu * jk**2 * alpha * jk**2 / ((s + nu * jk**2) * (s + alpha * jk**2))
             for wk, jk in zip(w, j)) + rN
    tail = (1 + 1 / Pr) / alpha * (mp.mpf(1) / 144 - sum(4 / jk**4 for jk in j))  # sum 4/j^4 = 1/144
    assert tail > 0
    return bool(abs(K - KN) <= omega * tail)


def refute() -> Witness:
    return Witness(
        entry="MD_0094",
        point={"omega": -1, "N": 1, "Pr": Fraction(2), "alpha": 1},
        claim=_claim,
        note=("Disc, MD_0090's weights and rates; the right side omega*tail is -0.00179 < 0 "
              "while the left side is |K - K_1| >= 0 (about 0.0018). The decision does not depend on "
              "rounding: the left side is an absolute value and the tail is a positive sum."),
    )
