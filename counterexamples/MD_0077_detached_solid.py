"""MD_0077: 1 - f(s) = <theta>_{Omega_g} = w0 + sum_n w_n s/(s+lambda_n), w0 = C_g|g|/(C_g|g|+C_s|s|).

Witness (d = 1, a solid piece detached from the gas): Omega_g = (0,1),
Omega_s = (-1,0) u (1,2) u (3,4), C_g = C_s = k_g = k_s = 1, s = 1/100.
Hypotheses: Omega_g, Omega_s disjoint bounded Lipschitz open sets; Gamma = {0, 1} has positive
(0-dimensional Hausdorff) measure; d Omega_g = {0,1} is contained in Gamma; the outer boundary
{-1, 2, 3, 4} is insulated. Omega = (-1,2) u (3,4) is disconnected, which the Statement allows.

Solution: on (3,4) the problem decouples with zero forcing, so theta = 0 there (uniqueness for
s not in (-inf,0]). On J = (-1,2), with q = sqrt(s), the solution is
theta = a cosh(q(x+1)) on (-1,0), 1 - 2a cosh(q/2) cosh(q(x-1/2)) on (0,1), a cosh(q(2-x)) on
(1,2), a = 1/(1+2cosh q) (continuity and flux continuity at x = 0 and by symmetry at 1), so
<theta>_g = 1 - 2 sinh(q) / (q (1 + 2 cosh q)), which tends to 1/3 as s -> 0.

Stipulated: w0 = 1/(1+3) = 1/4, w_n >= 0, sum_{n>=1} w_n = 3/4, lambda_n the positive
eigenvalues: Neumann spectra of J, (n pi/3)^2, and of (3,4), (n pi)^2, so lambda_n >= pi^2/9 > 1.
Since s/(s+lambda) decreases in lambda, the Statement forces
<theta>_g <= 1/4 + (3/4) s/(s+1) = 26/101 ~ 0.2574 at s = 1/100. The exact value is
0.33444... (evaluated below in mpmath interval arithmetic, so the comparison is rigorous).
The defect: with Omega disconnected the zero eigenspace is spanned by the indicator of each
component, and the true DC offset is C_g|g| / (C_g|g| + C_s|solid component touching g|) = 1/3.
"""
from fractions import Fraction

import mpmath

from mdept.refute import Witness


def _claim(s, Cg, Cs, kg, ks, gas, solids):
    # hypotheses this point satisfies
    assert min(Cg, Cs, kg, ks) > 0 and s > 0
    assert Cg == Cs == kg == ks == 1  # the closed form below uses unit coefficients
    assert gas == (0, 1) and solids == ((-1, 0), (1, 2), (3, 4))
    vol_g = Fraction(gas[1] - gas[0])
    vol_s = sum(Fraction(b - a) for a, b in solids)
    w0 = Cg * vol_g / (Cg * vol_g + Cs * vol_s)
    assert w0 == Fraction(1, 4)
    # lambda_1 = min(pi^2/9, pi^2) > 1 because pi > 3; the bound uses lambda_1 >= 1.
    bound = w0 + (1 - w0) * s / (s + 1)
    assert bound == Fraction(26, 101)
    iv = mpmath.iv
    iv.dps = 50
    q = iv.sqrt(iv.mpf(s.numerator) / s.denominator)
    eq, emq = iv.exp(q), iv.exp(-q)
    sinh_q, cosh_q = (eq - emq) / 2, (eq + emq) / 2
    mean = 1 - 2 * sinh_q / (q * (1 + 2 * cosh_q))
    b = iv.mpf(bound.numerator) / bound.denominator
    # The Statement asserts mean <= bound; certify it fails: lower end of mean > upper end of bound.
    assert mean.a > b.b, (mean, b)
    return False if mean.a > b.b else True


def refute() -> Witness:
    return Witness(
        entry="MD_0077",
        point={"s": Fraction(1, 100), "Cg": 1, "Cs": 1, "kg": 1, "ks": 1,
               "gas": (0, 1), "solids": ((-1, 0), (1, 2), (3, 4))},
        claim=_claim,
        note="d=1, gas (0,1), solid (-1,0)u(1,2)u(3,4), unit C and k; Omega disconnected. "
             "Statement forces <theta>_g(1/100) <= 26/101; exact value 0.3344 (interval-certified). "
             "True DC offset 1/3, stipulated w0 = 1/4. Fixable slip: add 'Omega connected'.",
    )
