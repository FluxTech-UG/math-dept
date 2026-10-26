"""MD_0023: the sensitivity error of the frozen-grid fixed point is bounded by C2 H^p / dist(1, spec M)
with C2 independent of M.

Family: d = m = 1, Theta = (0, 1), f(t, y; a) = a*y + cos(2 pi t), T = 1, theta = a.
Method: explicit Euler (p = 1, tableau A = [[0]], b = [1]).
Grid (independent of y0 and theta): N steps of size 1/(2N) on [0, 1/2], then 2N steps of
size 1/(4N) on [1/2, 1]; H = 1/(2N).
Exact: M = e^a, y*(a) = -a/(a^2 + 4 pi^2), d_a y* = (a^2 - 4 pi^2)/(a^2 + 4 pi^2)^2.
Euler is affine, P_h(y) = A y + B, so y*_h = B/(1 - A) and d_a y*_h is computed exactly by
differentiating the recursion; everything is evaluated in rigorous interval arithmetic.
Derivatives of f on a neighbourhood of the orbit are bounded uniformly in a in (0, 1]
(|f_y| = a, |f_a| = |y| <= 1/(4 pi), f_ya = 1, all higher ones vanish except the t-derivatives
of cos), so any C2 allowed by the statement is one fixed number for the whole family.
Asymptotics (sympy, first order in 1/N): y*_h - y* = e * y1(a) + O(e^2), e = 1/N,
y1 = pi^2 (e^{a/2} + 2 e^a - 1)(a^2 - 4 pi^2) / (2 (e^a - 1)(a^2 + 4 pi^2)^2), so
|d_a y*_h - d_a y*| / H -> 2|y1'(a)| = 1/(2 a^2) + O(1) = 1/(2 delta^2) + O(1/delta),
delta = dist(1, spec M) = e^a - 1. The ratio to H/delta grows like 1/(2 delta).
"""
from fractions import Fraction
from mpmath import iv, mp
from mdept.refute import Witness

mp.dps = 60
iv.dps = 60


def _split(x: Fraction):
    return iv.mpf(x.numerator) / iv.mpf(x.denominator)


def d_ystar_h(a, N):
    """d_a y*_h for Euler on the two-rate grid, interval-valued."""
    A, dA, B, dB = iv.mpf(1), iv.mpf(0), iv.mpf(0), iv.mpf(0)
    t = iv.mpf(0)
    steps = [iv.mpf(1) / (2 * N)] * N + [iv.mpf(1) / (4 * N)] * (2 * N)
    for n, h in enumerate(steps):
        # exact grid time as a rational to avoid interval growth
        r = 1 + h * a
        b = iv.cos(2 * iv.pi * t)
        A, dA, B, dB = r * A, h * A + r * dA, r * B + h * b, h * B + r * dB
        t = (iv.mpf(n + 1) / (2 * N)) if n + 1 <= N else iv.mpf(1) / 2 + iv.mpf(n + 1 - N) / (4 * N)
    return (dB * (1 - A) + B * dA) / (1 - A) ** 2


def claim(a: Fraction, C2: Fraction, Ns: tuple) -> bool:
    """The stipulated bound d_theta-error <= C2 H^p / dist(1, spec M), required at every small H;
    False when certified violated at every listed N."""
    a_i = _split(a)
    exact = (a_i**2 - 4 * iv.pi**2) / (a_i**2 + 4 * iv.pi**2) ** 2
    delta = iv.exp(a_i) - 1
    for N in Ns:
        H = iv.mpf(1) / (2 * N)
        err = abs(d_ystar_h(a_i, N) - exact)
        if not err.a > (_split(C2) * H / delta).b:
            return True  # at this N the bound holds or is not certified violated
    return False  # certified violation at every listed N


def refute() -> Witness:
    return Witness(
        entry="MD_0023",
        point={"a": Fraction(1, 10000), "C2": Fraction(1000), "Ns": (400, 800, 1600, 3200)},
        claim=claim,
        note="Scalar family y' = a y + cos(2 pi t), Euler (p=1), two-rate grid, H = 1/(2N). Hypotheses H1, H2 "
        "hold (M = e^a != 1, f smooth, derivative bounds uniform in a in (0,1]). Conclusion violated: "
        "|d_a y*_h - d_a y*| ~ H/(2 delta^2) > C2 H/delta once delta < 1/(2 C2); at a = 1e-4, C2 = 1000 the "
        "interval-certified error exceeds the bound. Sweeping a -> 0 defeats every C2, so no C2 independent of M "
        "exists; the correct factor is the squared resolvent 1/delta^2 (scalar: ||(I-M)^-1||^2). The N list "
        "shows the violation persists as H -> 0 (H0 may depend on M), asymptotics in the docstring.",
    )
