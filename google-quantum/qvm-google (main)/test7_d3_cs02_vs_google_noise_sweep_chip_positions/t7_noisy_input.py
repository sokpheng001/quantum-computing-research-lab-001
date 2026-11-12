"""Test 7, part D: noisy input to the double check (Google's G4 G6-style vs our cs02).

Earlier QVM runs start the double check from a PERFECT encoded T state. Here the input is noisy, the same
for both circuits, so that injection-like errors meet the double check as they would on the chip:

  1. unencoded logical qubit prepared at angle phi on the equator: H, then Z**(phi/pi)
     -> Bloch vector (cos phi, sin phi, 0); phi = pi/4 is the T state, the +1 eigenstate of (X+Y)/sqrt2
     (cliffordea's convention, as qvm_willow.prep_circuit);
  2. logical input error: depolarising q_L on that qubit BEFORE encoding = a valid but wrong code state,
     the failure mode of injection. At the T angle the wrong-state rate is 2 q_L / 3; we set it to Google's
     hardware value for injection, 1 in 224 (test 6, fig3/injection), or 1 in 56 (fig3/without_idle_rounds);
  3. ideal encoder (cliffordea's), then physical input error: depolarising p_d on each of the 7 data qubits;
  4. the double check with real T gates under a noise model: Google's QVM model for willow_pink
     (qvm_willow.noisy_main, unchanged) or SI1000 at p (test 6's cirq implementation, unchanged);
  5. ideal decode, measuring the logical qubit in basis H_XY (error per kept T), X or Y (Bloch circle).

Kept = no detector fired. Error / Bloch components use kept shots inside the code space (ideal decode:
6 stabiliser bits 0), exactly as in test 2 and MASTER_RESULTS.md.

    .venv/bin/python -u "<this file>" sanity
    .venv/bin/python -u "<this file>" run --part P1 [--workers 3]
Chunks (resumable) in results/noisy_input/chunks/.
"""
import argparse
import json
import math
import sys
import time
import zlib
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
Q = HERE.parent
ROOT = Q.parent
sys.path.insert(0, str(Q))
sys.path.insert(0, str(Q / "test6_reproduce_google_willow_simulation_and_hardware_data"))
import os  # noqa: E402

import numpy as np  # noqa: E402

import qvm_willow as QW  # noqa: E402

RES = HERE / "results" / "noisy_input"
CH = RES / "chunks"

# same registration as test 2 (run_qvm.py) and run_baseline_8M.sh
DESIGN_FILES = {"G4_G6style": "results/g4/G4-G6style", "cont_success02": "results/continuing/success02"}
LABEL = {"G4_G6style": "Google G4 G6-style", "cont_success02": "cs02 (ours)"}
for _n, _p in DESIGN_FILES.items():
    QW.DESIGNS[_n] = (ROOT / f"{_p}.full.stim", ROOT / f"{_p}.inner.stim", "CX", "test 7 noisy input")

W_INJ = 1 / 224   # Google hardware, fig3/injection, wrong-sign rate at the T angle (test 6)
W_INJ4 = 1 / 56   # Google hardware, fig3/without_idle_rounds (test 6)
P_D = 0.001       # physical input error per data qubit
SI_P = 0.0036     # SI1000 strength that reproduces Google's own simulation (test 6 gap check)
PHIS = [math.pi / 4 + 2 * math.pi * k / 24 for k in range(24)]

# part -> list of (model, phi, basis, w, p_d, shots)
PARTS = {
    "P1": [(m, phi, b, W_INJ, P_D, 20_000) for m in ("qvm",) for phi in PHIS for b in ("X", "Y")],
    "P2": [("qvm", math.pi / 4, "HXY", W_INJ, P_D, 8_000_000)],
    "P3": [("qvm", math.pi / 4, "HXY", W_INJ4, P_D, 4_000_000)],
    "P4": [(f"si1000@{SI_P}", math.pi / 4, "HXY", W_INJ, P_D, 4_000_000)],
}


def tag(design, model, phi, basis, w, pd):
    k = round((phi - math.pi / 4) / (2 * math.pi / 24)) % 24
    return f"{design}__{model}__phi{k:02d}__{basis}__w{round(1 / w) if w else 0}__pd{pd:g}"


def prep_noisy(d, phi, w, pd):
    import cirq
    lq = d.data_q[-1]
    ops = [cirq.H(lq), (cirq.Z ** (phi / math.pi)).on(lq)]
    if w:
        ops.append(cirq.depolarize(1.5 * w).on(lq))
    c = cirq.Circuit(ops) + cirq.Circuit(QW.encoder_ops(d))
    if pd:
        c.append(cirq.Moment(cirq.depolarize(pd).on(q) for q in d.data_q))
    return c


def decode(d, basis):
    import cirq
    lq = d.data_q[-1]
    c = cirq.Circuit(cirq.inverse(QW.encoder_ops(d)))
    rot = {"HXY": [cirq.T(lq) ** -1, cirq.H(lq)], "X": [cirq.H(lq)], "Y": [cirq.S(lq) ** -1, cirq.H(lq)]}[basis]
    c += cirq.Circuit(rot)
    c.append(cirq.Moment(cirq.measure(q, key=f"d{j}") for j, q in enumerate(d.data_q)))
    return c


@lru_cache(maxsize=None)
def noisy_check(name, model):
    import cirq
    d = QW.load_design(name)
    if model == "qvm":
        return QW.noisy_main(d)
    if model == "none":
        return QW.main_circuit(d)
    if model.startswith("si1000@"):
        import t6_common as T6
        return T6.si1000_circuit(QW.main_circuit(d), float(model.split("@")[1]))
    raise ValueError(model)


@lru_cache(maxsize=None)
def full_circuit(name, model, phi, basis, w, pd):
    d = QW.load_design(name)
    return prep_noisy(d, phi, w, pd) + noisy_check(name, model) + decode(d, basis)


def counts(d, meas):
    det = QW.detector_bits(d, meas)
    kept = det.sum(axis=1) == 0
    dec = np.concatenate([meas[f"d{j}"] for j in range(len(d.data))], axis=1)
    code = dec[:, :-1].sum(axis=1) == 0
    one = dec[:, -1] == 1
    return dict(shots=int(len(kept)), kept=int(kept.sum()), kept_code=int((kept & code).sum()),
                kept_code_one=int((kept & code & one).sum()),
                all_code=int(code.sum()), all_code_one=int((code & one).sum()))


def _chunk(args):
    name, model, phi, basis, w, pd, k, reps, path = args
    d = QW.load_design(name)
    seed = zlib.crc32(f"{tag(name, model, phi, basis, w, pd)}:{k}".encode())
    t0 = time.time()
    r = QW.qsim(seed=seed).run(full_circuit(name, model, phi, basis, w, pd), repetitions=reps)
    c = counts(d, r.measurements)
    c.update(chunk=k, seed=seed, wall_s=time.time() - t0, finished=QW.kst_now())
    Path(path).write_text(json.dumps(c))
    return c


def log(msg):
    line = f"[{QW.kst_now()}] {msg}"
    print(line, flush=True)
    with open(HERE / "logs" / "noisy_input.log", "a") as f:
        f.write(line + "\n")


def run(part, workers, chunk=5000):
    from multiprocessing import get_context
    CH.mkdir(parents=True, exist_ok=True)
    tasks = []
    for model, phi, basis, w, pd, shots in PARTS[part]:
        for name in DESIGN_FILES:
            t = tag(name, model, phi, basis, w, pd)
            n = min(chunk, shots)
            for k in range(math.ceil(shots / n)):
                p = CH / f"{t}__{k:05d}.json"
                if not p.exists():
                    tasks.append((name, model, phi, basis, w, pd, k, n, str(p)))
    log(f"{part}: {len(tasks)} chunks to run with {workers} workers")
    t0, done = time.time(), 0
    with get_context("fork").Pool(workers, maxtasksperchild=200) as pool:
        for _ in pool.imap_unordered(_chunk, tasks):
            done += 1
            if done % 100 == 0 or done == len(tasks):
                log(f"{part}: {done}/{len(tasks)} chunks, {time.time() - t0:.0f} s")


def sanity():
    """Noiseless input and check: retention (1 + cos(phi - pi/4)) / 2, kept state = T exactly
    (<X> = <Y> = 0.707, H_XY error 0). Noisy QVM check with perfect input reproduces test 2 E4
    statistics shape (small sample)."""
    out = {}
    for name in DESIGN_FILES:
        d = QW.load_design(name)
        for phi in (math.pi / 4, 0.0, math.pi / 2, 5 * math.pi / 4):
            row = {}
            for b in ("HXY", "X", "Y"):
                r = QW.qsim(seed=1).run(full_circuit(name, "none", phi, b, 0.0, 0.0), repetitions=4000)
                c = counts(d, r.measurements)
                row[b] = dict(retention=c["kept"] / c["shots"],
                              value=(1 - 2 * c["kept_code_one"] / c["kept_code"]) if c["kept_code"] else None,
                              in_code=c["kept_code"] / c["kept"] if c["kept"] else None)
            row["retention_ideal"] = (1 + math.cos(phi - math.pi / 4)) / 2
            out[f"{name} phi={phi:.4f}"] = row
            log(f"sanity {name} phi={phi:.3f}: retention {row['X']['retention']:.3f} "
                f"(ideal {row['retention_ideal']:.3f}), <X> {row['X']['value']}, <Y> {row['Y']['value']}, "
                f"<H_XY> {row['HXY']['value']}")
    (RES).mkdir(parents=True, exist_ok=True)
    (RES / "sanity.json").write_text(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sanity", "run"])
    ap.add_argument("--part", choices=list(PARTS))
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.chdir(ROOT)
    (HERE / "logs").mkdir(exist_ok=True)
    if a.cmd == "sanity":
        sanity()
    else:
        run(a.part, a.workers)


if __name__ == "__main__":
    main()
