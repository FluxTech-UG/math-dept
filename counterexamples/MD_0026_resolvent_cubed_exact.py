"""MD_0026: the sensitivity error of the frozen-grid fixed point is bounded by C2 H^p ||(I-M)^-1||^2
with C2 independent of M (exact witness; the numeric lead is triage/MD_0026_s1_witness_resolvent_cubed.py).

Family: d = m = p = 1, Theta = R, T = 1, theta0 = 0, s(t) = sin(2 pi t)/(2 pi), a in (0, 1],
  f(t, y; th) = cos(2 pi t) - a (y - s(t)) + (y - s(t))^2 + th.
With z = y - s(t): z' = -a z + z^2 + th. At th = 0 the orbit is y* = s, M = e^-a, R := (1-M)^-1 = 1/(1 - e^-a),
d_th y* = 1/a. Explicit Euler (A = [[0]], b = [1]) on the two-rate grid (N steps of 1/(2N), then 2N steps of
1/(4N); H = 1/(2N), c_n = h_n/H in {1, 1/2}). Derivative bounds of f near the orbit are uniform in a in (0, 1].

Exact first-order coefficient (sympy derivation in triage/MD_0026_s1_closed_form.py). With q = e^(a/2):
  e1(a) := lim_{H->0} (d y*_h - 1/a)/H
         = pi^2 [ (a^2 + 4 pi^2) q - 4 a q^2 + 12 a q - 8 a ] / ( a (a^2 + 4 pi^2)^2 (q - 1)^2 ),
  e1(a) a^3 = 1 + (1/(4 pi^2) - 1/48) a^2 - 3 a^3/(8 pi^2) + ...,  R a = 1 + a/2 + ...
  (e1 a^3 >= 0.96 on (0, 1] (numerically; not interval-proved), with e1 a^3 -> 1 as a -> 0)
so e1/R^2 ~ 1/a -> infinity and e1/R^3 -> 1.

Rigorous remainder (all constants explicit; rho_n = 1 - a h_n, tau_n = s(t_{n+1}) - s(t_n) - h_n s'(t_n),
|tau_n| <= pi h_n^2, tau_n = -pi h_n^2 sin(2 pi t_n) + R3, |R3| <= (2 pi^2/3) h_n^3):
 L0 (telescoping). If x_{n+1} = lam_n x_n + g_n is periodic with 0 <= lam_n <= 1 - kappa h_n, then
    |x_n| <= sup|g/h| / kappa, because kappa h_k prod_{i>k}(1 - kappa h_i) = prod_{i>k} - prod_{i>=k}.
 L1 (fixed point). z_{n+1} = rho_n z_n + h_n z_n^2 - tau_n. The map "periodic solution with forcing h z^2 - tau"
    is a 1/2-contraction on {sup|z| <= r}, r = 2 pi H/a, when H <= a^2/(8 pi). So P_h has a fixed point z*
    with sup|z*| <= r (unique in that ball; it lies in any neighbourhood V of y*(0) = 0 once H is small, so
    "the unique fixed point in V" is this one, or uniqueness already fails), and d_th y*_h = delta_0, where
    delta_{n+1} = (rho_n + 2 h_n z*_n) delta_n + h_n is periodic.
 L2 (first-order orbit). w is the 1-periodic solution of w' = -a w + pi c(t) sin(2 pi t), sup|w| <= pi/a,
    sup|w'| <= 2 pi. Then z*_n = H w(t_n) + O(H^2): split z* = z^L + eta with z^L the fixed point of the
    affine recursion; |eta| <= r^2/a by L0; d_n = z^L_n - H w(t_n) obeys d_{n+1} = rho d_n + defect with
    defect/h <= H^2 (pi a/2 + 8 pi^2/3 + pi) (|rho - e^-ah| <= a^2 h^2/2, Taylor on s, Lipschitz of the
    integrand), so sup|z* - H w(t_n)| <= B H^2/a^3, B = 3 pi/2 + 8 pi^2/3 + 4 pi^2.
 L3 (sensitivity). With delta = 1/a + eps: eps_{n+1} = (rho_n + 2 h_n z*_n) eps_n + 2 h_n z*_n/a, and
    lam_n = rho_n + 2 h_n z*_n satisfies 0 <= lam_n <= 1 - (a/2) h_n for H <= a^2/(8 pi). Let u be the
    periodic solution of u' = -a u + 2 w/a (sup|u| <= 2 pi/a^3), e1 := u(0). Then e_n = eps_n - H u(t_n) obeys
    e_{n+1} = lam e_n + defect with defect/h <= H^2 (pi + 8 pi^2 + 2 B + 6 pi)/a^4, hence by L0 (kappa = a/2)
        | d y*_h - 1/a - H e1(a) | <= F H^2 / a^5,   F = 2 (7 pi + 8 pi^2 + 2 B),   for H <= a^2/(8 pi).
    (measured remainder: (err - H e1) a^5/H^2 = 1.5 at a = 1/10, 1/5; sup|z* - Hw| a^3/H^2 = 0.26; the
    bounds are loose by a factor 300 and that is irrelevant here.)
Consequence: for every H <= H1 := min(a^2/(8 pi), gap a^5/(2F)), gap := e1 - C2 R^2 > 0, one has
  (d y*_h - d y*)/H >= e1 - F H/a^5 >= e1 - gap/2 > C2 R^2,
so |d y*_h - d y*| > C2 H ||(I-M)^-1||^2 for ALL H <= H1: no H0 helps, and H0, V, C1 are all allowed to depend
on M. `claim` evaluates this chain in interval arithmetic (45 digits) at a = a(C2) = 1/(4 ceil(C2)) for each
listed C2, and returns False exactly when gap > 0 is certified for every listed C2 (so H1 > 0 is explicit).
The same rule a(C2) = 1/(4 ceil(C2)) works for every C2 >= 1 (e1/R^2 ~ 1/a = 4 ceil(C2)); the listed C2 are
representatives, the construction does not depend on them.
Exact witness for C2 in {50, 150, 1000}; all H <= H1 via the audited hand lemma L0-L3; every C2 via the rule a = 1/(4 ceil C2) with e1 a^3 >= 0.96 from the series.
"""
from fractions import Fraction
from math import ceil
from mpmath import iv, mp
from mdept.refute import Witness

mp.dps = 45
iv.dps = 45


def _q(x):
    return iv.mpf(x.numerator) / iv.mpf(x.denominator) if isinstance(x, Fraction) else iv.mpf(x)


def e1_closed(a):
    """lim_{H->0} (d y*_h - 1/a)/H for Euler on the two-rate grid (a is an interval)."""
    pi = iv.pi
    q = iv.exp(a / 2)
    return pi**2 * ((a * a + 4 * pi**2) * q - 4 * a * q * q + 12 * a * q - 8 * a) / (
        a * (a * a + 4 * pi**2) ** 2 * (q - 1) ** 2
    )


def remainder_const():
    """F in |d y*_h - 1/a - H e1| <= F H^2 / a^5 for H <= a^2/(8 pi)."""
    pi = iv.pi
    B = 3 * pi / 2 + 8 * pi**2 / 3 + 4 * pi**2
    return 2 * (7 * pi + 8 * pi**2 + 2 * B)


def certified_H1(a, C2):
    """H1 > 0 such that |d y*_h - 1/a| > C2 H R^2 for every H <= H1, or None if gap > 0 is not certified."""
    a_i = _q(a)
    R = 1 / (1 - iv.exp(-a_i))
    gap = e1_closed(a_i) - _q(C2) * R * R
    if not gap.a > 0:
        return None
    h_a = (a_i * a_i / (8 * iv.pi)).a
    h_b = (iv.mpf(gap.a) * a_i**5 / (2 * remainder_const())).a
    return min(h_a, h_b)  # an mpf lower endpoint


def claim(C2s: tuple) -> bool:
    """The stipulated bound |d y*_h - d y*| <= C2 H ||(I-M)^-1||^2 for all H <= H0, for some H0 > 0.
    False when, for each listed C2, the point a(C2) violates it at every H <= H1(C2) with H1 > 0 certified."""
    for C2 in C2s:
        a = Fraction(1, 4 * max(1, ceil(C2)))
        H1 = certified_H1(a, C2)
        if H1 is None or not H1 > 0:
            return True  # not certified violated for this C2
    return False


def refute() -> Witness:
    return Witness(
        entry="MD_0026",
        point={"C2s": (Fraction(50), Fraction(150), Fraction(1000))},
        claim=claim,
        note="Scalar nonlinear family z' = -a z + z^2 + th, Euler p=1, two-rate grid; exact y*, M=e^-a, d y*=1/a. "
        "Hypotheses H1, H2 hold, derivative bounds uniform in a in (0,1]. For each C2, a=1/(4 ceil(C2)); the "
        "closed form e1(a) ~ 1/a^3 with the explicit remainder F H^2/a^5 (docstring, lemmas L0-L3) gives "
        "|d y*_h - d y*| > C2 H R^2 for all H <= H1(C2) with H1 certified positive in interval arithmetic. "
        "Defeats every C2 (representatives 50, 150, 1000); the correct factor is R^3, not R^2. The remainder "
        "lemma is a hand proof, not machine-checked: the adversarial review audits L0-L3.",
    )
