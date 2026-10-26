"""MD_0020 (b): there are tau0 > 0 and C' (independent of tau and U) such that for tau <= tau0, theta in U
and H <= H0, ||d_theta y_N(theta; h(theta, tau)) - d_theta y_N(theta; h)|_{h = h(theta, tau)}|| <= C' H^p.
Refuted: for every tau0, C', H0 there are tau <= tau0, an admissible U and theta in U with H <= H0 and
||R|| > C' H, where R is the difference above (the controller term).

Construction (a repelling fixed point of the accepted-step map, so no fold and no edge layer is visited).
  d = m = p = 1, Theta = (1/2, 3/2), f(y, theta) = -theta y, y0 = 1, T = 2, explicit Euler
  Psi_h(y, theta) = (1 - theta h) y (tableau A = [[0]], b = [1], c = [0], classical order 1).
  E(y, h, theta) = theta^2 h^2 / 2: the Heun-minus-Euler estimate theta^2 h^2 y / 2 in the relative norm
    (divided by y, i.e. rtol-only scaling). C^infinity, |E| <= C_E h^2 with C_E = 9/8 on Theta.
  phi(x) = (1 + 3v) / (3 + v), v = (x/2)^6. h_init(tau) = tau^(1/2), independent of theta. kappa = 1/4.
  The sequence: k >= 3, h_k = T/(k + 1/2) = 4/(2k+1), tau_k = h_k^2, theta = 1.

Hypotheses (H1, H2, all certified in claim()).
  phi: rational with positive denominator on (0, inf), so smooth; dphi/dx = 48 v / (x (3+v)^2) > 0, so
    increasing; range (1/3, 3), phi_min = 1/3 < 1 < phi_max = 3; for x < 1, phi(x) < phi(1) = 67/193 = rho < 1.
  Run at theta = 1, tau = tau_k: eps = h^2/2 = tau/2, so every unclipped step accepts (x = tau/eps = 2 > 1,
    strictly), eps/tau = 1/2 > kappa strictly, and the next trial is h phi(2) = h: k unclipped steps of h_k,
    then T - t_k = h_k/2 < h_k is a clip, eps = tau/8 accepts, stop. N = k + 1, H = h_k, no rejection.
  U: every decision is a strict inequality between continuous (indeed rational) functions of theta,
    finitely many, holding at theta = 1; by induction over the N steps (each quantity is continuous on
    the neighbourhood where the earlier decisions agree) they hold on an open interval U_k around 1, on
    which the pattern is constant and eps >= kappa tau at unclipped steps. claim() also certifies the whole
    pattern on an explicit closed box [1 - r_k, 1 + r_k] in interval arithmetic for every k it uses.

Proof that (b) fails (every step is checked in claim(); the symbolic identities are checked with sympy for
symbolic n, k, the inequalities by their base cases and induction steps).
  L1 (per-step expansion, exact). On U_k, h_{n+1} = h_n phi(x_n), x_n = 2 tau / (theta^2 h_n^2). With
    a_n = d log h_n / d theta: a_{n+1} = a_n + g(x_n)(-2/theta - 2 a_n), g = x phi'/phi, and g(2) = 3, so at
    theta = 1: a_{n+1} = -5 a_n - 6, a_0 = 0 (h_init independent of theta). Induction: a_n = (-5)^n - 1.
    The multiplier is exactly -5 at every step: the orbit sits on the fixed point x = 2, no layer exists.
  L2 (the controller term, forcing and clip cancellation explicit). y_N = prod (1 - theta h_n), so
    R = -theta y_N sum_n (dh_n/dtheta) / (1 - theta h_n). The clip gives h_k = T - sum_{n<k} h_n, so
    sum_{n<=k} dh_n = 0 (the cancellation), and with h_n = h for n < k, h_k = h/2:
    R = -theta^2 y_N h (1/2) / ((1 - h)(1 - h/2)) * h S_k, S_k = sum_{n<k} a_n = (1 - (-5)^k)/6 - k.
    At theta = 1, y_N = (1 - h)^k (1 - h/2): R = -(1 - h)^(k-1) h^2 S_k / 2, so |R|/H = (1-h)^(k-1) h |S_k| / 2.
    The forcing (-6 per step) enters only through the "-1" in a_n and the "- k" in S_k; nothing is dropped.
  L3 (lower bound). For k >= 3: (i) log(1-h) >= -h/(1-h) and (k-1) h/(1-h) = (4k-4)/(2k-3) <= 8/3, so
    (1-h)^(k-1) >= e^(-8/3) > 1/15; (ii) |S_k| >= (5^k - 1)/6 - k >= 5^k/12; (iii) h = 4/(2k+1) and
    (5/2)^k >= 2k + 1. Hence |R|/H >= 5^k / (90 (2k+1)) >= 2^k / 90 = 2^(N-1) / 90.
  Conclusion. Given tau0, C', H0 > 0, take k >= 3 with 2^k > 90 C', h_k <= H0 and tau_k = h_k^2 <= tau0
    (all hold for k large since h_k -> 0); then at theta = 1 in U_k, ||R|| > C' H. So no tau0, C' work,
    whatever H0 is. C' may not depend on tau or U, and h_init and U_k are the only tau-dependent data.

Script versus docstring. claim() certifies: every phi hypothesis (sympy, exact); L1's recurrence slope g(2) = 3
and closed form (sympy, symbolic n); L2's closed forms for S_k (symbolic k) and for R, by comparing the
generic forward-mode controller run (exact Fractions, the controller code of the Statement, not the closed
form) against the closed form at every k it uses; each inequality of L3 (sympy for symbolic k, base case
plus induction step; e^(8/3) < 15 in interval arithmetic); and, for each adversary (tau0, C', H0) in the
point, the explicit k chosen by the Conclusion, with the full decision pattern certified on a theta box and
the exact |R| > C' H. The docstring argues only the two standard facts: the continuity induction giving the
open U_k for every k, and the derivation of R = -theta y_N sum dh_n/(1 - theta h_n) from y_N = prod(1 - theta h_n)
(which the exact run also confirms at every k used). The universal step ("for every tau0, C', H0") is the
lower bound of L3, which is proved for every k >= 3; the listed adversaries are instances, not the proof.
"""
from fractions import Fraction
from math import isqrt

import sympy as sp
from mpmath import iv

from mdept.refute import Witness

KAPPA = Fraction(1, 4)
T = Fraction(2)
RHO = Fraction(67, 193)


def _certain(cond, what):
    if not cond:
        raise ValueError(f"not certified: {what}")


# ---- phi and its log-slope, exact ----------------------------------------------------------------
def _phi(x):
    v = (x / 2) ** 6
    return (1 + 3 * v) / (3 + v)


def _dphi(x):
    v = (x / 2) ** 6
    return 48 * v / (x * (3 + v) ** 2)


def _check_phi():
    x = sp.symbols("x", positive=True)
    v = (x / 2) ** 6
    phi = (1 + 3 * v) / (3 + v)
    dphi = sp.diff(phi, x)
    _certain(sp.simplify(dphi - 48 * v / (x * (3 + v) ** 2)) == 0, "phi' formula")
    _certain(sp.simplify(48 * v / (x * (3 + v) ** 2)).is_positive, "phi' > 0 on (0, inf)")
    _certain(sp.limit(phi, x, 0, "+") == sp.Rational(1, 3) and sp.limit(phi, x, sp.oo) == 3, "range (1/3, 3)")
    _certain(phi.subs(x, 1) == sp.Rational(67, 193) and RHO < 1, "phi(1) = rho < 1")
    _certain(phi.subs(x, 2) == 1, "phi(2) = 1")
    _certain(sp.simplify((x * dphi / phi).subs(x, 2)) == 3, "g(2) = 2 phi'(2) / phi(2) = 3")
    _certain(_phi(Fraction(2)) == 1 and 2 * _dphi(Fraction(2)) == 3, "exact phi helpers")


# ---- L1, L2, L3 symbolic ---------------------------------------------------------------------------
def _check_lemmas():
    n, k = sp.symbols("n k", integer=True, nonnegative=True)
    a = lambda m: (-5) ** m - 1
    _certain(a(0) == 0, "L1 base a_0 = 0")
    _certain(sp.simplify(a(n + 1) - (-5 * a(n) - 6)) == 0, "L1 step a_{n+1} = -5 a_n - 6")
    S = lambda m: (1 - (-5) ** m) / sp.Integer(6) - m
    _certain(S(0) == 0 and sp.simplify(S(k + 1) - S(k) - a(k)) == 0, "L2 S_k = sum_{n<k} a_n")
    # L2: at theta = 1 the general formula reduces to -(1-h)^(k-1) h^2 S / 2
    h, y, Ssym = sp.symbols("h y S")
    yN = (1 - h) ** k * (1 - h / 2)
    general = -yN * h * sp.Rational(1, 2) / ((1 - h) * (1 - h / 2)) * h * Ssym
    _certain(sp.simplify(general / (-(1 - h) ** (k - 1) * h**2 * Ssym / 2)) == 1, "L2 reduction at theta = 1")
    # L3 (i): 8/3 - (4k-4)/(2k-3) = (4k-12)/(3(2k-3)) >= 0 for k >= 3; e^(8/3) < 15
    _certain(sp.simplify(sp.Rational(8, 3) - (4 * k - 4) / (2 * k - 3) - (4 * k - 12) / (3 * (2 * k - 3))) == 0,
             "L3(i) algebra")
    _certain(sp.simplify(sp.Rational(4) / (2 * k + 1) / (1 - sp.Rational(4) / (2 * k + 1)) - 4 / (2 * k - 3)) == 0,
             "L3(i) h/(1-h) = 4/(2k-3)")
    iv.dps = 50
    _certain(iv.exp(iv.mpf(8) / 3).b < 15, "L3(i) e^(8/3) < 15")
    # L3 (ii): 5^k/12 >= k + 1/6 for k >= 3: base, and step 5 * 5^k/12 - (k+1+1/6) >= 5 (k+1/6) - k - 7/6 >= 0
    _certain(Fraction(5**3, 12) >= 3 + Fraction(1, 6), "L3(ii) base k = 3")
    _certain(sp.simplify(5 * (k + sp.Rational(1, 6)) - (k + 1 + sp.Rational(1, 6)) - (4 * k - sp.Rational(1, 3))) == 0
             and Fraction(4 * 3) - Fraction(1, 3) > 0, "L3(ii) step (4k - 1/3 >= 0 for k >= 3)")
    # |S_k| >= |1 - (-5)^k|/6 - k >= (5^k - 1)/6 - k (triangle inequality)
    # L3 (iii): (5/2)^k >= 2k+1 for k >= 2: base, and step (5/2)(2k+1) - (2k+3) = 3k - 1/2 >= 0
    _certain(Fraction(5, 2) ** 2 >= 5, "L3(iii) base k = 2")
    _certain(sp.simplify(sp.Rational(5, 2) * (2 * k + 1) - (2 * k + 3) - (3 * k - sp.Rational(1, 2))) == 0,
             "L3(iii) step")
    # assembly: (1/15) * (4/(2k+1)) * (5^k/12) / 2 = 5^k / (90 (2k+1)) >= 2^k / 90
    _certain(Fraction(1, 15) * 4 * Fraction(1, 12) / 2 == Fraction(1, 90), "L3 assembly constant")


# ---- the controller of the Statement, forward-mode, exact at a point -------------------------------
class _D:
    """Dual number (value, d/dtheta) over Fraction."""

    def __init__(self, v, d=Fraction(0)):
        self.v, self.d = Fraction(v), Fraction(d)

    def __add__(s, o):
        o = o if isinstance(o, _D) else _D(o)
        return _D(s.v + o.v, s.d + o.d)

    __radd__ = __add__

    def __sub__(s, o):
        o = o if isinstance(o, _D) else _D(o)
        return _D(s.v - o.v, s.d - o.d)

    def __rsub__(s, o):
        return _D(o) - s

    def __mul__(s, o):
        o = o if isinstance(o, _D) else _D(o)
        return _D(s.v * o.v, s.v * o.d + s.d * o.v)

    __rmul__ = __mul__

    def __truediv__(s, o):
        o = o if isinstance(o, _D) else _D(o)
        return _D(s.v / o.v, (s.d * o.v - s.v * o.d) / o.v**2)

    def __rtruediv__(s, o):
        return _D(o) / s


def _phi_dual(x):
    return _D(_phi(x.v), _dphi(x.v) * x.d)


def _sqrt_exact(q: Fraction) -> Fraction:
    a, b = isqrt(q.numerator), isqrt(q.denominator)
    _certain(a * a == q.numerator and b * b == q.denominator, "tau_k is a rational square")
    return Fraction(a, b)


def _run_point(theta: Fraction, tau: Fraction):
    """Exact run with duals. Returns (R, H, N, a_list, yN). Raises unless every decision is strict."""
    th = _D(theta, 1)
    h = _D(_sqrt_exact(tau))  # h_init(tau), no theta dependence
    y, dyf = _D(1), Fraction(0)
    t = _D(0)
    H, n, a = Fraction(0), 0, []
    while True:
        rem = T - t
        if h.v > rem.v:
            h, clipped = rem, True
        else:
            _certain(h.v < rem.v, f"strict no-clip at step {n}")
            clipped = False
        eps = th * th * h * h / 2
        _certain(0 < (1 - th * h).v and y.v > 0, f"positivity at step {n}")
        _certain(eps.v < tau, f"strict accept at step {n}")
        if not clipped:
            _certain(eps.v > KAPPA * tau, f"strict eps > kappa tau at step {n}")
            a.append(h.d / h.v)
        dyf = (1 - theta * h.v) * dyf - h.v * y.v  # frozen grid tangent
        y = (1 - th * h) * y
        t = t + h
        H = max(H, h.v)
        n += 1
        if clipped:
            _certain(t.v == T and t.d == 0, "clip lands on T, sum of dh = 0")
            return y.d - dyf, H, n, a, y.v
        h = h * _phi_dual(Fraction(tau) / eps)


def _run_box(theta: Fraction, tau: Fraction, r_exp: int):
    """Interval run of the same controller on theta in [theta - r, theta + r]; returns N."""
    iv.dps = r_exp + 60
    q = lambda f: iv.mpf(f.numerator) / iv.mpf(f.denominator)
    r = iv.mpf(10) ** (-r_exp)
    th = iv.mpf([(q(theta) - r).a, (q(theta) + r).b])
    tau_i = q(tau)
    h = q(_sqrt_exact(tau))
    y, t, n = iv.mpf(1), iv.mpf(0), 0
    while True:
        rem = q(T) - t
        if (h - rem).a > 0:
            h, clipped = rem, True
        else:
            _certain((h - rem).b < 0, f"box: strict no-clip at step {n}")
            clipped = False
        eps = th * th * h * h / 2
        _certain((1 - th * h).a > 0 and y.a > 0, f"box: positivity at step {n}")
        _certain((eps - tau_i).b < 0, f"box: strict accept at step {n}")
        if not clipped:
            _certain((eps - q(KAPPA) * tau_i).a > 0, f"box: eps > kappa tau at step {n}")
        y = (1 - th * h) * y
        t = t + h
        n += 1
        if clipped:
            return n
        x = tau_i / eps
        v = (x / 2) ** 6
        h = h * (1 + 3 * v) / (3 + v)


def _certify_k(k: int):
    """All hypotheses and the closed forms at tau_k; returns (R, H, N)."""
    h = Fraction(4, 2 * k + 1)
    tau = h * h
    R, H, N, a, yN = _run_point(Fraction(1), tau)
    _certain(N == k + 1 and H == h, f"k = {k}: N = k + 1, H = h_k")
    _certain(a == [Fraction((-5) ** i - 1) for i in range(k)], f"k = {k}: L1 a_n = (-5)^n - 1 in the run")
    S = Fraction(1 - (-5) ** k, 6) - k
    _certain(R == -(1 - h) ** (k - 1) * h * h * S / 2, f"k = {k}: L2 closed form of R")
    _certain(abs(R) / H >= Fraction(2**k, 90), f"k = {k}: L3 bound")
    Nb = _run_box(Fraction(1), tau, r_exp=3 * k + 10)
    _certain(Nb == N, f"k = {k}: pattern certified on the theta box")
    return R, H, N, tau


def _k_for(tau0: Fraction, Cprime: Fraction, H0: Fraction) -> int:
    """The Conclusion's choice: least k >= 3 with 2^k > 90 C', h_k <= H0, tau_k <= tau0."""
    k = 3
    while not (2**k > 90 * Cprime and Fraction(4, 2 * k + 1) <= H0 and Fraction(4, 2 * k + 1) ** 2 <= tau0):
        k += 1
    return k


def claim(theta: Fraction, ks: tuple, adversaries: tuple) -> bool:
    """Clause (b). Returns False when the proof's every step is certified (so (b) is false for every
    tau0, C', H0, by L3), and at each listed (tau0, C', H0) the chosen k gives a certified violation."""
    _certain(theta == 1, "the witness parameter is theta = 1")
    _check_phi()
    _check_lemmas()
    for k in ks:
        _certify_k(k)
    for tau0, Cprime, H0 in adversaries:
        k = _k_for(tau0, Cprime, H0)
        R, H, N, tau = _certify_k(k)
        _certain(tau <= tau0 and H <= H0 and abs(R) > Cprime * H, f"violation at adversary {tau0, Cprime, H0}")
    return False


def refute() -> Witness:
    return Witness(
        entry="MD_0020",
        point={
            "theta": Fraction(1),
            "ks": tuple(range(3, 13)),
            "adversaries": (
                (Fraction(1, 10), Fraction(10**5), Fraction(1, 10)),
                (Fraction(1, 10**4), Fraction(10**12), Fraction(1, 100)),
            ),
        },
        claim=claim,
        note="f = -theta y, Euler, E = theta^2 h^2 / 2 (relative Heun - Euler), phi(x) = (1 + 3v)/(3 + v) with "
        "v = (x/2)^6 (smooth, increasing, range (1/3, 3), rho = 67/193), h_init = tau^(1/2), kappa = 1/4, T = 2, "
        "tau_k = (4/(2k+1))^2. At theta = 1 the step sits on the repelling fixed point x = tau/eps = 2 of the "
        "step map (multiplier exactly -5), so every decision is strict (no rejection, one final clip to h/2) "
        "and holds on an open U_k. Exact: dlog h_n/dtheta = (-5)^n - 1, R = -(1-h)^(k-1) h^2 S_k / 2 with "
        "S_k = (1 - (-5)^k)/6 - k, hence |R|/H >= 2^k / 90 for every k >= 3 (proved, each step certified), "
        "so (b) fails for every tau0, C', H0.",
    )
