"""MD_0052: ||Mu - theta u|| <= eps < 1 - |theta| puts an eigenvalue of M within eps of theta.

Witness: the Jordan block M = [[0,1],[0,0]], theta = 1/10, u = (1, 1/10)/sqrt(101/100).
Then Mu = (1/10, 0)/s and theta u = (1/10, 1/100)/s with s = sqrt(101/100), so
Mu - theta u = (0, -1/100)/s and eps := ||Mu - theta u|| = (1/100)/s, with
eps^2 = (1/10^4)/(101/100) = 1/10100. Hypotheses: ||u|| = 1; eps < 1 - |theta| = 9/10
(eps^2 = 1/10100 < 81/100). The only eigenvalue of M is 0, at distance 1/10 from theta, and
(1/10)^2 = 1/100 > 1/10100 = eps^2, so no eigenvalue lies within eps. Exact: all comparisons
are between squares of rationals (u itself has the unit-normalised entries squared rational).
"""
from fractions import Fraction

from mdept.refute import Witness


def _claim(theta, u_unnorm):
    M = [[Fraction(0), Fraction(1)], [Fraction(0), Fraction(0)]]
    v = [Fraction(x) for x in u_unnorm]
    n2 = sum(x * x for x in v)  # ||v||^2 = 101/100; u = v / sqrt(n2)
    # residual r = M v - theta v, scaled: ||M u - theta u||^2 = ||r||^2 / n2.
    r = [sum(M[i][j] * v[j] for j in range(2)) - theta * v[i] for i in range(2)]
    eps2 = sum(x * x for x in r) / n2
    assert eps2 == Fraction(1, 10100)
    # hypothesis eps < 1 - |theta|  <=>  eps^2 < (1 - |theta|)^2 (both sides nonnegative).
    assert 0 <= 1 - abs(theta) and eps2 < (1 - abs(theta)) ** 2
    # eigenvalues of M: char poly lam^2, only root 0 (M is nilpotent: M^2 = 0, M != 0).
    assert all(sum(M[i][k] * M[k][j] for k in range(2)) == 0 for i in range(2) for j in range(2))
    eigenvalues = [Fraction(0)]
    # conclusion: exists eigenvalue with |lam - theta| <= eps, i.e. (lam - theta)^2 <= eps^2.
    return any((lam - theta) ** 2 <= eps2 for lam in eigenvalues)


def refute() -> Witness:
    return Witness(
        entry="MD_0052",
        point={"theta": Fraction(1, 10), "u_unnorm": (Fraction(1), Fraction(1, 10))},
        claim=_claim,
        note="M=[[0,1],[0,0]], theta=1/10, u ~ (1,1/10), eps=(1/100)/sqrt(101/100), eps^2=1/10100 < 81/100; "
             "only eigenvalue 0 at distance 1/10 > eps.",
    )
