"""MD_0002 claims that every integer strictly exceeds its own square."""

from mdept.refute import Witness


def refute() -> Witness:
    return Witness(
        entry="MD_0002",
        point={"n": 2},
        claim=lambda n: n * n > n,
        note="At n = 1 the claim reads 1 > 1, which is false.",
    )
