"""The stage S1 toolkit on toy claims.

Each helper answers exactly one question and returns an exact object or None.
None means the method found nothing, never that the claim is true, and these
tests pin that distinction.
"""

import sympy as sp

from mdept.search import random_search
from mdept.symbolic import inequality_counterexample, is_identity, rational_witness

x = sp.Symbol("x")


def test_is_identity_recognises_a_true_identity():
    assert is_identity(sp.sin(x) ** 2 + sp.cos(x) ** 2, 1) is True


def test_is_identity_rejects_a_false_one():
    assert is_identity(sp.sqrt(x ** 2), x) is False


def test_assumptions_can_make_an_identity_hold():
    assert is_identity(sp.sqrt(x ** 2), x, x=dict(nonnegative=True)) is True


def test_inequality_counterexample_finds_an_exact_point():
    point = inequality_counterexample(x ** 2 >= x, x, (0, 2))
    assert point is not None
    assert point.is_rational
    assert (point ** 2 >= point) == sp.false


def test_inequality_counterexample_returns_none_when_the_claim_holds():
    assert inequality_counterexample(x ** 2 >= 0, x, (-5, 5)) is None


def test_rational_witness_finds_a_rational_not_a_float():
    point = rational_witness(x ** 2 >= x, x, 0, 1, steps=4)
    assert point == sp.Rational(1, 4)
    assert isinstance(point, sp.Rational)


def test_rational_witness_returns_none_on_a_true_claim():
    assert rational_witness(x ** 2 >= 0, x, -1, 1, steps=8) is None


def test_random_search_returns_the_failing_point():
    found = random_search(
        lambda a: a < 10,
        lambda rng: {"a": int(rng.integers(0, 100))},
        n=500,
        seed=3,
    )
    assert found is not None and found["a"] >= 10


def test_random_search_returns_none_when_nothing_fails():
    assert random_search(
        lambda a: a >= 0,
        lambda rng: {"a": int(rng.integers(0, 10))},
        n=100,
        seed=0,
    ) is None


def test_random_search_is_reproducible():
    sampler = lambda rng: {"a": int(rng.integers(0, 1000))}
    first = random_search(lambda a: a < 900, sampler, n=500, seed=7)
    second = random_search(lambda a: a < 900, sampler, n=500, seed=7)
    assert first == second
