"""MD_0049: every eigenvalue of -(alpha K + diag(u) D + diag(h)) has negative real part.

Witness: N = 4, L = 2 pi, alpha = 1/100, u = (-3, 3, -3, 3), h = (1, 0, 0, 1).

Hypotheses. (D) N = 4 is even, L = 2 pi > 0. The symbol is s = (0, i, 0, -i) (s_0 = 0, s_1 = i,
s_2 = 0 at Nyquist, s_3 = -i since nbar = -1), and D_jl = (1/4) sum_n s_n i^((j-l) n) equals
(i/4)(i^m - (-i)^m) with m = j - l, i.e. D_{j,j+1} = 1/2, D_{j,j-1} = -1/2 (cyclic), all other
entries 0: the rational matrix with rows [0,1/2,0,-1/2], [-1/2,0,1/2,0], [0,-1/2,0,1/2],
[1/2,0,-1/2,0]. K = -D^2. N >= 4, u real, alpha > 0, h >= 0 with h_0 = h_3 = 1 > 0 and
indices 0, 3 of odd difference.

Conclusion fails. The characteristic polynomial of A = -(alpha K + diag(u) D + diag(h)) is
(200 l^2 - 398 l - 299)(200 l^2 + 802 l + 301)/40000, whose first factor has the positive real
root 199/200 + sqrt(99401)/200 (about 1.57). The predicate (all eigenvalues have negative real
part) is decided exactly: Routh-Hurwitz on the exact characteristic polynomial.
"""
from fractions import Fraction

import sympy as sp
from mdept.refute import Witness


def _D_from_definition(N, L):
    """The ledger definition, evaluated exactly in sympy (omega = exp(2 pi i / N))."""
    w = sp.exp(2 * sp.pi * sp.I / N)
    s = []
    for n in range(N):
        nbar = n if n < N // 2 else n - N
        s.append(0 if n == N // 2 else 2 * sp.pi * sp.I * nbar / L)
    D = sp.Matrix(N, N, lambda j, l: sum(s[n] * w ** ((j - l) * n) for n in range(N)) / N)
    return D.applyfunc(lambda e: sp.nsimplify(sp.simplify(sp.expand_complex(e))))


def _hurwitz_stable(poly, lam):
    """Exact: True iff every root of the real polynomial has negative real part (Routh-Hurwitz)."""
    p = sp.Poly(poly, lam)
    a = p.all_coeffs()
    if a[0] < 0:
        a = [-c for c in a]
    n = len(a) - 1
    if any(c <= 0 for c in a):
        return False
    coef = lambda k: a[k] if 0 <= k <= n else 0  # noqa: E731
    H = sp.Matrix(n, n, lambda i, j: coef(2 * (j + 1) - (i + 1)) if 0 <= 2 * (j + 1) - (i + 1) <= n else 0)
    return all(H[:k, :k].det() > 0 for k in range(1, n + 1))


def _claim(N, L_over_2pi, alpha, u, h):
    assert N == 4 and L_over_2pi == 1
    D = _D_from_definition(N, 2 * sp.pi * sp.Integer(L_over_2pi))
    assert D == sp.Matrix([[0, sp.Rational(1, 2), 0, -sp.Rational(1, 2)],
                           [-sp.Rational(1, 2), 0, sp.Rational(1, 2), 0],
                           [0, -sp.Rational(1, 2), 0, sp.Rational(1, 2)],
                           [sp.Rational(1, 2), 0, -sp.Rational(1, 2), 0]])
    assert D.T == -D
    K = -D * D
    assert K == D.T * D
    a = sp.Rational(alpha.numerator, alpha.denominator)
    A = -(a * K + sp.diag(*[sp.Integer(x) for x in u]) * D + sp.diag(*[sp.Integer(x) for x in h]))
    lam = sp.symbols("lam")
    cp = sp.expand(A.charpoly(lam).as_expr())
    target = sp.expand((200 * lam**2 - 398 * lam - 299) * (200 * lam**2 + 802 * lam + 301) / 40000)
    assert cp == target
    r = sp.Rational(199, 200) + sp.sqrt(99401) / 200
    assert sp.simplify(cp.subs(lam, r)) == 0 and r > 0
    # hypotheses: h >= 0, two indices of odd difference with h > 0, alpha > 0
    assert a > 0 and all(x >= 0 for x in h) and h[0] > 0 and h[3] > 0 and (3 - 0) % 2 == 1
    return bool(_hurwitz_stable(cp, lam))


def refute() -> Witness:
    return Witness(
        entry="MD_0049",
        point={"N": 4, "L_over_2pi": 1, "alpha": Fraction(1, 100), "u": (-3, 3, -3, 3), "h": (1, 0, 0, 1)},
        claim=_claim,
        note=(
            "N=4, L=2pi, alpha=1/100, u=(-3,3,-3,3), h=(1,0,0,1): charpoly of -(alpha K + diag(u)D + "
            "diag(h)) = (200l^2-398l-299)(200l^2+802l+301)/40000 has the positive root "
            "199/200+sqrt(99401)/200."
        ),
    )
