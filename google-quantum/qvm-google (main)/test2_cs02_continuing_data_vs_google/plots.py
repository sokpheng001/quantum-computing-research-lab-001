"""QVM figure for our final circuit cs02 vs Google's double check (PNG only).

    .venv/bin/python "qvm-google (main)/test2_cs02_continuing_data_vs_google/plots.py"

Designs: G4 as run in Fig. 2 (test 1: test1_fd3_circuits_vs_google_fig2/results/e3.json, e4.json), G4 G6-style = G4 with q7
not measured, as Google runs it in Fig. 4 (results/*_G4_G6style.json),
and cs02 (results/*_cont_success02.json). Stim calibration-model values
from ../results/continuing_validation.json, for comparison.

Plain academic style: white background, Okabe-Ito colours plus hatching and
markers, rates as % or "1 in N" (no e-notation).
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # google-quantum/
RES = HERE.parent / "test1_fd3_circuits_vs_google_fig2" / "results"  # G4 as run in Fig. 2 (test 1)
CRES, FIG = HERE / "results", HERE / "figures"
OI = dict(blue="#0072B2", orange="#E69F00", green="#009E73", red="#D55E00", grey="#777777")
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor":
                     "white", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

# key, label, (QVM e3 file, design name), (QVM e4 file, design name), stim name
DESIGNS = [
    ("G4", "G4 (Google,\nas run in Fig. 2)\nfault distance 2", (RES / "e3.json", "G4"),
     (RES / "e4.json", "G4"), "G4-CX"),
    ("G6s", "G4 G6-style (Google,\nas run in Fig. 4)\nfault distance 2",
     (CRES / "e3_G4_G6style.json", "G4_G6style"), (CRES / "e4_G4_G6style.json", "G4_G6style"),
     "G4-G6style"),
    ("cs02", "cs02 (ours)\nfault distance 3", (CRES / "e3_cont_success02.json", "cont_success02"),
     (CRES / "e4_cont_success02.json", "cont_success02"), "success02"),
]


def _one_in(x, _pos=None):
    return f"1 in {int(round(1 / x)):,}" if x > 0 else ""


def _load(path, key, name):
    return json.loads(path.read_text())[key][name] if path.exists() else None


def load():
    stim = json.loads((ROOT / "results" / "continuing_validation.json").read_text())["designs"]
    out = []
    for key, label, (f3, n3), (f4, n4), sname in DESIGNS:
        out.append(dict(key=key, label=label, e3=_load(f3, "designs", n3),
                        e4=_load(f4, "results", n4), stim=stim[sname]["willow"]["calibration"]))
    return out


def figure(ds, path):
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(13, 4.2), gridspec_kw=dict(width_ratios=[1.15, 1, 1]))
    x = np.arange(len(ds))
    labels = [d["label"] for d in ds]

    # (a) T error per kept T state: QVM with 95 % CI, stim calibration model enumerated
    for i, d in enumerate(ds):
        s = d["stim"]
        a.scatter(i + 0.14, s["rate_T"], marker="s", s=36, color=OI["orange"], edgecolor="black",
                  zorder=3, label="stim, Willow calibration model" if i == 0 else None)
        if d["e4"] is None:
            a.text(i - 0.14, 1 / 9_000, "QVM\nnot run", ha="center", fontsize=7, color=OI["grey"])
            continue
        r = d["e4"]["logical_error_given_code"]
        lo, hi = r["ci95"]
        a.errorbar(i - 0.14, r["rate"], yerr=[[r["rate"] - lo], [hi - r["rate"]]], fmt="o", ms=7,
                   color=OI["blue"], mec="black", capsize=3,
                   label="Google QVM (willow_pink), 95 % CI" if i == 0 else None)
        a.annotate(f"1 in {1 / r['rate']:,.0f}\n({r['events']} errors in\n"
                   f"{d['e4']['kept_code'] / 1e6:.2f} M kept)", (i - 0.14, r["rate"]),
                   xytext=(-8, 0), textcoords="offset points", ha="right", va="center", fontsize=6.5)
    a.set_yscale("log")
    a.set_yticks([1 / n for n in (10_000, 20_000, 50_000, 100_000, 200_000, 500_000)])
    a.set_ylim(1 / 500_000, 1 / 7_000)
    a.yaxis.set_major_formatter(FuncFormatter(_one_in))
    a.yaxis.set_minor_formatter(NullFormatter())
    a.set_xticks(x, labels, fontsize=7.5)
    a.set_xlim(-0.8, len(ds) - 0.5)
    a.set_ylabel("T error per kept T state (log scale, lower is better)")
    a.set_title("(a) Logical error per kept T state", fontsize=9)
    a.legend(fontsize=7, frameon=False, loc="lower left")

    # (b) acceptance: QVM vs stim calibration model, 1 s.e.
    w = 0.36
    qa = [100 * d["e4"]["acceptance"] if d["e4"] else 0 for d in ds]
    qe = [100 * d["e4"]["acceptance_se"] if d["e4"] else 0 for d in ds]
    sa = [100 * d["stim"]["mc"]["acceptance"] for d in ds]
    se = [100 * d["stim"]["mc"]["se"] for d in ds]
    b.bar(x - w / 2, qa, w, yerr=qe, capsize=2, color=OI["blue"], edgecolor="black", linewidth=0.5,
          label="Google QVM (willow_pink)")
    b.bar(x + w / 2, sa, w, yerr=se, capsize=2, color=OI["orange"], hatch="//", edgecolor="black",
          linewidth=0.5, label="stim, Willow calibration model")
    for xi, v in zip(x - w / 2, qa):
        if v:
            b.text(xi, v + 0.6, f"{v:.1f} %", ha="center", va="bottom", fontsize=7)
    for xi, v in zip(x + w / 2, sa):
        b.text(xi, v + 0.6, f"{v:.1f} %", ha="center", va="bottom", fontsize=7)
    b.set_xticks(x, labels, fontsize=7.5)
    b.set_ylabel("acceptance: no detector fired (%)")
    b.set_title("(b) Acceptance (error bars: 1 s.e.)", fontsize=9)
    b.set_ylim(0, 112)
    b.set_yticks(range(0, 101, 20))
    b.legend(fontsize=7, frameon=False, loc="upper center", ncol=2)

    # (c) real-T fault injection: kept-and-corrupted 2-fault configurations
    for j, (src, col, h, lab) in enumerate((("real", OI["blue"], "", "real T gates (qsim)"),
                                           ("cliffordea", OI["orange"], "//", "cliffordea"))):
        v = [d["e3"]["summary"]["all2"][src].get("malignant", 0) if d["e3"] else 0 for d in ds]
        c.bar(x + (j - 0.5) * w, v, w, color=col, hatch=h, edgecolor="black", linewidth=0.5,
              label=lab)
        for xi, vi, d in zip(x + (j - 0.5) * w, v, ds):
            if d["e3"]:
                c.text(xi, vi + 0.15, str(vi), ha="center", va="bottom", fontsize=8)
    for xi, d in zip(x, ds):
        if d["e3"]:
            s = d["e3"]["summary"]
            n = s["single"]["n"] + s["all2"]["n"]
            ag = s["single"]["agree"] + s["all2"]["agree"]
            c.text(xi, 9.2, f"agree:\n{ag:,} / {n:,}", ha="center", va="top", fontsize=6.5)
        else:
            c.text(xi, 1, "QVM\nnot run", ha="center", fontsize=7, color=OI["grey"])
    c.set_ylim(0, 10)
    c.set_xticks(x, labels, fontsize=7.5)
    c.set_ylabel("2-fault configurations kept with a wrong T state")
    c.set_title("(c) Fault injection with real T gates (all 1- and 2-fault\n"
                "configurations); 0 = fault distance 3", fontsize=9)
    c.legend(fontsize=7, frameon=False, loc="center right")

    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    out = FIG / "qvm_cs02_vs_google.png"
    figure(load(), out)
    print(out)
