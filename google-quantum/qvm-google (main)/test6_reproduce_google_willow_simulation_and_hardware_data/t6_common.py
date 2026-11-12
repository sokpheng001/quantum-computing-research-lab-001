"""Test 6 shared helpers: paths, logging, reading Google's Zenodo release (arXiv:2512.13908 data,
doi 10.5281/zenodo.17872003), loading its circuits, and the two noise models we put on them.

The release is untrusted data: it is only READ (CSV with numpy/pandas, circuits with
cirq.read_json + stimcirq's resolver, which builds cirq objects and runs no code). Scripts live in
this folder, data in references/zenodo_17872003/. Run every script with `python -I`.
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                       # google-quantum/
QVM_DIR = HERE.parent                        # qvm-google (main)/
for p in (str(ROOT), str(QVM_DIR)):
    if p not in sys.path:
        sys.path.append(p)                   # appended, so stdlib/site-packages win (python -I safe)

ZEN = HERE / "references" / "zenodo_17872003"
RES = HERE / "results"
FIG = HERE / "figures"
LOGS = HERE / "logs"
for d in (RES, FIG, LOGS):
    d.mkdir(exist_ok=True)
KST = timezone(timedelta(hours=9))

# experiment folders of the release
EXP = {
    "fig2/injection": ZEN / "fig2/fig2/injection",
    "fig2/cultivation": ZEN / "fig2/fig2/cultivation",
    "fig2/simulation": ZEN / "fig2/fig2/simulation",
    "fig3/injection": ZEN / "fig3/fig3/injection",
    "fig3/without_idle_rounds": ZEN / "fig3/fig3/without_idle_rounds",
    "fig3/with_idle_rounds": ZEN / "fig3/fig3/with_idle_rounds",
    "fig3/with_idle_rounds_zoom": ZEN / "fig3/fig3/with_idle_rounds_zoom",
    "fig3/simulation": ZEN / "fig3/fig3/simulation",
    "fig3/simulation_zoom": ZEN / "fig3/fig3/simulation_zoom",
    "fig4/injection_N=2": ZEN / "fig4/fig4/injection_N=2",
    "fig4/cultivation_N=2": ZEN / "fig4/fig4/cultivation_N=2",
    "fig4/cultivation_N=3": ZEN / "fig4/fig4/cultivation_N=3",
    "fig4/simulation_injection_N=2": ZEN / "fig4/fig4/simulation_injection_N=2",
}
T_THETA = 0.125   # theta is in turns of the injected rotation Z**(2 theta): 0.125 -> Z**0.25 = T (pi/4)


def kst_now() -> str:
    return datetime.now(KST).strftime("%b %d, %I:%M %p KST")


def log(msg: str, name="t6.log") -> None:
    line = f"[{kst_now()}] {msg}"
    print(line, flush=True)
    with open(LOGS / name, "a") as f:
        f.write(line + "\n")


def one_in(r: float) -> str:
    if r is None or not r or (isinstance(r, float) and math.isnan(r)):
        return "none"
    return f"1 in {1 / r:,.0f}"


def pct(x: float, nd=1) -> str:
    return f"{100 * x:.{nd}f} %"


def ci_prop(k: int, n: int):
    """Clopper-Pearson 95 % interval for k of n."""
    from scipy.stats import beta
    if n == 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return (lo, hi)


def circuit_files(exp: str, basis: str):
    d = EXP[exp]
    for cj, st in ((f"cirq_circuit_{basis}.json", f"stim_{basis}.stim"), ("cirq_circuit.json", "stim.stim")):
        if (d / cj).exists():
            return d / cj, d / st
    raise FileNotFoundError(d)


def load_cirq(path: Path):
    import cirq
    import stimcirq
    return cirq.read_json(str(path), resolvers=[*cirq.DEFAULT_RESOLVERS, stimcirq.JSON_RESOLVER])


def load_stim(path: Path):
    import stim
    return stim.Circuit.from_file(str(path))


def save_json(path: Path, obj) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=float))
    tmp.replace(path)


def load_json(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


# ---------------------------------------------------------------- noise models on the as-run circuit

def _is_annotation(op) -> bool:
    import cirq
    return not cirq.has_unitary(op) and not cirq.is_measurement(op) and not isinstance(
        op.gate, cirq.ResetChannel) if op.gate is not None else True


def si1000_circuit(c, p: float):
    """SI1000 (Gidney et al., Quantum 5, 605) on the as-run cirq circuit, the model Google's Fig. 2
    kraus-sim used (p = 0.30 %). Per moment: CZ -> 2q depolarising p; any other 1q gate (H, echo
    Paulis, Cliffords, Z rotations) -> depolarising p/10; idle qubits -> p/10, or 2p in a moment
    with a measurement or reset; measurement -> flip 5p before it; reset -> X flip 2p after it.
    Qubits measured for the last time get no further noise (nothing follows them)."""
    import cirq
    qubits = sorted(c.all_qubits())
    out = cirq.Circuit()
    for m in c:
        ops = [op for op in m if not _is_annotation(op)]
        anns = [op for op in m if _is_annotation(op)]
        resonator = any(cirq.is_measurement(op) or isinstance(op.gate, cirq.ResetChannel) for op in ops)
        busy = {q for op in ops for q in op.qubits}
        pre, post = [], []
        for op in ops:
            if cirq.is_measurement(op):
                pre += [cirq.bit_flip(5 * p).on(q) for q in op.qubits]
            elif isinstance(op.gate, cirq.ResetChannel):
                post += [cirq.bit_flip(2 * p).on(q) for q in op.qubits]
            elif len(op.qubits) == 2:
                post.append(cirq.depolarize(p, n_qubits=2).on(*op.qubits))
            else:
                post += [cirq.depolarize(p / 10).on(q) for q in op.qubits]
        idle = [q for q in qubits if q not in busy]
        post += [cirq.depolarize(2 * p if resonator else p / 10).on(q) for q in idle]
        if pre:
            out.append(cirq.Moment(pre))
        out.append(cirq.Moment(ops + anns))
        if post:
            out.append(cirq.Moment(post))
    return out


def qvm_ready(c):
    """Google's circuit in the gate forms the QVM noise model recognises (as in qvm_willow.py): every
    non-Z single-qubit gate as a PhasedXZGate (the noise model attaches 1q error only to PhasedXZ),
    Z rotations stay virtual Z (noiseless on Willow), CZ as is. Annotations dropped."""
    import cirq
    out = cirq.Circuit()
    for m in c:
        ops = []
        for op in m:
            if _is_annotation(op):
                continue
            if len(op.qubits) == 1 and cirq.has_unitary(op) and not isinstance(op.gate, cirq.ZPowGate):
                ops.append(cirq.PhasedXZGate.from_matrix(cirq.unitary(op)).on(op.qubits[0]))
            elif isinstance(op.gate, cirq.ZPowGate):
                ops.append(cirq.Z(op.qubits[0]) ** op.gate.exponent)
            else:
                ops.append(op)
        out.append(cirq.Moment(ops))
    return out


def measurement_record(result, c) -> np.ndarray:
    """Measurement bits in circuit order (keys '0', '1', ... as in Google's circuit), shots x M."""
    import cirq
    keys = [op.gate.key for m in c for op in m if cirq.is_measurement(op)]
    return np.concatenate([result.measurements[k] for k in keys], axis=1).astype(np.uint8)
