"""Figures of the QVM experiment (PNG only), from results/*.json.

    .venv/bin/python "qvm-google (main)/test1_fd3_circuits_vs_google_fig2/plots.py"

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
RES, FIG = HERE / "results", HERE / "figures"
ORDER = ["success03", "success04", "success00", "G4", "d3a6"]
LABEL = {"success03": "success03\n(main)", "success04": "success04", "success00": "success00",
         "G4": "G4\n(hardware ref.)", "d3a6": "d3a6\n(what if)"}
OI = dict(blue="#0072B2", orange="#E69F00", green="#009E73", red="#D55E00", purple="#CC79A7",
          sky="#56B4E9", grey="#777777")

plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor":
                     "white", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def _int(x, _pos=None):
    return f"{int(round(x)):,}"


def _one_in(x, _pos=None):
    if x <= 0:
        return ""
    return f"1 in {int(round(1 / x)):,}"


def fig_e3():
    e3 = json.loads((RES / "e3.json").read_text())["designs"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8))
    cats = [("single", "all single error events", OI["blue"], ""),
            ("all2", "all 2-fault configurations", OI["orange"], "//"),
            ("random2", "seeded random 2-fault sample", OI["green"], ".."),
            ("malignant2", "cliffordea's malignant 2-fault", OI["red"], "xx")]
    x = np.arange(len(ORDER))
    w = 0.2
    for i, (k, lab, col, h) in enumerate(cats):
        n = [e3[d]["summary"][k]["n"] for d in ORDER]
        ag = [e3[d]["summary"][k]["agree"] for d in ORDER]
        bars = a.bar(x + (i - 1.5) * w, [max(v, 0.8) if v else 0 for v in n], w, color=col,
                     hatch=h, edgecolor="black", linewidth=0.5, label=lab)
        for xi, nv, av in zip(x + (i - 1.5) * w, n, ag):
            if nv:
                a.text(xi, nv * 1.15, f"{100 * av / nv:.0f} %", ha="center", va="bottom",
                       fontsize=6.5, rotation=90)
    a.set_yscale("log")
    a.yaxis.set_major_formatter(FuncFormatter(_int))
    a.yaxis.set_minor_formatter(NullFormatter())
    a.set_ylim(1, 1e6)
    a.set_xticks(x, [LABEL[d] for d in ORDER])
    a.set_ylabel("configurations injected (log scale)")
    a.set_title("(a) Real-T fault injection: configurations and agreement\n"
                "with cliffordea (label = % agreeing)", fontsize=9)
    a.legend(fontsize=7, frameon=False, loc="upper left", ncol=2)

    # (b) kept configurations: benign / malignant, real T vs cliffordea, 1 and 2 faults
    groups = []
    for dname in ORDER:
        s = e3[dname]["summary"]
        for k, kl in (("single", "1"), ("all2", "2")):
            groups.append((dname, kl, s[k]["real"], s[k]["cliffordea"]))
    xs = np.arange(len(groups))
    for j, (src, col, h, mk) in enumerate((("real", OI["blue"], "", "o"),
                                          ("cliffordea", OI["orange"], "//", "s"))):
        ben = [g[2 + j].get("benign", 0) for g in groups]
        mal = [g[2 + j].get("malignant", 0) for g in groups]
        b.bar(xs + (j - 0.5) * 0.38, ben, 0.38, color=col, hatch=h, edgecolor="black",
              linewidth=0.5, label=f"kept, benign ({'real-T qsim' if src == 'real' else 'cliffordea'})")
        b.scatter(xs + (j - 0.5) * 0.38, [m if m else np.nan for m in mal], marker=mk, s=28,
                  color=OI["red"], edgecolor="black", zorder=3,
                  label=f"kept, malignant ({'real-T qsim' if src == 'real' else 'cliffordea'})")
    b.set_xticks(xs, [f"{g[1]}f" for g in groups], fontsize=7)
    for i, dname in enumerate(ORDER):
        b.text(2 * i + 0.5, -0.13, LABEL[dname], transform=b.get_xaxis_transform(),
               ha="center", va="top", fontsize=7)
    for i in range(1, len(ORDER)):
        b.axvline(2 * i - 0.5, color=OI["grey"], lw=0.5, ls=":")
    b.set_ylim(0, 75)
    b.set_ylabel("kept configurations")
    b.set_title("(b) Kept configurations: real-T qsim vs cliffordea", fontsize=9)
    b.legend(fontsize=6.5, frameon=False, ncol=2, loc="upper center")
    fig.tight_layout()
    fig.savefig(FIG / "e3_fault_injection_agreement.png", dpi=200)
    plt.close(fig)


def fig_e4():
    e4 = json.loads((RES / "e4.json").read_text())["results"]
    wn = json.loads((ROOT / "results" / "willow_noise.json").read_text())["designs"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.9))
    x = np.arange(len(ORDER))
    w = 0.26
    series = [("QVM (cirq_google willow_pink model)", OI["blue"], "", "o",
               [100 * e4[d]["acceptance"] for d in ORDER],
               [100 * e4[d]["acceptance_se"] for d in ORDER]),
              ("stim, calibration model", OI["orange"], "//", "s",
               [100 * wn[d]["models"]["calibration"]["mc"]["acceptance"] for d in ORDER],
               [100 * wn[d]["models"]["calibration"]["mc"]["se"] for d in ORDER]),
              ("stim, spec-sheet model", OI["green"], "..", "^",
               [100 * wn[d]["models"]["spec"]["mc"]["acceptance"] for d in ORDER],
               [100 * wn[d]["models"]["spec"]["mc"]["se"] for d in ORDER])]
    for i, (lab, col, h, mk, v, e) in enumerate(series):
        a.bar(x + (i - 1) * w, v, w, yerr=e, color=col, hatch=h, edgecolor="black",
              linewidth=0.5, label=lab, capsize=2)
    a.set_xticks(x, [LABEL[d] for d in ORDER])
    a.set_ylim(50, 85)
    a.set_ylabel("acceptance: no detector fired (%)")
    a.set_title("(a) Acceptance, QVM vs stim (error bars: 1 s.e.)", fontsize=9)
    a.legend(fontsize=7, frameon=False, loc="upper left")

    # (b) logical error per kept shot (ideal stabiliser postselection), QVM with 95 % CI
    for i, d in enumerate(ORDER):
        r = e4[d]["logical_error_given_code"]
        lo, hi = r["ci95"]
        if r["events"]:
            b.errorbar(i - 0.12, r["rate"], yerr=[[r["rate"] - lo], [hi - r["rate"]]], fmt="o",
                       color=OI["blue"], mec="black", capsize=3,
                       label="QVM, 95 % CI" if i == 0 else None)
        else:
            b.errorbar(i - 0.12, hi, yerr=[[hi * 0.4], [0]], uplims=True, fmt="v",
                       color=OI["blue"], mec="black", label="QVM, 95 % upper bound (0 events)")
        st = wn[d]["models"]["calibration"]
        b.scatter(i + 0.12, st["rate_T"], marker="s", color=OI["orange"], edgecolor="black",
                  zorder=3, label="stim calibration model, enumerated (mfc 3)" if i == 0 else None)
        b.scatter(i + 0.12, st["rate_T_mfc4"], marker="D", facecolor="white",
                  edgecolor=OI["orange"], zorder=3,
                  label="same, mfc 4" if i == 0 else None)
    b.set_yscale("log")
    b.set_yticks([1 / n for n in (10_000, 20_000, 50_000, 100_000, 200_000)])
    b.set_ylim(1 / 250_000, 1 / 8_000)
    b.yaxis.set_major_formatter(FuncFormatter(_one_in))
    b.yaxis.set_minor_formatter(NullFormatter())
    b.set_xticks(range(len(ORDER)), [LABEL[d] for d in ORDER])
    b.set_ylabel("T error per kept shot (log scale)")
    b.set_title("(b) Logical error per kept shot (ideal decode)", fontsize=9)
    h, l = b.get_legend_handles_labels()
    seen = {}
    for hh, ll in zip(h, l):
        seen.setdefault(ll, hh)
    b.legend(seen.values(), seen.keys(), fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "e4_acceptance_and_infidelity.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    if (RES / "e3.json").exists():
        fig_e3()
    if (RES / "e4.json").exists():
        fig_e4()
    print(sorted(p.name for p in FIG.iterdir()))
