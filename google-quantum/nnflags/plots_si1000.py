"""Figure for the SI1000 comparison (Google's noise model): figures/si1000_comparison.png.

(a) T error per kept T state ("1 in N", higher is better) against SI1000 strength p,
    cliffordea enumeration truncated at 4 faults, native CZ + H, double-check stage only.
(b) Acceptance at p = 0.23 % (Google's fitted value), stim Monte Carlo from results/si1000.json.

    .venv/bin/python -m nnflags.plots_si1000
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator

from nnflags import comparison as CMP
from nnflags import si1000 as S
from nnflags import willow_noise as WN
from nnflags.verify import load_measurement

P_SWEEP = (0.0005, 0.00075, 0.001, 0.0015, 0.002, 0.0023, 0.003)
# Okabe-Ito, fixed order by entity; markers and line styles as secondary encoding
SERIES = [("G4-CX", "G4 (Google, Fig. 2): fault distance 2", "#E69F00", "s", (0, (4, 2))),
          ("G4-G6style", "G4 G6-style (Google, Fig. 4 way): fault distance 2", "#56B4E9", "D", (0, (1, 1.5))),
          ("success03", "old success03: fault distance 3, 7 continuing conflicts", "#999999", "v", (0, (6, 2, 1, 2))),
          ("cs02", "cs02 (ours): fault distance 3, 0 conflicts", "#0072B2", "o", "-")]


def one_in(n):
    return f"1 in {n:,.0f}" if n < 1e6 else f"1 in {n / 1e6:g} million"


def sweep():
    ds = S.designs()
    out = {}
    for key, *_ in SERIES:
        d = ds[key]
        native = d["native"] if d["native"] is not None else WN.cx_to_native(d["inner"])
        m = load_measurement(d["full"], native)
        out[key] = []
        for p in P_SWEEP:
            en, _ = CMP.enumerated(d["full"], native, mfc=4, noisy=S.si1000(m.INNER_CIRCUIT, p), states=("T",))
            out[key].append(1 / en["custom"]["T"]["rate"])
        print(key, [f"{n:,.0f}" for n in out[key]], flush=True)
    return out


def main(out=Path("figures")):
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    N = sweep()
    Path("results/si1000_sweep.json").write_text(json.dumps(dict(p=P_SWEEP, one_in=N), indent=1))
    res = json.loads(Path("results/si1000.json").read_text())
    fig, (a, b) = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw=dict(width_ratios=[1.55, 1]))

    xs = [p * 100 for p in P_SWEEP]
    for key, label, col, mk, ls in SERIES:
        a.plot(xs, N[key], color=col, ls=ls, lw=2, marker=mk, ms=7, mec="white", mew=1.2, label=label)
    a.set_xscale("log")
    a.set_yscale("log")
    a.xaxis.set_major_locator(FixedLocator(xs))
    a.xaxis.set_minor_locator(NullLocator())
    a.set_xticklabels([f"{x:g}" for x in xs])
    yt = [1e5, 3e5, 1e6, 3e6, 1e7, 3e7, 1e8]
    a.yaxis.set_major_locator(FixedLocator(yt))
    a.yaxis.set_minor_locator(NullLocator())
    a.set_yticklabels(["100,000", "300,000", "1 million", "3 million", "10 million", "30 million", "100 million"])
    lo, hi = min(min(v) for v in N.values()), max(max(v) for v in N.values())
    a.set_ylim(lo / 1.6, hi * 1.6)
    a.axvline(0.23, color="#bbbbbb", lw=1, zorder=0)
    a.text(0.23, hi * 1.35, " p = 0.23 %\n (Google's fit)", fontsize=7.5, color="#555555", va="top")
    a.grid(axis="y", color="#e6e6e6", lw=0.8)
    a.set_xlabel("SI1000 noise strength p (%)")
    a.set_ylabel("T error per kept T state: 1 in N (higher is better)")
    a.set_title("(a) Error per kept T state under SI1000", loc="left", fontsize=10)
    i23 = P_SWEEP.index(0.0023)
    for key in ("G4-CX", "cs02"):
        a.annotate(one_in(round(N[key][i23], -3)), (0.23, N[key][i23]), xytext=(-58, -14) if key == "G4-CX" else (6, 6),
                   textcoords="offset points", fontsize=7.5, color="#333333")
    a.legend(loc="lower left", fontsize=7.5, frameon=False)

    keys = [k for k, *_ in SERIES]
    acc = [res[k]["0.0023"]["acceptance"] * 100 for k in keys]
    se = [res[k]["0.0023"]["mc"]["stderr"] * 100 if "stderr" in res[k]["0.0023"]["mc"] else 0 for k in keys]
    for i, (key, label, col, mk, ls) in enumerate(SERIES):
        b.bar(i, acc[i], width=0.6, color=col, edgecolor="white", linewidth=2,
              hatch=None if key == "cs02" else ["//", "..", "xx"][i % 3])
        b.text(i, acc[i] + 1.5, f"{acc[i]:.1f} %", ha="center", fontsize=8, color="#333333")
    b.set_xticks(range(len(keys)), ["G4\n(Fig. 2)", "G4\nG6-style", "old\nsuccess03", "cs02\n(ours)"], fontsize=8)
    b.set_ylim(0, 100)
    b.set_ylabel("Acceptance (% of shots kept)")
    b.grid(axis="y", color="#e6e6e6", lw=0.8)
    b.set_axisbelow(True)
    b.set_title("(b) Acceptance at p = 0.23 %", loc="left", fontsize=10)

    fig.text(0.01, -0.04,
             "Double-check stage only, native CZ + H at Willow positions. SI1000 (Gidney et al. 2021): CZ DEPOLARIZE2(p), "
             "1q gate and idle DEPOLARIZE1(p/10), idle during measurement/reset DEPOLARIZE1(2p), measurement flip 5p, "
             "reset X_ERROR(2p).\n(a) cliffordea enumeration truncated at 4 faults; (b) stim Monte Carlo, 4,000,000 shots "
             "per circuit (standard error below 0.03 %). Not comparable with the paper's whole-circuit error of about 1 in 10,000.",
             fontsize=7, color="#444444", ha="left", va="top")
    fig.tight_layout()
    fig.savefig(out / "si1000_comparison.png", dpi=200, bbox_inches="tight")
    print("wrote", out / "si1000_comparison.png")


if __name__ == "__main__":
    main()
