"""MD_0034: |l(u(t)) - l(y0)| <= delta t max_theta sum_i |beta_i(theta)| for every accepted-step piece.

Witness (explicit Euler with a dense-output weight that overshoots b inside the step):
V = R, l = identity, f(y) = 1 (constant), so |l(f(y))| = 1 and delta = 1 satisfies H0'.
s = 1, a_11 = 0, b_1 = 1, beta_1(theta) = 2 theta - theta^2 (a polynomial, beta_1(1) = 1 = b_1,
beta_1(0) = 0). Steps h_n = 1 for every n, t_0 = 0, t_n = n, y_n = n, k_{n,1} = 1, P_n = identity.

Every hypothesis holds: H1 (R is a real vector space, l linear, f any map); H2 (s = 1, real
coefficients, beta_1 a function on [0, 1]); H3 (end point y_n + 1 * 1 * 1 = n + 1); H4 holds
through the stage equation for every (n, i): k_{n,1} = f(y_n + h_n a_11 k_{n,1}) = 1, so the FSAL
alternative is never needed (and it would give the same value, f is constant); H5 (P_n = id
preserves l, y_{n+1} = n + 1 = end point); H6 and H7 (t_0 = 0, h_n = 1 > 0, beta_1 polynomial,
beta_1(1) = b_1).

The conclusion is read at t = 1/2, which lies in [t_0, t_1] = [0, 1] only, so the one piece that
applies at t is u_0, at theta = 1/2: u(1/2) = 0 + 1 * beta_1(1/2) * 1 = 3/4. The bound is
delta * t * max_theta |beta_1(theta)| = 1 * 1/2 * 1 = 1/2: beta_1'(theta) = 2 - 2 theta >= 0 on
[0, 1], so beta_1 is increasing and nonnegative there, with max beta_1(1) = 1. 3/4 > 1/2.
The statement fails because the dense weight sum_i |beta_i(theta)| is evaluated only through its
max, while the elapsed time t enters linearly: t * max|beta| can be smaller than h_0 * |beta(theta)|
(here 1/2 < 3/4).
"""
from fractions import Fraction
from mdept.refute import Witness


def _beta1(theta):
    return 2 * theta - theta**2


def _claim(t, delta):
    one = Fraction(1)
    f = lambda y: one  # noqa: E731
    ell = lambda v: v  # noqa: E731
    a11, b1, h, t0, y0 = Fraction(0), one, one, Fraction(0), Fraction(0)
    # H0': |l(f(y))| <= delta for every y (f is constant 1).
    assert delta >= 0 and abs(ell(f(y0))) <= delta
    # H7: beta_1(1) = b_1, h > 0, t_0 = 0.
    assert _beta1(one) == b1 and h > 0 and t0 == 0
    # Steps n = 0, 1, 2 (pattern y_n = n for all n): stage equation and post-step map P = id.
    y = y0
    for n in range(3):
        k = f(y + h * a11 * one)
        assert k == f(y + h * a11 * k)  # H4, stage equation
        end = y + h * b1 * k
        assert end == n + 1
        assert ell(end) == ell(end)  # H5, P_n = identity
        y = end
    # t = 1/2 lies only in piece 0 ([0, 1]); theta = (t - t_0)/h_0.
    assert t0 < t < t0 + h
    theta = (t - t0) / h
    k0 = f(y0)
    u = y0 + h * _beta1(theta) * k0
    # max over [0, 1] of |beta_1|: beta_1' = 2 - 2 theta >= 0, beta_1(0) = 0, so max = beta_1(1).
    max_beta = abs(_beta1(one))
    return abs(ell(u) - ell(y0)) <= delta * t * max_beta


def refute() -> Witness:
    return Witness(
        entry="MD_0034",
        point={"t": Fraction(1, 2), "delta": Fraction(1)},
        claim=_claim,
        note=(
            "V=R, l=id, f=1, delta=1, s=1 explicit Euler (a=0, b=1), beta_1 = 2 theta - theta^2 "
            "(polynomial, beta_1(1)=b_1), h_n=1, t_0=0, y_n=n, P_n=id; every stage by the stage "
            "equation, FSAL never used. At t=1/2 (piece 0 only, theta=1/2): |l(u)-l(y0)| = 3/4 > "
            "delta t max|beta_1| = 1/2."
        ),
    )
