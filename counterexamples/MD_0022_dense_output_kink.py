"""MD_0022: theta -> yhat(T; theta) is C^1 on all of Theta (claim (a)).

Setup: d = m = 1, Theta = R, f(y, theta) = y + theta, y0 = 1, g = (1 + y^2)/(1 + 2 y^2)
(in [1/2, 1], C^infinity). Heun's method (p = 2) at Delta s = 1/4 with the continuous
extension b1(sigma) = sigma - sigma^2/2, b2(sigma) = sigma^2/2, which is polynomial with
uniform order 2 (sum b_i = sigma, sum b_i c_i = sigma^2/2). T is t_2(theta = 0), so at
theta = 0 the node t_2 equals T and N switches between 2 and 3. The extension is not
Hermite, so its sigma-derivative at sigma = 1 (h*F(stage 2)) differs from the next step's
at sigma = 0 (h*F(y_n)), and d yhat/d theta jumps across theta = 0.
"""
import sympy as sp
from fractions import Fraction
from mdept.refute import Witness

_th, _sg = sp.symbols("theta sigma")
_h = sp.Rational(1, 4)


def _F(z):
    g = (1 + z[0] ** 2) / (1 + 2 * z[0] ** 2)
    return [g * (z[0] + _th), g]


def _step(z):
    k1 = _F(z)
    k2 = _F([zi + _h * ki for zi, ki in zip(z, k1)])
    b1, b2 = _sg - _sg ** 2 / 2, _sg ** 2 / 2
    u = [zi + _h * (b1 * a + b2 * b) for zi, a, b in zip(z, k1, k2)]
    zn = [zi + _h * (a + b) / 2 for zi, a, b in zip(z, k1, k2)]
    return u, zn


def _one_sided_derivatives(theta0):
    z0 = [sp.Integer(1), sp.Integer(0)]
    _, z1 = _step(z0)
    u1, z2 = _step(z1)
    u2, _ = _step(z2)
    T = z2[1].subs(_th, theta0)  # node t_2 equals T at theta0
    dts = sp.diff(z2[1], _th).subs(_th, theta0)  # sign decides which branch lies on which side
    out = {}
    for name, u, s0 in (("N2", u1, 1), ("N3", u2, 0)):
        # yhat = u_y(sigma*(theta); theta) with u_t(sigma*; theta) = T; implicit differentiation
        dsig = -sp.diff(u[1], _th) / sp.diff(u[1], _sg)
        dy = sp.diff(u[0], _th) + sp.diff(u[0], _sg) * dsig
        at = {_th: theta0, _sg: s0}
        assert sp.simplify(u[1].subs(at) - T) == 0  # s* sits exactly at the node
        out[name] = sp.nsimplify(sp.simplify(dy.subs(at)))
    # t_2 decreasing in theta (dts < 0): theta > theta0 gives t_2 < T, N = 3 (right side)
    assert dts < 0
    return out["N2"], out["N3"]  # (left derivative, right derivative)


def _derivative_is_continuous(theta):
    left, right = _one_sided_derivatives(sp.Rational(theta.numerator, theta.denominator))
    return bool(sp.simplify(left - right) == 0)


def refute() -> Witness:
    return Witness(
        entry="MD_0022",
        point={"theta": Fraction(0)},
        claim=_derivative_is_continuous,
        note=(
            "Heun p=2, dense output b=(s-s^2/2, s^2/2) of uniform order 2, f=y+theta, "
            "g=(1+y^2)/(1+2y^2), Delta s=1/4, T=t_2(0). One-sided d yhat/d theta at theta=0: "
            "left 0.3720674576..., right 0.3721939521... (exact rationals differ, jump about "
            "-1.26e-4). Violates (a): yhat is not C^1 at theta=0. Finite differences agree."
        ),
    )
