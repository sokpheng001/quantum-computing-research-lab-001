"""Test 7: make the d = 3 result (cs02) defence-ready. Three checks, all with real T:

 A. cs02 vs Google's d = 3 double checks (shown: Willow-runnable circuits only; Gidney d3a6 / Chan d3a6f2 computed, not shown), same noise models:
      Google G4 (Fig. 2, as run), Google G4 G6-style (Fig. 4 way), Gidney et al.'s original d3a6, Chan et al.'s
      flagged d3a6f2 (2 Z flags, fault distance 3, not nearest-neighbour), and our #0 (G6-fit).
      Models: uniform depolarising p = 0.1 % (cliffordea's / Chan's), SI1000 (Google's model) at p = 0.23 %,
      Willow spec, Willow calibration (per qubit, at each circuit's Willow placement; Gidney's and Chan's
      placements are the least-violating ones from earlier steps and are NOT Willow-valid).
 B. SI1000 sweep, p = 0.05 % ... 0.5 %: error per kept T state vs p, fitted slopes (fault distance 2 vs 3).
 C. Chip positions: cs02 and Google G4 G6-style at EVERY Willow placement (rigid moves of their layout) that
      keeps the continuing-data readout rule, under the Willow calibration model -> the spread over the chip.

Error per kept T state = cliffordea exact enumeration with real T up to --mfc faults (d = 3: 4 = two orders
beyond the leading term), as in tests 1-5 (validated against Google's QVM in test 1 and Clifft in test 4).
Acceptance = stim Monte Carlo. Native CZ + H circuits (nnflags.willow_noise.cx_to_native).

    .venv/bin/python "qvm-google (main)/test7_d3_cs02_vs_google_noise_sweep_chip_positions/t7_d3_benchmarks.py" --workers 4
    -> results/t7.json, RESULTS.md, figures/t7_*.png
"""
import argparse
import datetime as dt
import json
import math
import os
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

import stim

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from nnflags import comparison as CMP  # noqa: E402
from nnflags import constraints as C  # noqa: E402
from nnflags import continuing_validate as CV  # noqa: E402
from nnflags import willow_noise as WN  # noqa: E402
from nnflags.continuing_data import data_qubits  # noqa: E402
from nnflags.si1000 import si1000  # noqa: E402
from nnflags.verify import bundled_paths, load_measurement, verify  # noqa: E402
from nnflags.willow import WILLOW  # noqa: E402

RES = HERE / "results"
FIG = HERE / "figures"
SWEEP = [0.0005, 0.001, 0.0015, 0.0023, 0.003, 0.005]
SHOW = ["G4", "G4G6", "cs02", "g6fit00"]  # Willow-runnable circuits only (user, Nov 6: no Chan / Gidney d3a6)
MODELS_A = ["uniform_0.001", "si1000_0.0023", "spec", "calibration"]
LABEL_M = {"uniform_0.001": "uniform depolarising, p = 0.1 %", "si1000_0.0023": "SI1000, p = 0.23 % (Google's)",
           "spec": "Willow spec (medians)", "calibration": "Willow calibration (per qubit)"}


def kst():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%b %d, %I:%M %p KST")


def log(*a):
    print(f"[{kst()}]", *a, flush=True)


def designs():
    ref = CV.references()
    D = {}
    D["G4"] = dict(label="Google G4 (Fig. 2, as run)", full=ref["G4-CX"]["full"], inner=ref["G4-CX"]["inner"])
    D["G4G6"] = dict(label="Google G4 G6-style (Fig. 4 way)", full=ref["G4-G6style"]["full"], inner=ref["G4-G6style"]["inner"])
    for n, lab in (("d3a6", "Gidney et al. original (d3a6)"), ("d3a6f2", "Chan et al., 2 Z flags (d3a6f2, not NN)")):
        f, i = bundled_paths(n)
        D[n] = dict(label=lab, full=stim.Circuit.from_file(str(f)), inner=stim.Circuit.from_file(str(i)))
    D["cs02"] = dict(label="ours cs02", full=stim.Circuit.from_file("results/continuing/success02.full.stim"),
                     inner=stim.Circuit.from_file("results/continuing/success02.inner.stim"))
    p = "qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6/results/g6_search_d6n14/success00"
    D["g6fit00"] = dict(label="ours #0 (G6-fit)", full=stim.Circuit.from_file(p + ".full.stim"),
                        inner=stim.Circuit.from_file(p + ".inner.stim"))
    for n, d in D.items():
        d["emb"] = WN.placement(n if n in ("d3a6", "d3a6f2") else "x", d["inner"])[0]
    return D


def noisy_for(model, m_inner, emb, cal):
    if model.startswith("si1000_"):
        return si1000(m_inner, float(model.split("_")[1]))
    return WN.noisy_native(m_inner, WN.model_params(model, cal, emb), "symmetric")[0]


def exact(d, model, cal, mfc, emb=None, acc_shots=2_000_000):
    emb = d["emb"] if emb is None else emb
    if model.startswith("uniform_"):
        p = float(model.split("_")[1])
        r = verify(d["full"], d["inner"], max_fault_count=mfc, noise_level=p, states=("T",))
        from cliffordea import enum
        m = load_measurement(d["full"], d["inner"])
        acc = CMP.mc_acceptance(enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=p), acc_shots,
                                seed=zlib.crc32(model.encode()))["acceptance"]
        return dict(rate=r["error_rate_per_kept_shot"]["T"], acceptance=acc,
                    malignant={k: v["malignant"] for k, v in r["T"].items()})
    native = WN.cx_to_native(d["inner"])
    m = load_measurement(d["full"], native)
    noisy = noisy_for(model, m.INNER_CIRCUIT, emb, cal)
    en, _ = CMP.enumerated(d["full"], native, mfc=mfc, noisy=noisy, states=("T",))
    e = en["custom"]["T"]
    acc = CMP.mc_acceptance(noisy, acc_shots, seed=zlib.crc32(model.encode()))["acceptance"] if acc_shots else None
    return dict(rate=e["rate"], acceptance=acc)


_D, _CAL = None, None


def _task(args):
    global _D, _CAL
    kind, name, model, mfc, emb = args
    if _D is None:
        _D, _CAL = designs(), WN.load_calibration()
    try:
        r = exact(_D[name], model, _CAL, mfc, emb=emb, acc_shots=0 if kind == "C" else 2_000_000)
    except MemoryError:
        r = dict(error="out of memory")
    return kind, name, model, emb, r


def placements(d):
    """Every rigid Willow placement of the circuit's layout that keeps the continuing-data rule."""
    inner = d["inner"]
    data = tuple(sorted(data_qubits(inner)))
    out = []
    for sym, off, emb in C.grid_embeddings(inner, WILLOW):
        if not C.check_circuit(inner, emb, data_qubits=data, data_continue=True):
            out.append(emb)
    return out


def one_in(x):
    return f"1 in {1 / x:,.0f}" if x and x > 0 else "0"


def slope(pts):
    pts = [(math.log(p), math.log(r)) for p, r in pts if r and r > 0]
    mx = sum(x for x, _ in pts) / len(pts)
    my = sum(y for _, y in pts) / len(pts)
    return sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)


def report(R, D):
    L = [f"# Test 7: cs02 (d = 3) against Google's d = 3 double checks on Willow (written {kst()})", "",
         "Error per kept T state: cliffordea exact enumeration with real T (up to 4 faults); acceptance: stim Monte "
         "Carlo (2,000,000 shots). Native CZ + H circuits.", ""]
    names = [n for n in D if n in SHOW]
    for mo in MODELS_A:
        L += [f"## A. {LABEL_M[mo]}", "", "| circuit | error per kept T state | acceptance | cs02 is better by |", "|---|---|---|---|"]
        cs = R["A"].get("cs02", {}).get(mo, {}).get("rate")
        for n in names:
            r = R["A"].get(n, {}).get(mo)
            if not r or "rate" not in r:
                continue
            gain = f"{r['rate'] / cs:.1f}x" if cs and n != "cs02" else ""
            L.append(f"| {D[n]['label']} | {one_in(r['rate'])} | {100 * (r['acceptance'] or 0):.1f} % | {gain} |")
        L.append("")
    L += ["Only circuits that run on Willow are compared (Google's two versions and ours). Gidney's original d3a6 and "
          "Chan et al.'s flagged d3a6f2 were also computed (results/t7.json) but are not shown: neither can run on "
          "Willow (readout rule / non-nearest-neighbour gates).", "",
          "## B. SI1000 sweep", "", "| circuit | " + " | ".join(f"p = {100 * p:g} %" for p in SWEEP) + " | slope (p <= 0.23 %) |",
          "|---|" + "---|" * (len(SWEEP) + 1)]
    for n in names:
        row = R["B"].get(n, {})
        if not row:
            continue
        pts = [(p, row.get(str(p), {}).get("rate")) for p in SWEEP]
        s = slope([(p, r) for p, r in pts if p <= 0.0023 and r])
        L.append(f"| {D[n]['label']} | " + " | ".join(one_in(r) for _, r in pts) + f" | {s:.2f} |")
    L += ["", "Fault distance 2 gives slope -> 2 and fault distance 3 gives slope -> 3 as p -> 0.", ""]
    if R["C"]:
        L += ["## C. Chip positions (Willow calibration, every placement keeping the continuing-data rule)", "",
              "| circuit | placements | best | median | worst |", "|---|---|---|---|---|"]
        for n, rows in R["C"].items():
            rates = sorted(r["rate"] for r in rows if r.get("rate"))
            if rates:
                L.append(f"| {D[n]['label']} | {len(rates)} | {one_in(rates[0])} | {one_in(rates[len(rates) // 2])} | {one_in(rates[-1])} |")
        g = sorted(r["rate"] for r in R["C"].get("G4G6", []) if r.get("rate"))
        c = sorted(r["rate"] for r in R["C"].get("cs02", []) if r.get("rate"))
        if g and c:
            L += ["", f"Median gain cs02 vs Google G4 G6-style over the chip: {g[len(g) // 2] / c[len(c) // 2]:.1f}x; "
                  f"cs02's WORST placement vs Google's BEST: {g[0] / c[-1]:.1f}x."]
    L += ["", "![A](figures/t7_models.png)", "", "![B](figures/t7_si1000_sweep.png)", "", "![C](figures/t7_chip_positions.png)", ""]
    (HERE / "RESULTS.md").write_text("\n".join(L))


def figures(R, D):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, NullFormatter
    FIG.mkdir(exist_ok=True)
    col = {"G4": "#9a9a9a", "G4G6": "#555555", "d3a6": "#c9a227", "d3a6f2": "#d08a2c", "cs02": "#2a6db0", "g6fit00": "#6aa0d8"}
    fmt = FuncFormatter(lambda v, _: f"{v:,.0f}")
    # A
    fig, ax = plt.subplots(figsize=(7.6, 4.2), dpi=150)
    names = [n for n in D if n in R["A"] and n in SHOW]
    w = 0.8 / max(1, len(names))
    for i, n in enumerate(names):
        ys = [R["A"][n].get(mo, {}).get("rate") for mo in MODELS_A]
        xs = [k + (i - (len(names) - 1) / 2) * w for k in range(len(MODELS_A))]
        ax.bar(xs, [1 / y if y else 0 for y in ys], w * 0.9, color=col[n], label=D[n]["label"])
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(fmt)
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(range(len(MODELS_A)))
    ax.set_xticklabels([LABEL_M[m].replace(", ", ",\n").replace(" (", "\n(") for m in MODELS_A], fontsize=7)
    ax.set_ylabel("N in '1 in N' error per kept T state")
    ax.grid(True, axis="y", lw=0.4, color="#dddddd")
    ax.legend(fontsize=6.5, frameon=False, ncol=2)
    ax.set_title("d = 3 double checks, real T (higher = better)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "t7_models.png")
    plt.close(fig)
    # B
    fig, ax = plt.subplots(figsize=(6.2, 4.4), dpi=150)
    for n in names:
        row = R["B"].get(n, {})
        pts = [(100 * p, row.get(str(p), {}).get("rate")) for p in SWEEP if row.get(str(p), {}).get("rate")]
        if pts:
            ax.plot([x for x, _ in pts], [y for _, y in pts], marker="o", ms=3.5, lw=1.5, color=col[n], label=D[n]["label"])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([100 * p for p in SWEEP])
    ax.set_xticklabels([f"{100 * p:g}" for p in SWEEP])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"1 in {1 / v:,.0f}"))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("SI1000 noise strength p (%)")
    ax.set_ylabel("error per kept T state")
    ax.grid(True, lw=0.4, color="#dddddd")
    ax.legend(fontsize=6.5, frameon=False)
    ax.set_title("d = 3, real T, SI1000: the gap grows as p falls", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "t7_si1000_sweep.png")
    plt.close(fig)
    # C
    if R["C"]:
        fig, ax = plt.subplots(figsize=(5.4, 3.8), dpi=150)
        for k, n in enumerate(R["C"]):
            vals = [1 / r["rate"] for r in R["C"][n] if r.get("rate")]
            ax.scatter([k + (j % 7 - 3) * 0.03 for j in range(len(vals))], vals, s=7, color=col[n], alpha=0.7)
            if vals:
                vs = sorted(vals)
                ax.plot([k - 0.25, k + 0.25], [vs[len(vs) // 2]] * 2, color="black", lw=1.5)
        ax.set_xticks(range(len(R["C"])))
        ax.set_xticklabels([D[n]["label"] for n in R["C"]], fontsize=7)
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(fmt)
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_ylabel("N in '1 in N' (Willow calibration)")
        ax.grid(True, axis="y", lw=0.4, color="#dddddd")
        ax.set_title("every valid placement on the chip (line = median)", fontsize=9)
        fig.tight_layout()
        fig.savefig(FIG / "t7_chip_positions.png")
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--mfc", type=int, default=4)
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    D = designs()
    path = RES / "t7.json"
    R = json.loads(path.read_text()) if path.exists() else dict(A={}, B={}, C={})
    if a.report_only:
        report(R, D)
        figures(R, D)
        return
    tasks = []
    for n in D:
        for mo in MODELS_A:
            if mo not in R["A"].get(n, {}):
                tasks.append(("A", n, mo, a.mfc, None))
        for p in SWEEP:
            if str(p) not in R["B"].get(n, {}):
                tasks.append(("B", n, f"si1000_{p}", a.mfc, None))
    pl = {}
    if not R["C"]:
        for n in ("cs02", "G4G6"):
            pl[n] = placements(D[n])
            log(f"C: {n}: {len(pl[n])} Willow placements keep the continuing-data rule")
            tasks += [("C", n, "calibration", 3, e) for e in pl[n]]
    log(f"{len(tasks)} tasks, {a.workers} workers")
    with Pool(a.workers, maxtasksperchild=20) as pool:
        for k, (kind, n, mo, emb, r) in enumerate(pool.imap_unordered(_task, tasks)):
            if kind == "A":
                R["A"].setdefault(n, {})[mo] = r
            elif kind == "B":
                R["B"].setdefault(n, {})[mo.split("_")[1]] = r
            else:
                R["C"].setdefault(n, []).append(dict(r, emb={str(q): v for q, v in emb.items()}))
            if kind != "C" or k % 20 == 0:
                log(f"{kind} {n} {mo}: {one_in(r.get('rate'))}" + (f" acc {r['acceptance']:.3f}" if r.get("acceptance") else ""))
            if k % 10 == 0:
                path.write_text(json.dumps(R, indent=1, default=str))
                report(R, D)
    path.write_text(json.dumps(R, indent=1, default=str))
    report(R, D)
    figures(R, D)
    log("done")


if __name__ == "__main__":
    main()
