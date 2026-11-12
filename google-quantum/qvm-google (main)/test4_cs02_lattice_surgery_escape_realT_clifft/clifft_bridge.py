"""Test 4 bridge: one noisy real-T circuit, two simulators.

Builds the E4 protocol of qvm_willow.py (ideal |T_L> preparation, T_L^dagger layer, the
double check, T_L layer, ideal decode) as ONE cirq circuit with a simple Pauli noise model
(DEPOLARIZE1(p) on every qubit after every moment of the noisy part), and converts it
gate by gate to Clifft's stim text (stim + T / T_DAG). The same circuit then runs in
Google's qsim (state vector, real T) and in Clifft (exact near-Clifford, real T), and
both are counted with qvm_willow.e4_counts' rule:

  kept      = no double-check detector fired
  kept_code = kept and the 6 decoded stabiliser bits are 0
  error     = kept_code and the decoded logical bit is 1  (error per kept T state)

The Pauli noise model is used because Clifft only supports Pauli channels; it is a
cross-check of the two simulators, not a Willow-noise result.
"""
import sys
from pathlib import Path

import cirq
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # qvm_willow.py
import qvm_willow as QW  # noqa: E402

DESIGN_FILES = {  # name -> stim prefix (relative to google-quantum/)
    "G4_G6style": "results/g4/G4-G6style",
    "cont_success02": "results/continuing/success02",
    "g6fit00": "qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6/results/g6_search_d6n14/success00",
}


def register(name):
    prefix = DESIGN_FILES[name]
    QW.DESIGNS[name] = (QW.ROOT / f"{prefix}.full.stim", QW.ROOT / f"{prefix}.inner.stim", "CX", "test 4")
    return QW.load_design(name)


def noisy_circuit(d, p):
    """prep (ideal) + main circuit with DEPOLARIZE1(p) after every moment + decode (ideal)."""
    main = QW.main_circuit(d, h_gate=cirq.H)
    qs = sorted(main.all_qubits() | set(d.data_q))
    moments = []
    for m in main:
        moments.append(m)
        if p > 0:
            moments.append(cirq.Moment(cirq.depolarize(p).on(q) for q in qs))
    return QW.prep_circuit(d) + cirq.Circuit(moments) + QW.decode_circuit(d)


def _gate_name(g):
    if isinstance(g, cirq.PhasedXZGate):
        assert cirq.equal_up_to_global_phase(cirq.unitary(g), cirq.unitary(cirq.H))
        return "H"
    table = [(cirq.H, "H"), (cirq.T, "T"), (cirq.T ** -1, "T_DAG"), (cirq.S, "S"), (cirq.S ** -1, "S_DAG"),
             (cirq.X, "X"), (cirq.Y, "Y"), (cirq.Z, "Z"), (cirq.X ** 0.5, "SQRT_X"), (cirq.X ** -0.5, "SQRT_X_DAG"),
             (cirq.CNOT, "CX"), (cirq.CZ, "CZ"), (cirq.SWAP, "SWAP")]
    for ref, n in table:
        if g == ref:
            return n
    raise ValueError(f"unsupported gate {g!r}")


def to_clifft_text(c, d):
    """Clifft stim text of circuit c: gates, DEPOLARIZE1, R, M; then the double-check
    DETECTORs (d.detectors, records by key m<r>), 6 code-space DETECTORs (keys d0..d5)
    and OBSERVABLE 0 = decoded logical bit (key d6). Returns (text, n_check_detectors)."""
    idx = {q: i for i, q in enumerate(sorted(c.all_qubits()))}
    lines, rec = [], {}
    n_meas = 0
    for mom in c:
        for o in mom:
            qs = " ".join(str(idx[q]) for q in o.qubits)
            g = o.gate
            if isinstance(g, cirq.DepolarizingChannel):
                lines.append(f"DEPOLARIZE1({g.p}) {qs}")
            elif isinstance(g, cirq.ResetChannel):
                lines.append(f"R {qs}")
            elif cirq.is_measurement(o):
                lines.append(f"M {qs}")
                rec[cirq.measurement_key_name(o)] = n_meas
                n_meas += 1
            else:
                lines.append(f"{_gate_name(g)} {qs}")
        lines.append("TICK")

    def rel(keys):
        return " ".join(f"rec[{rec[k] - n_meas}]" for k in keys)

    for det in d.detectors:  # MPP reference records are deterministic 0 here, as in detector_bits
        lines.append(f"DETECTOR {rel([f'm{r}' for r in det])}")
    for j in range(len(d.data) - 1):
        lines.append(f"DETECTOR {rel([f'd{j}'])}")
    lines.append(f"OBSERVABLE_INCLUDE(0) {rel([f'd{len(d.data) - 1}'])}")
    return "\n".join(lines) + "\n", len(d.detectors)
