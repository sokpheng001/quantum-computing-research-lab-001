"""Test 6, retention-gap diagnosis: our SI1000 (p = 0.30 %) keeps more shots than Google's own released
simulation of the same Fig. 2 circuit, with every detector firing about 18 % less often.

This script (1) scans p for our SI1000 on the as-run circuit at the T angle, and (2) compares per-detector
firing rates with Google's simulated shots (fig2/simulation) and the hardware (fig2/cultivation), to find the
p at which our model reproduces Google's simulation, and whether one p fits all detectors (a uniform
noise-strength difference) or not (a difference in where noise is placed).

    .venv/bin/python -I "<this folder>/t6_gap_check.py" [--ps 0.003 0.0033 0.0036 0.0039] [--shots 60000]
Writes results/gap_check.json.
"""
import argparse
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import t6_common as C  # noqa: E402

THETA = C.T_THETA


def google_rates(exp: str, basis: str) -> dict:
    tot, n = None, 0
    for ch in pd.read_csv(C.EXP[exp] / "detection_events.csv", chunksize=1_000_000):
        s = ch[(ch.basis == basis) & np.isclose(ch.theta, THETA)]
        if len(s) == 0:
            continue
        a = s.iloc[:, 3:].to_numpy(np.int64)
        tot = a.sum(0) if tot is None else tot + a.sum(0)
        n += len(s)
        kept = (a.sum(1) == 0).sum()
        if "kept" not in locals():
            pass
    return dict(shots=n, rates=(tot / n).tolist())


def google_retention(exp: str, basis: str) -> float:
    k = n = 0
    for ch in pd.read_csv(C.EXP[exp] / "detection_events.csv", chunksize=1_000_000):
        s = ch[(ch.basis == basis) & np.isclose(ch.theta, THETA)]
        if len(s):
            a = s.iloc[:, 3:].to_numpy(np.int64)
            k += int((a.sum(1) == 0).sum())
            n += len(s)
    return k / n


def _run(args):
    p, basis, k, reps = args
    import cirq
    import qsimcirq
    cj, st = C.circuit_files("fig2/cultivation", basis)
    c = C.load_cirq(cj)
    conv = C.load_stim(st).compile_m2d_converter()
    run = C.si1000_circuit(cirq.resolve_parameters(c, {"theta": THETA}), p)
    res = qsimcirq.QSimSimulator(seed=zlib.crc32(f"gap:{p}:{basis}:{k}".encode())).run(run, repetitions=reps)
    det, _ = conv.convert(measurements=C.measurement_record(res, c).astype(np.bool_), separate_observables=True)
    return p, int(reps), det.sum(0).astype(int), int((det.sum(1) == 0).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ps", nargs="*", type=float, default=[0.003, 0.0033, 0.0036, 0.0039])
    ap.add_argument("--shots", type=int, default=60_000)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    from multiprocessing import get_context
    chunk = 2_000
    tasks = [(p, "X", k, chunk) for p in a.ps for k in range(a.shots // chunk)]
    acc = {p: [0, 0, 0] for p in a.ps}
    with get_context("fork").Pool(a.workers, maxtasksperchild=50) as pool:
        for p, n, fires, kept in pool.imap_unordered(_run, tasks):
            acc[p][0] += n
            acc[p][1] = fires + acc[p][1] if isinstance(acc[p][1], np.ndarray) else fires
            acc[p][2] += kept
    gs = google_rates("fig2/simulation", "X")
    hw = google_rates("fig2/cultivation", "X")
    g = np.array(gs["rates"])
    out = dict(theta=THETA, basis="X", google_sim=dict(gs, retention=google_retention("fig2/simulation", "X")),
               hardware=dict(hw, retention=google_retention("fig2/cultivation", "X")), ours={})
    for p in a.ps:
        n, fires, kept = acc[p]
        r = fires / n
        ratio = r / g
        out["ours"][f"{p}"] = dict(shots=n, retention=kept / n, rates=r.tolist(), ratio_to_google=ratio.tolist(),
                                   ratio_mean=float(ratio[:-1].mean()), ratio_spread=float(ratio[:-1].std()),
                                   sq_err_vs_google=float(((r - g) ** 2).sum()))
        C.log(f"gap check: p = {100 * p:.2f} %: retention {C.pct(kept / n)} (Google sim "
              f"{C.pct(out['google_sim']['retention'])}), detector ratio to Google mean {ratio[:-1].mean():.2f}, "
              f"spread {ratio[:-1].std():.2f}", name="gap.log")
    best = min(out["ours"], key=lambda k: out["ours"][k]["sq_err_vs_google"])
    out["best_p"] = float(best)
    C.save_json(C.RES / "gap_check.json", out)
    C.log(f"gap check done: best p = {100 * float(best):.2f} %", name="gap.log")


if __name__ == "__main__":
    main()
