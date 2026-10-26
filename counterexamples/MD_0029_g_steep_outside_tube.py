"""MD_0029: Euler + cubic Hermite, small step, the t-component of every u_n has positive slope.

Setup (d = 2, m = 1, p = 1, max norm on R^2): Theta = (-2, 2), Theta' = (-1, 1), y0 = (0, 0),
f(y) = (1, 2 y1) (exact orbit y = (t, t^2) while g = 1), T = h = Delta s, g = 1 on the whole
closed delta-tube K around the orbit, delta = h^2/4, and g steep only OUTSIDE K, where the
Euler iterate y_1 = (h, 0) lands (vertical offset r = y2 - y1^2 = -h^2). Tuple shared by every
h <= 1/8: g_min = 1, g_max = 5, Lip_y(g) on K = 0, sup_K ||f||_inf = 1, method = Euler with
cubic Hermite (slopes Delta s F at both nodes). So no Delta s0(tuple) can serve all h.

The ledger leaves delta unbound. H1 says "For theta in Theta and delta > 0, K_delta is the
closed delta-neighbourhood of the trajectory {y(t; theta) : 0 <= t <= T}"; nothing fixes delta,
quantifies it, or puts it in the dependence list of Delta s0 (g_min, g_max, Lip_y(g) on K,
sup_K ||f||, the method), and no hypothesis places the iterates or the RK stages in K. The
witness takes delta = h^2/4 as problem data of P_h.

The claim is evaluated at h = 1/16. The asserted inequalities (the tube inequality
|r| <= delta (1 + 2h + delta) < h^2/2 with the max norm, and 2 (h + delta) <= 1) make the same
failure hold for every h <= 1/8; the probe triage/MD_0029_s1_probe.py covers h = 2^-k for
k = 3..13.
"""
from fractions import Fraction
from mdept.refute import Witness


def _psi(x):
    x = min(max(x, Fraction(0)), Fraction(1))
    return 10 * x**3 - 15 * x**4 + 6 * x**5  # C^2 smoothstep, flat to order 2 at 0 and 1


def _g(y, h):
    r = y[1] - y[0] ** 2
    return 1 + 4 * _psi(-2 * r / h**2 - 1)


def _t_slope_is_positive(h):
    assert 0 < h <= Fraction(1, 8)
    delta = h**2 / 4
    # g = 1 on K: |r| <= delta (1 + 2h + delta) < h^2/2 for every point within delta (max norm)
    # of an orbit point (s, s^2), 0 <= s <= h, and _g vanishes for -2r/h^2 - 1 <= 0.
    assert delta * (1 + 2 * h + delta) < h**2 / 2
    # sup_K ||f||_inf = 1: the first component of f is 1 and |2 y1| <= 2 (h + delta) on K (max norm).
    assert 2 * (h + delta) <= 1
    y0 = (Fraction(0), Fraction(0))
    assert _g(y0, h) == 1
    t1 = h * _g(y0, h)
    assert t1 == h  # T = h: N = 1, t_1 >= T first reached at the first step (equality)
    y1 = (y0[0] + h * _g(y0, h) * 1, y0[1] + h * _g(y0, h) * 2 * y0[0])  # Euler step
    assert y1 == (h, Fraction(0))
    g1 = _g(y1, h)
    assert g1 == 5  # g in [1, 5] throughout (psi in [0, 1])
    # Hermite t-component: values 0, h; sigma-slopes h*g0 = h at 0 and h*g1 at 1.
    # d/dsigma t = h * (1 + (2 - 2b) s + 3 (b - 1) s^2), b = g1/g0
    b = g1 / _g(y0, h)
    a1, a2 = 2 - 2 * b, 3 * (b - 1)
    pts = [Fraction(0), Fraction(1)]
    if a2 != 0:
        vertex = -a1 / (2 * a2)
        if 0 < vertex < 1:
            pts.append(vertex)
    slope_min = min(h * (1 + a1 * s + a2 * s * s) for s in pts)
    return slope_min > 0


def refute() -> Witness:
    return Witness(
        entry="MD_0029",
        point={"h": Fraction(1, 16)},
        claim=_t_slope_is_positive,
        note=(
            "Euler p=1 with cubic Hermite, Delta s = h (any h <= 1/8), T = h, d=2. Tuple fixed "
            "across h: g_min=1, g_max=5, Lip_y(g) on K = 0 (g = 1 on the delta-tube, "
            "delta=h^2/4), sup_K||f||_inf = 1. Euler iterate leaves K (curvature of the orbit), "
            "where g climbs to 5: beta = 5 > 4, t-slope = h(1 - 8s + 12s^2) < 0 on (1/6, 1/2), "
            "min -h/3 at s=1/3. Violates the positivity of the t-slope. Exploits that Lip_y(g) "
            "is only measured on K while the iterates and Hermite slope use g off K."
        ),
    )
