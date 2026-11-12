"""Our double checks inside Google's Quantum Virtual Machine (QVM) for Willow.

Independent re-check with Google's own software (cirq 1.7.0, cirq_google 1.7.0,
qsimcirq 0.22.1). Circuits, cliffordea loading and placements come from nnflags
(imported, not copied). Run from the repository root:

    .venv/bin/python qvm-google/qvm_willow.py e1      # conversion + device validation
    .venv/bin/python qvm-google/qvm_willow.py e2      # real-T correctness, noiseless qsim
    .venv/bin/python qvm-google/qvm_willow.py e3      # fault injection vs cliffordea
    .venv/bin/python qvm-google/qvm_willow.py e4 --shots N   # noisy QVM sampling (checkpointed)

cirq_google sources used (paths relative to .venv/lib/python3.12/site-packages):
  * cirq_google/engine/virtual_engine_factory.py
      - create_device_from_processor_id            :346-357  (GridDevice from the bundled proto)
      - MOST_RECENT_TEMPLATES / MEDIAN_CALIBRATIONS :44-54    ('willow_pink' -> d7v1-2024_08_16)
      - load_median_device_calibration             :141-168
      - load_device_noise_properties               :116-138  (gate times from the device, :135)
      - extract_gate_times_ns_from_device          :471-505
      - create_default_noisy_quantum_virtual_machine :427-467 (qsim + NoiseModelFromGoogleNoiseProperties)
  * cirq_google/engine/calibration_to_noise_properties.py:93-226 (calibration -> noise properties)
  * cirq_google/devices/google_noise_properties.py:191-250, 309-313 (gates, fsim errors, virtual Z)
  * cirq/devices/superconducting_qubits_noise_properties.py:130-192 (thermal, depolarising, readout)
  * cirq/devices/noise_properties.py:76-133 (noisy_moments), cirq/devices/thermal_noise_model.py:264-314
  * cirq_google/devices/grid_device.py:686-753 (validate_circuit)
  * cirq_google/engine/validating_sampler.py:54-70 (QVM validates every circuit against the device)
  * qsimcirq/qsim_simulator.py:254-258 (qsim applies noise.noisy_moments(program, sorted(all_qubits)))

Protocol simulated (cliffordea's conventions, enum/circuits/main.py:42-53 and
accept/logical_analyzers.py:185-208): ideal encoding of |+_L> (stim tableau of
the code's stabilisers and X_L), ideal logical T_L = T on the LOGICAL_S "S"
(majority) sublattice and T^dagger on the "S_DAG" (minority) sublattice -> the
T state; then the device circuit = T_L^dagger layer, the double check (native
CZ + PhasedXZ, its MPP marker and noiseless trailing reset dropped), T_L layer,
with real cirq.T / cirq.T**-1 gates; then an ideal noiseless decode (T_L^dagger,
inverse encoder, Z measurement of the 7 data qubits: 6 stabiliser bits + X_L).
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

# one BLAS / OpenMP thread per process: parallelism comes from worker processes
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cirq  # noqa: E402
import cirq_google  # noqa: E402
import qsimcirq  # noqa: E402
import stim  # noqa: E402
from cirq_google.engine import virtual_engine_factory as vef  # noqa: E402

from cliffordea import accept, enum  # noqa: E402
from cliffordea.enum.circuit_tools import split_by_ticks  # noqa: E402

from nnflags import willow_noise as WN  # noqa: E402
from nnflags.verify import bundled_paths, load_measurement  # noqa: E402

PROCESSOR = "willow_pink"
KST = timezone(timedelta(hours=9))
RES = HERE / "test1_fd3_circuits_vs_google_fig2" / "results"  # test 1; other tests redirect RES
LOGS = HERE / "test1_fd3_circuits_vs_google_fig2" / "logs"


def kst_now() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %I:%M:%S %p KST")


# ---- designs ----------------------------------------------------------------------

# name -> (full, inner, form, role)
DESIGNS = {
    "success03": (ROOT / "results/zz/success03.full.stim", ROOT / "results/zz/success03.inner.stim",
                  "CX", "main: ZZ + X flag, fault distance 3"),
    "success04": (ROOT / "results/zz/success04.full.stim", ROOT / "results/zz/success04.inner.stim",
                  "CX", "2nd best ZZ success"),
    "success00": (ROOT / "results/zz/success00.full.stim", ROOT / "results/zz/success00.inner.stim",
                  "CX", "3rd best ZZ success"),
    "G4": (ROOT / "results/g4/G4-native_CZH.full.stim", ROOT / "results/g4/G4-native_CZH.inner.stim",
           "native", "hardware reference: Google's as-run double check (native CZ + H)"),
    "d3a6": (*bundled_paths("d3a6"), "CX", "what if: best Willow placement, breaks the readout rule"),
}

# The PhasedXZ form of H (Willow's native microwave gate; H itself is also accepted by
# the device, but the noise model only attaches 1q gate error to PhasedXZGate,
# google_noise_properties.py:191-193).
H_NATIVE = cirq.PhasedXZGate.from_matrix(cirq.unitary(cirq.H))


@dataclass
class Design:
    name: str
    role: str
    full: stim.Circuit
    inner_src: stim.Circuit          # as analysed by the earlier rounds (CX or native)
    native: stim.Circuit             # native CZ + H inner circuit, cliffordea layout
    data: tuple[int, ...]
    majority: tuple[int, ...]        # LOGICAL_S "S" targets: logical T = T here
    minority: tuple[int, ...]        # LOGICAL_S "S_DAG" targets: logical T = T^dagger here
    stab_x: list[tuple[int, ...]]
    stab_z: list[tuple[int, ...]]
    pos: dict[int, tuple[int, int]]
    placement_note: str
    layers: list = field(default_factory=list)          # per stim TICK: [(name, qubits, rec)]
    detectors: list = field(default_factory=list)       # tuples of record indices (MPP removed)
    det_has_mpp: list = field(default_factory=list)
    mpp_recs: set = field(default_factory=set)
    meas_at: dict = field(default_factory=dict)         # (timeslice, qubit) -> record
    n_rec: int = 0

    @property
    def Q(self) -> dict[int, cirq.GridQubit]:
        return {i: cirq.GridQubit(*rc) for i, rc in self.pos.items()}

    @property
    def data_q(self) -> list[cirq.GridQubit]:
        return [self.Q[i] for i in self.data]


def _supports(paulis, data):
    return [tuple(data[j] for j in range(len(data)) if p[j]) for p in paulis]


@lru_cache(maxsize=None)
def load_design(name: str) -> Design:
    full_p, inner_p, form, role = DESIGNS[name]
    full = stim.Circuit.from_file(str(full_p))
    inner = stim.Circuit.from_file(str(inner_p))
    native = WN.cx_to_native(inner) if form == "CX" else inner
    m = load_measurement(full, native)
    data = tuple(m.DATA_INDICES)
    maj, mino = [], []
    for ins in m.LOGICAL_S:
        (maj if ins.name == "S" else mino).extend(t.value for t in ins.targets_copy())
    cwd = os.getcwd()
    try:  # nnflags resolves its results/ paths relative to the repository root
        os.chdir(ROOT)
        pos, note = WN.placement(name, inner)
    finally:
        os.chdir(cwd)
    d = Design(name=name, role=role, full=full, inner_src=inner, native=native, data=data,
               majority=tuple(sorted(maj)), minority=tuple(sorted(mino)),
               stab_x=_supports(m.STABILIZER_GENERATORS["X"], data),
               stab_z=_supports(m.STABILIZER_GENERATORS["Z"], data),
               pos=pos, placement_note=note)
    _parse(d)
    return d


def _parse(d: Design) -> None:
    rec = 0
    for t, L in enumerate(split_by_ticks(d.native)):
        items = []
        for op in L:
            n = op.name
            if n == "QUBIT_COORDS":
                continue
            if n == "MPP":
                d.mpp_recs.update(range(rec, rec + op.num_measurements))
                rec += op.num_measurements
                continue
            if n == "DETECTOR":
                recs = [rec + x.value for x in op.targets_copy()]
                d.det_has_mpp.append(any(r in d.mpp_recs for r in recs))
                d.detectors.append(tuple(r for r in recs if r not in d.mpp_recs))
                continue
            qs = [x.value for x in op.targets_copy()]
            if n == "CZ":
                items += [("CZ", (a, b), None) for a, b in zip(qs[::2], qs[1::2])]
            elif n in ("H", "R"):
                items += [(n, (q,), None) for q in qs]
            elif n in ("M", "MR"):
                for q in qs:
                    d.meas_at[(t, q)] = rec
                    items.append((n, (q,), rec))
                    rec += 1
            else:
                raise ValueError(f"unsupported native op {n}")
        d.layers.append(items)
    d.n_rec = rec


# ---- cirq circuits ------------------------------------------------------------------

def t_layer(d: Design, dagger: bool) -> cirq.Moment:
    """Logical T (dagger=False) or T^dagger: real cirq.T / cirq.T**-1 on the data."""
    Q = d.Q
    t, td = cirq.T, cirq.T ** -1
    a, b = (td, t) if dagger else (t, td)
    return cirq.Moment([a.on(Q[q]) for q in d.majority] + [b.on(Q[q]) for q in d.minority])


def _layer_moments(d: Design, items, h_gate) -> list[cirq.Moment]:
    Q = d.Q
    m1, m2 = [], []
    for n, qs, r in items:
        if n == "H":
            m1.append(h_gate.on(Q[qs[0]]))
        elif n == "CZ":
            m1.append(cirq.CZ(Q[qs[0]], Q[qs[1]]))
        elif n == "R":
            m1.append(cirq.ResetChannel().on(Q[qs[0]]))
        elif n == "M":
            m1.append(cirq.measure(Q[qs[0]], key=f"m{r}"))
        elif n == "MR":
            m1.append(cirq.measure(Q[qs[0]], key=f"m{r}"))
            m2.append(cirq.ResetChannel().on(Q[qs[0]]))
    return [cirq.Moment(m1)] + ([cirq.Moment(m2)] if m2 else [])


def inner_moments(d: Design, inject: dict | None = None, h_gate=H_NATIVE) -> list[cirq.Moment]:
    """The double check on Willow: stim TICKs 1..L-2 of the native circuit (TICK 0 is
    cliffordea's noiseless MPP marker, TICK L-1 its noiseless trailing reset).
    ``inject`` maps a stim timeslice to {qubit: 'X'|'Y'|'Z'} Paulis applied after
    all operations of that timeslice (cliffordea places noise after the TICK's
    operations, enum/noise/main.py)."""
    out = []
    for t in range(1, len(d.layers) - 1):
        out += _layer_moments(d, d.layers[t], h_gate)
        if inject and t in inject:
            out.append(cirq.Moment({"X": cirq.X, "Y": cirq.Y, "Z": cirq.Z}[p].on(d.Q[q])
                                   for q, p in sorted(inject[t].items())))
    return out


def main_circuit(d: Design, inject=None, h_gate=H_NATIVE) -> cirq.Circuit:
    """The device circuit: T_L^dagger layer, double check, T_L layer (real T gates)."""
    return cirq.Circuit([t_layer(d, True), *inner_moments(d, inject, h_gate), t_layer(d, False)])


_STIM_TO_CIRQ = {
    "H": cirq.H, "S": cirq.S, "S_DAG": cirq.S ** -1, "X": cirq.X, "Y": cirq.Y, "Z": cirq.Z,
    "CX": cirq.CNOT, "CZ": cirq.CZ, "SWAP": cirq.SWAP, "SQRT_X": cirq.X ** 0.5,
    "SQRT_X_DAG": cirq.X ** -0.5,
}


@lru_cache(maxsize=None)
def cliffordea_encoder(name: str) -> stim.Tableau:
    """cliffordea's own encoding tableau of the code (accept/logical_analyzers.py:281-287,
    307-345): unencoded qubits 0..5 -> stabilisers (signs +), qubit 6: X -> X^n, Z -> Z^n."""
    d = load_design(name)
    m = load_measurement(d.full, d.native)
    an = accept.CliffordLogicalAnalyzer(data_indices=m.DATA_INDICES,
                                        stabilizer_generators=m.STABILIZER_GENERATORS,
                                        logical_s=m.LOGICAL_S)
    return an.encoder


def encoder_ops(d: Design) -> list[cirq.Operation]:
    """cliffordea's encoder as cirq gates on the data qubits (ideal, noiseless)."""
    dq = d.data_q
    ops = []
    for ins in cliffordea_encoder(d.name).to_circuit("elimination"):
        g = _STIM_TO_CIRQ[ins.name]
        ts = [x.value for x in ins.targets_copy()]
        k = 2 if ins.name in ("CX", "CZ", "SWAP") else 1
        ops += [g.on(*(dq[x] for x in ts[i:i + k])) for i in range(0, len(ts), k)]
    return ops


def prep_circuit(d: Design) -> cirq.Circuit:
    """Ideal (noiseless) encoded T state |T_L>: the unencoded logical qubit (data-local
    index 6) is put in T H|0>, the +1 eigenstate of (X + Y)/sqrt 2, i.e. cliffordea's
    LOGICAL_COEFFICIENTS['T'] (logical_analyzers.py:42), then cliffordea's encoder."""
    lq = d.data_q[-1]
    return cirq.Circuit([cirq.H(lq), cirq.T(lq)]) + cirq.Circuit(encoder_ops(d))


def decode_circuit(d: Design) -> cirq.Circuit:
    """Ideal (noiseless) logical H_XY + stabiliser measurement: inverse encoder, then
    T^dagger, H on the logical qubit, M on the data. Bits d0..d5 = stabilisers
    (0 = +1), d6 = logical H_XY (0 = +1, the T state)."""
    lq = d.data_q[-1]
    c = cirq.Circuit(cirq.inverse(encoder_ops(d))) + cirq.Circuit([cirq.T(lq) ** -1, cirq.H(lq)])
    c.append(cirq.Moment(cirq.measure(q, key=f"d{j}") for j, q in enumerate(d.data_q)))
    return c


# ---- ideal reference quantities ------------------------------------------------------

@lru_cache(maxsize=None)
def ideal_refs(name: str):
    """(|T_L> on the data, code projector on the data), data qubits in d.data order."""
    d = load_design(name)
    dq = d.data_q
    psi = cirq.Simulator(dtype=np.complex128).simulate(
        prep_circuit(d), qubit_order=dq).final_state_vector
    proj = np.eye(2 ** len(dq), dtype=np.complex128)
    for sup, b in [(s, cirq.X) for s in d.stab_x] + [(s, cirq.Z) for s in d.stab_z]:
        P = cirq.PauliString({d.Q[q]: b for q in sup}).matrix(qubits=dq)
        proj = proj @ (np.eye(len(P)) + P) / 2
    return psi / np.linalg.norm(psi), proj


def data_rho(d: Design, state: np.ndarray, qubit_map: dict) -> np.ndarray:
    n = len(qubit_map)
    order = [qubit_map[q] for q in d.data_q]
    rest = [i for i in range(n) if i not in order]
    t = state.reshape([2] * n).transpose(order + rest).reshape(2 ** len(order), -1)
    return t @ t.conj().T


def logical_figures(d: Design, state, qubit_map) -> dict:
    psi, proj = ideal_refs(d.name)
    rho = data_rho(d, np.asarray(state, dtype=np.complex128), qubit_map)
    rho /= np.trace(rho).real
    F = float(np.real(psi.conj() @ rho @ psi))
    P = float(np.real(np.trace(proj @ rho)))
    return dict(fidelity=F, p_code=P, fid_given_code=F / P if P > 1e-12 else float("nan"))


def detector_bits(d: Design, meas: dict, flips=()) -> np.ndarray:
    """Detection events (reps x detectors) from a cirq Result's measurements."""
    reps = next(iter(meas.values())).shape[0]
    R = np.zeros((reps, d.n_rec), dtype=np.uint8)
    for k, v in meas.items():
        if k.startswith("m"):
            R[:, int(k[1:])] = v[:, 0]
    for r in flips:
        R[:, r] ^= 1
    return np.stack([np.bitwise_xor.reduce(R[:, list(det)], axis=1) if det else
                     np.zeros(reps, np.uint8) for det in d.detectors], axis=1)


def qsim(seed=None, threads=1) -> qsimcirq.QSimSimulator:
    return qsimcirq.QSimSimulator(qsim_options={"t": threads}, seed=seed)


# ---- E1: conversion + device validation ---------------------------------------------

def device():
    return vef.create_device_from_processor_id(PROCESSOR)


def cirq_to_stim(c: cirq.Circuit, d: Design) -> stim.Circuit:
    """Round trip of the inner moments back to stim (H_NATIVE -> H, a measure moment
    followed by a reset moment on the same qubits -> MR), to compare with the native
    stim circuit instruction by instruction."""
    inv = {v: k for k, v in d.Q.items()}
    out = stim.Circuit()
    last_measured: set[int] = set()
    for mom in c:
        ops = list(mom)
        if ops and all(isinstance(o.gate, cirq.ResetChannel) and inv[o.qubits[0]] in last_measured
                       for o in ops):
            out = _merge_mr(out, [inv[o.qubits[0]] for o in ops])
            last_measured = set()
            continue
        if len(out):
            out.append("TICK")
        last_measured = set()
        for o in ops:
            qs = [inv[q] for q in o.qubits]
            if isinstance(o.gate, cirq.PhasedXZGate) or o.gate == cirq.H:
                assert cirq.equal_up_to_global_phase(cirq.unitary(o.gate), cirq.unitary(cirq.H))
                out.append("H", qs)
            elif o.gate == cirq.CZ:
                out.append("CZ", qs)
            elif isinstance(o.gate, cirq.ResetChannel):
                out.append("R", qs)
            elif cirq.is_measurement(o):
                out.append("M", qs)
                last_measured.add(qs[0])
            else:
                raise ValueError(f"unexpected op {o}")
    return out


def _merge_mr(c: stim.Circuit, qubits) -> stim.Circuit:
    """Turn 'M q' in the last TICK of c into 'MR q' for q in qubits."""
    qs = set(qubits)
    out = stim.Circuit()
    ticks = [i for i, ins in enumerate(c) if ins.name == "TICK"]
    start = ticks[-1] + 1 if ticks else 0
    for i, ins in enumerate(c):
        if i >= start and ins.name == "M":
            for t in ins.targets_copy():
                out.append("MR" if t.value in qs else "M", [t.value])
        else:
            out.append(ins)
    return out


def _ops_only(c: stim.Circuit) -> list[tuple[str, tuple[int, ...]]]:
    """Sequence of (name, targets) per TICK, split per target and sorted inside a TICK."""
    res = []
    for L in split_by_ticks(c):
        items = []
        for ins in L:
            if ins.name in ("DETECTOR", "QUBIT_COORDS", "MPP", "OBSERVABLE_INCLUDE"):
                continue
            ts = [t.value for t in ins.targets_copy()]
            k = 2 if ins.name == "CZ" else 1
            items += [(ins.name, tuple(ts[i:i + k])) for i in range(0, len(ts), k)]
        if items:
            res.append(sorted(items))
    return res


def e1_design(name: str, dev) -> dict:
    d = load_design(name)
    out = dict(name=name, role=d.role, placement=d.placement_note,
               qubits={str(i): list(rc) for i, rc in sorted(d.pos.items())})
    # the native stim used by the comparison round must be the same circuit
    saved = ROOT / "results/willow_noise" / f"{name}.native.inner.stim"
    out["native_equals_comparison_round_file"] = (
        str(stim.Circuit.from_file(str(saved))) == str(d.native)) if saved.exists() else None
    # 1) gate-level: H_NATIVE equals H up to global phase
    out["phasedxz_is_H"] = bool(cirq.equal_up_to_global_phase(cirq.unitary(H_NATIVE),
                                                              cirq.unitary(cirq.H)))
    out["H_native_gate"] = repr(H_NATIVE)
    # 2) round trip: cirq inner moments -> stim, instruction for instruction
    inner_c = cirq.Circuit(inner_moments(d))
    back = cirq_to_stim(inner_c, d)
    nat_core = stim.Circuit()
    layers = split_by_ticks(d.native)
    for t in range(1, len(layers) - 1):
        if t > 1:
            nat_core.append("TICK")
        nat_core += layers[t]
    out["roundtrip_identical"] = _ops_only(back) == _ops_only(nat_core)
    # 3) stabiliser flows of the round-tripped Clifford circuit (with the MPP marker and the
    #    trailing reset put back, and the detectors re-attached) equal the native circuit's
    rebuilt = _with_detectors(d, back)
    out["flows_equal"] = bool(rebuilt.has_all_flows(d.native.flow_generators(), unsigned=False)
                              and d.native.has_all_flows(rebuilt.flow_generators(), unsigned=False))
    out["detectors_deterministic"] = _deterministic(rebuilt)
    out["detector_error_model_equal"] = (
        str(enum.noise.uniformly_depolarize(rebuilt, 1e-3).detector_error_model())
        == str(enum.noise.uniformly_depolarize(d.native, 1e-3).detector_error_model()))
    # 4) device validation of the device circuit (T layers + double check)
    res = {}
    for label, gate in (("H as cirq.H", cirq.H), ("H as PhasedXZGate (used)", H_NATIVE)):
        c = main_circuit(d, h_gate=gate)
        try:
            dev.validate_circuit(c)
            res[label] = "PASS"
        except ValueError as e:
            res[label] = f"FAIL: {e}"
    out["device_validation"] = res
    # where the qubits/couplers are: all on device, all CZ pairs on couplers
    pairs = {frozenset(p) for p in dev.metadata.qubit_pairs}
    czs = {frozenset((d.Q[qs[0]], d.Q[qs[1]])) for L in d.layers for n, qs, _ in L if n == "CZ"}
    out["cz_pairs"] = len(czs)
    out["cz_pairs_on_couplers"] = sum(p in pairs for p in czs)
    out["qubits_on_device"] = all(q in dev.metadata.qubit_set for q in d.Q.values())
    c = main_circuit(d)
    out["moments"] = len(c)
    out["gate_counts"] = {k: int(v) for k, v in _gate_counts(c).items()}
    out["readout_lines"] = _readout_conflicts(d)
    return out


def _gate_counts(c):
    from collections import Counter
    cnt = Counter()
    for o in c.all_operations():
        g = o.gate
        if isinstance(g, cirq.PhasedXZGate):
            cnt["PhasedXZ (H)"] += 1
        elif g == cirq.CZ:
            cnt["CZ"] += 1
        elif isinstance(g, cirq.ResetChannel):
            cnt["reset"] += 1
        elif cirq.is_measurement(o):
            cnt["measure"] += 1
        elif g in (cirq.T, cirq.T ** -1):
            cnt["T / T^-1 (virtual Z)"] += 1
        else:
            cnt[str(g)] += 1
    return cnt


def _readout_conflicts(d: Design) -> dict:
    """nnflags' hardware rules on the analysed circuit at this placement (strict readout,
    live_rule="gate", final_layer="auto", as in the earlier rounds). Not part of cirq's
    device model: GridDevice.validate_circuit checks gates, qubits and couplers only."""
    from nnflags.constraints import check_circuit, summarize
    return summarize(check_circuit(d.inner_src, d.pos, data_qubits=d.data))


def _with_detectors(d: Design, core: stim.Circuit) -> stim.Circuit:
    layers = split_by_ticks(d.native)
    c = stim.Circuit()
    c += layers[0]
    c.append("TICK")
    # re-attach the native circuit's DETECTORs after the TICK that closes each measurement
    core_layers = split_by_ticks(core)
    for t, L in enumerate(core_layers, start=1):
        c += L
        for ins in layers[t]:
            if ins.name == "DETECTOR":
                c.append(ins)
        c.append("TICK")
    c += layers[-1]
    return c


def _deterministic(c: stim.Circuit) -> bool:
    try:
        c.detector_error_model(allow_gauge_detectors=False)
        return True
    except ValueError:
        return False


def run_e1() -> dict:
    t0 = time.time()
    dev = device()
    out = dict(started=kst_now(), processor=PROCESSOR,
               device_source="virtual_engine_factory.create_device_from_processor_id "
                             "(virtual_engine_factory.py:346-357), template "
                             + vef.MOST_RECENT_TEMPLATES[PROCESSOR],
               designs={n: e1_design(n, dev) for n in DESIGNS})
    out["runtime_s"] = time.time() - t0
    return out


# ---- E2: real-T correctness (noiseless qsim) ----------------------------------------

def e2_design(name: str, shots=2000, seeds=5) -> dict:
    d = load_design(name)
    prep = prep_circuit(d)
    full = prep + main_circuit(d)
    sim = qsim(seed=2026)
    r = sim.run(full, repetitions=shots)
    det = detector_bits(d, r.measurements)
    out = dict(name=name, shots=shots, detectors=len(d.detectors),
               detectors_using_mpp_record=int(sum(d.det_has_mpp)),
               detector_fires=int(det.sum()), all_detectors_zero=bool(det.sum() == 0))
    figs = []
    for s in range(seeds):
        res = qsim(seed=s).simulate(full)
        figs.append(logical_figures(d, res.final_state_vector, res.qubit_map))
    out["fidelity_min"] = min(f["fidelity"] for f in figs)
    out["infidelity_max"] = max(1 - f["fidelity"] for f in figs)
    out["p_code_min"] = min(f["p_code"] for f in figs)
    # cross-check with cirq's own simulator: same trajectory gives measurements + state
    cr = cirq.Simulator(dtype=np.complex128, seed=7).simulate(full)
    out["cirq_simulator"] = dict(
        detectors_zero=bool(detector_bits(
            d, {k: np.array([v]) for k, v in cr.measurements.items()}).sum() == 0),
        **logical_figures(d, cr.final_state_vector, cr.qubit_map))
    # ideal decode appended: every logical H_XY outcome is +1, every stabiliser +1
    rd = sim.run(full + decode_circuit(d), repetitions=shots)
    dec = np.concatenate([rd.measurements[f"d{j}"] for j in range(len(d.data))], axis=1)
    out["decode_all_zero"] = bool(dec.sum() == 0)
    out["decode_shots"] = shots
    # negative control: T^dagger / T on *every* data qubit (ignoring the LOGICAL_S sublattices)
    bad = prep + cirq.Circuit([cirq.Moment((cirq.T ** -1).on_each(d.data_q)), *inner_moments(d),
                               cirq.Moment(cirq.T.on_each(d.data_q))])
    rb = sim.run(bad, repetitions=shots)
    sb = qsim(seed=0).simulate(bad)
    out["control_uniform_T"] = dict(
        acceptance=float((detector_bits(d, rb.measurements).sum(axis=1) == 0).mean()),
        **logical_figures(d, sb.final_state_vector, sb.qubit_map))
    return out


def run_e2() -> dict:
    t0 = time.time()
    out = dict(started=kst_now(), designs={n: e2_design(n) for n in DESIGNS})
    out["runtime_s"] = time.time() - t0
    return out


# ---- E3: fault injection --------------------------------------------------------------

@lru_cache(maxsize=None)
def cliffordea_faults(name: str, mfc: int = 2):
    """cliffordea on the native circuit that is run: FaultCombinator, kept effects."""
    d = load_design(name)
    m = load_measurement(d.full, d.native)
    noisy = enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=1e-3)
    analyzer = accept.CliffordLogicalAnalyzer(
        data_indices=m.DATA_INDICES, stabilizer_generators=m.STABILIZER_GENERATORS,
        logical_s=m.LOGICAL_S)
    comb = enum.FaultCombinator(noisy)
    kept = comb.get_kept_effects(logical_analyzer=analyzer, max_fault_count=mfc,
                                 cultivated_states=("T",))
    cls = {}
    for k, effects in enumerate(kept["T"]):
        for p, fid, cfgs in effects.values():
            for cfg in cfgs:
                cls[tuple(cfg)] = (float(p), float(fid))
    return comb, cls


def _event_key(ev):
    t, n, ts = ev
    return (t, n, tuple((x.value, x.pauli_type if n == "E" else "") for x in ts))


def event_injection(d: Design, events) -> tuple[dict, list]:
    """Pauli injections {timeslice: {qubit: P}} and classical measurement flips."""
    inj, flips = {}, []
    mult = {("X", "X"): "I", ("Y", "Y"): "I", ("Z", "Z"): "I", ("X", "Y"): "Z", ("Y", "X"): "Z",
            ("X", "Z"): "Y", ("Z", "X"): "Y", ("Y", "Z"): "X", ("Z", "Y"): "X"}

    def add(t, q, p):
        cur = inj.setdefault(t, {}).get(q, "I")
        new = p if cur == "I" else mult[(cur, p)]
        if new == "I":
            inj[t].pop(q)
        else:
            inj[t][q] = new

    for t, n, ts in events:
        if n == "E":
            for x in ts:
                add(t, x.value, x.pauli_type)
        elif n in ("X_ERROR", "Y_ERROR", "Z_ERROR"):
            add(t, ts[0].value, n[0])
        else:  # measurement result flip (classical)
            flips.append(d.meas_at[(t, ts[0].value)])
    return {t: v for t, v in inj.items() if v}, flips


def classify_real_t(d: Design, events, seed=0) -> dict:
    inj, flips = event_injection(d, events)
    full = prep_circuit(d) + main_circuit(d, inject=inj)
    r = qsim(seed=seed).run(full, repetitions=3)
    det = detector_bits(d, r.measurements, flips)
    deterministic = bool((det == det[0]).all())
    fired = bool(det[0].any())
    res = qsim(seed=seed).simulate(full)
    f = logical_figures(d, res.final_state_vector, res.qubit_map)
    if fired:
        verdict = "rejected"
    elif f["p_code"] < 1e-9:
        verdict = "rejected"
    elif f["fid_given_code"] < 1 - 1e-6:
        verdict = "malignant"
    else:
        verdict = "benign"
    return dict(verdict=verdict, detector_fired=fired, deterministic=deterministic,
                signature=det[0].tolist(), **f)


def cliffordea_verdict(cls: dict, cfg: tuple) -> tuple[str, float | None]:
    if cfg not in cls:
        return "rejected", None
    p, fid = cls[cfg]
    return ("malignant" if fid != 1 else "benign"), p


def _events_of(comb, i):
    return sorted(comb.index_to_events[i], key=_event_key)


def _e3_task(args):
    name, cfg, ev_idx, seed = args  # ev_idx[j]: which error event realises fault cfg[j]
    d = load_design(name)
    comb, cls = cliffordea_faults(name)
    events = [_events_of(comb, i)[j] for i, j in zip(cfg, ev_idx)]
    real = classify_real_t(d, events, seed)
    cv, p = cliffordea_verdict(cls, tuple(cfg))
    # cliffordea's detector signature from its own public per-event analysis
    sig = np.zeros(len(d.detectors), dtype=bool)
    for ev in events:
        s, _eff = comb.circuit.get_signature_and_effect(ev)
        sig ^= s
    return dict(cfg=list(cfg), events=[repr(_event_key(e)) for e in events],
                cliffordea=cv, cliffordea_accept=p, real=real["verdict"],
                agree=cv == real["verdict"],
                signature_agree=bool((sig.astype(int) == np.array(real["signature"])).all()),
                deterministic=real["deterministic"], p_code=real["p_code"],
                fid_given_code=real["fid_given_code"],
                accept_agree=(p is None or abs(p - real["p_code"]) < 1e-6))


def e3_tasks(name: str, n_random_pairs: int, seed: int = 2026):
    comb, cls = cliffordea_faults(name)
    tasks = []
    # all single faults, every error event of every fault
    for i in range(comb.fault_count):
        for j in range(len(comb.index_to_events[i])):
            tasks.append(("single", (name, (i,), (j,), 1)))
    # all malignant 2-fault configurations cliffordea reports
    mal = sorted(c for c, (p, fid) in cls.items() if len(c) == 2 and fid != 1)
    for c in mal:
        tasks.append(("malignant2", (name, c, (0, 0), 2)))
    # every 2-fault configuration (one representative event per fault); the requested
    # seeded random sample is a subset of these and is reported separately
    allpairs = list(itertools.combinations(range(comb.fault_count), 2))
    for c in allpairs:
        tasks.append(("all2", (name, c, (0, 0), 3)))
    return tasks, dict(faults=comb.fault_count, events=sum(len(v) for v in comb.index_to_events.values()),
                       malignant2=len(mal), all_pairs=len(allpairs),
                       random_sample=random_pairs(comb.fault_count, n_random_pairs, seed, name))


def random_pairs(n_faults: int, n: int, seed: int, name: str) -> list[tuple[int, int]]:
    """The fixed-seed random sample of distinct 2-fault configurations."""
    rng = np.random.default_rng(seed + zlib.crc32(name.encode()))
    chosen = set()
    while len(chosen) < min(n, n_faults * (n_faults - 1) // 2):
        a, b = sorted(rng.choice(n_faults, size=2, replace=False).tolist())
        chosen.add((a, b))
    return sorted(chosen)


def run_e3(n_random=2000, workers=12, designs=None) -> dict:
    from multiprocessing import get_context
    t0 = time.time()
    designs = designs or list(DESIGNS)
    out = dict(started=kst_now(), random_pairs_per_design=n_random, seed=2026, designs={})
    with get_context("fork").Pool(workers) as pool:
        for name in designs:
            part = RES / "e3_parts" / f"{name}.json"
            if part.exists():  # checkpoint: one file per design
                out["designs"][name] = json.loads(part.read_text())
                continue
            tasks, info = e3_tasks(name, n_random)
            sample = set(info.pop("random_sample"))
            rows = pool.map(_e3_task, [a for _, a in tasks], chunksize=16)
            kinds = [k for k, _ in tasks]
            kinds += ["random2"] * len(sample)
            rows += [r for k, r in zip(kinds, rows) if k == "all2" and tuple(r["cfg"]) in sample]
            summ = {}
            for kind in ("single", "malignant2", "all2", "random2"):
                rs = [r for k, r in zip(kinds, rows) if k == kind]
                summ[kind] = dict(
                    n=len(rs), agree=sum(r["agree"] for r in rs),
                    signature_agree=sum(r["signature_agree"] for r in rs),
                    accept_agree=sum(r["accept_agree"] for r in rs),
                    nondeterministic=sum(not r["deterministic"] for r in rs),
                    real=_count(r["real"] for r in rs), cliffordea=_count(r["cliffordea"] for r in rs),
                    disagreements=[r for r in rs if not (r["agree"] and r["signature_agree"]
                                                         and r["accept_agree"])])
            out["designs"][name] = dict(info=info, summary=summ,
                                        malignant2_rows=[r for k, r in zip(kinds, rows)
                                                         if k == "malignant2"])
            _dump(out["designs"][name], part)
            print(f"[{kst_now()}] E3 {name}: " + json.dumps(
                {k: {kk: vv for kk, vv in v.items() if kk != "disagreements"}
                 for k, v in summ.items()}), flush=True)
    out["runtime_s"] = time.time() - t0
    return out


def _count(it):
    from collections import Counter
    return dict(Counter(it))


# ---- E4: noisy QVM ------------------------------------------------------------------

@lru_cache(maxsize=None)
def noise_model():
    """Exactly what create_default_noisy_quantum_virtual_machine builds
    (virtual_engine_factory.py:452-456)."""
    return cirq_google.NoiseModelFromGoogleNoiseProperties(vef.load_device_noise_properties(PROCESSOR))


def noisy_main(d: Design) -> cirq.Circuit:
    """noise.noisy_moments(program, sorted(all_qubits)), as qsim does (qsim_simulator.py:254-258)."""
    c = main_circuit(d)
    return cirq.Circuit(noise_model().noisy_moments(c, sorted(c.all_qubits())))


@lru_cache(maxsize=None)
def e4_circuit(name: str) -> cirq.Circuit:
    d = load_design(name)
    return prep_circuit(d) + noisy_main(d) + decode_circuit(d)


def e4_counts(d: Design, meas: dict) -> dict:
    det = detector_bits(d, meas)
    kept = det.sum(axis=1) == 0
    dec = np.concatenate([meas[f"d{j}"] for j in range(len(d.data))], axis=1)
    syn0 = dec[:, :-1].sum(axis=1) == 0
    log1 = dec[:, -1] == 1
    return dict(shots=int(len(kept)), kept=int(kept.sum()),
                kept_code=int((kept & syn0).sum()),
                kept_code_logical_error=int((kept & syn0 & log1).sum()),
                kept_not_T=int((kept & ~(syn0 & ~log1)).sum()),
                all_code=int(syn0.sum()), all_not_T=int((~(syn0 & ~log1)).sum()),
                detector_fires=det.sum(axis=0).astype(int).tolist())


def _e4_chunk(args):
    name, chunk, reps, seed, path = args
    d = load_design(name)
    t0 = time.time()
    r = qsim(seed=seed).run(e4_circuit(name), repetitions=reps)
    c = e4_counts(d, r.measurements)
    c.update(chunk=chunk, seed=seed, wall_s=time.time() - t0, finished=kst_now())
    Path(path).write_text(json.dumps(c))
    return c


def run_e4(shots: dict, chunk=2000, workers=12, outdir=RES / "e4_chunks") -> dict:
    from multiprocessing import get_context
    outdir.mkdir(parents=True, exist_ok=True)
    tasks = []
    for name, n in shots.items():
        for k in range(math.ceil(n / chunk)):
            p = outdir / f"{name}_{k:05d}.json"
            if p.exists():
                continue
            seed = zlib.crc32(f"{name}:{k}".encode())
            tasks.append((name, k, chunk, seed, str(p)))
    t0 = time.time()
    print(f"[{kst_now()}] E4: {len(tasks)} chunks of {chunk} shots to run", flush=True)
    done = 0
    with get_context("fork").Pool(workers) as pool:
        for c in pool.imap_unordered(_e4_chunk, tasks):
            done += 1
            if done % 50 == 0 or done == len(tasks):
                print(f"[{kst_now()}] E4: {done}/{len(tasks)} chunks, {time.time() - t0:.0f} s",
                      flush=True)
    return summarize_e4(shots, outdir)


def summarize_e4(shots: dict, outdir=RES / "e4_chunks") -> dict:
    from scipy.stats import beta
    out = {}
    for name in shots:
        cs = [json.loads(p.read_text()) for p in sorted(outdir.glob(f"{name}_*.json"))]
        if not cs:
            continue
        S = {k: sum(c[k] for c in cs) for k in ("shots", "kept", "kept_code",
                                                "kept_code_logical_error", "kept_not_T",
                                                "all_code", "all_not_T")}
        S["chunks"] = len(cs)
        S["wall_s_sum"] = sum(c["wall_s"] for c in cs)
        S["detector_fires"] = np.sum([c["detector_fires"] for c in cs], axis=0).tolist()
        n, k = S["shots"], S["kept"]
        acc = k / n
        S["acceptance"] = acc
        S["acceptance_se"] = math.sqrt(acc * (1 - acc) / n)
        S["acceptance_rel_se"] = S["acceptance_se"] / acc
        for key, num, den in (("logical_error_given_code", "kept_code_logical_error", "kept_code"),
                              ("infidelity_kept", "kept_not_T", "kept")):
            x, m = S[num], S[den]
            p = x / m if m else float("nan")
            lo = 0.0 if x == 0 else float(beta.ppf(0.025, x, m - x + 1))
            hi = float(beta.ppf(0.975, x + 1, m - x)) if x < m else 1.0
            S[key] = dict(events=x, of=m, rate=p, se=math.sqrt(max(p * (1 - p), 0) / m) if m else None,
                          ci95=[lo, hi], upper95_one_sided=float(beta.ppf(0.95, x + 1, m - x)))
        out[name] = S
    return out


def engine_crosscheck(name="success03", shots=20000) -> dict:
    """Run the device circuit through the literal QVM (SimulatedLocalEngine) and through
    the explicit noisy circuit, both from |0...0> (the QVM cannot prepare the ideal
    encoded input), and compare detector statistics."""
    import qsimcirq as qc
    d = load_design(name)
    eng = vef.create_default_noisy_quantum_virtual_machine(PROCESSOR, qc.QSimSimulator,
                                                           seed=11)
    proc = eng.get_processor(PROCESSOR)
    c = main_circuit(d)
    t0 = time.time()
    r_eng = proc.get_sampler().run(c, repetitions=shots)
    t_eng = time.time() - t0
    r_exp = qsim(seed=12).run(noisy_main(d), repetitions=shots)
    a = detector_bits(d, r_eng.measurements).mean(axis=0)
    b = detector_bits(d, r_exp.measurements).mean(axis=0)
    se = np.sqrt(a * (1 - a) / shots + b * (1 - b) / shots)
    z = np.where(se > 0, (a - b) / np.where(se > 0, se, 1), 0)
    nm = proc._sampler._sampler.noise  # ValidatingSampler(sampler=QSimSimulator(noise=...))
    return dict(name=name, shots=shots, engine_wall_s=t_eng,
                # NoiseModelFromNoiseProperties compares by its noise properties
                # (cirq/devices/noise_properties.py:45-60, value_equality)
                engine_noise_model_equal=bool(nm == noise_model()),
                det_rate_engine=a.tolist(), det_rate_explicit=b.tolist(),
                max_abs_z=float(np.abs(z).max()))


def noise_inventory() -> dict:
    """What the willow_pink noise model contains, read back from the objects."""
    props = vef.load_device_noise_properties(PROCESSOR)
    nm = noise_model()
    d1 = props._depolarizing_error
    by = {}
    for op_id, p in d1.items():
        by.setdefault(op_id.gate_type.__name__, []).append(p)
    st = lambda v: dict(n=len(v), median=float(np.median(v)), min=float(np.min(v)),
                        max=float(np.max(v)))
    ro = np.array(list(props.readout_errors.values()))
    fs = [(g.theta, g.phi) for g in props.fsim_errors.values()]
    return dict(
        gate_times_ns={k.__name__: v for k, v in props.gate_times_ns.items()},
        t1_us=st([v / 1000 for v in props.t1_ns.values()]),
        tphi_us=st([v / 1000 for v in props.tphi_ns.values()]),
        depolarizing_after_gate=({k: st(v) for k, v in by.items()}),
        depolarizing_nonpositive_dropped={k: int(sum(x <= 0 for x in v)) for k, v in by.items()},
        readout_p00=st(ro[:, 0]), readout_p11=st(ro[:, 1]),
        fsim_theta_rad=st([abs(t) for t, _ in fs]), fsim_phi_rad=st([abs(p) for _, p in fs]),
        models=[type(m).__name__ for m in nm.noise_models])


# ---- CLI -------------------------------------------------------------------------------

def _dump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=lambda o: o.tolist()
                               if isinstance(o, np.ndarray) else str(o)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exp", choices=["e1", "e2", "e3", "e4", "e4sum", "crosscheck", "noise"])
    ap.add_argument("--shots", type=int, default=200_000)
    ap.add_argument("--shots-json", default=None, help='e.g. {"success03": 400000}')
    ap.add_argument("--random-pairs", type=int, default=2000)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--chunk", type=int, default=2000)
    a = ap.parse_args()
    os.chdir(ROOT)
    if a.exp == "e1":
        _dump(run_e1(), RES / "e1.json")
    elif a.exp == "e2":
        _dump(run_e2(), RES / "e2.json")
    elif a.exp == "e3":
        _dump(run_e3(a.random_pairs, a.workers), RES / "e3.json")
    elif a.exp in ("e4", "e4sum"):
        shots = json.loads(a.shots_json) if a.shots_json else {n: a.shots for n in DESIGNS}
        res = run_e4(shots, a.chunk, a.workers) if a.exp == "e4" else summarize_e4(shots)
        _dump(dict(updated=kst_now(), chunk=a.chunk, results=res), RES / "e4.json")
        for n, s in res.items():
            print(n, s["shots"], f"{100 * s['acceptance']:.3f} %",
                  s["logical_error_given_code"], s["infidelity_kept"])
    elif a.exp == "crosscheck":
        _dump(engine_crosscheck(shots=a.shots), RES / "e4_engine_crosscheck.json")
    elif a.exp == "noise":
        _dump(noise_inventory(), RES / "noise_model.json")


if __name__ == "__main__":
    main()
