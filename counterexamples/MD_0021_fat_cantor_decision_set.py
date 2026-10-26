"""MD_0021 (a): the set B of non-locally-constant decision patterns can have positive measure.

Construction, with every hypothesis of MD_0020/MD_0021 met (d = m = 1, p = 1):
  Theta = (0, 1); Euler step Psi_h(y) = y + h f(y, theta) (A = [[0]], b = [1], order 1);
  f(y, theta) = -mu(theta) y, y0 = 1, T = 1/4, tau = 1/32, h_init = 1;
  E = Heun minus Euler = (h/2)(f(y + h f, theta) - f(y, theta)) = mu^2 h^2 y / 2, which is C^2 and
  satisfies |E| <= C_E h^2 on K_delta;
  mu = 1 + psi, psi >= 0 of class C^2, psi(theta) = sum over the removed gaps (a, b) of the
  Smith-Volterra-Cantor set K of ((theta - a)(b - theta))^3 on (a, b), 0 elsewhere. A piece is
  O(dist(theta, K)^3), so psi is C^2 with all derivatives to order 2 zero on K; psi = 0 exactly
  on K, and K has measure 1/2 (stage j removes 2^(j-1) gaps of length 4^(-j)).
  phi(x) = 1/2 + (3/2) g(x-2) / (g(x-2) + g(3-x)), g(t) = exp(-1/t) for t > 0 else 0: smooth,
  nondecreasing, values in [1/2, 2], exactly 1/2 for x <= 2 and exactly 2 for x >= 3.
Controller at theta (exact rationals): the first trial is clipped to T and has eps = mu^2/32 = tau
iff psi = 0.  On K: accepted at once, N = 1, y_N = 3/4.  Off K (psi > 0, mu <= 1 + 2e-5): rejected
(x = 1/mu^2 <= 2, so phi = 1/2), retried at h = 1/8, eps = mu^2/128 (unclipped, eps >= tau/4, so
kappa = 1/4 holds at every theta), accepted; the next trial has x >= 3, phi = 2, is clipped to 1/8
and accepted: N = 2, y_N = (1 - mu/8)^2.  Hence the pattern at each point of K differs from the
pattern at points off K arbitrarily near it (K is closed with empty interior), so K is inside B
and lambda(B) >= 1/2.  The conclusion (a), "B has Lebesgue measure zero", is false.
(Side effect: y_N jumps by 1/64 across each point of K, with H = 1/4.)
"""
from fractions import Fraction as F

import sympy as sp

from mdept.refute import Witness

PSI_BOUND = F(1, 10**4)  # certified below: mu - 1 <= PSI_BOUND everywhere


def _gaps(stages):
    """Removed gaps (a, b, stage) of the Smith-Volterra-Cantor set, exact rationals."""
    intervals, gaps = [(F(0), F(1))], []
    for j in range(1, stages + 1):
        g, nxt = F(1, 4**j), []
        for l, r in intervals:
            c = (l + r) / 2
            gaps.append((c - g / 2, c + g / 2, j))
            nxt += [(l, c - g / 2), (c + g / 2, r)]
        intervals = nxt
    return gaps


def _mu(theta, gaps):
    for a, b, _ in gaps:
        if a < theta < b:
            return 1 + ((theta - a) * (b - theta)) ** 3
    return F(1)


def _phi(x):
    if x <= 2:
        return F(1, 2)
    if x >= 3:
        return F(2)
    raise ValueError("phi evaluated inside its smooth transition (2, 3); not reached by construction")


def _controller(theta, gaps, T, tau, h_init):
    """Exact run of the MD_0020 controller; returns (pattern, N, y_N, min unclipped eps/tau)."""
    mu, y, t, h = _mu(theta, gaps), F(1), F(0), h_init
    pattern, n, kmin = [], 0, None
    while t < T:
        while True:
            clip = h > T - t
            if clip:
                h = T - t
            eps = mu**2 * h**2 * abs(y) / 2
            accept = eps <= tau
            pattern.append((accept, clip))
            if not clip:
                kmin = eps / tau if kmin is None else min(kmin, eps / tau)
            if accept:
                break
            h = h * _phi(tau / eps)
        y, t, n = y * (1 - mu * h), t + h, n + 1
        h = h * _phi(tau / eps)
    return tuple(pattern), n, y, kmin


def _claim(stages, tau, T, h_init):
    gaps = _gaps(stages)
    # psi is bounded (hypotheses on E, eps >= kappa tau, phi region) uniformly over all stages.
    j = sp.Symbol("j", integer=True, positive=True)
    psi_sup = sp.summation(2 ** (j - 1) * (sp.Rational(1, 2) * sp.Rational(1, 4) ** j) ** 6, (j, 1, sp.oo))
    assert F(int(psi_sup.p), int(psi_sup.q)) <= PSI_BOUND
    kappa = F(1, 4)
    on_K = [x for a, b, s in gaps for x in (a, b)]
    mids = [((a + b) / 2, s) for a, b, s in gaps]
    ref_in, n_in, y_in, _ = _controller(on_K[0], gaps, T, tau, h_init)
    ok = ref_in == ((True, True),) and n_in == 1 and y_in == F(3, 4)
    for x in on_K:
        pat, n, y, kmin = _controller(x, gaps, T, tau, h_init)
        ok = ok and (pat, n, y) == (ref_in, 1, F(3, 4))
    jump = None
    for m, _ in mids:
        pat, n, y, kmin = _controller(m, gaps, T, tau, h_init)
        ok = ok and pat == ((False, True), (True, False), (True, True)) and n == 2 and kmin >= kappa
        jump = abs(y - F(3, 4)) if jump is None else jump
    # every endpoint of a stage-s gap (s < stages) has a deeper gap midpoint within 2^(-s) of it
    for a, b, s in gaps:
        if s < stages:
            for e in (a, b):
                ok = ok and any(s2 > s and abs(m - e) < F(1, 2**s) for m, s2 in mids)
    # lambda(K) = 1 - sum_j 2^(j-1) 4^(-j) = 1/2, exactly
    removed = sp.summation(2 ** (j - 1) * sp.Rational(1, 4) ** j, (j, 1, sp.oo))
    measure_K = 1 - removed
    assert measure_K == sp.Rational(1, 2)
    measure_B_positive = ok and measure_K > 0  # K inside B
    return not measure_B_positive  # claim (a): lambda(B) = 0


def refute() -> Witness:
    return Witness(
        entry="MD_0021",
        point={"stages": 6, "tau": F(1, 32), "T": F(1, 4), "h_init": F(1)},
        claim=_claim,
        note=(
            "Claim (a) false. d=m=1, p=1, Euler stepper, f=-mu(theta)y, mu=1+psi, psi>=0 C^2 vanishing exactly "
            "on the Smith-Volterra-Cantor set K (measure 1/2); E=mu^2h^2y/2 (Heun-Euler, C^2, <=C_E h^2); "
            "phi smooth nondecreasing in [1/2,2], =1/2 on x<=2, =2 on x>=3. First trial (clipped to T) has "
            "eps=mu^2/32=tau iff theta in K: accepted on K (N=1), rejected off K (N=2); kappa=1/4 at every "
            "theta. Hence K is inside B and lambda(B)>=1/2. Exact rationals; the finite stage checks sample "
            "the infinite construction, the measure is the exact geometric series."
        ),
    )
