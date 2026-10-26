"""MD_0012: g_vk at Pr = 1 is NOT 1 - F(a) + a F'(a). The sign of the derivative term is minus.

MD_0012's Statement ends with two clauses that cannot both hold. It asserts

    (i)   lim_{Pr -> 1} (f_k - f_v) / ((1 - f_v)(1 - Pr))  =  a F'(a) / (1 - F(a)),
    (ii)  g_vk | _{Pr = 1}                                 =  1 - F(a) + a F'(a),

where F(D) = <h_D> is the averaged channel function, F'(D) = dF/dD, and a is the thermal
diffusivity. The bracket of (i) is 1 - g_vk/(1 - f_v) identically, so (i) and (ii) together
force a F'(a) = 0, which holds at no frequency: writing 1 - F(D) = sum_n w_n s/(s + D mu_n)
with s = i omega gives a F'(a) = sum_n w_n s a mu_n / (s + a mu_n)^2, every term of which
has argument pi/2 - 2 arctan(omega / (a mu_n)) in (-pi/2, pi/2), hence strictly positive
real part.

Clause (i) is correct. Clause (ii) is not: the true value is

          g_vk | _{Pr = 1}  =  1 - F(a) - a F'(a),                                    (*)

proved three independent ways in proofs/MD_0012.md section 5 (l'Hopital on MD_0011's
formula, resolvent calculus, and a term-by-term identity on the modal sum).

THE WITNESS. One frequency on one geometry is enough, and the refutation is not close:
the printed and the correct values differ by 2 a F'(a), which is 165 percent of the true
value on the plates and 399 percent on the disc.

  primary        parallel plates of half-gap y_0 = 1, a = 1, omega = 3
  corroborating  the disc of radius R = 1, a = 1, omega = 3

Both are carried because MD_0012's hypotheses are ambiguous about the domain class in a way
this entry inherits from MD_0011: H1 imports "the single-geometry setting of C1", whose
Omega is a bounded Lipschitz domain in R^2, while MD_0012's own Statement names parallel
plates explicitly, and the slab is unbounded in R^2 (it is bounded in R^1). The disc is a
bounded Lipschitz domain in R^2 under any reading, so the refutation does not depend on how
that ambiguity is resolved. `refute()` returns the disc.

THE REFERENCE IS INDEPENDENT OF THE DISPUTED SIGN. The claim is graded against

          g_vk(s) = s^2 sum_{n=1}^{N} w_n / ((s + nu mu_n)(s + a mu_n))                (**)

at nu = a, MD_0011 (17), summed over N = 4000 Dirichlet modes. (**) carries no 1 - Pr and no
derivative, so it cannot inherit either sign convention. Its truncation error at the witness
is below 1e-12 relative, checked by doubling N, which is nine orders below the 165 percent
discrepancy being certified.

NUMERIC WITNESS. The point carries complex floats (Bessel and hyperbolic function values at
a complex argument), so `numeric=True`, and the ledger records this as "refuted (numeric)".
Upgrading it to exact values would mean carrying tanh and I_0, I_1 at z = sqrt(3i)
symbolically; the discrepancy is a factor of 1.65, so nothing about the verdict is at the
mercy of floating point, but the qualifier is the honest one and is left in place.
"""

from __future__ import annotations

import numpy as np
from scipy.special import ive, jn_zeros

from mdept.refute import Witness

N_MODES = 4000
#: The claim is an equality between complex numbers. It is graded at a tolerance nine orders
#: of magnitude looser than the discrepancy, so that a False verdict means the clause is
#: wrong and never that the arithmetic is.
CLAIM_RTOL = 1e-6


# ------------------------------------------------------------------ the two geometries
def _slab(s: complex, D: float, y0: float = 1.0) -> complex:
    z = y0 * np.sqrt(s / D)
    return np.tanh(z) / z


def _disc(s: complex, D: float, R: float = 1.0) -> complex:
    z = R * np.sqrt(s / D)
    return 2.0 * (ive(1, z) / ive(0, z)) / z


def _ladder_slab(y0: float = 1.0, n: int = N_MODES):
    k = np.arange(1, n + 1)
    return 8.0 / ((2 * k - 1) ** 2 * np.pi**2), ((2 * k - 1) * np.pi / (2 * y0)) ** 2


def _ladder_disc(R: float = 1.0, n: int = N_MODES):
    j = jn_zeros(0, n)
    return 4.0 / j**2, (j / R) ** 2


GEOMETRY = {
    "slab": (_slab, _ladder_slab),
    "disc": (_disc, _ladder_disc),
}


# --------------------------------------------------------------------- the three values
def _reference(omega: float, alpha: float, geometry: str) -> complex:
    """g_vk at Pr = 1 from MD_0011 (17), which contains neither 1 - Pr nor a derivative."""
    _, ladder = GEOMETRY[geometry]
    w, mu = ladder()
    s = 1j * omega
    return s**2 * np.sum(w / (s + alpha * mu) ** 2)


def _a_F_prime(omega: float, alpha: float, geometry: str) -> complex:
    """a F'(a), by the modal series, so it too is free of the disputed algebra.

    1 - F(D) = sum_n w_n s/(s + D mu_n)  =>  F'(D) = sum_n w_n s mu_n/(s + D mu_n)^2.
    """
    _, ladder = GEOMETRY[geometry]
    w, mu = ladder()
    s = 1j * omega
    return alpha * np.sum(w * s * mu / (s + alpha * mu) ** 2)


def _F(omega: float, alpha: float, geometry: str) -> complex:
    closed, _ = GEOMETRY[geometry]
    return closed(1j * omega, alpha)


def _claim(omega, alpha, geometry, g_reference, a_F_prime, F_alpha) -> bool:
    """MD_0012's printed clause (ii), evaluated at the point.

    The point carries the three ingredients so that the witness records the numbers it was
    judged on; the claim recomputes nothing except the printed combination.
    """
    del omega, alpha, geometry
    printed = 1.0 - F_alpha + a_F_prime
    return bool(abs(printed - g_reference) <= CLAIM_RTOL * abs(g_reference))


def _check_hypotheses(omega: float, alpha: float, geometry: str, label: str) -> None:
    """Every hypothesis of MD_0012, by name. Raises on the first violation."""
    if geometry not in GEOMETRY:
        raise AssertionError(f"{label}: unknown geometry {geometry!r}")
    # H1: the single-geometry setting. One domain carries both channel problems and the only
    # difference between them is the diffusivity. At Pr = 1 there is literally one problem,
    # so H1 holds in the strongest possible way rather than merely being satisfiable.
    if not alpha > 0:
        raise AssertionError(f"{label}: H1 needs a positive diffusivity, got alpha = {alpha}")
    # H2: omega > 0, which is what gives F(alpha) != 1 and keeps the denominator away from 0.
    if not omega > 0:
        raise AssertionError(f"{label}: H2 omega > 0 fails (omega = {omega})")
    F_alpha = _F(omega, alpha, geometry)
    if abs(1.0 - F_alpha) < 1e-9:
        raise AssertionError(f"{label}: H2's consequence F(alpha) != 1 fails, 1 - F = {1 - F_alpha}")


def _point(omega: float, alpha: float, geometry: str) -> dict:
    return {
        "omega": omega,
        "alpha": alpha,
        "geometry": geometry,
        "g_reference": _reference(omega, alpha, geometry),
        "a_F_prime": _a_F_prime(omega, alpha, geometry),
        "F_alpha": _F(omega, alpha, geometry),
    }


def _corrected_formula_holds(omega: float, alpha: float, geometry: str) -> None:
    """Non-vacuity: (*) DOES match the reference, so the failure is the sign and nothing else.

    Without this the witness would be consistent with a broken reference. It also pins that
    the closed-form channel function and the modal ladder agree, which is what lets the
    printed clause be graded against the ladder at all.
    """
    p = _point(omega, alpha, geometry)
    corrected = 1.0 - p["F_alpha"] - p["a_F_prime"]
    err = abs(corrected - p["g_reference"]) / abs(p["g_reference"])
    if err > 1e-9:
        raise AssertionError(
            f"non-vacuity ({geometry}): the corrected formula 1 - F - a F' misses the modal "
            f"reference by {err:.3e} relative; the reference, not the clause, is suspect"
        )


def _reference_is_converged(omega: float, alpha: float, geometry: str) -> None:
    """Truncation control: halving the mode count must not move the reference."""
    _, ladder = GEOMETRY[geometry]
    s = 1j * omega
    w, mu = ladder(n=N_MODES)
    w2, mu2 = ladder(n=N_MODES // 2)
    full = s**2 * np.sum(w / (s + alpha * mu) ** 2)
    half = s**2 * np.sum(w2 / (s + alpha * mu2) ** 2)
    err = abs(full - half) / abs(full)
    if err > 1e-12:
        raise AssertionError(
            f"reference not converged ({geometry}): {N_MODES} against {N_MODES // 2} modes "
            f"differ by {err:.3e} relative"
        )


def _report() -> str:
    lines = []
    for geometry in ("slab", "disc"):
        p = _point(3.0, 1.0, geometry)
        printed = 1.0 - p["F_alpha"] + p["a_F_prime"]
        corrected = 1.0 - p["F_alpha"] - p["a_F_prime"]
        lines.append(
            f"{geometry}: a F'(a) = {p['a_F_prime']:.10f}\n"
            f"    printed   1 - F + a F' = {printed:.10f}\n"
            f"    corrected 1 - F - a F' = {corrected:.10f}\n"
            f"    modal sum, {N_MODES} modes = {p['g_reference']:.10f}\n"
            f"    printed misses by {abs(printed - p['g_reference']) / abs(p['g_reference']):.6f} relative"
        )
    return "\n".join(lines)


def refute() -> Witness:
    for geometry in ("slab", "disc"):
        _check_hypotheses(3.0, 1.0, geometry, label=geometry)
        _reference_is_converged(3.0, 1.0, geometry)
        _corrected_formula_holds(3.0, 1.0, geometry)
    point = _point(3.0, 1.0, "disc")
    return Witness(
        entry="MD_0012",
        point=point,
        claim=_claim,
        numeric=True,
        note=(
            "Disc of radius 1, alpha = 1, omega = 3, so Pr = 1 and the single-geometry setting "
            "holds trivially (one domain, one diffusivity, one channel problem). Satisfied: H1, "
            "one bounded Lipschitz Omega in R^2 carrying both channel problems; H2, omega = 3 > 0, "
            "and 1 - F(alpha) = 0.148022 + 0.298794i is bounded away from 0. Violated: the printed "
            "clause g_vk|_{Pr=1} = 1 - F(alpha) + alpha F'(alpha), whose value "
            "0.381849 + 0.477441i differs from the true 1 - F(alpha) - alpha F'(alpha) = "
            "-0.085804 + 0.120147i by 2 alpha F'(alpha) = 0.467652 + 0.357294i, that is by 399 "
            "percent of the true value (165 percent on the plates). The "
            "true value is certified against MD_0011 (17), g_vk = s^2 sum_n w_n/(s + alpha mu_n)^2 "
            "over 4000 Dirichlet modes, which carries neither 1 - Pr nor a derivative and so cannot "
            "inherit the disputed sign; the corrected formula matches it to 1e-9 relative and the "
            "reference is converged to 1e-12 under halving the mode count. The same failure holds "
            "on parallel plates of half-gap 1, which is the geometry MD_0012's own Statement names; "
            "the disc is returned because it is a bounded Lipschitz domain in R^2 under any reading "
            "of the hypotheses, while the slab is bounded only in R^1. The printed clause also "
            "contradicts the Statement's own preceding clause, which is correct: the two together "
            "force alpha F'(alpha) = 0, and Re(alpha F'(alpha)) > 0 strictly for every omega > 0."
        ),
    )


if __name__ == "__main__":
    w = refute()
    print(_report())
    print()
    print("verify():", w.verify())
