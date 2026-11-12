"""Test 6, steps 2 and 3: simulate Google's AS-RUN Fig. 2 circuits (released cirq circuits, real
injection rotation and real T gates) with our tools, and compare with Google's own simulated shots
(step 2) and with the Willow hardware shots (step 3).

Models (qsim state-vector trajectories, 12 qubits):
  ideal       noiseless reference
  si1000      SI1000 at p = 0.30 %, the model Google's Fig. 2 kraus-sim used   -> vs fig2/simulation
  qvm         Google's QVM noise for willow_pink (cirq_google NoiseModelFromGoogleNoiseProperties,
              as in qvm_willow.py)                                             -> vs fig2/cultivation (hardware)
Experiments: fig2/cultivation (X and Z tomography) at THETAS; fig2/injection at the T angle.
Detection events and the observable come from Google's released stim circuit (stim m2d converter),
exactly as checked against Google's own files in step 1. Kept = no detection event.

Chunked and resumable (results/sim_chunks/), 3 worker processes (memory-safe rule).
    .venv/bin/python -I "<this folder>/t6_sim.py" [--models si1000 qvm] [--workers 3]
Writes results/step23_sim.json.
"""
import argparse
import math
import sys
import time
import zlib
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import t6_common as C  # noqa: E402

P_SI1000 = 0.003
THETAS = [0.0, 0.0625, 0.125, 0.1875, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]
SHOTS = {"ideal": 4_000, "si1000": 100_000, "qvm": 100_000}
SHOTS_AT_T = {"ideal": 4_000, "si1000": 300_000, "qvm": 300_000}   # Google's sim/hardware: 300,000 per basis
INJ_SHOTS = {"ideal": 4_000, "si1000": 200_000, "qvm": 200_000}
CHUNK = 2_000
OUT = C.RES / "sim_chunks"


def injection_theta() -> float:
    """The released injection sweep uses its own theta grid; take the value closest to the T angle."""
    import pandas as pd
    th = pd.read_csv(C.EXP["fig2/injection"] / "detection_events.csv", usecols=["theta"], nrows=5_000_000)["theta"].unique()
    return float(th[np.argmin(np.abs(th - C.T_THETA))])


@lru_cache(maxsize=None)
def program(model: str, exp: str, basis: str, theta: float):
    import cirq
    cj, st = C.circuit_files(exp, basis)
    c = C.load_cirq(cj)
    conv = C.load_stim(st).compile_m2d_converter()
    cr = cirq.resolve_parameters(c, {"theta": theta})
    if model == "ideal":
        run = C.qvm_ready(cr)
    elif model == "si1000":
        run = C.si1000_circuit(cr, P_SI1000)
    elif model.startswith("si1000@"):          # SI1000 at another p, e.g. si1000@0.0036 (gap check)
        run = C.si1000_circuit(cr, float(model.split("@")[1]))
    elif model == "qvm":
        import cirq_google
        from cirq_google.engine import virtual_engine_factory as vef
        nm = cirq_google.NoiseModelFromGoogleNoiseProperties(vef.load_device_noise_properties("willow_pink"))
        q = C.qvm_ready(cr)
        run = cirq.Circuit(nm.noisy_moments(q, sorted(q.all_qubits())))
    else:
        raise ValueError(model)
    return c, run, conv


def _chunk(task):
    model, exp, basis, theta, k, reps, path = task
    import qsimcirq
    c, run, conv = program(model, exp, basis, theta)
    seed = zlib.crc32(f"{model}:{exp}:{basis}:{theta}:{k}".encode())
    t0 = time.time()
    res = qsimcirq.QSimSimulator(seed=seed).run(run, repetitions=reps)
    rec = C.measurement_record(res, c).astype(np.bool_)
    det, obs = conv.convert(measurements=rec, separate_observables=True)
    kept = det.sum(axis=1) == 0
    out = dict(shots=int(reps), kept=int(kept.sum()), o_kept=int(obs[kept, 0].sum()),
               o_all=int(obs[:, 0].sum()), det_fires=det.sum(axis=0).astype(int).tolist(),
               wall_s=time.time() - t0)
    C.save_json(Path(path), out)
    return out


def tasks(models):
    th_inj = injection_theta()
    todo = []
    for model in models:
        base = model.split("@")[0]
        plan = [("fig2/cultivation", b, t, SHOTS_AT_T[base] if t == C.T_THETA else SHOTS[base])
                for t in THETAS for b in ("X", "Z")]
        plan += [("fig2/injection", b, th_inj, INJ_SHOTS[base]) for b in ("X", "Z")]
        for exp, b, t, n in plan:
            for k in range(math.ceil(n / CHUNK)):
                p = OUT / model / f"{exp.replace('/', '_')}_{b}_{t:.6f}_{k:04d}.json"
                if not p.exists():
                    todo.append((model, exp, b, t, k, CHUNK, str(p)))
    return todo, th_inj


def summarize() -> dict:
    out = {}
    for mdir in sorted(OUT.glob("*")):
        groups = {}
        for p in mdir.glob("*.json"):
            parts = p.stem.split("_")
            exp = "/".join(parts[:2])
            b, t = parts[2], float(parts[3])
            g = groups.setdefault((exp, b, t), dict(shots=0, kept=0, o_kept=0, o_all=0, chunks=0))
            d = C.load_json(p)
            for key in ("shots", "kept", "o_kept", "o_all"):
                g[key] += d[key]
            g["chunks"] += 1
        rows = []
        for (exp, b, t), g in sorted(groups.items()):
            n, k = g["shots"], g["kept"]
            rows.append(dict(exp=exp, basis=b, theta=t, shots=n, kept=k, retention=k / n,
                             retention_ci95=C.ci_prop(k, n),
                             expectation_kept=1 - 2 * g["o_kept"] / k if k else None,
                             expectation_kept_se=2 * math.sqrt((g["o_kept"] / k) * (1 - g["o_kept"] / k) / k) if k else None))
        out[mdir.name] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=["ideal", "si1000", "qvm"])
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    for m in a.models:
        (OUT / m).mkdir(parents=True, exist_ok=True)
    todo, th_inj = tasks(a.models)
    C.log(f"steps 2-3: {len(todo)} chunks of {CHUNK} shots to run (models {a.models}; "
          f"injection theta {th_inj:.6f}), {a.workers} workers")
    from multiprocessing import get_context
    t0, done = time.time(), 0
    with get_context("fork").Pool(a.workers, maxtasksperchild=100) as pool:
        for _ in pool.imap_unordered(_chunk, todo):
            done += 1
            if done % 100 == 0 or done == len(todo):
                el = time.time() - t0
                C.log(f"steps 2-3: {done}/{len(todo)} chunks, {el / 60:.0f} min, "
                      f"about {el / done * (len(todo) - done) / 60:.0f} min left")
    C.save_json(C.RES / "step23_sim.json", dict(p_si1000=P_SI1000, injection_theta=th_inj, models=summarize()))
    C.log("steps 2-3 done")


if __name__ == "__main__":
    main()
