"""Tests of the comparison round: acceptance, per-location weights, native form, Willow noise."""
import numpy as np
import pytest
import stim

from cliffordea import enum

from nnflags import comparison as CMP
from nnflags import equivalence as Q
from nnflags import willow_noise as W
from nnflags.verify import load_measurement, verify


@pytest.fixture(scope="module")
def ds():
    return CMP.designs()


def test_odds_from_circuit_reproduces_cliffordea_uniform_odds(ds):
    full, inner = CMP.load(ds["success03"])
    _, _, comb, _ = CMP.combinator_and_analyzer(full, inner, noise_level=0.002)
    assert np.allclose(CMP.odds_from_circuit(comb), CMP.uniform_odds(comb, 0.002), rtol=1e-10)


def test_rate_matches_cliffordea_and_acceptance_matches_monte_carlo(ds):
    full, inner = CMP.load(ds["d3a6"])
    en, _ = CMP.enumerated(full, inner, p_list=(0.001,), mfc=2)  # asserts the rate inside
    acc = en[0.001]["detectors"]["acceptance"]
    m = load_measurement(full, inner)
    mc = CMP.mc_acceptance(enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=0.001),
                           400_000, seed=1)
    assert abs(mc["acceptance"] - acc) < 5 * mc["se"]
    assert en[0.001]["T"]["acceptance"] < acc  # final stabiliser postselection discards more


def test_d3a4_final_readout_is_noiseless_in_stim_but_enumerated(ds):
    """The documented d3a4 discrepancy: no trailing reset, so the last TICK (MX) is
    noiseless in uniformly_depolarize, while FaultCombinator weights its flips at p."""
    full, inner = CMP.load(ds["d3a4"])
    _, noisy, comb, _ = CMP.combinator_and_analyzer(full, inner)
    last = str(noisy).strip().split("\n")
    assert any(line.startswith("MX 8 2 7 3") for line in last)
    groups = comb.circuit.group_error_events_by_location()
    assert sum(1 for k in groups if k[1] == "MX") == 4
    assert np.sum(CMP.odds_from_circuit(comb) == 0) >= 1  # those flips have strength 0 in the circuit


@pytest.mark.parametrize("name", ["success03", "d3a6"])
def test_cx_to_native_keeps_counts_and_round_trips(ds, name):
    full, inner = CMP.load(ds[name])
    nat = W.cx_to_native(inner)
    assert Q.is_deterministic(nat)
    assert {op.name for op in nat} <= {"QUBIT_COORDS", "MPP", "R", "H", "CZ", "M", "MR", "DETECTOR", "TICK"}
    assert Q.absorb_hadamards(nat, W.CMP_data(nat))[1]["non_cx"] == 0
    a, b = verify(full, inner, max_fault_count=2), verify(full, nat, max_fault_count=2)
    assert [a["T"][k]["malignant"] for k in range(3)] == [b["T"][k]["malignant"] for k in range(3)]
    assert [a["S"][k]["malignant"] for k in range(3)] == [b["S"][k]["malignant"] for k in range(3)]


def test_calibration_loads_and_cz_error_is_xeb_minus_single_qubit():
    cal = W.load_calibration()
    assert len(cal["t1_us"]) == 105 and len(cal["xeb"]) == 182
    (a, b), x = next(iter(cal["xeb"].items()))
    assert cal["e2"][(a, b)] == pytest.approx(max(x - cal["e1"][a] - cal["e1"][b], 0))
    assert all(0 < t2 <= 2 * cal["t1_us"][q] + 1e-9 for q, t2 in cal["t2_us"].items())


def test_noisy_native_readout_modes(ds):
    cal = W.load_calibration()
    full, inner = CMP.load(ds["success03"])
    nat = W.cx_to_native(inner)
    emb, _ = W.placement("success03", inner)
    prm = W.model_params("calibration", cal, emb)
    m = load_measurement(full, nat)
    sym, _ = W.noisy_native(m.INNER_CIRCUIT, prm, "symmetric")
    asym, rmap = W.noisy_native(m.INNER_CIRCUIT, prm, "asymmetric")
    assert sym.without_noise() == asym.without_noise()
    assert len(rmap) == sum(op.num_measurements for op in nat if op.name in ("M", "MR"))
    assert "PAULI_CHANNEL" not in str(sym)  # only channels cliffordea enumerates
    _, _, comb, _ = CMP.combinator_and_analyzer(full, nat, noisy=sym)
    assert np.all(CMP.odds_from_circuit(comb) >= 0)
