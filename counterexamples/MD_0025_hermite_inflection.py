"""MD_0025: theta -> yhat(T; theta) is C^1 on all of Theta (cubic Hermite extension).

Setup: d = m = 1, Theta = (1/2, 2), explicit Euler (p = 1), Delta s = 1, T = 1/9.
y0(theta) = theta, f(y, theta) = y / theta, and
g(y, theta) = theta (1 + 4 w), w = (y - theta)^2 / ((y - theta)^2 + theta^2 / 3),
so g lies in [1/2, 10) for every (y, theta). The extension is the cubic Hermite
interpolant of the nodes (y_n, t_n) with end slopes Delta s F(y_n), Delta s F(y_{n+1}).
Euler step 0: y_1 = 2 theta, t_1 = theta, g_0 = theta, g_1 = 4 theta, so on the first
interval the t-component is theta * p(sigma) with p(0)=0, p(1)=1, p'(0)=1, p'(1)=4, i.e.
p(sigma) = ((3 sigma - 1)^3 + 1) / 9, p' = (3 sigma - 1)^2 >= 0 with a double zero at 1/3.
t_0 = 0 < T = 1/9 <= t_1 = theta for every theta in Theta, so N = 1, and p strictly
increasing makes the crossing unique: (3 sigma* - 1)^3 = 1/theta - 1. At theta = 1 the
crossing sits at the stationary inflection sigma = 1/3 (d t / d sigma = 0 there), so
sigma*(theta) is a real cube root, not differentiable, and yhat inherits the cube-root
singularity because the y-component has nonzero sigma-slope at 1/3. The difference
quotient of yhat at theta = 1 diverges.
"""
import sympy as sp
from fractions import Fraction
from mdept.refute import Witness

_th, _sg, _r = sp.symbols("theta sigma r", positive=True)
_h = sp.Integer(1)
_T = sp.Rational(1, 9)


def _g(y, th):
    d2 = (y - th) ** 2
    return th * (1 + 4 * d2 / (d2 + th ** 2 / 3))


def _f(y, th):
    return y / th


def _F(y, t, th):
    g = _g(y, th)
    return g * _f(y, th), g


def _hermite(z0, z1, F0, F1):
    """Cubic Hermite in sigma on one component, from values and Delta s F slopes."""
    a, b = z0, z1
    s0, s1 = _h * F0, _h * F1
    return (a * (1 - 3 * _sg**2 + 2 * _sg**3) + b * (3 * _sg**2 - 2 * _sg**3)
            + s0 * (_sg - 2 * _sg**2 + _sg**3) + s1 * (-_sg**2 + _sg**3))


def _first_interval():
    y0, t0 = _th, sp.Integer(0)
    Fy0, Ft0 = _F(y0, t0, _th)
    y1, t1 = y0 + _h * Fy0, t0 + _h * Ft0  # explicit Euler
    Fy1, Ft1 = _F(y1, t1, _th)
    uy = _hermite(y0, y1, Fy0, Fy1)
    ut = _hermite(t0, t1, Ft0, Ft1)
    return (y0, t0, y1, t1), (Fy0, Ft0, Fy1, Ft1), uy, ut


def _checks():
    (y0, t0, y1, t1), (Fy0, Ft0, Fy1, Ft1), uy, ut = _first_interval()
    s = sp.simplify
    assert s(y1 - 2 * _th) == 0 and s(t1 - _th) == 0
    # C^1 gluing and endpoint interpolation of the actual extension
    for u, a, b, Fa, Fb in ((uy, y0, y1, Fy0, Fy1), (ut, t0, t1, Ft0, Ft1)):
        assert s(u.subs(_sg, 0) - a) == 0 and s(u.subs(_sg, 1) - b) == 0
        assert s(sp.diff(u, _sg).subs(_sg, 0) - _h * Fa) == 0
        assert s(sp.diff(u, _sg).subs(_sg, 1) - _h * Fb) == 0
    # t-component is theta * ((3 sigma - 1)^3 + 1) / 9
    assert s(ut - _th * ((3 * _sg - 1) ** 3 + 1) / 9) == 0
    # t_0 < T <= t_1 on Theta = (1/2, 2): N = 1
    assert _T <= sp.Rational(1, 2) and sp.Rational(1, 2) > _T
    # uniform bounds on g: theta in (1/2, 2), 1 <= 1 + 4w < 5
    return uy, ut


def _yhat_is_differentiable_at(theta):
    uy, ut = _checks()
    assert theta == 1
    # crossing: theta * p(sigma) = T  <=>  (3 sigma - 1)^3 = 1/theta - 1; put 1/theta - 1 = r^3
    th_r = 1 / (1 + _r**3)
    sg_r = (1 + _r) / 3
    assert sp.simplify(ut.subs({_th: th_r, _sg: sg_r}) - _T) == 0  # a root of u_t = T
    Y = sp.simplify(uy.subs({_th: th_r, _sg: sg_r}))  # yhat as a function of r
    # r = 0 is theta = 1 and sigma = 1/3; the t-slope there is zero
    assert sp.diff(ut, _sg).subs({_th: 1, _sg: sp.Rational(1, 3)}) == 0
    assert sp.diff(uy, _sg).subs({_th: 1, _sg: sp.Rational(1, 3)}) != 0
    Q = sp.simplify((Y - Y.subs(_r, 0)) / (th_r - th_r.subs(_r, 0)))
    lim = sp.limit(Q, _r, 0, "+")
    assert sp.limit(Q, _r, 0, "-") == lim
    return bool(lim.is_finite)  # divergent difference quotient: not differentiable


def refute() -> Witness:
    return Witness(
        entry="MD_0025",
        point={"theta": Fraction(1)},
        claim=_yhat_is_differentiable_at,
        note=(
            "Euler (p=1), cubic Hermite extension (C^1-glued, order 3), Delta s = 1, T = 1/9, "
            "Theta=(1/2,2), g in [1/2,10), f=y/theta in C^inf. On the interval [s_0,s_1] the "
            "t-component is theta*((3 sigma-1)^3+1)/9: monotone (unique crossing) but with "
            "dt/dsigma = 0 at sigma = 1/3, where s* sits at theta = 1. Hence sigma* is a cube "
            "root in (theta-1) and yhat has an infinite difference quotient at theta = 1."
        ),
    )
