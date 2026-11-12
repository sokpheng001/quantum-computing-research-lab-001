"""Test 6, step 1: Google's own numbers recomputed from its released data with our code.

For every experiment folder of the Zenodo release and every (basis, theta):
  * shots, and kept = shots with no detection event (post-selection, as in the paper);
  * our detection events / observables recomputed from the raw measurements with the released stim
    circuit (stim's measurements-to-detections converter), compared bit-for-bit with Google's files
    (on a 200,000-shot sample per experiment, full files for the count checks);
  * logical expectation <O> = 1 - 2 * mean(observable) over kept shots, from raw observables, and the
    same from Google's corrected_observables.csv (their post-selected/decoded output): counts and sums
    must agree.

    .venv/bin/python -I "<this folder>/t6_step1_data.py" [--only fig2/cultivation ...]
Writes results/step1_data.json.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import t6_common as C  # noqa: E402

CHUNK = 500_000
SAMPLE = 200_000


def m2d_check(exp: str) -> dict:
    d = C.EXP[exp]
    m = pd.read_csv(d / "measurements.csv", nrows=SAMPLE)
    de = pd.read_csv(d / "detection_events.csv", nrows=SAMPLE)
    ro = pd.read_csv(d / "raw_observables.csv", nrows=SAMPLE)
    out = {}
    for b in sorted(m["basis"].unique()):
        sel = (m["basis"] == b).to_numpy()
        _, st = C.circuit_files(exp, b)
        conv = C.load_stim(st).compile_m2d_converter()
        det, obs = conv.convert(measurements=m.iloc[sel, 3:].to_numpy(np.bool_), separate_observables=True)
        out[b] = dict(rows=int(sel.sum()),
                      detectors_equal=bool((det == de.iloc[sel, 3:].to_numpy(np.bool_)).all()),
                      observable_equal=bool((obs[:, 0] == ro.iloc[sel, 3].to_numpy(np.bool_)).all()))
    return out


def aggregate(exp: str) -> dict:
    d = C.EXP[exp]
    acc = {}
    it_de = pd.read_csv(d / "detection_events.csv", chunksize=CHUNK)
    it_ro = pd.read_csv(d / "raw_observables.csv", chunksize=CHUNK)
    for de, ro in zip(it_de, it_ro):
        assert (de["shot"].to_numpy() == ro["shot"].to_numpy()).all() and \
               (de["theta"].to_numpy() == ro["theta"].to_numpy()).all(), "row order differs"
        kept = de.iloc[:, 3:].to_numpy(np.uint8).sum(axis=1) == 0
        o = ro.iloc[:, 3].to_numpy(np.int64)
        g = pd.DataFrame(dict(basis=de["basis"], theta=de["theta"], kept=kept, o_all=o, o_kept=o * kept))
        s = g.groupby(["basis", "theta"]).agg(shots=("kept", "size"), kept=("kept", "sum"),
                                              o_all=("o_all", "sum"), o_kept=("o_kept", "sum"))
        for (b, t), r in s.iterrows():
            a = acc.setdefault((b, float(t)), dict(shots=0, kept=0, o_all=0, o_kept=0))
            for k in a:
                a[k] += int(r[k])
    corr = {}
    for co in pd.read_csv(d / "corrected_observables.csv", chunksize=CHUNK):
        s = co.groupby(["basis", "theta"])["corrected_observables"].agg(["size", "sum"])
        for (b, t), r in s.iterrows():
            a = corr.setdefault((b, float(t)), [0, 0])
            a[0] += int(r["size"])
            a[1] += int(r["sum"])
    rows = []
    for (b, t), a in sorted(acc.items()):
        n, k = a["shots"], a["kept"]
        cn, cs = corr.get((b, t), [0, 0])
        rows.append(dict(basis=b, theta=t, shots=n, kept=k, retention=k / n,
                         retention_ci95=C.ci_prop(k, n),
                         obs_mean_kept=a["o_kept"] / k if k else None,
                         expectation_kept=1 - 2 * a["o_kept"] / k if k else None,
                         expectation_all=1 - 2 * a["o_all"] / n,
                         corrected_rows=cn, corrected_sum=cs,
                         corrected_expectation=1 - 2 * cs / cn if cn else None,
                         corrected_is_postselected_raw=(cn == k and cs == a["o_kept"])))
    return dict(rows=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    outp = C.RES / "step1_data.json"
    out = C.load_json(outp, {})
    for exp in (a.only or list(C.EXP)):
        if exp in out and not a.only:
            continue
        C.log(f"step 1: {exp}: m2d check + aggregation")
        r = dict(m2d=m2d_check(exp), **aggregate(exp))
        out[exp] = r
        C.save_json(outp, out)
        rows = r["rows"]
        tot = sum(x["shots"] for x in rows)
        kept = sum(x["kept"] for x in rows)
        ok = all(x["corrected_is_postselected_raw"] for x in rows)
        C.log(f"step 1: {exp}: {tot:,} shots, kept {kept:,} ({C.pct(kept / tot)}), "
              f"m2d {r['m2d']}, corrected file = post-selected raw for every (basis, theta): {ok}")
    C.log("step 1 done")


if __name__ == "__main__":
    main()
