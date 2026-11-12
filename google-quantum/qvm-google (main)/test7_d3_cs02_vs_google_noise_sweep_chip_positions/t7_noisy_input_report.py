"""Report for test 7 part D (noisy input): RESULTS_noisy_input.md + two PNG figures. Works on partial data.

    .venv/bin/python -I "<this file>"
"""
import datetime as dt
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scipy.stats import beta  # noqa: E402

HERE = Path(__file__).resolve().parent
Q = HERE.parent
RES = HERE / "results" / "noisy_input"
CH = RES / "chunks"
FIG = HERE / "figures"
T2 = Q / "test2_cs02_continuing_data_vs_google" / "results"
DES = ["G4_G6style", "cont_success02"]
LABEL = {"G4_G6style": "Google G4 G6-style", "cont_success02": "cs02 (ours)"}
COL = {"G4_G6style": "#D55E00", "cont_success02": "#0072B2"}
MARK = {"G4_G6style": "s", "cont_success02": "o"}
W_INJ, P_D, SI_P = 224, 0.001, 0.0036
KST = dt.timezone(dt.timedelta(hours=9))


def one_in(r):
    return "0" if not r else f"1 in {round(1 / r):,}"


def cp(k, n):
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = float(beta.ppf(0.975, k + 1, n - k)) if k < n else 1.0
    return lo, hi


def ratio_ci(k1, n1, k2, n2):
    if k1 == 0 or k2 == 0:
        return None
    r = (k1 / n1) / (k2 / n2)
    w = 1.96 * math.sqrt(1 / k1 + 1 / k2)
    return r, r * math.exp(-w), r * math.exp(w)


def load():
    agg = defaultdict(lambda: defaultdict(int))
    for p in CH.glob("*.json"):
        t = p.name.rsplit("__", 1)[0]
        c = json.loads(p.read_text())
        for k in ("shots", "kept", "kept_code", "kept_code_one", "all_code", "all_code_one"):
            agg[t][k] += c[k]
        agg[t]["chunks"] += 1
    return agg


def parse(t):
    d, model, phi, basis, w, pd = t.split("__")
    return dict(design=d, model=model, k=int(phi[3:]), basis=basis, w=int(w[1:]), pd=float(pd[2:]))


def perfect_input():
    out = {}
    for d in DES:
        r = json.loads((T2 / f"e4_{d}.json").read_text())["results"][d]
        out[d] = dict(shots=r["shots"], kept=r["kept"], kept_code=r["kept_code"],
                      kept_code_one=r["kept_code_logical_error"])
    return out


def main():
    agg = load()
    rows = {t: {**parse(t), **v} for t, v in agg.items()}
    now = dt.datetime.now(KST).strftime("%Y-%m-%d %I:%M %p KST")
    FIG.mkdir(exist_ok=True)

    # ---------- error per kept T at the T angle: conditions ----------
    conds = [("perfect input (test 2)", None)]
    conds += [(f"noisy input: 1 in {W_INJ} wrong + {100 * P_D:g} % per data qubit, Google QVM", ("qvm", W_INJ)),
              ("noisy input: 1 in 56 wrong + 0.1 % per data qubit, Google QVM", ("qvm", 56)),
              (f"noisy input: 1 in {W_INJ} wrong + 0.1 % per data qubit, SI1000 p = {100 * SI_P:g} %",
               (f"si1000@{SI_P}", W_INJ))]
    perf = perfect_input()
    table = []
    for label, key in conds:
        cell = {}
        for d in DES:
            if key is None:
                s = perf[d]
            else:
                t = f"{d}__{key[0]}__phi00__HXY__w{key[1]}__pd{P_D:g}"
                if t not in rows:
                    continue
                s = rows[t]
            cell[d] = s
        if len(cell) == 2:
            table.append((label, cell))

    L = [f"# Test 7, part D: noisy input to the double check (written {now})", "",
         "Question: earlier runs start the double check from a **perfect** encoded T state. Does cs02 still beat "
         "Google's double check when the input is **noisy**, as after injection on the chip?", "",
         "Setup (`t7_noisy_input.py`): the unencoded logical qubit is prepared at angle phi, then a logical "
         "depolarising error is applied **before** encoding (a valid but wrong code state, the failure mode of "
         "injection), at a strength giving Google's hardware wrong-state rate at the T angle (1 in 224, test 6, "
         "fig3/injection; or 1 in 56, fig3/without_idle_rounds); then the ideal encoder; then 0.1 % depolarising "
         "noise on each of the 7 data qubits; then the double check with real T gates under the noise model; then "
         "an ideal decode. The input noise is **identical for both circuits**. Kept = no detector fired; errors "
         "and Bloch components use kept shots in the code space, as in test 2 / MASTER_RESULTS.md. Only the "
         "double check is noisy apart from the input layer; this is not the full Fig. 2 flow (no noisy "
         "encoding circuit).", "",
         "## 1. Error per kept T state at the T angle", "",
         "| input / noise model | circuit | shots | acceptance | errors / kept in code | T error per kept T state "
         "(95 % CI) | cs02 better by (95 % CI) |", "|---|---|---|---|---|---|---|"]
    bars = []
    for label, cell in table:
        g, c = cell["G4_G6style"], cell["cont_success02"]
        rc = ratio_ci(g["kept_code_one"], g["kept_code"], c["kept_code_one"], c["kept_code"])
        rtxt = f"{rc[0]:.1f}× ({rc[1]:.1f}× to {rc[2]:.1f}×)" if rc else "-"
        for d in DES:
            s = cell[d]
            k, n = s["kept_code_one"], s["kept_code"]
            lo, hi = cp(k, n)
            L.append(f"| {label} | {LABEL[d]} | {s['shots']:,} | {100 * s['kept'] / s['shots']:.1f} % | "
                     f"{k:,} / {n:,} | {one_in(k / n)} ({one_in(hi)} to {one_in(lo) if lo else '0'}) | "
                     f"{rtxt if d == 'cont_success02' else ''} |")
            bars.append((label, d, k / n if n else 0, lo, hi))
    L.append("")

    # ---------- Bloch circle (P1) ----------
    circ = defaultdict(dict)
    for t, r in rows.items():
        if r["model"] == "qvm" and r["basis"] in ("X", "Y") and r["w"] == W_INJ:
            circ[(r["design"], r["k"])][r["basis"]] = r
    have_circle = any(len(v) == 2 for v in circ.values())
    if have_circle:
        L += ["## 2. Bloch circle and retention against the input angle (Google QVM, noisy input 1 in 224)", "",
              "Our frame: the T state is the +1 eigenstate of (X + Y)/√2, so it sits at ⟨X⟩ = ⟨Y⟩ = 0.707 "
              "(Google's Fig. 2 uses an equivalent rotated frame with X and Z). phi = input angle on the equator, "
              "T at phi = π/4.", "",
              "| phi (π) | circuit | shots (X + Y) | retention | ⟨X⟩_L | ⟨Y⟩_L | kept in code (X + Y) |",
              "|---|---|---|---|---|---|---|"]
        for k in range(24):
            for d in DES:
                v = circ.get((d, k), {})
                if len(v) < 2:
                    continue
                X, Y = v["X"], v["Y"]
                phi = 0.25 + 2 * k / 24
                ex = 1 - 2 * X["kept_code_one"] / X["kept_code"] if X["kept_code"] else float("nan")
                ey = 1 - 2 * Y["kept_code_one"] / Y["kept_code"] if Y["kept_code"] else float("nan")
                ret = (X["kept"] + Y["kept"]) / (X["shots"] + Y["shots"])
                L.append(f"| {phi % 2:.3f} | {LABEL[d]} | {X['shots'] + Y['shots']:,} | {100 * ret:.2f} % | "
                         f"{ex:.3f} | {ey:.3f} | {X['kept_code'] + Y['kept_code']:,} |")
        L.append("")
        fig_circle(circ)
    if bars:
        fig_error(table)
    L += ["## Figures", ""]
    if have_circle:
        L.append("- `figures/t7_noisy_input_circle.png`: (a) Bloch circle, (b) zoom near the T state, "
                 "(c) retention against the input angle.")
    if bars:
        L.append("- `figures/t7_noisy_input_error.png`: error per kept T state, perfect vs noisy input, both circuits.")
    L += ["", f"Chunks read: {sum(v['chunks'] for v in agg.values())} "
          f"({sum(v['shots'] for v in agg.values()):,} shots). Log: `logs/noisy_input.log`."]
    (HERE / "RESULTS_noisy_input.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def fig_circle(circ):
    fig, axs = plt.subplots(1, 3, figsize=(13.5, 4.6), gridspec_kw=dict(width_ratios=[1, 1, 1.25]))
    a, z, r = axs
    th = [2 * math.pi * i / 400 for i in range(401)]
    for ax in (a, z):
        ax.plot([math.cos(t) for t in th], [math.sin(t) for t in th], color="black", lw=1)
        ax.plot([-1, 1], [-1, 1], color="#bbbbbb", lw=0.8, ls=":")
        ax.plot([math.sqrt(0.5)], [math.sqrt(0.5)], marker="*", ms=16, mfc="#F0E442", mec="black", zorder=5)
    q = 1.5 / W_INJ
    sh = (1 - 4 * q / 3) * (1 - 4 * P_D / 3)  # rough shrink of the noisy input (logical + one data error)
    a.plot([sh * math.cos(t) for t in th], [sh * math.sin(t) for t in th], color="#999999", lw=1,
           label="noisy input (before the check)")
    ret = defaultdict(list)
    for d in DES:
        xs, ys, exs, eys = [], [], [], []
        for k in range(24):
            v = circ.get((d, k), {})
            if len(v) < 2:
                continue
            X, Y = v["X"], v["Y"]
            phi = math.pi / 4 + 2 * math.pi * k / 24
            ret[d].append((phi, (X["kept"] + Y["kept"]) / (X["shots"] + Y["shots"])))
            if X["kept_code"] < 20 or Y["kept_code"] < 20:
                continue
            ex = 1 - 2 * X["kept_code_one"] / X["kept_code"]
            ey = 1 - 2 * Y["kept_code_one"] / Y["kept_code"]
            xs.append(ex), ys.append(ey)
            exs.append(2 * math.sqrt(max(1 - ex * ex, 1e-12) / X["kept_code"]))
            eys.append(2 * math.sqrt(max(1 - ey * ey, 1e-12) / Y["kept_code"]))
        for ax in (a, z):
            ax.errorbar(xs, ys, xerr=exs, yerr=eys, fmt=MARK[d], ms=5, mfc=COL[d], mec="black", mew=0.5,
                        ecolor=COL[d], elinewidth=0.8, ls="", label=f"after double check: {LABEL[d]}")
    a.set(xlim=(-1.1, 1.1), ylim=(-1.1, 1.1), xlabel="⟨X⟩_L", ylabel="⟨Y⟩_L", aspect="equal")
    a.set_title("(a) logical state after the double check", loc="left", fontsize=10)
    a.legend(fontsize=7.5, loc="lower right", frameon=False)
    z.set(xlim=(0.66, 0.73), ylim=(0.66, 0.73), xlabel="⟨X⟩_L", ylabel="⟨Y⟩_L", aspect="equal")
    z.set_title("(b) zoom near the T state (star)", loc="left", fontsize=10)
    phis = [2 * math.pi * i / 400 for i in range(401)]
    r.plot([p / math.pi for p in phis], [(1 + math.cos(p - math.pi / 4)) / 2 for p in phis], color="#999999",
           lw=1, ls="--", label="noiseless check: (1 + cos(φ − π/4)) / 2")
    for d in DES:
        pts = sorted(((p % (2 * math.pi)) / math.pi, v) for p, v in ret[d])
        r.plot([p for p, _ in pts], [v for _, v in pts], marker=MARK[d], ms=4.5, color=COL[d], mec="black",
               mew=0.4, lw=1, label=LABEL[d])
    r.axvline(0.25, color="black", lw=0.6, ls=":")
    r.text(0.27, 0.95, "T", fontsize=9)
    r.set(xlim=(0, 2), ylim=(0, 1.02), xlabel="input angle φ (π)", ylabel="retention (no detector fired)")
    r.set_title("(c) retention against the input angle", loc="left", fontsize=10)
    r.legend(fontsize=7.5, frameon=False, loc="upper right")
    for ax in axs:
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.text(0.01, -0.03, f"Google QVM (willow_pink), real T. Input: logical error at Google's injection rate "
             f"(1 in {W_INJ} wrong at the T angle) + {100 * P_D:g} % depolarising per data qubit, identical for "
             "both circuits; ideal encoder and ideal decode. Points need ≥ 20 kept shots in the code space; bars = 2 s.e.",
             fontsize=7.5)
    fig.tight_layout()
    fig.savefig(FIG / "t7_noisy_input_circle.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_error(table):
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    n = len(table)
    for i, (label, cell) in enumerate(table):
        for j, d in enumerate(DES):
            s = cell[d]
            k, m = s["kept_code_one"], s["kept_code"]
            rate = k / m
            lo, hi = cp(k, m)
            x = i + (j - 0.5) * 0.36
            ax.bar(x, rate, width=0.34, color=COL[d], edgecolor="black", lw=0.5,
                   label=LABEL[d] if i == 0 else None)
            ax.errorbar(x, rate, yerr=[[rate - lo], [hi - rate]], color="black", lw=0.8, capsize=3)
            ax.text(x, hi * 1.08, one_in(rate), ha="center", va="bottom", fontsize=7, rotation=90)
        g, c = cell["G4_G6style"], cell["cont_success02"]
        rc = ratio_ci(g["kept_code_one"], g["kept_code"], c["kept_code_one"], c["kept_code"])
        if rc:
            ax.text(i, 2.2e-3, f"{rc[0]:.1f}×\n({rc[1]:.1f}–{rc[2]:.1f}×)", ha="center", fontsize=8)
    ax.set_yscale("log")
    ax.set_ylim(2e-6, 5e-3)
    ticks = [1e-5, 1e-4, 1e-3]
    ax.set_yticks(ticks, [f"1 in {round(1 / t):,}" for t in ticks])
    ax.set_xticks(range(n), [lbl.replace(", ", ",\n").replace(": ", ":\n") for lbl, _ in table], fontsize=7.5)
    ax.set_ylabel("T error per kept T state")
    ax.set_title("Double check with perfect vs noisy input (same input noise for both circuits)", loc="left",
                 fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "t7_noisy_input_error.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
