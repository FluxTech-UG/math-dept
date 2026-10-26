"""MD_0097 part (a): a one-internal-node synchronous Boolean network passes the associative
conditioning protocol at every even training window W >= 2 and every gap G >= 1.

The network: one internal node x, two source inputs u1 (unconditioned) and u2 (neutral),
readout r = x, update  x' = (x XOR u1) OR (x AND u2),  rest state x* = 0 (a fixed point of
the input-free update, as is x = 1: the node is bistable under u = (0,0)).

Why it passes at even W: under u1 alone the node toggles 0,1,0,1,..., so an even window ends
at x = 0 and leaves no trace; under the paired input the node sets to 1 and the u2 term holds
it, so the memory survives the gap and u2 alone then reads it out. The pretest under u2 alone
from x* = 0 stays 0; the pretest under u1 alone evokes at its first step. The protocol's
"evokes at some step of the window" plus an even-length window is what the witness exploits.
Odd W defeats it (the enumeration in triage/MD_0097.md finds no one-node passer at W odd).

The claim evaluated is part (a) of the Statement at the point (W, G) = (2, 1): "no (F, r) with
k <= 1 passes at (W, G)". The exhaustive search over all 256 one-node update tables returns a
passer, so the claim is False there.
"""
import itertools
from mdept.refute import Witness


def _run(F, x, inputs):
    out = []
    for u in inputs:
        x = F(x, u)
        out.append(x)
    return out


def _passes(F, W, G):
    """the pass predicate of MD_0097 for k = 1 (readout is the single node)"""
    for x in (0, 1):
        if F(x, (0, 0)) != x:
            continue  # rest state must be a fixed point of the input-free update
        pre_n = _run(F, x, [(0, 1)] * W)
        pre_u = _run(F, x, [(1, 0)] * W)
        if any(pre_n) or not any(pre_u):
            continue

        def test(v):
            st = _run(F, x, [v] * W + [(0, 0)] * G + [(0, 1)] * W)
            return any(st[W + G:])

        if test((1, 1)) and not test((1, 0)) and not test((0, 1)):
            return True
    return False


def _no_one_node_network_passes(W, G):
    assert W >= 1 and G >= 1
    for bits in itertools.product((0, 1), repeat=8):
        F = lambda x, u, b=bits: b[x * 4 + u[0] * 2 + u[1]]
        if _passes(F, W, G):
            return False
    return True


def refute() -> Witness:
    # the explicit passer, checked directly as well as found by the sweep
    F = lambda x, u: (x ^ u[0]) | (x & u[1])
    assert _passes(F, 2, 1)
    assert not any(_passes(F, W, G) for W in (1, 3, 5) for G in (1, 2, 3))
    return Witness(
        entry="MD_0097",
        point={"W": 2, "G": 1},
        claim=_no_one_node_network_passes,
        note=(
            "One internal node, x' = (x XOR u1) OR (x AND u2), readout x, rest x* = 0, passes the "
            "protocol at (W, G) = (2, 1) and at every even W tested; part (a) of MD_0097 ('no network "
            "with k <= 1 passes at any W >= 1, G >= 1') is false. The node is bistable under (0,0), "
            "consistent with MD_0096; the loophole is the parity of an even window under u1 alone. "
            "Part (b), the two-node witness, holds at every (W, G) in 1..5 (triage/MD_0097.md)."
        ),
    )
