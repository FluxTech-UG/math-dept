"""MD_0015: the high-frequency deficit is NOT carried by the single length Lambda''.

ONE OF TWO WITNESSES. This artifact refutes the single-length clause. Its sibling
`counterexamples/MD_0015_shape_varying_duct.py` refutes the betweenness clause on a full
three-dimensional Laplace solve. `python -m mdept.refute MD_0015` runs and reports both.
Betweenness is well posed on the frozen text with no normalization attached, while this
clause carries the slack described below, which the graded quantity removes.

MD_0015's Statement asserts that in the thin-layer regime

    g_vk = 1 - (1 - i) sqrt(2 alpha / omega) (1 + sqrt(Pr) + Pr)/((1 + sqrt(Pr)) Lambda'')
           + O(1/omega),                                                            (*)

with Lambda'' the wall length weighted by |v|, so that ONE weighted length carries the
whole O(omega^-1/2) deficit. It does not. The deficit splits between two lengths, the
viscous one Lambda (weight |v|^2, inherited from the Johnson, Koplik and Dashen
expansion) with Prandtl weight sqrt(Pr), and the cross one Lambda'' with Prandtl weight
1/(1 + sqrt(Pr)):

    g_vk = (1/alpha_inf)[1 - (1 - i) delta_kappa (sqrt(Pr)/Lambda
                                                  + 1/((1 + sqrt(Pr)) Lambda''))]    (**)

which is MD_0018. On every straight uniform pore Lambda = Lambda'' and (*) and (**)
agree, which is why no single-geometry test can separate them. This witness is a pore on
which they differ.

THE WITNESS. A slowly varying axisymmetric duct of radius R(x) = 1 + eps cos(2 pi x / L)
over one period, in the limit L/R -> infinity where the quasi-one-dimensional reduction is
the leading-order exact solution. The ordering of limits is delta_kappa << R << L. Every
quantity below is a period average in x and is therefore independent of L, which is what
lets that limit be taken freely.

At eps = 0.6 the three weighted lengths are

    alpha_inf = 2.30469,   Lambda = 0.54237,   Lambda'' = 0.80000,   Lambda' = 1.18000,

so Lambda''/Lambda = 1.475 and the two candidate coefficients differ by tens of percent.
H1 holds: the wall is smooth and, in the slowly varying limit, its radii of curvature are
O(L) and O(R), both enormous against delta_kappa. H2 holds: |v| = c/(pi R^2) is bounded
above and below away from zero because R is, and v . e_hat = |v| > 0 everywhere, so there
are no stagnation points on the wall and, the field being parallel to e_hat at leading
order, MD_0015's unsigned weight |v| and MD_0018's signed weight v . e_hat coincide here.
The witness therefore bears on MD_0015's clause as frozen, with its own definition of
Lambda''.

THE REFERENCE CARRIES NO BOUNDARY-LAYER ASYMPTOTICS. g_vk is assembled from the EXACT
circular-tube channel functions evaluated station by station, closed by the
incompressibility constraint Q = V_loc A(x) (1 - f_v,loc) = const:

    W := 1/(A (1 - f_v,loc)),
    g_vk = L * mean(g_loc/(1 - f_v,loc)) / (mean(W) mean(A)).

So the quantity being graded is not produced by the expansion it is grading. That flux
constraint is the displacement effect in concrete form, and it is exactly what makes the
viscous deficit carry Lambda rather than Lambda''; dropping it returns Lambda''.

WHAT IS GRADED, AND WHY IT IS NORMALIZATION-FREE. MD_0015's Statement fixes no
normalization for v and no definition of g_vk on a three-dimensional pore, and a different
normalization moves the 1/alpha_inf prefactor. So the witness does not grade g_vk against a
printed constant. It grades the RELATIVE deficit coefficient

    K := (g(inf) - g(omega)) / ((1 - i) delta_kappa g(inf)),

in which any overall constant in g cancels top and bottom. (*) asserts K = C(Pr)/Lambda'';
(**) asserts K = sqrt(Pr)/Lambda + 1/((1 + sqrt(Pr)) Lambda''). The measured K settles the
question with no convention attached.

THE GUARD. If the two-length form (**) did not itself match at this point, the reference
would be suspect and a False verdict would be meaningless. The claim therefore RAISES
rather than returning False unless (**) agrees to 1e-2 relative at the same point. A
refutation here can only mean the single-length form is wrong.

NUMERIC WITNESS. The point carries a quadrature over a cosine profile and complex Bessel
ratios, so `numeric=True` and the ledger records this as "refuted (numeric)". The
discrepancy being graded is 31.7 percent at Pr = 1 against a 5 percent threshold, and the
two-length form lands at 7.1e-5 on the same evaluation, four thousand times closer, so
nothing about the verdict is at the mercy of floating point. Across the Prandtl range the
single-length form misses by 10.2 percent at Pr = 0.05, 26.0 at 0.5, 31.7 at 1, 39.2 at 3
and 45.6 at 20, while the two-length form stays between 4.6e-5 and 2.6e-4 throughout.
An exact upgrade would mean carrying I_0 and I_1 at complex
argument symbolically across a quadrature, which is not available.
"""

from __future__ import annotations

import numpy as np
from scipy.special import ive

from mdept.refute import Witness

#: The two-length form must agree this well at the witness point, or the reference is not
#: trustworthy and the claim raises instead of returning a verdict.
GUARD_RTOL = 1e-2


def _f_tube(s: complex, D: float, R: float) -> complex:
    """<h_D> on the disc of radius R, through the scaled Bessel ratio so large |z| is finite."""
    z = R * np.sqrt(s / D)
    return 2.0 * (ive(1, z) / ive(0, z)) / z


def _g_tube(s: complex, nu: float, al: float, R: float) -> complex:
    """Exact g_vk on the disc (MD_0011), with the MD_0016 derivative form at Pr = 1."""
    if abs(nu - al) < 1e-12 * al:
        z = R * np.sqrt(s / al)
        F = _f_tube(s, al, R)
        return 2.0 * (1 - F) - 0.25 * z**2 * F**2
    Pr = nu / al
    return ((1 - _f_tube(s, al, R)) - Pr * (1 - _f_tube(s, nu, R))) / (1 - Pr)


def _lengths(R: np.ndarray) -> tuple[float, float, float, float]:
    """(alpha_inf, Lambda, Lambda'', Lambda') for the quasi-1D duct, from |v| ~ 1/R^2."""
    m = np.mean
    return (
        float(m(R**2) * m(R**-2)),          # alpha_inf = <R^2><R^-2>
        float(m(R**-2) / m(R**-3)),         # Lambda   = <R^-2>/<R^-3>,  weight |v|^2
        float(1.0 / m(R**-1)),              # Lambda'' = 1/<R^-1>,       weight |v|
        float(m(R**2) / m(R)),              # Lambda'  = <R^2>/<R>,      weight 1
    )


def _g_quasi1d(s: complex, nu: float, al: float, R: np.ndarray) -> complex:
    """Exact quasi-1D g_vk over one period. The period length divides out."""
    A = np.pi * R**2
    fv = np.array([_f_tube(s, nu, r) for r in R])
    gl = np.array([_g_tube(s, nu, al, r) for r in R])
    W = 1.0 / (A * (1 - fv))
    return complex(np.mean(gl / (1 - fv)) / (np.mean(W) * np.mean(A)))


def single_length_holds(eps: float, n_x: int, Pr: float, omega_over_wc: float, rtol: float) -> bool:
    """True when MD_0015's single-length coefficient matches the measured deficit.

    Raises when the two-length form does not match at the same point, because then the
    reference, not the claim, would be what a False verdict was reporting.
    """
    t = (np.arange(n_x) + 0.5) / n_x
    R = 1.0 + eps * np.cos(2 * np.pi * t)
    a_inf, Lam, Lam2, _Lam1 = _lengths(R)

    al = 1.0
    nu = Pr * al
    om = omega_over_wc * 2.0 * nu
    dk = np.sqrt(2.0 * al / om)
    g_inf = 1.0 / a_inf
    g = _g_quasi1d(1j * om, nu, al, R)

    # The relative deficit coefficient. Any overall constant in g cancels here.
    K_meas = (g_inf - g) / ((1 - 1j) * dk * g_inf)

    x = np.sqrt(Pr)
    K_printed = (1.0 + x + Pr) / ((1.0 + x) * Lam2)      # MD_0015 as frozen
    K_two = x / Lam + 1.0 / ((1.0 + x) * Lam2)           # MD_0018

    err_two = abs(K_meas / K_two - 1.0)
    if not err_two < GUARD_RTOL:
        raise AssertionError(
            f"MD_0015 witness guard: the two-length form misses by {err_two:.3e} at this "
            f"point, so the quasi-1D reference is not trustworthy and no verdict is issued"
        )
    return bool(abs(K_meas / K_printed - 1.0) < rtol)


def refute() -> Witness:
    return Witness(
        entry="MD_0015",
        point={"eps": 0.6, "n_x": 4096, "Pr": 1.0, "omega_over_wc": 1e8, "rtol": 0.05},
        claim=single_length_holds,
        note=(
            "A slowly varying axisymmetric duct R(x) = 1 + 0.6 cos(2 pi x / L), one period, "
            "in the limit L/R -> infinity. It satisfies H1 (smooth wall, radii of curvature "
            "O(R) and O(L), both enormous against delta_kappa) and H2 (|v| = c/(pi R^2) is "
            "bounded above and below away from zero, and v . e_hat = |v| > 0, so there are no "
            "stagnation points and the signed and unsigned weights agree). Its weighted "
            "lengths are alpha_inf = 2.30469, Lambda = 0.54237, Lambda'' = 0.80000, "
            "Lambda' = 1.18000. It violates the conclusion: the measured relative deficit "
            "coefficient misses MD_0015's single-length C(Pr)/Lambda'' by 31.7 percent at "
            "Pr = 1, 10.2 percent at Pr = 0.05 rising to 45.6 percent at Pr = 20, while "
            "MD_0018's two-length coefficient matches it to 7.1e-5 on the same "
            "evaluation. Betweenness is NOT what fails here: Lambda <= Lambda'' <= Lambda' "
            "holds on this duct, and on the whole slowly varying axisymmetric class by "
            "Chebyshev's sum inequality. What fails is the single-length clause."
        ),
        numeric=True,
    )


if __name__ == "__main__":
    import sys

    w = refute()
    ok = w.verify()
    print(f"MD_0015 single-length witness: verify() = {ok}  (numeric={w.numeric})")
    sys.exit(0 if ok else 1)
