"""
Full-stack QEC + magic-state-cultivation workflow, runnable in simulation.

Diagram box                     -> what this script does
-------------------------------------------------------------------------------
Quantum circuit                 -> read OpenQASM 3 (Qiskit)
Compile                         -> transpile to Clifford + T, drop useless diagonal gates
T gates?                        -> count T gates, switch factory on/off
Normal QEC (surface code)       -> REAL Stim + PyMatching memory simulation at d = 3, 5,
                                   then extrapolate to the distance needed
Magic-state factory             -> cultivation error / discard rates from Gidney, Shutty &
                                   Jones (2024), Fig. 2 (p = 1e-3 and 5e-4 only)
Logical execution               -> ideal logical simulation (Statevector, small circuits)
                                   + logical errors injected at the rates found above
Readout + decode -> Result      -> answer histogram, success chance, resources

Limits (state them when you show results):
  * QEC is simulated as a surface-code MEMORY; logical gates (lattice surgery) are not
    simulated physically, only their duration is counted.
  * Cultivation is not re-simulated here; its published numbers are used.
  * A logical failure is modelled crudely as flipping one random measured bit.

Requires: pip install qiskit qiskit-qasm3-import stim pymatching numpy
"""

import math
import random
from collections import Counter

import numpy as np
import pymatching
import qiskit.qasm3
import stim
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector

try:
    from cultivation_plugin import cultivation_numbers   # runs / caches the paper's code
except ImportError:
    cultivation_numbers = None

CLIFFORD = {"id", "x", "y", "z", "h", "s", "sdg", "cx", "cz", "swap"}
T_GATES = {"t", "tdg"}
DIAGONAL = {"z", "s", "sdg", "t", "tdg"}

# (p, d1) -> (error of a kept T state, fraction of attempts discarded), end-to-end
CULTIVATION = {
    (1e-3, 3): (3e-6, 0.80),
    (1e-3, 5): (2e-9, 0.99),
    (5e-4, 5): (4e-11, 0.90),
}


# ---------------------------------------------------------------- 1-3. circuit side
def load(qasm: str) -> QuantumCircuit:
    return qiskit.qasm3.loads(qasm)


def compile_clifford_t(qc: QuantumCircuit) -> QuantumCircuit:
    out = transpile(qc, basis_gates=sorted(CLIFFORD | T_GATES), optimization_level=1)
    return drop_diagonal_before_measure(out)


def drop_diagonal_before_measure(qc: QuantumCircuit) -> QuantumCircuit:
    data, keep = list(qc.data), [True] * len(qc.data)
    for i, inst in enumerate(data):
        if inst.operation.name != "measure":
            continue
        q, j = inst.qubits[0], i - 1
        while j >= 0:
            prev = data[j]
            if q not in prev.qubits:
                j -= 1
                continue
            if prev.operation.name in DIAGONAL and len(prev.qubits) == 1 and keep[j]:
                keep[j] = False
                j -= 1
                continue
            break
    out = qc.copy_empty_like()
    for k, inst in enumerate(data):
        if keep[k]:
            out.append(inst)
    return out


def analyse(qc: QuantumCircuit) -> dict:
    counts = Counter(i.operation.name for i in qc.data)
    used = sorted({qc.find_bit(q).index for i in qc.data for q in i.qubits})
    measured = [qc.find_bit(i.qubits[0]).index for i in qc.data if i.operation.name == "measure"]
    return {
        "used_qubits": used,
        "measured": measured,
        "gates": dict(counts),
        "t_count": sum(counts[g] for g in T_GATES),
        "logical_depth": max(1, qc.depth()),
        "unsupported": sorted(g for g in counts if g not in CLIFFORD | T_GATES | {"measure", "barrier"}),
    }


# ---------------------------------------------------------------- 4. normal QEC (real sim)
def surface_code_memory(d: int, p: float, shots: int, seed: int = 1) -> float:
    """Logical error rate PER CYCLE of a rotated surface-code memory, from Stim + PyMatching."""
    circ = stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=d, rounds=d,
        after_clifford_depolarization=p, before_round_data_depolarization=p,
        before_measure_flip_probability=p, after_reset_flip_probability=p,
    )
    dem = circ.detector_error_model(decompose_errors=True)
    matcher = pymatching.Matching.from_detector_error_model(dem)
    sampler = circ.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(shots, separate_observables=True)
    pred = matcher.decode_batch(det)
    fails = int(np.sum(np.any(pred != obs, axis=1)))
    per_shot = max(fails, 0.5) / shots          # avoid zero (report as an upper-ish value)
    return 1 - (1 - per_shot) ** (1 / d), fails


def memory_sweep(p: float) -> dict:
    """Per-cycle errors at this p from run_memory.py's memory_results.csv (d -> (rate, failures))."""
    import csv
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_results.csv")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {int(r["d"]): (float(r["per_cycle"]), int(r["errors"])) for r in csv.DictReader(f)
                if math.isclose(float(r["p"]), p) and int(r["errors"]) > 0}


def qec_error_model(p: float, shots: int = 20000) -> dict:
    sweep = memory_sweep(p)
    if len(sweep) >= 2:                          # prefer the long sweep (~100 failures per point)
        source = "memory_results.csv"
        p_cycle = {d: e for d, (e, _) in sorted(sweep.items())}
        fails = {d: f for d, (_, f) in sorted(sweep.items())}
    else:
        source = f"quick simulation, {shots} shots"
        e3, f3 = surface_code_memory(3, p, shots)
        e5, f5 = surface_code_memory(5, p, shots)
        p_cycle, fails = {3: e3, 5: e5}, {3: f3, 5: f5}
    d_hi, d_lo = sorted(p_cycle)[-1], sorted(p_cycle)[-2]
    lam = max((p_cycle[d_lo] / p_cycle[d_hi]) ** (2 / (d_hi - d_lo)), 1.5)  # suppression per +2 distance
    return {"p_cycle": p_cycle, "fails": fails, "lambda": lam, "source": source}


def per_cycle_error(model: dict, d: int) -> float:
    if d in model["p_cycle"]:
        return model["p_cycle"][d]
    d_hi = max(model["p_cycle"])
    return model["p_cycle"][d_hi] / model["lambda"] ** ((d - d_hi) / 2)


# ---------------------------------------------------------------- 5. choose protection
def plan(info: dict, p: float, target_fail: float, model: dict) -> dict:
    n = max(1, len(info["used_qubits"]))
    t = info["t_count"]
    data_budget = target_fail / 2 if t else target_fail
    d = 3
    while True:
        cycles = d * (info["logical_depth"] + 2)  # ~d cycles per logical step + prep/readout
        data_fail = 1 - (1 - per_cycle_error(model, d)) ** (n * cycles)
        if data_fail <= data_budget or d >= 41:
            break
        d += 2
    result = {"d": d, "cycles": cycles, "data_fail": data_fail, "factory": None}
    if t:
        per_state = (target_fail / 2) / t
        opts = []
        for d1 in (3, 5):
            if cultivation_numbers:                    # plugin: cache, simulation or published
                try:
                    r = cultivation_numbers(p, d1)
                    opts.append((d1, (r["error"], r["discard"]), r.get("source", "published")))
                    continue
                except KeyError:
                    pass
            if (p, d1) in CULTIVATION:                 # built-in published table
                opts.append((d1, CULTIVATION[(p, d1)], "published"))
        pick = next(((d1, v, src) for d1, v, src in opts if v[0] <= per_state), None)
        result["factory"] = {
            "magic_states": t, "max_error_each": per_state,
            "d1": pick[0] if pick else None,
            "error_each": pick[1][0] if pick else None,
            "discard": pick[1][1] if pick else None,
            "attempts_per_state": 1 / (1 - pick[1][1]) if pick else None,
            "source": pick[2] if pick else None,
            "options": [{"d1": d1, "error": v[0], "discard": v[1], "source": src} for d1, v, src in opts],
        }
    return result


def physical_qubits(info: dict, pl: dict) -> dict:
    d = pl["d"]
    data = len(info["used_qubits"]) * (2 * d * d - 1)
    factory = (2 * 15 * 15 - 1) if pl["factory"] else 0
    routing = data // 2
    return {"data": data, "factory": factory, "routing": routing, "total": data + factory + routing}


# ---------------------------------------------------------------- 6-7. execute and report
def execute(qc: QuantumCircuit, info: dict, pl: dict, shots: int, seed: int = 7) -> dict:
    rng = random.Random(seed)
    bare = qc.remove_final_measurements(inplace=False)
    probs = Statevector(bare).probabilities_dict(qargs=info["measured"])
    outcomes, weights = list(probs), list(probs.values())
    t_fail = 0.0
    if pl["factory"] and pl["factory"]["error_each"] is not None:
        t_fail = 1 - (1 - pl["factory"]["error_each"]) ** info["t_count"]
    p_fail = 1 - (1 - pl["data_fail"]) * (1 - t_fail)
    counts, bad = Counter(), 0
    for _ in range(shots):
        bits = list(rng.choices(outcomes, weights)[0])
        if rng.random() < p_fail:                  # crude logical-failure model
            k = rng.randrange(len(bits))
            bits[k] = "1" if bits[k] == "0" else "0"
            bad += 1
        counts["".join(bits)] += 1
    return {"ideal": {str(k): round(float(v), 4) for k, v in probs.items() if v > 1e-12},
            "counts": dict(counts), "p_fail": p_fail, "failed_shots": bad}


def run(qasm: str, p: float = 1e-3, target_success: float = 0.999, shots: int = 1000):
    model = qec_error_model(p)
    qc = compile_clifford_t(load(qasm))
    info = analyse(qc)
    pl = plan(info, p, 1 - target_success, model)
    res = execute(qc, info, pl, shots)
    qubits = physical_qubits(info, pl)

    print("\n[Compile + Analyse]")
    print(f"  used qubits: {info['used_qubits']}  measured: {info['measured']}")
    print(f"  gates: {info['gates']}")
    print(f"  T count: {info['t_count']}")
    if info["unsupported"]:
        print(f"  WARNING, not Clifford+T (needs synthesis): {info['unsupported']}")
    print("\n[T gates?]  factory " + ("ON" if info["t_count"] else "OFF"))
    print("\n[Normal QEC]  (real Stim simulation at p = %.0e, from %s)" % (p, model["source"]))
    for d in model["p_cycle"]:
        print(f"  d={d}: logical error per cycle {model['p_cycle'][d]:.2e}  ({model['fails'][d]} failures)")
    if pl["d"] not in model["p_cycle"]:
        print(f"  d={pl['d']}: logical error per cycle {per_cycle_error(model, pl['d']):.2e}  "
              f"(extrapolated, suppression {model['lambda']:.1f} per +2 distance)")
    print(f"  chosen d = {pl['d']}, ~{pl['cycles']} cycles, data failure ~ {pl['data_fail']:.1e}")
    if pl["factory"]:
        f = pl["factory"]
        print("\n[Magic-state factory]  (cultivation numbers: simulated or published, per line)")
        print(f"  magic states needed: {f['magic_states']}, max error each: {f['max_error_each']:.1e}")
        for o in f["options"]:
            print(f"  option d1 = {o['d1']}: error {o['error']:.2e}, discard {o['discard']:.1%}  [{o['source']}]")
        if f["d1"]:
            print(f"  chosen d1 = {f['d1']}: error {f['error_each']:.2e}, "
                  f"discard {f['discard']:.1%}, ~{f['attempts_per_state']:.1f} attempts per state  [{f['source']}]")
        else:
            print("  no tabulated setting meets the target at this p")
    print("\n[Logical execution + Readout]")
    print(f"  ideal outcome probabilities: {res['ideal']}")
    print(f"  counts over {shots} shots: {res['counts']}")
    print("\n[Result]")
    print(f"  estimated success chance per run: {1 - res['p_fail']:.6f}")
    print(f"  physical qubits ~ {qubits}")
    return {"p": p, "target_success": target_success, "shots": shots,
            "t_count": info["t_count"], "gates": info["gates"], "measured": info["measured"],
            "qec": {"p_cycle": model["p_cycle"], "fails": model["fails"], "lambda": model["lambda"]},
            "plan": pl, "execution": res, "qubits": qubits}


EXAMPLES = {
    "useless T": """
OPENQASM 3.0;
include "stdgates.inc";
qubit[4] q; bit[4] c;
x q[0];
t q[0];
measure q[0] -> c[0];
""",
    "Toffoli AND": """
OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q; bit[3] c;
h q[0];
h q[1];
ccx q[0], q[1], q[2];
c = measure q;
""",
}

if __name__ == "__main__":
    import json
    import os
    outputs = {}
    for name, qasm in EXAMPLES.items():
        print("=" * 70, f"\nEXAMPLE: {name}\n" + "=" * 70)
        outputs[name] = run(qasm, p=1e-3, target_success=0.999, shots=1000)
        print()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline_results.json")
    with open(out, "w") as f:
        json.dump(outputs, f, indent=2, default=str)
    print(f"saved {out}")
