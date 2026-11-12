"""Test 7, part E: WHERE the improvement comes from (mechanism proof, no noise sampling of the whole model).

E1  Same circuits, S-proxy vs real T (cliffordea exact, all fault pairs): Google's silent pairs exist only with T.
E2  One of Google's silent pairs injected as exact Paulis into Google's QVM circuit (no other noise):
    per-detector firing probability, probability that all detectors stay silent, and the logical state of the
    silent shots (ideal decode). Each fault alone is injected too.
E3  cs02 ablation (cliffordea exact): (a) as is, (b) the two flag detectors ignored (flags still in the circuit),
    (c) flag qubits removed entirely (= the bare fold tree). Malignant T pairs in each; for (b), which flag
    detector each pair fires in (a).
E4  The pairs of E3(b) injected into cs02 in the QVM with all detectors and with the flag detectors ignored.

    .venv/bin/python -u "<this file>"      (from google-quantum/; a few minutes)
Writes results/mechanism/mechanism.json and MECHANISM.md.
"""
import json
import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
Q = HERE.parent
ROOT = Q.parent
sys.path.insert(0, str(Q))
import numpy as np  # noqa: E402
import stim  # noqa: E402

import qvm_willow as QW  # noqa: E402
from cliffordea import accept, enum  # noqa: E402
from nnflags.verify import load_measurement  # noqa: E402

OUT = HERE / "results" / "mechanism"
OUT.mkdir(parents=True, exist_ok=True)
SHOTS = 40_000

BASE = {"G4_G6style": "results/g4/G4-G6style", "cont_success02": "results/continuing/success02"}


def register(name, prefix):
    QW.DESIGNS[name] = (ROOT / f"{prefix}.full.stim", ROOT / f"{prefix}.inner.stim", "CX", "test 7 mechanism")


for n, p in BASE.items():
    register(n, p)


# ---------------- cliffordea exact classification of all <= 2 fault configurations ----------------

def classify(name, states=("T", "S")):
    d = QW.load_design(name)
    m = load_measurement(d.full, d.native)
    noisy = enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=1e-3)
    an = accept.CliffordLogicalAnalyzer(data_indices=m.DATA_INDICES, stabilizer_generators=m.STABILIZER_GENERATORS,
                                        logical_s=m.LOGICAL_S)
    comb = enum.FaultCombinator(noisy)
    kept = comb.get_kept_effects(logical_analyzer=an, max_fault_count=2, cultivated_states=states)
    res = {}
    for s in states:
        mal = {}
        for effects in kept[s]:
            for p, fid, cfgs in effects.values():
                for cfg in cfgs:
                    if fid != 1:
                        mal[tuple(cfg)] = (float(p), float(fid))
        res[s] = mal
    return comb, res, d


def ev_str(d, ev):
    t, n, ts = ev
    if n == "E":
        body = " ".join(f"{x.pauli_type}{x.value}" for x in ts)
    else:
        body = f"{n[0] if n.endswith('_ERROR') else n} on q{ts[0].value}"
    return f"time slice {t}: {body}"


def role(d, q):
    if q in d.data:
        return "data"
    return "ancilla"


# ---------------- QVM exact-Pauli injection ----------------

def inject_stats(d, events, shots=SHOTS, ignore=()):
    import cirq
    inj, flips = QW.event_injection(d, events)
    c = QW.prep_circuit(d) + QW.main_circuit(d, inject=inj) + QW.decode_circuit(d)
    r = QW.qsim(seed=7).run(c, repetitions=shots)
    det = QW.detector_bits(d, r.measurements, flips)
    use = [i for i in range(det.shape[1]) if i not in ignore]
    silent = det[:, use].sum(axis=1) == 0
    dec = np.concatenate([r.measurements[f"d{j}"] for j in range(len(d.data))], axis=1)
    code = dec[:, :-1].sum(axis=1) == 0
    wrong = dec[:, -1] == 1
    return dict(shots=shots, fire_prob=det.mean(axis=0).round(4).tolist(), silent=float(silent.mean()),
                silent_in_code=int((silent & code).sum()), silent_in_code_wrong=int((silent & code & wrong).sum()))


# ---------------- cs02 variants ----------------

def write_variant(src_prefix, dst_prefix, drop_flag_detectors=False, drop_flags=False, flags=(10, 11)):
    for kind in ("full", "inner"):
        txt = (ROOT / f"{src_prefix}.{kind}.stim").read_text()
        c = stim.Circuit(txt)
        out = stim.Circuit()
        rec_q = []  # measured qubit per record (to identify detectors on flags)
        for ins in c.flattened():
            name = ins.name
            if name == "DETECTOR":
                qs = [rec_q[len(rec_q) + t.value] for t in ins.targets_copy()]
                if (drop_flag_detectors or drop_flags) and any(q in flags for q in qs if q is not None):
                    continue
                out.append(ins)
                continue
            if name in ("M", "MX", "MR", "MRX", "MPP"):
                if name == "MPP":
                    n_rec = len(str(ins).split()) - 1
                    rec_q += [None] * n_rec
                    out.append(ins)
                    continue
                ts = [t.value for t in ins.targets_copy()]
                keep = [q for q in ts if not (drop_flags and q in flags)]
                rec_q += [q for q in ts if q in keep] if drop_flags else ts
                if keep:
                    out.append(name, keep)
                continue
            if drop_flags and name in ("CX", "CZ"):
                ts = [t.value for t in ins.targets_copy()]
                pairs = [(a, b) for a, b in zip(ts[::2], ts[1::2]) if a not in flags and b not in flags]
                if pairs:
                    out.append(name, [x for pr in pairs for x in pr])
                continue
            if drop_flags and name in ("R", "RX", "H"):
                ts = [t.value for t in ins.targets_copy() if t.value not in flags]
                if ts:
                    out.append(name, ts)
                continue
            if drop_flags and name == "QUBIT_COORDS" and ins.targets_copy()[0].value in flags:
                continue
            out.append(ins)
        (ROOT / f"{dst_prefix}.{kind}.stim").write_text(str(out) + "\n")


def main():
    os.chdir(ROOT)
    R = {}
    lines = []

    # E1 -----------------------------------------------------------------------------------------
    combs = {}
    for name in BASE:
        comb, res, d = classify(name)
        combs[name] = (comb, res, d)
        R[f"E1_{name}"] = dict(fault_locations=comb.fault_count, malignant_T_pairs=len([c for c in res["T"] if len(c) == 2]),
                               malignant_T_single=len([c for c in res["T"] if len(c) == 1]),
                               malignant_S_pairs=len([c for c in res["S"] if len(c) == 2]),
                               malignant_S_single=len([c for c in res["S"] if len(c) == 1]))
        print("E1", name, R[f"E1_{name}"], flush=True)

    # E2 -----------------------------------------------------------------------------------------
    comb, res, d = combs["G4_G6style"]
    pairs = sorted(c for c in res["T"] if len(c) == 2)
    e2 = []
    for cfg in pairs:
        evs = [sorted(comb.index_to_events[i], key=QW._event_key)[0] for i in cfg]
        both = inject_stats(d, evs)
        alone = [inject_stats(d, [e], shots=4000) for e in evs]
        sig = [comb.circuit.get_signature_and_effect(e)[0].astype(int).tolist() for e in evs]
        e2.append(dict(cfg=list(cfg), events=[ev_str(d, e) for e in evs], pauli_signatures=sig,
                       accept_T_cliffordea=res["T"][cfg][0], in_S_proxy="malignant" if cfg in res["S"] else "not malignant",
                       qvm_pair=both, qvm_alone=alone))
        print("E2", cfg, e2[-1]["events"], "silent", both["silent"], "fires", both["fire_prob"], flush=True)
    R["E2_google_pairs"] = e2
    R["google_detectors"] = [list(x) for x in d.detectors]
    R["google_data"] = list(d.data)
    R["google_pos"] = {str(k): v for k, v in d.pos.items()}

    # E3 -----------------------------------------------------------------------------------------
    write_variant(BASE["cont_success02"], "results/continuing/success02_noflagdet", drop_flag_detectors=True)
    write_variant(BASE["cont_success02"], "results/continuing/success02_noflags", drop_flags=True)
    register("cs02_noflagdet", "results/continuing/success02_noflagdet")
    register("cs02_noflags", "results/continuing/success02_noflags")
    e3 = {}
    for name in ("cont_success02", "cs02_noflagdet", "cs02_noflags"):
        comb3, res3, d3 = classify(name, states=("T",))
        mal = sorted(c for c in res3["T"] if len(c) <= 2)
        e3[name] = dict(fault_locations=comb3.fault_count, detectors=len(d3.detectors),
                        malignant_T_le2=len(mal), malignant=[list(c) for c in mal])
        print("E3", name, e3[name]["fault_locations"], e3[name]["detectors"], e3[name]["malignant_T_le2"], flush=True)
    R["E3_cs02_ablation"] = e3

    # E4: the pairs that become silent when the flag detectors are ignored, injected into full cs02 -----------
    comb_b, res_b, d_b = classify("cs02_noflagdet", states=("T",))
    d_full = QW.load_design("cont_success02")
    flag_dets = [i for i, det in enumerate(d_full.detectors)
                 if any(d_full.meas_at.get(k) in det for k in d_full.meas_at if k[1] in (10, 11))]
    # flag detector indices of the full circuit: those whose records are flag measurements
    flag_recs = {r for (t, q), r in d_full.meas_at.items() if q in (10, 11)}
    flag_dets = [i for i, det in enumerate(d_full.detectors) if set(det) & flag_recs]
    e4 = []
    for cfg in sorted(c for c in res_b["T"] if len(c) == 2):
        evs = [sorted(comb_b.index_to_events[i], key=QW._event_key)[0] for i in cfg]
        # same physical events, now in the full cs02 circuit (identical gates; only detectors differ)
        full = inject_stats(d_full, evs)
        ign = inject_stats(d_full, evs, ignore=flag_dets)
        which = [i for i in flag_dets if full["fire_prob"][i] > 0]
        flag_name = {i: ("ZZ flag F10" if any(r in flag_recs and d_full.meas_at and
                                                 [q for (t, q), rr in d_full.meas_at.items() if rr == r][0] == 10
                                                 for r in d_full.detectors[i]) else "X flag F11") for i in flag_dets}
        e4.append(dict(cfg=list(cfg), events=[ev_str(d_full, e) for e in evs], with_all_detectors=full,
                       flag_detectors_ignored=ign, caught_by=[flag_name[i] for i in which]))
        print("E4", e4[-1]["events"], "silent all", full["silent"], "silent no-flag", ign["silent"],
              "caught by", e4[-1]["caught_by"], flush=True)
    R["E4_cs02_flag_catches"] = e4
    R["cs02_detectors"] = [list(x) for x in d_full.detectors]
    R["cs02_flag_detector_indices"] = flag_dets
    R["cs02_data"] = list(d_full.data)
    R["cs02_pos"] = {str(k): v for k, v in d_full.pos.items()}
    (OUT / "mechanism.json").write_text(json.dumps(R, indent=1, default=str))
    print("written", OUT / "mechanism.json")


if __name__ == "__main__":
    main()
