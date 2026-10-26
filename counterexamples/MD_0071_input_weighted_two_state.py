"""MD_0071 (b): the input-weighted bank is passive for every input iff rdot_j >= -2 p_j r_j for every j, t.

Witness against the "only if": n = 2, T = 1/2, p_1 = p_2 = 0, r_1 = 1 - t, r_2 = 1 + t
(C^1, p >= 0, r >= 1/2 > 0 on [0, 1/2]). The rate condition fails for j = 1 at every t
(rdot_1 = -1 < 0 = -2 p_1 r_1), yet the bank is passive for every initial state and input
with respect to the stated storage V = z_1^2/(2 r_1) + z_2^2/(2 r_2). Certificate: since
r_1 + r_2 = 2, y = z_1 + z_2 obeys ydot = 2u, so S = y^2/4 has u y - dS/dt = 0 identically,
S >= 0, and V(0, z) - S(z) = (z_1 - z_2)^2/4 >= 0 (Cauchy-Schwarz with weights r(0)).
Hence int_0^T u y dt = S(z(T)) - S(z(0)) >= -V(z(0)). Exact sympy algebra over the rationals.
"""
import sympy as sp

from mdept.refute import Witness


def _claim(T, p, r):
    t, z1, z2, u = sp.symbols("t z1 z2 u", real=True)
    p = [sp.sympify(e) for e in p]
    r = [sp.sympify(e) for e in r]
    z = [z1, z2]
    for e in p + r:
        assert sp.Poly(e, t).degree() <= 1
    assert all(e.subs(t, s) >= 0 for e in p for s in (0, T))
    assert all(e.subs(t, s) > 0 for e in r for s in (0, T))
    # rate condition rdot_j >= -2 p_j r_j for all j, t
    rate_holds = all(
        sp.solve_univariate_inequality(sp.diff(rj, t) + 2 * pj * rj < 0, t, relational=False)
        .intersect(sp.Interval(0, T)).is_empty
        for pj, rj in zip(p, r)
    )
    # identity of clause (b): u y = dV/dt + sum (p/r + rdot/(2 r^2)) z^2 along solutions
    zdot = [-pj * zj + rj * u for pj, rj, zj in zip(p, r, z)]
    y = z1 + z2
    V = sum(zj**2 / rj for rj, zj in zip(r, z)) / 2
    dV = sp.diff(V, t) + sum(sp.diff(V, zj) * dzj for zj, dzj in zip(z, zdot))
    D = sum((pj / rj + sp.diff(rj, t) / (2 * rj**2)) * zj**2 for pj, rj, zj in zip(p, r, z))
    assert sp.simplify(u * y - dV - D) == 0
    # passivity certificate
    S = y**2 / 4
    dS = sp.diff(S, t) + sum(sp.diff(S, zj) * dzj for zj, dzj in zip(z, zdot))
    assert sp.expand(u * y - dS) == 0
    assert sp.expand(V.subs(t, 0) - S - (z1 - z2) ** 2 / 4) == 0
    passive = True
    return passive == rate_holds


def refute() -> Witness:
    t = sp.Symbol("t", real=True)
    return Witness(
        entry="MD_0071",
        point={"T": sp.Rational(1, 2), "p": (sp.Integer(0), sp.Integer(0)), "r": (1 - t, 1 + t)},
        claim=_claim,
        note="(b) only-if: p=0, r=(1-t, 1+t), T=1/2; rate fails at j=1 for all t, yet y=z1+z2 has "
             "ydot=2u, so int u y = (y(T)^2-y(0)^2)/4 >= -y(0)^2/4 >= -V(z(0)).",
    )
