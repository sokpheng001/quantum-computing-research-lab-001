"""Tests of the QVM experiment (qvm-google/qvm_willow.py). Run from the repository root:

    .venv/bin/python -m pytest -q qvm-google/tests
"""
import os
import sys
from pathlib import Path

import cirq
import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
os.chdir(HERE.parent)

import qvm_willow as V  # noqa: E402


@pytest.fixture(scope="module")
def dev():
    return V.device()


def test_h_native_is_hadamard():
    assert cirq.equal_up_to_global_phase(cirq.unitary(V.H_NATIVE), cirq.unitary(cirq.H))


@pytest.mark.parametrize("name", list(V.DESIGNS))
def test_conversion_faithful_and_device_valid(name, dev):
    r = V.e1_design(name, dev)
    assert r["roundtrip_identical"] and r["flows_equal"] and r["detectors_deterministic"]
    assert r["detector_error_model_equal"]
    assert all(v == "PASS" for v in r["device_validation"].values())
    assert r["cz_pairs"] == r["cz_pairs_on_couplers"] and r["qubits_on_device"]


def test_device_rejects_a_cz_off_coupler(dev):
    d = V.load_design("success03")
    a, b = d.Q[d.data[0]], cirq.GridQubit(0, 6)  # not a neighbour of the data qubit
    with pytest.raises(ValueError):
        dev.validate_circuit(V.main_circuit(d) + cirq.Circuit(cirq.CZ(a, b)))


def test_readout_rule_flags_d3a6_only(dev):
    assert V.e1_design("success03", dev)["readout_lines"] == {}
    assert V.e1_design("d3a6", dev)["readout_lines"].get("readout", 0) >= 1


@pytest.mark.parametrize("name", ["success03", "G4"])
def test_t_state_in_code_space_and_marker_is_plus_one(name):
    d = V.load_design(name)
    psi, proj = V.ideal_refs(name)
    assert np.isclose(np.real(psi.conj() @ proj @ psi), 1)
    after = cirq.Simulator(dtype=np.complex128).simulate(
        cirq.Circuit(V.t_layer(d, True)), qubit_order=d.data_q, initial_state=psi).final_state_vector
    X = cirq.PauliString({q: cirq.X for q in d.data_q}).matrix(qubits=d.data_q)
    assert np.isclose(np.real(after.conj() @ X @ after), 1)  # cliffordea's MPP marker = +1


def test_real_t_noiseless_detectors_zero_and_fidelity_one():
    r = V.e2_design("success03", shots=300, seeds=2)
    assert r["all_detectors_zero"] and r["decode_all_zero"]
    assert r["infidelity_max"] < 1e-9
    assert r["control_uniform_T"]["acceptance"] < 0.9  # the wrong T pattern is caught


def test_fault_injection_matches_cliffordea_on_g4_malignant_pairs():
    tasks, info = V.e3_tasks("G4", n_random_pairs=0)
    mal = [a for k, a in tasks if k == "malignant2"]
    assert info["malignant2"] == 7 == len(mal)
    for a in mal:
        r = V._e3_task(a)
        assert r["real"] == "malignant" and r["agree"] and r["signature_agree"] and r["accept_agree"]


def test_fault_injection_single_events_sample():
    tasks, _ = V.e3_tasks("success03", n_random_pairs=0)
    singles = [a for k, a in tasks if k == "single"][::40]
    for a in singles:
        r = V._e3_task(a)
        assert r["agree"] and r["signature_agree"] and r["deterministic"]


def test_measurement_flip_is_classical():
    d = V.load_design("d3a6")
    comb, _ = V.cliffordea_faults("d3a6")
    ev = next(e for i in range(comb.fault_count) for e in V._events_of(comb, i)
              if e[1].startswith("M"))
    inj, flips = V.event_injection(d, [ev])
    assert inj == {} and len(flips) == 1


def test_noise_model_is_the_qvm_one():
    nm = V.noise_model()
    import cirq_google.engine.virtual_engine_factory as vef
    eng = vef.create_default_noisy_quantum_virtual_machine("willow_pink")
    assert nm == eng.get_processor("willow_pink")._sampler._sampler.noise
    # T gates are virtual Z: no noise attached
    assert nm.is_virtual(cirq.T(cirq.GridQubit(6, 7)))
    assert not nm.is_virtual(V.H_NATIVE(cirq.GridQubit(6, 7)))


def test_noisy_sampling_runs_and_counts_are_consistent():
    d = V.load_design("success03")
    r = V.qsim(seed=5).run(V.e4_circuit("success03"), repetitions=200)
    c = V.e4_counts(d, r.measurements)
    assert c["shots"] == 200 and 0 < c["kept"] <= 200
    assert c["kept_code_logical_error"] <= c["kept_code"] <= c["kept"]
