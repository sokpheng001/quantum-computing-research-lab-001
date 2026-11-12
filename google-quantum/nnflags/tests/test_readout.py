"""Strict readout-line rule with per-qubit live intervals (RESULTS_step3.md, task A).

Qubits 0, 1, 2 sit on readout line 10 (r + c = 10); qubit 3 is on line 11.
Data qubit = the MPP target (qubit 0), live from the start of the circuit.

Since the Option-1 round (2026-11-01) the defaults are live_rule="gate" and
final_layer="auto" (tests/test_live_rule.py). The tests in this file pin the
Step-3 variant explicitly (live_rule="prep", final_layer="exempt"), so their
expected pairs are unchanged.
"""
import stim
import pytest

from nnflags import constraints as C

EMB = {0: (6, 4), 1: (5, 5), 2: (4, 6), 3: (6, 5)}


OLD = dict(live_rule="prep", final_layer="exempt")  # Step-3 rule


def pairs(text, **kw):
    """(tick, measured, victim) of every strict readout violation (Step-3 rule
    unless overridden)."""
    v = C.readout_violations(stim.Circuit(text), EMB, **{**OLD, **kw})
    return [(x.detail["tick"], x.detail["measured"], x.detail["victim"]) for x in v]


def test_victim_live_vs_not_yet_prepared():
    # TICK 3: M 1. Data 0 is live; ancilla 2 is not prepared until TICK 4.
    c = "MPP X0\nTICK\nR 1\nTICK\nH 1\nTICK\nM 1\nTICK\nR 2 1\nTICK\nCX 2 1\nTICK\nM 1 2"
    assert pairs(c) == [(3, 1, 0)]


def test_first_gate_prepares():
    # Qubit 2 has no reset; its first gate (TICK 1) makes it live.
    c = "MPP X0\nTICK\nH 2\nTICK\nR 1\nTICK\nMR 1\nTICK\nM 2"
    assert pairs(c) == [(3, 1, 0), (3, 1, 2)]


def test_mr_keeps_live_and_ancilla_vs_ancilla():
    # TICK 2: MR 2 hits data 0 and ancilla 1. TICK 3: M 1 hits 0 and 2,
    # because MR measured and reset 2, so 2 is still live.
    c = "MPP X0\nTICK\nR 1 2\nTICK\nMR 2\nTICK\nM 1\nTICK\nM 2"
    assert pairs(c) == [(2, 2, 0), (2, 2, 1), (3, 1, 0), (3, 1, 2)]


def test_m_without_reset_ends_liveness_until_next_reset():
    # TICK 2: M 2 (no reset) -> 2 is dead in TICK 3, live again after R at TICK 4.
    c = ("MPP X0\nTICK\nR 1 2\nTICK\nM 2\nTICK\nMR 1\nTICK\nR 2\nTICK\nMR 1\nTICK\n"
         "M 1 2")
    assert pairs(c) == [(2, 2, 0), (2, 2, 1), (3, 1, 0), (5, 1, 0), (5, 1, 2)]


def test_measured_qubit_not_its_own_victim_and_simultaneous_readout():
    # Data 0 measured with MRX (stays live afterwards, it holds the code state);
    # 1 and 2 measured together in TICK 2 are not each other's victims.
    c = "MPP X0\nTICK\nR 1 2\nTICK\nM 1 2\nTICK\nMRX 0\nTICK\nR 1\nTICK\nM 1"
    got = pairs(c)
    assert all(m != v for _, m, v in got)
    assert got == [(2, 1, 0), (2, 2, 0)]  # TICK 3: MRX 0, nobody else live on line 10


def test_reset_in_same_tick_is_not_a_victim():
    c = "MPP X0\nTICK\nR 1\nTICK\nMR 1\nR 2\nTICK\nM 1 2"
    assert pairs(c) == [(2, 1, 0)]


def test_other_line_never_a_victim():
    c = "MPP X0*X3\nTICK\nR 1\nTICK\nMR 1\nTICK\nM 1"
    assert pairs(c) == [(2, 1, 0)]  # data 3 is on line 11


def test_final_layer_exempt_by_default_and_checkable():
    c = "MPP X0\nTICK\nR 1\nTICK\nH 1\nTICK\nM 1"
    assert pairs(c) == []
    assert pairs(c, final_layer="check") == [(3, 1, 0)]


def test_data_measured_without_reset_is_dead_until_prepared():
    c = "MPP X0\nTICK\nR 1 2\nTICK\nMX 0\nTICK\nMR 1\nTICK\nM 1 2"
    assert pairs(c) == [(2, 0, 1), (2, 0, 2), (3, 1, 2)]


def test_check_circuit_modes():
    c = stim.Circuit("MPP X0\nTICK\nR 1\nTICK\nMR 1\nTICK\nM 1")
    strict = C.check_circuit(c, EMB, **OLD)
    assert [x.kind for x in strict] == ["readout"]
    assert C.check_circuit(c, EMB, readout="ignore") == []
    assert C.check_circuit(c, EMB, ignore_readout=True) == []
    with pytest.raises(ValueError):
        C.check_circuit(c, EMB, readout="loose")


def test_d3a6_strict_native():
    from cliffordea import enum
    c = enum.circuits.DoubleCheck(distance=3, ancilla_count=6).INNER_CIRCUIT
    v = C.readout_violations(c, C.native_coords(c), **OLD)
    assert [(x.detail["tick"], x.detail["measured"], x.detail["victim"]) for x in v] == [(6, 5, 8)]
    live, measured = C.liveness(c, live_rule="prep")
    assert measured[6] == {5} and live[6] == set(range(13)) - {5}
    assert live[1] == set(c and C.find_data_indices(c))  # ancillas being reset in TICK 1
