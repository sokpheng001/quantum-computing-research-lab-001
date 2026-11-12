"""Test 7, part F: one input error + one fault inside the double check (Google G4 G6-style vs cs02).

Question: the double check alone has fault distance 2 (Google) and 3 (cs02) from a perfect input. With a noisy
input (part D) both circuits get extra error. Can ONE input error plus ONE fault in the check give a silent,
wrong T state, in either circuit?

Input errors (24): logical X, Y, Z on the unencoded qubit before the ideal encoder (a valid but wrong code
state, injection's failure mode), and X, Y, Z on each of the 7 data qubits after the encoder.
Check faults: one representative error event of every distinct cliffordea fault (events with the same detector
signature and data effect act identically), plus "no fault". Measurement-flip faults are applied classically.
Each (input, fault) pair: Google's QVM circuit with real T gates, no other noise, ideal decode, 400 shots
(outcomes can be random once the input is wrong). Recorded: fraction of shots with no detector fired, in the
code space and with the wrong logical value ("silent wrong"). A pair is called malignant if any shot is silent
wrong; with 400 shots a probability of 1/64 or more is missed with chance below 0.2 %.

    .venv/bin/python -u "<this file>" [--workers 3] [--shots 400]
Writes results/input_plus_fault/{design}.json and RESULTS_input_plus_fault.md.
"""
import argparse
import json
import os
import sys
import time
import zlib
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
Q = HERE.parent
ROOT = Q.parent
sys.path.insert(0, str(Q))
import numpy as np  # noqa: E402

import qvm_willow as QW  # noqa: E402

OUT = HERE / "results" / "input_plus_fault"
BASE = {"G4_G6style": "results/g4/G4-G6style", "cont_success02": "results/continuing/success02"}
LABEL = {"G4_G6style": "Google G4 G6-style", "cont_success02": "cs02 (ours)"}
for n, p in BASE.items():
    QW.DESIGNS[n] = (ROOT / f"{p}.full.stim", ROOT / f"{p}.inner.stim", "CX", "test 7 input + fault")


def inputs(d):
    out = [("logical", None, P) for P in "XYZ"]
    out += [("data", q, P) for q in d.data for P in "XYZ"]
    return out


@lru_cache(maxsize=None)
def design(name):
    return QW.load_design(name)


@lru_cache(maxsize=None)
def faults(name):
    comb, _ = QW.cliffordea_faults(name)
    reps = [None] + [sorted(comb.index_to_events[i], key=QW._event_key)[0] for i in range(comb.fault_count)]
    return reps


def ev_str(ev):
    if ev is None:
        return "no check fault"
    t, n, ts = ev
    if n == "E":
        return f"slice {t}: " + " ".join(f"{x.pauli_type}{x.value}" for x in ts)
    return f"slice {t}: {n} q{ts[0].value}"


def circuit(d, inp, ev):
    import cirq
    kind, q, P = inp
    G = {"X": cirq.X, "Y": cirq.Y, "Z": cirq.Z}[P]
    lq = d.data_q[-1]
    prep = cirq.Circuit([cirq.H(lq), cirq.T(lq)])
    if kind == "logical":
        prep.append(G.on(lq))
    prep += cirq.Circuit(QW.encoder_ops(d))
    if kind == "data":
        prep.append(G.on(d.Q[q]))
    inj, flips = QW.event_injection(d, [ev]) if ev is not None else ({}, [])
    return prep + QW.main_circuit(d, inject=inj) + QW.decode_circuit(d), flips


def task(args):
    name, ii, fi, shots = args
    d = design(name)
    inp = inputs(d)[ii]
    ev = faults(name)[fi]
    c, flips = circuit(d, inp, ev)
    r = QW.qsim(seed=zlib.crc32(f"{name}:{ii}:{fi}".encode())).run(c, repetitions=shots)
    det = QW.detector_bits(d, r.measurements, flips)
    silent = det.sum(axis=1) == 0
    dec = np.concatenate([r.measurements[f"d{j}"] for j in range(len(d.data))], axis=1)
    code = dec[:, :-1].sum(axis=1) == 0
    wrong = dec[:, -1] == 1
    return dict(input=list(inp), input_index=ii, fault_index=fi, fault=ev_str(ev),
                silent=float(silent.mean()), silent_wrong=float((silent & code & wrong).mean()),
                silent_right=float((silent & code & ~wrong).mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--shots", type=int, default=400)
    a = ap.parse_args()
    os.chdir(ROOT)
    OUT.mkdir(parents=True, exist_ok=True)
    from multiprocessing import get_context
    summary = {}
    for name in BASE:
        d = design(name)
        nf = len(faults(name))
        tasks = [(name, ii, fi, a.shots) for ii in range(len(inputs(d))) for fi in range(nf)]
        t0 = time.time()
        print(f"[{QW.kst_now()}] {name}: {len(tasks)} (input, fault) pairs", flush=True)
        rows = []
        with get_context("fork").Pool(a.workers, maxtasksperchild=300) as pool:
            for k, r in enumerate(pool.imap_unordered(task, tasks, chunksize=8)):
                rows.append(r)
                if (k + 1) % 500 == 0:
                    print(f"[{QW.kst_now()}] {name}: {k + 1}/{len(tasks)}, {time.time() - t0:.0f} s", flush=True)
        rows.sort(key=lambda r: (r["input_index"], r["fault_index"]))
        (OUT / f"{name}.json").write_text(json.dumps(rows))
        mal = [r for r in rows if r["silent_wrong"] > 0]
        alone = [r for r in rows if r["fault_index"] == 0]
        summary[name] = dict(pairs=len(rows), check_faults=nf - 1, inputs=len(inputs(d)),
                             input_alone_silent_wrong=sum(r["silent_wrong"] > 0 for r in alone), malignant=mal)
        print(f"[{QW.kst_now()}] {name}: done, malignant pairs {len(mal)}", flush=True)
    report(summary, a.shots)


def report(S, shots):
    import datetime as dt
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %I:%M %p KST")
    L = [f"# Test 7, part F: one input error + one fault in the double check (written {now})", "",
         "Each of 24 input errors (logical X, Y, Z before encoding; X, Y, Z on each data qubit after encoding) "
         "combined with no fault and with every distinct single fault of the check; Google's QVM circuit, real T, "
         f"no other noise, ideal decode, {shots} shots per pair. 'Silent wrong' = no detector fired, in the code "
         "space, wrong logical value. Script `t7_input_plus_fault.py`.", "",
         "| circuit | check faults | pairs tested | input alone: silent wrong | input + 1 fault: silent wrong pairs |",
         "|---|---|---|---|---|"]
    for n, s in S.items():
        L.append(f"| {LABEL[n]} | {s['check_faults']} | {s['pairs']:,} | {s['input_alone_silent_wrong']} | "
                 f"{len([m for m in s['malignant'] if m['fault_index'] > 0])} |")
    for n, s in S.items():
        mal = [m for m in s["malignant"] if m["fault_index"] > 0]
        L += ["", f"## {LABEL[n]}: silent wrong (input, fault) pairs", ""]
        if not mal:
            L.append("None.")
            continue
        by = {}
        for m in mal:
            k = m["input"][0] + (f" {m['input'][2]}" if m["input"][0] == "logical" else f" {m['input'][2]} on q{m['input'][1]}")
            by.setdefault(k, []).append(m)
        L += ["| input error | pairs | largest silent-wrong probability |", "|---|---|---|"]
        for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
            L.append(f"| {k} | {len(v)} | {max(m['silent_wrong'] for m in v):.3f} |")
        L += ["", "| input error | check fault | silent | silent wrong |", "|---|---|---|---|"]
        for m in sorted(mal, key=lambda m: -m["silent_wrong"]):
            k = "logical " + m["input"][2] if m["input"][0] == "logical" else f"{m['input'][2]} on data q{m['input'][1]}"
            L.append(f"| {k} | {m['fault']} | {m['silent']:.3f} | {m['silent_wrong']:.3f} |")
    (HERE / "RESULTS_input_plus_fault.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    main()
