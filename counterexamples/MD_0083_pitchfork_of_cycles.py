"""MD_0083 clause 2: at a fold (mu'(s0)=0, mu''(s0) != 0) with the eigenvalue 1 of
algebraic multiplicity exactly 2, the multiplier m(s) near 1 crosses 1 with m'(s0) != 0.

Witness (exact, closed-form flow): a pitchfork of cycles. f(x, y, z, mu) =
(x(1 - r^2) - y, y(1 - r^2) + x, z(mu - z^2)), r^2 = x^2 + y^2; polynomial, so C^2.
Family: mu_s = s^2, T_s = 2 pi, gamma_s(t) = (cos t, sin t, s): a nonconstant 2 pi-periodic
solution (z' = s(s^2 - s^2) = 0), C^infinity in s, tangent gamma_s'(0) = (0, 0, 1) != 0
(transversal to f, and gamma_s(0) stays on the section {y = 0}, so no phase drift), orbits
distinct for distinct s. mu'(0) = 0, mu''(0) = 2 != 0. Monodromy at (1, 0, s):
diag(e^{-4 pi}, 1, m(s)) with m(s) = e^{-4 pi s^2} (m(0) = 1), so at s0 = 0 the eigenvalue 1
has algebraic multiplicity exactly 2, and for s != 0 near 0 m(s) is the unique real
multiplier != 1 near 1. But m'(0) = 0 and m(s) < 1 on both sides: no crossing. The fold
conditions stated omit transversality (d_mu of the return map not in the range of DP - I),
which a pitchfork violates.
"""
import sympy as sp

from mdept.refute import Witness


def _claim(s0):
    t, z0, mu, s = sp.symbols("t z0 mu s", real=True)
    E = sp.exp(2 * mu * t)
    Z = mu * z0**2 * E / (mu + z0**2 * (E - 1))  # z(t)^2 for z' = z(mu - z^2), mu != 0
    assert sp.simplify(sp.diff(Z, t) - 2 * Z * (mu - Z)) == 0 and sp.simplify(Z.subs(t, 0) - z0**2) == 0
    zt = z0 * sp.sqrt(E * mu / (mu + z0**2 * (E - 1)))  # sign of z preserved
    # Along the family (s != 0): z0 = s, mu = s^2 is an equilibrium of the z-equation.
    assert sp.simplify(zt.subs({mu: s**2, z0: s}) - s) == 0
    m_expr = sp.diff(zt, z0).subs({t: 2 * sp.pi}).subs({mu: s**2, z0: s})
    m = sp.exp(-4 * sp.pi * s**2)
    for sv in (sp.Rational(1, 7), sp.Rational(-1, 3), sp.Rational(1, 2)):
        assert sp.simplify(m_expr.subs(s, sv) - m.subs(s, sv)) == 0
    # Identity for every s > 0; s < 0 follows from the symmetry z -> -z of the z-equation.
    sp_ = sp.symbols("sp_", positive=True)
    assert sp.simplify(m_expr.subs(s, sp_) - m.subs(s, sp_)) == 0
    # z multiplier at s = 0 (mu = 0): z' = -z^3 linearised at z = 0 is delta' = 0, multiplier 1 = m(0).
    assert m.subs(s, 0) == 1
    # Planar block at (1, 0): r' = r(1 - r^2), theta' = 1: radial multiplier exp(2 pi (1 - 3)) = e^{-4 pi},
    # tangential multiplier 1 (theta' independent of r); the blocks decouple.
    planar = [sp.exp(-4 * sp.pi), sp.Integer(1)]
    lam = sp.symbols("lam")
    p0 = sp.expand((lam - planar[0]) * (lam - planar[1]) * (lam - m.subs(s, s0)))
    mult = 0
    while sp.simplify(p0.subs(lam, 1)) == 0:
        mult += 1
        p0 = sp.cancel(p0 / (lam - 1))
    assert mult == 2  # the clause-2 hypothesis "exactly 2" holds
    mu_s = s**2
    assert sp.diff(mu_s, s).subs(s, s0) == 0 and sp.diff(mu_s, s, 2).subs(s, s0) == 2
    mprime = sp.diff(m, s).subs(s, s0)
    assert mprime == 0
    # No crossing: m(s) < 1 for s = +-1/10.
    assert all(sp.exp(-4 * sp.pi * sv**2) < 1 for sv in (sp.Rational(1, 10), sp.Rational(-1, 10)))
    return mprime != 0


def refute() -> Witness:
    return Witness(
        entry="MD_0083",
        point={"s0": 0},
        claim=_claim,
        note="Planar cycle r'=r(1-r^2) times z'=z(mu-z^2); family gamma_s(0)=(1,0,s), mu_s=s^2, T=2pi: "
             "mu''=2, eigenvalue 1 of multiplicity exactly 2 at s=0, m(s)=e^{-4 pi s^2}, m'(0)=0, no crossing. "
             "Clause 2 needs transversality of the fold (w.P_mu != 0).",
    )
