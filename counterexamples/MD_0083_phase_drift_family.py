"""MD_0083 clause 1: mu'(s0)=0 and a family that is not locally a reparametrisation of a
single orbit force the eigenvalue 1 of the monodromy to have algebraic multiplicity >= 2.

Witness (exact, closed-form flow). f(x, y, mu) = (x(mu - r^2) - y, y(mu - r^2) + x),
r^2 = x^2 + y^2, i.e. r' = r(mu - r^2), theta' = 1; f is polynomial, so C^2.
Family: mu_s = 1 + s^2, T_s = 2 pi, gamma_s(t) = sqrt(1 + s^2)(cos(t + s), sin(t + s)).
Each gamma_s is a nonconstant T_s-periodic solution at mu_s; the family is C^infinity;
at s0 = 0: mu' = 0, T' = 0, gamma_s'(0) = (0, 1) != 0, so (gamma', T', mu') != 0. The
orbits are the circles of radius sqrt(1 + s^2), pairwise distinct for |s| distinct, so the
family is not locally a reparametrisation of a single orbit. The monodromy of gamma_0 at
(1, 0) is diag(e^{-4 pi}, 1): the eigenvalue 1 is simple. The phase of gamma_s(0) along its
orbit moves with s, which supplies the nonzero tangent; the tangent (0, 1) = f(gamma_0(0))
is the reparametrisation direction, so (M - I) gamma' = -T' f carries no information.
"""
import sympy as sp

from mdept.refute import Witness


def _flow():
    t, x, y, mu = sp.symbols("t x y mu", real=True)
    rho = x**2 + y**2
    E = sp.exp(2 * mu * t)
    R = mu * rho * E / (mu + rho * (E - 1))  # r(t)^2 for r' = r(mu - r^2)
    scale = sp.sqrt(R / rho)
    phi = sp.Matrix([scale * (x * sp.cos(t) - y * sp.sin(t)), scale * (x * sp.sin(t) + y * sp.cos(t))])
    return t, x, y, mu, R, rho, phi


def _claim(s0):
    t, x, y, mu, R, rho, phi = _flow()
    # The closed form solves the ODE: R' = 2R(mu - R), R(0) = rho; the angle advances at rate 1.
    assert sp.simplify(sp.diff(R, t) - 2 * R * (mu - R)) == 0
    assert sp.simplify(R.subs(t, 0) - rho) == 0
    s = sp.symbols("s", real=True)
    mu_s = 1 + s**2
    g0 = sp.Matrix([sp.sqrt(mu_s) * sp.cos(s), sp.sqrt(mu_s) * sp.sin(s)])
    # gamma_s(t) = phi(t, gamma_s(0), mu_s) is the stated circle, so it is 2 pi-periodic.
    gam = phi.subs({x: g0[0], y: g0[1], mu: mu_s})
    target = sp.Matrix([sp.sqrt(mu_s) * sp.cos(t + s), sp.sqrt(mu_s) * sp.sin(t + s)])
    assert sp.simplify(gam - target) == sp.zeros(2, 1)
    # Hypotheses at s0: mu' = 0, tangent nonzero, orbit nonconstant, family not one orbit.
    assert sp.diff(mu_s, s).subs(s, s0) == 0
    tangent = sp.diff(g0, s).subs(s, s0)
    assert tangent == sp.Matrix([0, 1])
    assert sp.diff(mu_s, s, 2).subs(s, s0) == 2  # radius sqrt(1+s^2) != 1 for s != 0
    # Monodromy at gamma_0(0) = (1, 0), mu = 1, T = 2 pi.
    M = phi.jacobian([x, y]).subs({t: 2 * sp.pi, mu: 1}).subs({x: 1, y: 0})
    M = sp.simplify(M)
    assert M == sp.Matrix([[sp.exp(-4 * sp.pi), 0], [0, 1]])
    lam = sp.symbols("lam")
    p = (M - lam * sp.eye(2)).det()
    mult = 0
    while sp.simplify(p.subs(lam, 1)) == 0:
        mult += 1
        p = sp.cancel(p / (lam - 1))
    assert mult == 1 and sp.simplify(p.subs(lam, 1)) == 1 - sp.exp(-4 * sp.pi) and (1 - sp.exp(-4 * sp.pi)).is_positive
    return mult >= 2


def refute() -> Witness:
    return Witness(
        entry="MD_0083",
        point={"s0": 0},
        claim=_claim,
        note="r'=r(mu-r^2), theta'=1; family mu_s=1+s^2, T=2pi, gamma_s(0)=sqrt(1+s^2)(cos s, sin s): "
             "mu'(0)=0, gamma'(0)=(0,1)=f, distinct orbits; monodromy diag(e^{-4pi},1), eigenvalue 1 simple. "
             "Clause 1 needs a phase condition (gamma_s(0) on a fixed transversal section).",
    )
