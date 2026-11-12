"""Option-1 round (user decisions 2 and 3): live_rule="gate" (default) and the
checked final-layer exemption (final_layer="auto", default).

Qubits 0, 1, 2 sit on readout line 10; qubit 3 is on line 11. Qubit 0 is the
data qubit (MPP target), live from the start.
"""
from pathlib import Path

import pytest
import stim

from cliffordea import enum
from nnflags import constraints as C

EMB = {0: (6, 4), 1: (5, 5), 2: (4, 6), 3: (6, 5)}
DATA = Path(__file__).parents[1] / "data" / "google_circuits"


def pairs(text, **kw):
    v = C.readout_violations(stim.Circuit(text), EMB, **kw)
    return [(x.detail["tick"], x.detail["measured"], x.detail["victim"]) for x in v]


def live_pairs(text, **kw):
    """Liveness tests: final layer exempt unconditionally (these toy circuits
    have no gate between their last two measurement TICKs)."""
    return pairs(text, **{"final_layer": "exempt", **kw})


def test_defaults():
    assert C.DEFAULT_LIVE_RULE == "gate" and C.DEFAULT_FINAL_LAYER == "auto"


def test_reset_idle_in_zero_is_not_live_until_h_or_two_qubit_gate():
    # 2 is reset at TICK 1 and idles in |0> through TICK 2 (M 1): not a victim.
    # At TICK 3 it gets an H, so the MR 1 at TICK 4 hits it.
    c = "MPP X0\nTICK\nR 1 2\nTICK\nMR 1\nTICK\nH 2\nTICK\nMR 1\nTICK\nM 1 2"
    assert live_pairs(c) == [(2, 1, 0), (4, 1, 0), (4, 1, 2)]
    assert live_pairs(c, live_rule="prep") == [(2, 1, 0), (2, 1, 2), (4, 1, 0), (4, 1, 2)]


def test_two_qubit_gate_makes_live():
    c = "MPP X0\nTICK\nR 1 2\nTICK\nCZ 2 3\nTICK\nMR 1\nTICK\nM 1 2 3"
    assert live_pairs(c) == [(3, 1, 0), (3, 1, 2)]


@pytest.mark.parametrize("gate", ["I", "X", "Y", "Z", "S", "S_DAG"])
def test_z_basis_preserving_gates_keep_dormant(gate):
    c = f"MPP X0\nTICK\nR 1 2\nTICK\n{gate} 2\nTICK\nMR 1\nTICK\nM 1 2"
    assert live_pairs(c) == [(3, 1, 0)]


@pytest.mark.parametrize("gate", ["H", "H_YZ", "SQRT_X", "SQRT_Y", "C_XYZ"])
def test_basis_changing_gates_make_live(gate):
    c = f"MPP X0\nTICK\nR 1 2\nTICK\n{gate} 2\nTICK\nMR 1\nTICK\nM 1 2"
    assert live_pairs(c) == [(3, 1, 0), (3, 1, 2)]


def test_rx_is_r_then_h_live_from_that_tick():
    # RX 2 in TICK 1: busy (not a victim) in TICK 1, live from TICK 2 on.
    c = "MPP X0\nTICK\nRX 2\nMR 1\nTICK\nMR 1\nTICK\nM 1 2"
    assert live_pairs(c) == [(1, 1, 0), (2, 1, 0), (2, 1, 2)]


def test_mr_makes_dormant_mrx_keeps_live():
    c = "MPP X0\nTICK\nRX 2\nTICK\nH 1\nTICK\nMR 2\nTICK\nMR 1\nTICK\nM 1 2"
    # TICK 3: MR 2 hits 0 and live 1. TICK 4: MR 1 hits 0; 2 is in |0> again.
    assert live_pairs(c) == [(3, 2, 0), (3, 2, 1), (4, 1, 0)]
    c2 = c.replace("MR 2", "MRX 2")
    assert live_pairs(c2) == [(3, 2, 0), (3, 2, 1), (4, 1, 0), (4, 1, 2)]


def test_no_reset_qubit_dormant_until_first_gate():
    # Qubit 2 starts in |0> (no reset, like G4's qubit 7); I keeps it dormant.
    c = "MPP X0\nTICK\nI 2\nR 1\nTICK\nMR 1\nTICK\nH 2\nTICK\nMR 1\nTICK\nM 1 2"
    assert live_pairs(c) == [(2, 1, 0), (4, 1, 0), (4, 1, 2)]


def test_final_layer_status_ok():
    c = stim.Circuit("MPP X0\nTICK\nRX 1\nTICK\nCX 1 0\nTICK\nMX 1\nTICK\nR 1")
    s = C.final_layer_status(c)
    assert s["exempt"] and s["final_tick"] == 3 and s["reasons"] == []
    assert pairs(str(c)) == []


def test_final_layer_not_exempt_if_gate_in_or_after_it():
    # H on 2 in the same TICK as the final M 1: basis change not before it.
    c = "MPP X0\nTICK\nR 1 2\nTICK\nH 1 2\nTICK\nM 1\nH 2\nTICK\nM 2"
    s = C.final_layer_status(stim.Circuit(c))
    assert s["final_tick"] == 4 and s["exempt"]  # the last TICK (M 2) is fine
    c2 = "MPP X0\nTICK\nR 1\nTICK\nH 1\nTICK\nM 1\nH 0"
    s2 = C.final_layer_status(stim.Circuit(c2))
    assert not s2["exempt"] and not s2["no_gate_at_or_after"]
    assert pairs(c2) == [(3, 1, 0)]
    assert pairs(c2, final_layer="exempt") == []


def test_final_layer_not_exempt_if_split():
    c = "MPP X0\nTICK\nR 1 2\nTICK\nH 1 2\nTICK\nM 1\nTICK\nM 2"
    s = C.final_layer_status(stim.Circuit(c))
    assert not s["exempt"] and not s["simultaneous"]
    # M 1 (TICK 3) is mid-circuit anyway; the final M 2 (TICK 4) is now checked too.
    assert pairs(c) == [(3, 1, 0), (3, 1, 2), (4, 2, 0)]
    assert pairs(c, final_layer="exempt") == [(3, 1, 0), (3, 1, 2)]


def test_d3a6_d3a4_unchanged_under_new_rule():
    c = enum.circuits.DoubleCheck(distance=3, ancilla_count=6).INNER_CIRCUIT
    assert C.final_layer_status(c)["exempt"]
    v = C.readout_violations(c, C.native_coords(c))
    assert [(x.detail["tick"], x.detail["measured"], x.detail["victim"]) for x in v] == [(6, 5, 8)]
    live, _ = C.liveness(c)
    assert live[6] == set(range(13)) - {5}  # RX-prepared ancillas are live


def test_google_g4_g5_real_coordinates():
    for key, expected in (("G4", 0), ("G5", 0)):
        g = stim.Circuit.from_file(str(DATA / f"rosenfeld2512_{key}.stim"))
        emb = {q: tuple(int(x) for x in p) for q, p in C.native_coords(g).items()}
        assert C.final_layer_status(g)["exempt"]
        assert len(C.readout_violations(g, emb, ())) == expected
    g5 = stim.Circuit.from_file(str(DATA / "rosenfeld2512_G5.stim"))
    emb = {q: tuple(int(x) for x in p) for q, p in C.native_coords(g5).items()}
    assert len(C.readout_violations(g5, emb, (), live_rule="prep", final_layer="exempt")) == 12
