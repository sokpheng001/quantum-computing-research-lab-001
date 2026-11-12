"""
Regenerate figures F1-F5 (PNG + PDF in figures/) from saved results only:
  cultivation_results.json  (run_validation.py finalize)
  memory_results.csv        (run_memory.py)
  pipeline_results.json     (full_stack_sim.py)
  Magic state cultivation/stats.csv (the paper's published data, read-only)
No simulation is rerun.  python plot_results.py
"""

import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sinter

import cultivation_plugin as cp
from run_validation import clopper_pearson

HERE = cp.HERE
FIG = os.path.join(HERE, "figures")
# Categorical slots 1-4 of the dataviz reference palette (light mode), fixed order.
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, MUTED = "#1f1f1e", "#6b6a63"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": "#e4e3dc",
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 2, "lines.markersize": 7, "legend.frameon": False,
})


def save(fig, name: str, caption: str) -> None:
    fig.text(0.01, 0.005, caption, fontsize=8, color=MUTED, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, f"{name}.{ext}"), dpi=200)
    plt.close(fig)
    print(f"wrote figures/{name}.png and .pdf")


def load_json(name: str) -> dict:
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


# ------------------------------------------------------------------ F1 validation
def f1(cache: dict) -> None:
    stages = [("ungrown", "1e-03,3,ungrown"), ("end_to_end", "1e-03,3")]
    rows = [(st, cache.get(k)) for st, k in stages]
    rows = [(st, r) for st, r in rows if r and r.get("source") == "simulated"]
    if not rows:
        print("F1 skipped: no simulated validation results")
        return
    verdict = "PASS" if all(r["pass"] for _, r in rows) else "FAIL"
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.2))
    x = np.arange(len(rows))
    names = [{"ungrown": "ungrown\n(inject+cultivate)", "end_to_end": "end-to-end\n(+escape, gap ≥ %d dB)" % cp.GAP_CUTOFF_DB}[st] for st, _ in rows]
    for i, (st, r) in enumerate(rows):
        lo, hi = r["error_ci95"]
        if r["failures"]:
            ax1.errorbar(i - 0.12, r["error"], yerr=[[r["error"] - lo], [hi - r["error"]]],
                         fmt="o", color=BLUE, capsize=4, label="ours (simulated, 95% CI)" if i == 0 else None)
        else:
            ax1.errorbar(i - 0.12, hi, yerr=[[hi * 0.5], [0]], uplims=True, fmt="v", color=BLUE,
                         label="ours: upper limit (0 failures)" if i == 0 else None)
        ax1.plot(i + 0.12, r["paper_value"]["error"], "s", color=ORANGE, label="paper (Fig. 2 value)" if i == 0 else None)
        ax1.plot(i + 0.12, r["paper_stats_csv"]["error"], "D", mfc="white", color=ORANGE,
                 label="paper (stats.csv, same cut)" if i == 0 else None)
        ax1.fill_between([i - 0.3, i + 0.3], r["paper_value"]["error"] / 2, r["paper_value"]["error"] * 2,
                         color=ORANGE, alpha=0.10, lw=0, label="paper × [½, 2] (PASS band)" if i == 0 else None)
        dlo, dhi = r["discard_ci95"]
        ax2.bar(i - 0.17, 100 * r["discard"], 0.32, color=BLUE, label="ours (simulated)" if i == 0 else None)
        ax2.errorbar(i - 0.17, 100 * r["discard"], yerr=[[100 * (r["discard"] - dlo)], [100 * (dhi - r["discard"])]],
                     fmt="none", color=INK, capsize=3)
        ax2.bar(i + 0.17, 100 * r["paper_value"]["discard"], 0.32, color=ORANGE, label="paper (Fig. 2 value)" if i == 0 else None)
        ax2.plot(i + 0.17, 100 * r["paper_stats_csv"]["discard"], "D", mfc="white", color=INK,
                 label="paper (stats.csv, same cut)" if i == 0 else None)
    ax1.set_yscale("log")
    ax1.set_xticks(x, names)
    ax1.set_ylabel("logical error per kept T state")
    ax1.set_title("Logical error of kept T states")
    ax1.legend(fontsize=7.5, loc="upper left")
    ax2.set_xticks(x, names)
    ax2.set_ylabel("discard rate (% of attempts)")
    ax2.set_ylim(0, 100)
    ax2.set_title("Discard rate")
    ax2.legend(fontsize=7.5, loc="upper left")
    fig.suptitle(f"F1 · Validation vs paper at p = 0.1%, d1 = 3 — {verdict}", fontweight="bold")
    cap = "; ".join(f"{st}: {r['shots']:,} shots, {r['kept']:,} kept, {r['failures']} failures" for st, r in rows)
    save(fig, "F1_validation", f"Simulated (paper's own circuits + samplers, S-for-T ×2) vs published. Uniform depolarizing p = 0.1%, d1 = 3, b = Y. {cap}.")


# ------------------------------------------------------------------ F2 memory
def f2() -> None:
    path = os.path.join(HERE, "memory_results.csv")
    if not os.path.exists(path):
        print("F2 skipped: memory_results.csv missing")
        return
    with open(path) as f:
        rows = list(csv.DictReader(f))
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    for (d, color, m) in ((3, BLUE, "o"), (5, ORANGE, "s"), (7, AQUA, "^")):
        pts = sorted((r for r in rows if int(r["d"]) == d), key=lambda r: float(r["p"]))
        p = np.array([float(r["p"]) for r in pts])
        e = np.array([float(r["per_cycle"]) for r in pts])
        lo = np.array([float(r["per_cycle_lo"]) for r in pts])
        hi = np.array([float(r["per_cycle_hi"]) for r in pts])
        has = np.array([int(r["errors"]) > 0 for r in pts])
        ax.errorbar(p[has], e[has], yerr=[e[has] - lo[has], hi[has] - e[has]], fmt=m + "-", color=color,
                    capsize=3, label=f"d = {d}")
        if (~has).any():
            ax.errorbar(p[~has], hi[~has], yerr=[hi[~has] * 0.6, 0 * hi[~has]], uplims=True, fmt=m,
                        mfc="white", color=color, label=f"d = {d}: 0 failures (95% upper limit)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ticks = [2e-4, 5e-4, 1e-3, 2e-3, 5e-3]
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xticks(ticks, [f"{100 * t:g}%" for t in ticks])
    ax.set_xlabel("physical error rate p (per operation)")
    ax.set_ylabel("logical error per QEC cycle")
    ax.set_title("F2 · Rotated surface-code memory (Stim + PyMatching)")
    ax.axvline(1e-3, color=MUTED, lw=1, ls=":")
    ax.text(1.05e-3, ax.get_ylim()[0] * 3, "pipeline p", color=MUTED, fontsize=8)
    ax.legend(fontsize=8)
    total = sum(int(r["shots"]) for r in rows)
    save(fig, "F2_memory", f"Simulated. rotated_memory_z, rounds = d, uniform depolarizing p; MWPM decoding; ≤100 failures or ≤{max(int(r['shots']) for r in rows):,} shots per point ({total:,} shots total); 95% Clopper-Pearson intervals.")


# ------------------------------------------------------------------ F3 cost
def f3(cache: dict) -> None:
    cultiv, gen, _ = cp._paper_modules()
    stats = sinter.read_stats_from_csv_files(cp.STATS_CSV)
    fig, ax = plt.subplots(figsize=(11, 5.2))
    colors = {5e-4: BLUE, 1e-3: ORANGE, 2e-3: AQUA}
    base = {}

    def baseline(p, d1, stage):
        if (p, d1, stage) not in base:
            base[(p, d1, stage)] = cultiv.compute_expected_injection_growth_volume(
                cp.build_cultivation_circuit(p, d1, stage), discard_rate=0)
        return base[(p, d1, stage)]

    for s in stats:
        m = s.json_metadata
        if s.decoder == "desaturation" and m.get("c") == "end2end-inplace-distillation":
            p, d1 = m["p"], m["d1"]
            gs = cultiv.stat_to_gap_stats([s], rounding=1, func=lambda arg: sinter.AnonTaskStats(
                shots=arg.source.shots, discards=arg.at_least.discards + arg.less.shots, errors=arg.at_least.errors))
            xs, ys = [], []
            for g in gs:
                kept = g.shots - g.discards
                if kept and g.errors:
                    xs.append(baseline(p, d1, "end_to_end") * g.shots / kept)
                    ys.append(cp.T_OVER_S * g.errors / kept)
            ax.plot(xs, ys, "-" if d1 == 3 else "--", color=colors[p], lw=1.5,
                    label=f"end-to-end, p={p:g}, d1={d1} (gap sweep)")
        elif s.decoder == "perfectionist" and m.get("c") == "inject[unitary]+cultivate" and s.errors:
            p, d1 = m["p"], m["d1"]
            kept = s.shots - s.discards
            ax.plot(baseline(p, d1, "ungrown") * s.shots / kept, cp.T_OVER_S * s.errors / kept,
                    "o" if d1 == 3 else "s", color=colors[p], mfc="white", mew=2,
                    label=f"ungrown, p={p:g}, d1={d1}")
    for key, st in (("1e-03,3", "end_to_end"), ("1e-03,3,ungrown", "ungrown")):
        r = cache.get(key)
        if r and r.get("source") == "simulated" and r["kept"]:
            x = baseline(1e-3, 3, st) * r["shots"] / r["kept"]
            lo, hi = r["error_ci95"]
            label = f"ours, {st} p=0.001 d1=3" + (" (used by pipeline)" if st == "end_to_end" else "")
            if r["failures"]:
                ax.errorbar(x, r["error"], yerr=[[r["error"] - lo], [hi - r["error"]]], fmt="*", ms=15,
                            color=INK, mfc=YELLOW, capsize=3, label=label)
            else:
                ax.errorbar(x, hi, yerr=[[hi * 0.6], [0]], uplims=True, fmt="*", ms=15, color=INK, mfc=YELLOW,
                            label=label + " — 0 failures, 95% upper limit")
    for (p, d1) in ((1e-3, 5),):
        pub = cp.PUBLISHED[cp._key(p, d1)]
        ax.plot(baseline(p, d1, "end_to_end") / (1 - pub["discard"]), pub["error"], "P", ms=11,
                color=INK, mfc=YELLOW, label="published value used by pipeline (p=0.001, d1=5)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("expected qubit·rounds per kept T state (incl. retries)")
    ax.set_ylabel("logical error per kept T state")
    ax.set_title("F3 · Cultivation error vs cost")
    ax.legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(1.02, 1))
    save(fig, "F3_cost", "Published (stats.csv; S-for-T ×2) plus our simulated points (stars). Cost = cultiv.compute_expected_injection_growth_volume(circuit) / keep rate, as in the paper's tools/write_historical_data_csv.py. Uniform noise, b = Y, d2 = 15.")


# ------------------------------------------------------------------ F4 / F5 pipeline
def f4(pipe: dict) -> None:
    if not pipe:
        print("F4 skipped: pipeline_results.json missing")
        return
    fig, axes = plt.subplots(1, len(pipe), figsize=(5 * len(pipe), 4.2))
    for ax, (name, r) in zip(np.atleast_1d(axes), pipe.items()):
        ex = r["execution"]
        keys = sorted(set(ex["counts"]) | set(ex["ideal"]))
        counts = [ex["counts"].get(k, 0) for k in keys]
        ideal = [ex["ideal"].get(k, 0) for k in keys]
        x = np.arange(len(keys))
        ax.bar(x, counts, 0.6, color=BLUE, label="measured counts")
        lo = [clopper_pearson(c, r["shots"])[0] * r["shots"] for c in counts]
        hi = [clopper_pearson(c, r["shots"])[1] * r["shots"] for c in counts]
        ax.errorbar(x, counts, yerr=[np.array(counts) - lo, np.array(hi) - counts], fmt="none", color=INK, capsize=3)
        ax.plot(x, np.array(ideal) * r["shots"], "D", color=ORANGE, label="ideal probability × shots")
        ax.set_xticks(x, keys)
        ax.set_xlabel("measured bitstring")
        ax.set_ylabel(f"counts (of {r['shots']} shots)")
        f = r["plan"]["factory"]
        ax.set_title(f"{name}: T count {r['t_count']}, factory {'ON' if f else 'OFF'}, d = {r['plan']['d']}", fontsize=10)
        ax.legend(fontsize=8)
    fig.suptitle("F4 · Pipeline results for the example circuits", fontweight="bold")
    save(fig, "F4_pipeline", "Simulated logical execution (ideal statevector + crude logical-failure model) at p = 0.1%, target success 99.9%; error bars: 95% CI on counts. Factory numbers: see RESULTS_cultivation.md for simulated vs published.")


def f5(pipe: dict) -> None:
    if not pipe:
        print("F5 skipped: pipeline_results.json missing")
        return
    fig, ax = plt.subplots(figsize=(6, 4.4))
    names = list(pipe)
    x = np.arange(len(names))
    bottom = np.zeros(len(names))
    for part, color in (("data", BLUE), ("factory", ORANGE), ("routing", AQUA)):
        vals = np.array([pipe[n]["qubits"][part] for n in names], float)
        ax.bar(x, vals, 0.5, bottom=bottom, color=color, label=f"{part} qubits", edgecolor="white", linewidth=2)
        bottom += vals
    for i, t in enumerate(bottom):
        ax.text(i, t, f"{int(t):,}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, [f"{n}\n(d = {pipe[n]['plan']['d']})" for n in names])
    ax.set_ylabel("physical qubits")
    ax.set_title("F5 · Physical-qubit breakdown per example circuit")
    ax.legend(fontsize=8)
    save(fig, "F5_resources", "Pipeline estimate (full_stack_sim.physical_qubits): data = n·(2d²−1), factory = one 2·15²−1 patch when T count > 0, routing = data/2. p = 0.1%.")


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    cache = cp.load_cache()
    pipe = load_json("pipeline_results.json")
    f1(cache)
    f2()
    f3(cache)
    f4(pipe)
    f5(pipe)
