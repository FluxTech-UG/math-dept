"""MD_0027 (b): with a stable step-size map (slope bound) and a nondegenerate estimate, there are tau0 > 0 and C'
(independent of tau and U) with ||d_theta y_N(theta; h(theta, tau)) - d_theta y_N(theta; h)|_{h = h(theta, tau)}|| <= C' H^p.
Refuted: for every tau0, C', H0 there are tau <= tau0, an admissible U and theta in U with H <= H0 and
||R|| > C' H (R the controller term). The estimate E is C^2 = C^{p+1} jointly, ||E|| ~ h^2, but d log||E||/d theta
is unbounded like h^{-1/2}; the hypotheses give E only C^{p+1}, which does not bound d_theta E / E.

Construction.  d = m = p = 1, Theta = (1/2, 3/2), f(y, theta) = -theta y, y0 = 1, T = 2, explicit Euler
  Psi_h(y, theta) = (1 - theta h) y (A = [[0]], b = [1], c = [0], classical order 1).  kappa = 1/4.
  E(y, h, theta) = h^2 (2 + a(h) Q((theta - 1)/h)) for h > 0, E(y, 0, theta) = 0, independent of y, where
    a(h) = w / (4 (1 + w)), w = sqrt(h);  Q(s) = s chi(s), chi smooth, chi = 1 on |s| <= 1, chi = 0 on |s| >= 2,
    0 <= chi <= 1 (the standard bump chi(s) = b(2 - |s|) / (b(2 - |s|) + b(|s| - 1)), b(u) = exp(-1/u) for u > 0, 0 else).
  phi(x) = (1 + 3v)/(3 + v), v = (x/2)^(1/2).  h_init(tau) = sqrt(tau)/2, independent of theta.
  The sequence: j >= 3 odd, h = 4/j^2, k = (j^2 - 1)/2 (so T = (k + 1/2) h), tau = 4 h^2 = 64/j^4, theta = 1.

Hypotheses (checked in claim() or below).
  H1: f is C^infinity, y0 = 1 is C^1, Euler has order 1, the exact solution exists on [0, 2]; E does not depend on y, so
    K_delta plays no role for E; the derivative bounds of f on K_delta and of E are fixed numbers (E is one fixed
    function; the family is indexed only by tau).
  E is C^2 on the closed domain {h >= 0}, all arguments jointly (also at h = 0): for h > 0 write
    E = 2 h^2 + A(h) Q(s), A = h^2 a(h) = h^(5/2)/(4 (1 + sqrt h)), s = (theta - 1)/h.  Every partial of order <= 2
    in (y, h, theta), as a function of (w, s, Q, Q', Q''), is w times a limit-finite expression of (w, s, Q, Q', Q'')
    (sympy, claim() step "E is C^2"); Q, Q', Q'' are bounded and supported on |s| <= 2, so every partial of order <= 2
    of E - 2 h^2 is O(h^(1/2)) uniformly in theta, tends to 0 as h -> 0 and the value of E - 2h^2 and its partials
    at h = 0 are 0; hence all partials extend continuously to h = 0 (by the mean value theorem they are the one-sided
    derivatives) and E is C^2 jointly.  C^infinity for h > 0.
  Nondegenerate: 0 < a < 1/4 and |Q| <= 2 give |aQ| < 1/2, so (3/2) h^2 <= ||E|| <= (5/2) h^2: c_E = 3/2, C_E = 5/2.
  phi (sympy): smooth on (0, inf), phi' > 0, range (1/3, 3) so phi_min = 1/3 < 1 < phi_max = 3, phi(x) <= phi(1) = rho
    < 1 for x < 1 (phi increasing), phi(2) = 1, and (p+1) x phi'/phi = 8v/((3+v)(1+3v)) = 1/2 - 3(v-1)^2 /
    (2 (3+v)(1+3v)) <= 1/2 = 2 - gamma with gamma = 3/2 (certified identity).
  Run at theta = 1, tau: eps = 2 h^2 = tau/2 at every unclipped step (Q(0) = 0, so E(h, 1) = 2 h^2 exactly), x = tau/eps = 2,
    phi(2) = 1: no rejection, eps = tau/2 > kappa tau strictly, every trial step is h; after k steps t = k h =
    2 - h/2, so the trial h is clipped to h/2; at the clipped step eps <= (5/2)(h/2)^2 < tau accepts.  N = k + 1, H = h.
  U: all decisions are finitely many strict inequalities between continuous functions of theta that hold at theta = 1; by
    induction they hold on an open interval U around 1.  claim() certifies the whole pattern on a closed box
    [1 - r, 1 + r] in interval arithmetic (with |theta - 1|/h < 1, where Q(s) = s) for every j it uses.

Proof that (b) fails (every step is certified in claim()).
  L1 (step map, exact).  Let a_n = d log h_n / d theta at theta = 1.  x_n = tau/eps_n, h_{n+1} = h_n phi(x_n), so
    a_{n+1} = a_n + psi (d log x_n/d theta), psi = x phi'(x)/phi(x) = 1/4 at x = 2 and d log x_n = -(2 a_n + G_theta/G):
    G = eps/h^2 = 2 + a(h) Q(s), at theta = 1: G = 2, G_theta = a(h) Q'(0)/h = a(h)/h.  With g = G_theta/G = a(h)/(2h)
    = 1/(8 w (1 + w)) (h = w^2, w = 2/j):  a_{n+1} = a_n/2 - g/4, a_0 = 0, so a_n = a* (1 - 2^(-n)),
    a* = -g/2 = -1/(16 w (1 + w)) = -j^2/(32 (j + 2)).  The multiplier is 1/2 (contraction), the forcing is the
    unbounded d log E/d theta ~ h^(-1/2)/8.
  L2 (the controller term).  y_N = prod (1 - theta h_n), so R = -theta y_N sum dh_n/(1 - theta h_n); the clip
    h_k = T - sum_{n<k} h_n gives sum_{n<=k} dh_n = 0, and with h_n = h (n < k), h_k = h/2, theta = 1:
    R = -(1 - h)^(k-1) h^2 S / 2, S = sum_{n<k} a_n = a* (k - 2 + 2^(1-k)).
  L3 (lower bound).  (i) (k-1) h/(1-h) = 2 (j^2-3)/(j^2-4) <= 3, log(1-h) >= -h/(1-h), so (1-h)^(k-1) >= e^-3 > 1/21;
    (ii) |S| >= |a*| (k - 2) = j^2 (j^2 - 5) / (64 (j + 2)); (iii) |R|/H = (1-h)^(k-1) h |S| / 2 >= (j^2 - 5)/(672 (j+2))
    >= (j - 3)/672.  So |R|/H -> infinity like j = 2 H^(-1/2).
  Conclusion.  Given tau0, C', H0, take odd j >= 3 with (j - 3)/672 > C', 4/j^2 <= H0, 64/j^4 <= tau0.  Then at
  theta = 1 in the admissible U for tau = 64/j^4: ||R|| > C' H, whatever tau0, C', H0.

Script versus docstring.  claim() certifies the phi and E facts (sympy), L1/L2 closed forms symbolically and against the
exact forward-mode controller run (Fractions, the controller of the Statement) at every j in the point, each inequality
of L3 (sympy; e^3 < 21 in interval arithmetic), and for each adversary the chosen j with the L3 bound.  The docstring
argues only the continuity induction for U (also interval-certified), the derivation of R from y_N = prod(1 - theta h_n),
and the rate of the C^2 remainder (the limit check).  The universal step is L3, proved for every odd j >= 3.
"""
from fractions import Fraction
from math import isqrt

import sympy as sp
from mpmath import iv

from mdept.refute import Witness

KAPPA = Fraction(1, 4)
T = Fraction(2)


def _certain(cond, what):
    if not cond:
        raise ValueError(f"not certified: {what}")


# ---- phi -------------------------------------------------------------------------------------------
def _check_phi():
    x = sp.symbols("x", positive=True)
    v = sp.sqrt(x / 2)
    phi = (1 + 3 * v) / (3 + v)
    dphi = sp.diff(phi, x)
    V = sp.symbols("V", positive=True)
    slope = sp.simplify((2 * x * dphi / phi).subs(x, 2 * V**2))
    _certain(sp.simplify(slope - 8 * V / ((3 + V) * (1 + 3 * V))) == 0, "(p+1) x phi'/phi = 8V/((3+V)(1+3V))")
    _certain(sp.simplify(sp.Rational(1, 2) - slope - 3 * (V - 1) ** 2 / (2 * (3 + V) * (1 + 3 * V))) == 0,
             "slope = 1/2 - 3(V-1)^2/(2(3+V)(1+3V)) <= 1/2 = 2 - gamma, gamma = 3/2")
    _certain(sp.simplify(dphi - 4 / (sp.sqrt(2) * sp.sqrt(x) * (3 + v) ** 2)) == 0, "phi' formula")
    _certain(sp.simplify(4 / (sp.sqrt(2) * sp.sqrt(x) * (3 + v) ** 2)).is_positive, "phi' > 0 on (0, inf)")
    _certain(sp.limit(phi, x, 0, "+") == sp.Rational(1, 3) and sp.limit(phi, x, sp.oo) == 3, "range (1/3, 3)")
    _certain(phi.subs(x, 2) == 1 and sp.simplify(x * dphi / phi).subs(x, 2) == sp.Rational(1, 4), "phi(2) = 1, psi(2) = 1/4")
    rho = sp.simplify(phi.subs(x, 1))
    _certain((1 - rho).is_positive and (rho - sp.Rational(1, 3)).is_positive, "phi(1) = rho < 1")


# ---- E is C^2 jointly, partials O(w) -----------------------------------------------------------------
def _check_E_c2():
    h, th = sp.symbols("h theta", positive=True)
    w, s, q0, q1, q2 = sp.symbols("w s q0 q1 q2", positive=True)
    Q = sp.Function("Q")
    a = sp.sqrt(h) / (4 * (1 + sp.sqrt(h)))
    F = h**2 * a * Q((th - 1) / h)  # E - 2 h^2
    seen = 0
    for (i, j) in [(0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2)]:  # (d_h order, d_theta order)
        d = F
        if i:
            d = sp.diff(d, h, i)
        if j:
            d = sp.diff(d, th, j)
        d = d.doit()
        # replace Q and its derivatives by symbols at argument s
        u = sp.Dummy("u")
        d = d.replace(lambda e: isinstance(e, sp.Subs), lambda e: e.doit())
        d = d.subs({sp.Subs(sp.Derivative(Q(u), (u, 2)), u, (th - 1) / h): q2})
        for k, qk in ((2, q2), (1, q1)):
            d = d.replace(lambda e, k=k: isinstance(e, sp.Derivative) and e.args[0].func == Q and e.derivative_count == k
                          , lambda e, qk=qk: qk)
        d = d.subs(Q((th - 1) / h), q0)
        d = d.subs(th, 1 + s * h).subs(h, w**2)
        d = sp.simplify(d)
        _certain(not d.has(Q), f"Q symbols replaced for order ({i},{j})")
        lim = sp.limit(sp.simplify(d / w), w, 0, "+")  # finite polynomial in s, q0, q1, q2
        _certain(lim.is_finite is not False and not lim.has(sp.oo, sp.zoo, sp.nan), f"partial ({i},{j}) = O(w)")
        seen += 1
    _certain(seen == 6, "all partials of order <= 2 in (h, theta)")  # y-partials vanish (E independent of y)


# ---- L1, L2, L3 ----------------------------------------------------------------------------------------
def _check_lemmas():
    n, j = sp.symbols("n j", integer=True, positive=True)
    wv = 2 / sp.Symbol("j", positive=True)
    jj = sp.Symbol("j", positive=True)
    w = 2 / jj
    g = 1 / (8 * w * (1 + w))
    astar = -g / 2
    _certain(sp.simplify(astar + jj**2 / (32 * (jj + 2))) == 0, "a* = -j^2/(32(j+2))")
    an = lambda m: astar * (1 - sp.Rational(1, 2) ** m)
    _certain(an(0) == 0, "L1 base")
    _certain(sp.simplify(an(n + 1) - (an(n) / 2 - g / 4)) == 0, "L1 step a_{n+1} = a_n/2 - g/4")
    k = sp.Symbol("k", integer=True, positive=True)
    S = lambda m: astar * (m - 2 + sp.Rational(1, 2) ** (m - 1))
    _certain(S(0) == 0 + astar * (-2 + 2) and sp.simplify(S(k + 1) - S(k) - an(k)) == 0, "L2 S_k = sum_{n<k} a_n")
    # L3
    h = 4 / jj**2
    kk = (jj**2 - 1) / 2
    _certain(sp.simplify((kk - 1) * h / (1 - h) - 2 * (jj**2 - 3) / (jj**2 - 4)) == 0, "(k-1)h/(1-h)")
    _certain(sp.simplify(3 - 2 * (jj**2 - 3) / (jj**2 - 4) - (jj**2 - 6) / (jj**2 - 4)) == 0, "3 - ... = (j^2-6)/(j^2-4) >= 0")
    iv.dps = 50
    _certain(iv.exp(iv.mpf(3)).b < 21, "e^3 < 21")
    _certain(sp.simplify(sp.Rational(1, 21) * (h / 2) * (-astar) * (kk - 2) - (jj**2 - 5) / (672 * (jj + 2))) == 0,
             "L3 assembly (j^2-5)/(672(j+2))")
    _certain(sp.simplify((jj**2 - 5) - (jj - 3) * (jj + 2) - (jj + 1)) == 0, "(j^2-5) = (j-3)(j+2) + (j+1) >= (j-3)(j+2)")


# ---- exact forward-mode controller of the Statement -------------------------------------------------------
class _D:
    def __init__(self, v, d=Fraction(0)):
        self.v, self.d = Fraction(v), Fraction(d)

    def _c(o): return o if isinstance(o, _D) else _D(o)
    def __add__(s, o): o = _D._c(o); return _D(s.v + o.v, s.d + o.d)
    __radd__ = __add__
    def __sub__(s, o): o = _D._c(o); return _D(s.v - o.v, s.d - o.d)
    def __rsub__(s, o): return _D(o) - s
    def __mul__(s, o): o = _D._c(o); return _D(s.v * o.v, s.v * o.d + s.d * o.v)
    __rmul__ = __mul__
    def __truediv__(s, o): o = _D._c(o); return _D(s.v / o.v, (s.d * o.v - s.v * o.d) / o.v**2)
    def __rtruediv__(s, o): return _D(o) / s


def _rat_sqrt(q: Fraction) -> Fraction:
    a, b = isqrt(q.numerator), isqrt(q.denominator)
    _certain(a * a == q.numerator and b * b == q.denominator, f"{q} is a rational square")
    return Fraction(a, b)


def _eps_dual(h: _D, th: _D) -> _D:
    w = _D(_rat_sqrt(h.v), h.d / (2 * _rat_sqrt(h.v)))
    a = w / (4 * (1 + w))
    s = (th - 1) / h
    _certain(abs(s.v) <= 1, "Q(s) = s region")
    return h * h * (2 + a * s)


def _phi_dual(x: _D) -> _D:
    _certain(x.v == 2, "x = 2 exactly (fixed point of the step map)")
    v = _D(1, x.d / 4)  # v = (x/2)^(1/2), dv/dx = v/(2x) = 1/4
    return (1 + 3 * v) / (3 + v)


def _run_point(j: int):
    h0 = Fraction(4, j * j)
    tau = 4 * h0 * h0
    th = _D(1, 1)
    h = _D(_rat_sqrt(tau) / 2)  # h_init(tau), independent of theta
    y, dyf, t, n, a = _D(1), Fraction(0), _D(0), 0, []
    H = Fraction(0)
    while True:
        rem = T - t.v
        if h.v > rem:
            h, clipped = _D(rem, -t.d), True  # clip: h = T - t_n
        else:
            _certain(h.v < rem, f"strict no-clip at step {n}")
            clipped = False
        if clipped:  # eps only decides acceptance: bound by (5/2) h^2 < tau
            _certain(Fraction(5, 2) * h.v**2 < tau, "clipped step accepts")
        else:
            eps = _eps_dual(h, th)
            _certain(eps.v < tau and eps.v > KAPPA * tau, f"strict accept and eps > kappa tau at step {n}")
            a.append(h.d / h.v)
        _certain(1 - h.v > 0 and y.v > 0, "positivity")
        dyf = (1 - h.v) * dyf - h.v * y.v  # frozen-grid tangent at theta = 1
        y = (1 - th * h) * y
        t = t + h
        H = max(H, h.v)
        n += 1
        if clipped:
            _certain(t.v == T and t.d == 0, "sum dh = 0")
            return y.d - dyf, H, n, a, h0, tau
        h = h * _phi_dual(tau / eps)


def _run_box(j: int, r_exp: int = 40):
    """Interval run of the controller on theta in [1 - r, 1 + r]; returns N. All decisions strict."""
    iv.dps = r_exp + 80
    q = lambda f: iv.mpf(f.numerator) / iv.mpf(f.denominator)
    h0 = Fraction(4, j * j)
    tau = q(4 * h0 * h0)
    r = iv.mpf(10) ** (-r_exp)
    th = iv.mpf([1 - r.b, 1 + r.b])
    h = q(_rat_sqrt(4 * h0 * h0) / 2)
    t, n = iv.mpf(0), 0
    while True:
        rem = q(T) - t
        if (h - rem).a > 0:
            h, clipped = rem, True
        else:
            _certain((h - rem).b < 0, f"box: strict no-clip at step {n}")
            clipped = False
        s = (th - 1) / h
        _certain(s.a > -1 and s.b < 1, "box: |s| < 1 (Q(s) = s)")
        w = iv.sqrt(h)
        eps = h * h * (2 + w / (4 * (1 + w)) * s)
        _certain((eps - tau).b < 0, f"box: strict accept at step {n}")
        if not clipped:
            _certain((eps - q(KAPPA) * tau).a > 0, f"box: eps > kappa tau at step {n}")
        _certain((1 - th * h).a > 0, "box: positivity")
        t = t + h
        n += 1
        if clipped:
            return n
        v = iv.sqrt(tau / eps / 2)
        h = h * (1 + 3 * v) / (3 + v)


def _certify_j(j: int):
    R, H, N, a, h, tau = _run_point(j)
    k = (j * j - 1) // 2
    _certain(N == k + 1 and H == h and len(a) == k, f"j = {j}: N = k + 1, H = h")
    astar = Fraction(-j * j, 32 * (j + 2))
    _certain(all(a[i] == astar * (1 - Fraction(1, 2**i)) for i in range(k)), f"j = {j}: L1 a_n in the run")
    S = astar * (k - 2 + Fraction(1, 2 ** (k - 1)))
    _certain(R == -((1 - h) ** (k - 1)) * h * h * S / 2, f"j = {j}: L2 closed form of R")
    _certain(abs(R) / H >= Fraction(j - 3, 672), f"j = {j}: L3 bound")
    _certain(_run_box(j, r_exp=k + 30) == N, f"j = {j}: pattern certified on the theta box")
    return R, H, tau


def _j_for(tau0: Fraction, Cp: Fraction, H0: Fraction) -> int:
    """An odd j >= 3 with (j - 3)/672 > C', 4/j^2 <= H0 and 64/j^4 <= tau0 (integer search by doubling, then bisect)."""
    ok = lambda j: (j - 3) > 672 * Cp and Fraction(4, j * j) <= H0 and Fraction(64, j**4) <= tau0
    hi = 3
    while not ok(hi):
        hi *= 2
    lo = 3
    while lo < hi:  # ok is monotone in j
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if ok(mid) else (mid + 1, hi)
    return lo if lo % 2 == 1 else lo + 1


def claim(theta: Fraction, js: tuple, adversaries: tuple) -> bool:
    """Clause (b). Returns False when every step of the proof is certified: the exact runs at the listed j match the
    closed forms, the L3 lower bound (proved for all odd j >= 3) exceeds C' for the chosen j of every adversary."""
    _certain(theta == 1, "the witness parameter is theta = 1")
    _check_phi()
    _check_E_c2()
    _check_lemmas()
    for j in js:
        _certify_j(j)
    for tau0, Cp, H0 in adversaries:
        j = _j_for(tau0, Cp, H0)
        _certain(j % 2 == 1 and Fraction(64, j**4) <= tau0 and Fraction(4, j * j) <= H0 and Fraction(j - 3, 672) > Cp,
                 f"adversary {tau0, Cp, H0}: chosen j = {j} beats it by L3 (L3 holds for every odd j >= 3)")
    return False


def refute() -> Witness:
    return Witness(
        entry="MD_0027",
        point={
            "theta": Fraction(1),
            "js": (3, 5, 7, 9, 11, 15, 21, 31),
            "adversaries": (
                (Fraction(1, 10), Fraction(1, 2), Fraction(1, 10)),
                (Fraction(1, 10**4), Fraction(10**6), Fraction(1, 100)),
                (Fraction(1, 10**20), Fraction(10**30), Fraction(1, 10**9)),
            ),
        },
        claim=claim,
        note="f = -theta y, Euler, E = h^2 (2 + a(h) Q((theta-1)/h)) with a = w/(4(1+w)), w = sqrt h, Q(s) = s chi(s): "
        "C^2 jointly, (3/2) h^2 <= E <= (5/2) h^2, but d log E/d theta = h^(-1/2)/8 at theta = 1. phi = (1+3v)/(3+v), "
        "v = sqrt(x/2) (slope 1/2 = 2 - gamma, gamma = 3/2; rho < 1), h_init = sqrt(tau)/2, kappa = 1/4, T = 2, "
        "tau = 64/j^4, h = 4/j^2. At theta = 1 the step map sits on its fixed point x = 2 (multiplier 1/2), forced by "
        "the unbounded d log E/d theta: a_n = a*(1 - 2^-n), a* = -j^2/(32(j+2)); R = -(1-h)^(k-1) h^2 S/2, "
        "|R|/H >= (j-3)/672 -> infinity, so (b) fails for every tau0, C', H0.",
    )
