"""Test 5, B4 cross-check: Clifft sampling (real T) vs cliffordea's exact count under SI1000, p = 0.5 %,
for Gidney's d5a19, Chan's d5a19f3 and our best two circuits (by the SI1000 p = 0.23 % first pass).

Separate from b4_real_noise.py so it can run beside the one-at-a-time retry without both writing
results/b4/b4.json: it only READS b4.json and writes results/b4/b4_clifft.json.

    .venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b4_clifft_check.py" [--threads 3]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b4_real_noise as B4  # noqa: E402  (sets sys.path / cwd)

from nnflags import willow_noise as WN  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--shots", type=int, default=2_000_000_000)
    ap.add_argument("--mfc", type=int, default=4)
    a = ap.parse_args()
    res = json.loads((B4.RES / "b4.json").read_text())
    ours = sorted([n for n, v in res.items() if n.startswith("seed") and "si1000_0.0023" in v["models"]],
                  key=lambda n: res[n]["models"]["si1000_0.0023"]["rate"])
    names = ["d5a19", "d5a19f3"] + ours[:2]
    ds = B4.designs()
    cal = WN.load_calibration()
    outp = B4.RES / "b4_clifft.json"
    out = json.loads(outp.read_text()) if outp.exists() else {}
    for n in names:
        if n in out:
            continue
        d = ds[n]
        d5 = dict(d, emb=d["emb"] or {q: (0, 0) for q in range(d["inner"].num_qubits)})
        ex = B4.exact(d5, "si1000_0.005", cal, a.mfc)
        cl = B4.clifft_check(d, 0.005, a.shots, a.threads)
        out[n] = dict(label=d["label"], exact_rate=ex["rate"], exact_mfc=a.mfc, exact_acceptance=ex["acceptance"], clifft=cl)
        e = cl["error"]
        B4.log(f"clifft {n}: {e['events']} errors / {e['of']:,} = {B4.one_in(e['rate'])} "
               f"(95 % CI {B4.one_in(e['ci95'][1])} to {B4.one_in(e['ci95'][0])}) vs exact {B4.one_in(ex['rate'])}")
        outp.write_text(json.dumps(out, indent=1, default=str))
    B4.log("clifft check done")


if __name__ == "__main__":
    main()
