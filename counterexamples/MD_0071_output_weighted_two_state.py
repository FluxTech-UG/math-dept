"""MD_0071 (a): the output-weighted bank is passive for every input iff rdot_j <= 2 p_j r_j for every j, t.

Witness against the "only if": n = 2, T = 1/2, p_1 = p_2 = 0, r_1 = 1 + t, r_2 = 4 - 2t
(C^1, p >= 0, r >= 1 > 0 on [0, 1/2]). The rate condition fails for j = 1 at every t
(rdot_1 = 1 > 0 = 2 p_1 r_1), yet the bank is passive for every initial state and input
with respect to the stated storage V = (r_1 z_1^2 + r_2 z_2^2)/2. Certificate: the
quadratic S(t, z) = V(t, z) - t (z_1 - z_2)^2 satisfies, along every solution,
  u y - dS/dt = (z_1 - 2 z_2)^2 / 2 >= 0   (identically in z, u, t),
S(0, .) = V(0, .), and S(1/2, z) = (z_1 + 2 z_2)^2 / 4 >= 0 (its matrix
[[1/2, 1], [1, 2]] is positive semidefinite). Hence int_0^T u y dt >= S(T) - S(0) >= -V(z(0)).
Everything below is exact sympy algebra over the rationals.
"""
import sympy as sp

from mdept.refute import Witness


def _claim(T, p, r):
    t, z1, z2, u = sp.symbols("t z1 z2 u", real=True)
    p = [sp.sympify(e) for e in p]
    r = [sp.sympify(e) for e in r]
    z = [z1, z2]
    # hypotheses on [0, T]: p_j >= 0, r_j > 0 (both are affine, so endpoints suffice)
    for e in p + r:
        assert sp.Poly(e, t).degree() <= 1
    assert all(e.subs(t, s) >= 0 for e in p for s in (0, T))
    assert all(e.subs(t, s) > 0 for e in r for s in (0, T))
    # rate condition rdot_j <= 2 p_j r_j for all j, t (affine/quadratic: check it fails somewhere)
    rate_holds = all(
        sp.solve_univariate_inequality(sp.diff(rj, t) - 2 * pj * rj > 0, t, relational=False)
        .intersect(sp.Interval(0, T)).is_empty
        for pj, rj in zip(p, r)
    )
    # identity of clause (a): u y = dV/dt + sum (p r - rdot/2) z^2 along solutions
    zdot = [-pj * zj + u for pj, zj in zip(p, z)]
    y = sum(rj * zj for rj, zj in zip(r, z))
    V = sum(rj * zj**2 for rj, zj in zip(r, z)) / 2
    dV = sp.diff(V, t) + sum(sp.diff(V, zj) * dzj for zj, dzj in zip(z, zdot))
    D = sum((pj * rj - sp.diff(rj, t) / 2) * zj**2 for pj, rj, zj in zip(p, r, z))
    assert sp.expand(u * y - dV - D) == 0
    # passivity certificate
    S = V - t * (z1 - z2) ** 2
    dS = sp.diff(S, t) + sum(sp.diff(S, zj) * dzj for zj, dzj in zip(z, zdot))
    assert sp.expand(u * y - dS - (z1 - 2 * z2) ** 2 / 2) == 0
    assert sp.expand(S.subs(t, 0) - V.subs(t, 0)) == 0
    ST = sp.hessian(S.subs(t, T), z) / 1
    assert all(m >= 0 for m in [ST[0, 0], ST[1, 1], ST.det()])
    passive = True
    return passive == rate_holds


def refute() -> Witness:
    t = sp.Symbol("t", real=True)
    return Witness(
        entry="MD_0071",
        point={"T": sp.Rational(1, 2), "p": (sp.Integer(0), sp.Integer(0)), "r": (1 + t, 4 - 2 * t)},
        claim=_claim,
        note="(a) only-if: p=0, r=(1+t, 4-2t), T=1/2; rate fails at j=1 for all t, yet "
             "u y - dS/dt = (z1-2z2)^2/2 with S = V - t (z1-z2)^2, S(0)=V(0), S(T) psd, so passive.",
    )
