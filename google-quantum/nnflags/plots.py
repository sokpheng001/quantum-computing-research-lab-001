"""Figures of the Step 0-2 results (first-ex.md).

Usage: python -m nnflags.plots [--out figures]

Reads only existing outputs:
  results/step0_{d3a6,d3a6f2}_summary.csv, results/step0_*.json (Step 0),
  results/step1.json (Step 1 embeddings and violations),
  results/step2.json (Step 2 verify() counts).
The circuits are rebuilt with cliffordea's DoubleCheck only to list their
two-qubit gates; Step 1 violations are recomputed with check_circuit on the
stored embeddings and checked against results/step1.json.
Every figure is written as PNG only (200 dpi).
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MaxNLocator

from cliffordea import enum

from nnflags import constraints as C
from nnflags.willow import SPEC_FILE, WILLOW, edges, load_spec_file, readout_line

RESULTS = Path("results")
READOUT_MODE = ("Readout rule: strict (measuring any qubit dephases its r + c line; victims = other qubits "
                "live at that TICK, any role; final measurement layer exempt).")
CIRCUITS = {"d3a6": dict(distance=3, ancilla_count=6, flag_count=0),
            "d3a6f2": dict(distance=3, ancilla_count=6, flag_count=2)}

# Okabe-Ito colour-blind-safe palette.
BLUE, ORANGE, GREEN, VERMILION, SKY, GREY = (
    "#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9", "#999999")
BENIGN = dict(facecolor=BLUE, hatch="", edgecolor="black", linewidth=0.6)
MALIGNANT = dict(facecolor=VERMILION, hatch="////", edgecolor="black", linewidth=0.6)
CIRCUIT_STYLE = {"d3a6": dict(facecolor=ORANGE, hatch="", edgecolor="black", linewidth=0.6),
                 "d3a6f2": dict(facecolor=SKY, hatch="\\\\\\\\", edgecolor="black", linewidth=0.6)}

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
    "axes.labelsize": 9, "legend.fontsize": 8, "legend.frameon": False,
    "axes.spines.top": False, "axes.spines.right": False,
    "hatch.linewidth": 0.6,
})


def plain(x, _pos=None):
    """Tick/label formatter: plain numbers, never e-notation."""
    if x == int(x):
        return f"{int(x)}"
    return f"{x:.6f}".rstrip("0").rstrip(".")


def pct(x, _pos=None):
    return f"{x:g} %" if abs(x) >= 0.01 or x == 0 else f"{x:.4f} %"


def one_in(rate):
    return "0" if rate == 0 else f"1 in {round(1 / rate):,}"


def save(fig, out: Path, name: str):
    fig.savefig(out / f"{name}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"wrote {out / name}.png")


# ---- data -------------------------------------------------------------------

def load_step0():
    """{circuit: DataFrame indexed by (state, fault_count)} plus the json records."""
    tables, records = {}, {}
    for name in CIRCUITS:
        df = pd.read_csv(RESULTS / f"step0_{name}_summary.csv", header=[0, 1], index_col=[0, 1])
        df.columns = [f"{a}.{b}" for a, b in df.columns]
        tables[name] = df
        records[name] = json.loads((RESULTS / f"step0_{name}.json").read_text())
    return tables, records


def settings_line(records, name=None):
    r = records["d3a6"]
    p = plain(float(r["noise_model"].split("noise_level=")[1].rstrip(")")))
    flags = (f"flag_count {CIRCUITS[name]['flag_count']}" if name else
             "flag_count 0 (d3a6) / 2 (d3a6f2)")
    return (f"distance {r['distance']}, ancilla_count {r['ancilla_count']}, {flags}, "
            f"max_fault_count {r['max_fault_count']}; noise: cliffordea uniformly_depolarize, p = {p}")


def bar_label(ax, rects, values, fmt=str):
    for rect, v in zip(rects, values):
        ax.annotate(fmt(v), (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                    xytext=(0, 2), textcoords="offset points", ha="center", va="bottom",
                    fontsize=7.5)


def two_level_xticks(ax, centres, inner_labels, group_centres, group_labels):
    ax.set_xticks(centres, inner_labels, fontsize=8)
    ax.tick_params(axis="x", length=0)
    for x, lab in zip(group_centres, group_labels):
        ax.annotate(lab, (x, 0), xycoords=("data", "axes fraction"), xytext=(0, -22),
                    textcoords="offset points", ha="center", va="top", fontsize=9)


# ---- F1 ---------------------------------------------------------------------

def counts_panel(ax, counts, title):
    """counts[(circuit, k)] = (benign, malignant); grouped bars per fault count."""
    w, centres, labels, gcentres = 0.38, [], [], []
    ks = sorted({k for _, k in counts})
    ymax = max(max(v) for v in counts.values())
    for i, k in enumerate(ks):
        for j, name in enumerate(CIRCUITS):
            x = i * 2.6 + j * 1.05
            b, m = counts[name, k]
            rb = ax.bar(x - w / 2, b, w, **BENIGN)
            rm = ax.bar(x + w / 2, m, w, **MALIGNANT)
            bar_label(ax, rb, [b])
            bar_label(ax, rm, [m])
            centres.append(x)
            labels.append(name)
        gcentres.append(i * 2.6 + 0.525)
    two_level_xticks(ax, centres, labels, gcentres, [f"{k} fault" + ("" if k == 1 else "s") for k in ks])
    ax.set_ylim(0, ymax * 1.15)
    ax.yaxis.set_major_formatter(FuncFormatter(plain))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylabel("kept configurations (count)")
    ax.set_title(title)


def fig_step0_configurations(out, tables, records):
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, state in zip(axes, ("T", "S")):
        counts = {(name, k): (int(df.loc[(state, k), "configuration_count.benign"]),
                              int(df.loc[(state, k), "configuration_count.malignant"]))
                  for name, df in tables.items() for k in sorted(df.loc[state].index)}
        counts_panel(ax, counts, f"cultivated state {state}")
    axes[1].tick_params(labelleft=True)
    axes[0].legend(handles=[Patch(**BENIGN, label="benign"), Patch(**MALIGNANT, label="malignant")],
                   loc="upper left")
    fig.suptitle("Step 0: kept fault configurations, benign vs malignant", x=0.01, ha="left",
                 y=1.0, fontsize=11)
    fig.text(0.01, 0.935, settings_line(records), fontsize=8, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, out, "step0_configurations")


# ---- F2 ---------------------------------------------------------------------

def fig_step0_malignant_weight(out, tables, records):
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    w = 0.36
    ks = sorted(tables["d3a6"].loc["T"].index)
    for ax, col, ylabel, fmt in (
            (axes[0], "weight.malignant", "malignant weight\n(accept-weighted coefficient of p^k)", plain),
            (axes[1], "weight.malignant_probability", "malignant share of kept weight (%)", None)):
        for j, name in enumerate(CIRCUITS):
            vals = [float(tables[name].loc[("T", k), col]) for k in ks]
            if fmt is None:
                vals = [100 * v for v in vals]
            xs = [k + (j - 0.5) * w for k in ks]
            rects = ax.bar(xs, vals, w, label=name, **CIRCUIT_STYLE[name])
            bar_label(ax, rects, vals,
                      (lambda v: plain(round(v, 4))) if fmt else (lambda v: "0 %" if v == 0 else f"{v:.2f} %"))
        ax.set_xticks(ks, [str(k) for k in ks])
        ax.set_xlabel("fault count k")
        ax.set_ylabel(ylabel)
        ax.yaxis.set_major_formatter(FuncFormatter(plain if fmt else pct))
        ax.set_ylim(0, ax.get_ylim()[1] * 1.15)
    axes[0].set_title("malignant weight, state T")
    axes[1].set_title("malignant probability, state T")
    axes[1].legend(loc="upper left")
    rates = ", ".join(f"{n}: {one_in(records[n]['T_error_rate_per_kept_shot'])}" for n in CIRCUITS)
    fig.suptitle("Step 0: malignant weight per fault count (T state), d3a6 vs d3a6f2",
                 x=0.01, ha="left", y=1.0, fontsize=11)
    fig.text(0.01, 0.93, settings_line(records), fontsize=8, ha="left")
    fig.text(0.01, -0.06, "Weight and share from FaultCombinator.summarize_contributions; "
             "share = malignant / (benign + malignant) weight.\n"
             f"Logical error per kept shot at p = 0.001 (truncated at 2 faults): {rates}.",
             fontsize=7.5, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, out, "step0_malignant_weight")


# ---- F3-F5: Willow grid -----------------------------------------------------

def xy(q):
    """(row, col) -> plot (x, y) with row 0 at the top."""
    return q[1], -q[0]


def draw_willow(ax, *, faint=False, line_labels=None):
    if line_labels is None:
        line_labels = not faint
    lines = sorted({readout_line(q) for q in WILLOW})
    rmin, rmax = min(r for r, _ in WILLOW), max(r for r, _ in WILLOW)
    for L in lines:
        qs = sorted((q for q in WILLOW if readout_line(q) == L))
        (x0, y0), (x1, y1) = xy(qs[0]), xy(qs[-1])
        ax.plot([x0 + 0.35, x1 - 0.35], [y0 + 0.35, y1 - 0.35], color="#bbbbbb",
                lw=0.6, ls=(0, (3, 3)), zorder=0)
        if line_labels:
            ax.text(x0 + 0.45, y0 + 0.45, str(L), fontsize=6, color="#777777",
                    ha="left", va="bottom", zorder=0)
    for a, b in edges():
        (xa, ya), (xb, yb) = xy(a), xy(b)
        ax.plot([xa, xb], [ya, yb], color="#d0d0d0" if faint else "#888888",
                lw=0.8 if faint else 1.0, zorder=1)
    xs, ys = zip(*(xy(q) for q in WILLOW))
    ax.scatter(xs, ys, s=14 if faint else 22, color="#cccccc" if faint else "black", zorder=2,
               linewidths=0)
    ax.set_aspect("equal")
    cols = range(min(c for _, c in WILLOW), max(c for _, c in WILLOW) + 1)
    ax.set_xticks(list(cols)[::2], [str(c) for c in list(cols)[::2]])
    ax.set_yticks([-r for r in range(rmin, rmax + 1, 2)],
                  [str(r) for r in range(rmin, rmax + 1, 2)])
    ax.set_xlabel("column c")
    ax.set_ylabel("row r")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def fig_willow_grid(out):
    spec_q, spec_e = load_spec_file()
    assert spec_q == set(WILLOW) and spec_e == edges(), "Willow list differs from spec file"
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    draw_willow(ax)
    ax.set_title(f"Willow grid used in Step 1: {len(WILLOW)} qubits, {len(edges())} couplers",
                 loc="left")
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", color="black", markersize=4, label="qubit (r, c)"),
        Line2D([], [], color="#888888", lw=1.0, label="coupler (nearest neighbour)"),
        Line2D([], [], color="#bbbbbb", lw=0.6, ls=(0, (3, 3)),
               label="readout line r + c (number = index)")],
        loc="lower left", bbox_to_anchor=(0.0, -0.02))
    fig.text(0.01, -0.01, f"Source: Google device spec in cirq-google 1.7.0, {SPEC_FILE.name} "
             "(copy in nnflags/data/);\nsame grid and (row, col) labels as the Willow spec sheet "
             "(Dec 9 2024, p. 2). Readout lines r + c = const: Google's\nHardware Experiment Proposal "
             "Guidance (March 2026).", fontsize=7, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "willow_grid")


def load_circuit(name):
    return enum.circuits.DoubleCheck(**CIRCUITS[name])


def draw_embedding(ax, circuit, emb, violations, *, on_grid=True):
    """Circuit qubits on their positions; gates as edges, violations highlighted."""
    inner = circuit.INNER_CIRCUIT
    data = set(circuit.DATA_INDICES)
    pairs = {tuple(sorted((a, b))) for _, _, a, b in C.two_qubit_gates(inner)}
    bad = {tuple(sorted(v.detail["pair"])) for v in violations if v.kind == "non_neighbour"}
    deg = {v.detail["qubit"]: v.detail["partner_count"] for v in violations if v.kind == "degree"}
    readout = [v for v in violations if v.kind == "readout"]
    for a, b in sorted(pairs):
        (xa, ya), (xb, yb) = xy(emb[a]), xy(emb[b])
        if (a, b) in bad:
            # Curved so the edge does not run through the qubits in between; bend
            # towards the side whose curve midpoint is farther from other qubits.
            def clearance(rad):
                mx = (xa + xb) / 2 + rad / 2 * (yb - ya)
                my = (ya + yb) / 2 - rad / 2 * (xb - xa)
                return min((mx - x) ** 2 + (my - y) ** 2
                           for q, pq in emb.items() if q not in (a, b) for x, y in [xy(pq)])
            rad = max((0.35, -0.35, 0.6, -0.6), key=clearance)
            # Quadratic Bezier with the arc3 control point, drawn with ax.plot so
            # the dash pattern is really rendered (FancyArrowPatch ignores it).
            cx = (xa + xb) / 2 + rad * (yb - ya)
            cy = (ya + yb) / 2 - rad * (xb - xa)
            ts = [i / 40 for i in range(41)]
            ax.plot([(1 - t) ** 2 * xa + 2 * t * (1 - t) * cx + t ** 2 * xb for t in ts],
                    [(1 - t) ** 2 * ya + 2 * t * (1 - t) * cy + t ** 2 * yb for t in ts],
                    color=VERMILION, lw=2.0, ls=(0, (4, 2)), zorder=3)
        else:
            ax.plot([xa, xb], [ya, yb], color=BLUE, lw=2.4, zorder=3)
    for q, p in emb.items():
        x, y = xy(p)
        is_data = q in data
        ax.scatter([x], [y], s=210, marker="o" if is_data else "s",
                   facecolor="white", edgecolor=VERMILION if q in deg else "black",
                   linewidths=2.4 if q in deg else 1.2, zorder=4)
        ax.text(x, y, str(q), ha="center", va="center", fontsize=7.5, zorder=5,
                fontweight="bold" if is_data else "normal")
        if q in deg:
            ax.annotate(f"{deg[q]} partners", (x, y), xytext=(10, 9), textcoords="offset points",
                        fontsize=7.5, color=VERMILION, zorder=6,
                        bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none"))
    for v in readout:
        draw_readout(ax, v.detail["measured_at"], v.detail["victim_at"])
    return bool(bad), sorted({plain(v.detail["line"]) for v in readout}, key=float)


READOUT_LINE = dict(color=GREEN, lw=1.8, ls=(0, (1, 1.6)), dash_capstyle="round")
"""Readout-conflict segment style: dotted, used in the plot and the legend alike."""


def draw_readout(ax, a, b, shrink=0.28):
    """Dotted segment from measured qubit a to victim b, shortened at both ends."""
    (xa, ya), (xb, yb) = xy(a), xy(b)
    d = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
    ux, uy = (xb - xa) / d, (yb - ya) / d
    ax.plot([xa + shrink * ux, xb - shrink * ux], [ya + shrink * uy, yb - shrink * uy],
            zorder=2, **READOUT_LINE)


def embedding_legend(ax, has_bad, has_readout, has_deg, loc="upper left", anchor=(1.01, 1.0)):
    h = [Line2D([], [], marker="o", ls="", mfc="white", mec="black", markersize=9,
                label="data qubit"),
         Line2D([], [], marker="s", ls="", mfc="white", mec="black", markersize=8,
                label="ancilla / flag qubit"),
         Line2D([], [], color=BLUE, lw=2.4, label="two-qubit gate on a coupler")]
    if has_bad:
        h.append(Line2D([], [], color=VERMILION, lw=2.0, ls=(0, (4, 2)),
                        label="gate between non-neighbours (violation)"))
    if has_readout:
        h.append(Line2D([], [], **READOUT_LINE,
                        label="readout conflict (strict rule): mid-circuit M\nvs a live qubit "
                              "on the same r + c line; line " + "; ".join(has_readout)))
    if has_deg:
        h.append(Line2D([], [], marker="o", ls="", mfc="white", mec=VERMILION, mew=2.4,
                        markersize=9, label="qubit with > 4 partners (count in red)"))
    ax.legend(handles=h, loc=loc, bbox_to_anchor=anchor)


def readout_text(violations):
    return "; ".join(f"M {v.detail['measured']} at {v.detail['measured_at']} (TICK {v.detail['tick']}) "
                     f"vs {v.detail['victim_role']} {v.detail['victim']} at {v.detail['victim_at']}, "
                     f"line {plain(v.detail['line'])}"
                     for v in violations if v.kind == "readout")


def zoom(ax, emb, pad=1.6):
    rs = [p[0] for p in emb.values()]
    cs = [p[1] for p in emb.values()]
    ax.set_xlim(min(cs) - pad, max(cs) + pad)
    ax.set_ylim(-max(rs) - pad, -min(rs) + pad)


def check_against_json(name, key, violations, step1):
    stored = step1[key]["violations"]
    assert sorted(map(str, violations)) == sorted(stored), f"{name}: violations differ from step1.json"


def fig_embedding_d3a6(out, step1):
    circ = load_circuit("d3a6")
    emb = {int(q): tuple(p) for q, p in step1["d3a6_primary"]["embedding"].items()}
    v = C.check_circuit(circ.INNER_CIRCUIT, emb)
    check_against_json("d3a6", "d3a6_primary", v, step1)
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    draw_willow(ax, faint=True)
    has_bad, has_ro = draw_embedding(ax, circ, emb, v)
    zoom(ax, emb)
    embedding_legend(ax, has_bad, [", ".join(has_ro)], False)
    s = C.summarize(v)
    ax.set_title("Step 1: d3a6 embedded on Willow (native coordinates + (4, 4))", loc="left")
    fig.text(0.01, -0.02,
             f"DoubleCheck(distance=3, ancilla_count=6), 13 qubits. Non-neighbour gates: "
             f"{s.get('non_neighbour', 0)}; qubits with > 4 partners: {s.get('degree', 0)} "
             f"(max 4: qubits 5 and 9); readout conflicts: {s.get('readout', 0)}.\n"
             f"Readout conflict: {readout_text(v)}.\nAll 350 rigid Willow placements pass the "
             "neighbour/degree checks; strict readout conflicts: 1 in 180 placements, 2 in 170. "
             "All 182,968 nearest-neighbour embeddings have at least 1.\n" + READOUT_MODE,
             fontsize=7.5, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "embedding_d3a6")


def fig_embedding_d3a6f2(out, step1):
    circ = load_circuit("d3a6f2")
    emb = {int(q): tuple(p) for q, p in step1["d3a6f2_willow"]["embedding"].items()}
    v = C.check_circuit(circ.INNER_CIRCUIT, emb)
    check_against_json("d3a6f2", "d3a6f2_willow", v, step1)
    native = C.native_coords(circ.INNER_CIRCUIT)
    vn = C.check_circuit(circ.INNER_CIRCUIT, native, grid=None)
    assert sorted(map(str, vn)) == sorted(step1["d3a6f2_native"])

    fig, (ax, axn) = plt.subplots(1, 2, figsize=(11, 5.0), width_ratios=[1.25, 1])
    draw_willow(ax, faint=True)
    has_bad, has_ro = draw_embedding(ax, circ, emb, v)
    zoom(ax, emb)
    s = C.summarize(v)
    ax.set_title("(a) on Willow, Step 1 placement", loc="left")

    # (b) native QUBIT_COORDS: guide lattice of integer points, half-integer flags.
    rs = [p[0] for p in native.values()]
    cs = [p[1] for p in native.values()]
    for r in range(int(min(rs)), int(max(rs)) + 1):
        axn.axhline(-r, color="#eeeeee", lw=0.6, zorder=0)
    for c in range(int(min(cs)), int(max(cs)) + 1):
        axn.axvline(c, color="#eeeeee", lw=0.6, zorder=0)
    _, ro_n = draw_embedding(axn, circ, native, vn)
    axn.set_aspect("equal")
    zoom(axn, native, pad=0.8)
    axn.set_xticks(range(int(min(cs)), int(max(cs)) + 1))
    axn.set_yticks([-r for r in range(int(min(rs)), int(max(rs)) + 1)],
                   [str(r) for r in range(int(min(rs)), int(max(rs)) + 1)])
    axn.set_xlabel("native column (QUBIT_COORDS)")
    axn.set_ylabel("native row (QUBIT_COORDS)")
    sn = C.summarize(vn)
    axn.set_title("(b) native coordinates (as in the paper)", loc="left")
    embedding_legend(axn, True, [", ".join(has_ro) + " in (a)", ", ".join(ro_n) + " in (b)"], True,
                     anchor=(1.02, 1.0))

    fig.suptitle("Step 1: d3a6f2 (flag_count 2) does not fit the Willow nearest-neighbour grid",
                 x=0.01, ha="left", fontsize=11)
    fig.text(0.01, 0.0,
             f"(a) 13 shared qubits as in the d3a6 placement; flags 4 and 9 on the free qubits "
             f"minimising non-neighbour gates. Distinct non-neighbour gates "
             f"{len({tuple(sorted(x.detail['pair'])) for x in v if x.kind == 'non_neighbour'})} "
             f"({s.get('non_neighbour', 0)} instances), qubits > 4 partners {s.get('degree', 0)}, "
             f"readout conflicts {s.get('readout', 0)}.\n"
             f"(b) Distinct diagonal gates "
             f"{len({tuple(sorted(x.detail['pair'])) for x in vn if x.kind == 'non_neighbour'})} "
             f"({sn.get('non_neighbour', 0)} instances, fold and unfold), qubits > 4 partners "
             f"{sn.get('degree', 0)}, readout conflicts {sn.get('readout', 0)} (readout line = r + c "
             "of the native coordinates).\nQubit 6 has 6 partners, so no placement on a grid "
             "with at most 4 neighbours can remove all violations.\n" + READOUT_MODE,
             fontsize=7.5, ha="left", va="top")
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    save(fig, out, "embedding_d3a6f2")


# ---- F6 ---------------------------------------------------------------------

def fig_step2_verify_check(out, tables, records):
    step2 = json.loads((RESULTS / "step2.json").read_text())
    fig, axes = plt.subplots(2, 2, figsize=(9, 6.2), sharey="row")
    w = 0.2
    for row, name in enumerate(CIRCUITS):
        for col, state in enumerate(("T", "S")):
            ax = axes[row, col]
            ks = sorted(tables[name].loc[state].index)
            centres, labels, gcentres, allmatch = [], [], [], True
            for i, k in enumerate(ks):
                s0 = (int(tables[name].loc[(state, k), "configuration_count.benign"]),
                      int(tables[name].loc[(state, k), "configuration_count.malignant"]))
                s2 = (step2[name][state][str(k)]["benign"], step2[name][state][str(k)]["malignant"])
                allmatch &= s0 == s2
                for j, (src, (b, m)) in enumerate((("Step 0", s0), ("verify()", s2))):
                    x = i * 1.3 + j * 0.5
                    rb = ax.bar(x - w / 2, b, w, **BENIGN)
                    rm = ax.bar(x + w / 2, m, w, **MALIGNANT)
                    bar_label(ax, rb, [b])
                    bar_label(ax, rm, [m])
                    centres.append(x)
                    labels.append(src)
                gcentres.append(i * 1.3 + 0.25)
            two_level_xticks(ax, centres, labels, gcentres, [f"{k} fault" + ("" if k == 1 else "s") for k in ks])
            ax.yaxis.set_major_formatter(FuncFormatter(plain))
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_ylim(0, 44)
            ax.set_title(f"{name}, state {state}: "
                         + ("identical" if allmatch else "MISMATCH"), loc="left")
            if col == 0:
                ax.set_ylabel("kept configurations (count)")
    fig.legend(handles=[Patch(**BENIGN, label="benign"), Patch(**MALIGNANT, label="malignant")],
               loc="upper right", ncol=2, bbox_to_anchor=(0.99, 1.0))
    fig.suptitle("Step 2: verify() on the bundled Stim files vs Step 0 DoubleCheck",
                 x=0.01, ha="left", y=1.0, fontsize=11)
    fig.text(0.01, 0.95, settings_line(records), fontsize=8, ha="left")
    flags = all(step2[n][key] for n in CIRCUITS for key in
                ("identical_to_step0_summary", "same_malignant_T_fault_indices", "same_T_rate_as_step0"))
    fig.text(0.01, -0.01, "Also identical (results/step2.json): full summarize_contributions table, "
             "malignant T fault indices, T logical error per kept shot: "
             + ("yes for both circuits." if flags else "NO, see step2.json."),
             fontsize=7.5, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93), h_pad=3.0)
    save(fig, out, "step2_verify_check")


# ---- F7: Google's experimental circuits on Willow ----------------------------

def fig_google_on_willow(out):
    import stim
    from types import SimpleNamespace
    gc = json.loads((RESULTS / "google_check.json").read_text())
    g4 = gc["G4"]
    circ = stim.Circuit.from_file(str(Path("nnflags/data/google_circuits/rosenfeld2512_G4.stim")))
    emb = {q: tuple(p) for q, p in C.native_coords(circ).items()}
    emb = {q: (int(r), int(c)) for q, (r, c) in emb.items()}
    _, measured = C.liveness(circ, ())
    final = max(t for t, m in enumerate(measured) if m)
    mid = {}
    for t, ms in enumerate(measured):
        if ms and t != final:
            for q in ms:
                mid.setdefault(q, []).append(t)
    pairs = {tuple(sorted((a, b))) for _, _, a, b in C.two_qubit_gates(circ)}

    fig, (ax, axb) = plt.subplots(1, 2, figsize=(11.5, 5.4))
    draw_willow(ax, faint=True)
    for a, b in pairs:
        (xa, ya), (xb, yb) = xy(emb[a]), xy(emb[b])
        ax.plot([xa, xb], [ya, yb], color=BLUE, lw=2.4, zorder=3)
    for L in sorted({readout_line(emb[q]) for q in mid}):
        qs = sorted(q for q in WILLOW if readout_line(q) == L)
        (x0, y0), (x1, y1) = xy(qs[0]), xy(qs[-1])
        ax.plot([x0, x1], [y0, y1], color=ORANGE, lw=1.2, ls=(0, (6, 3)), zorder=1)
    for q, p in emb.items():
        x, y = xy(p)
        ax.scatter([x], [y], s=230, marker="D" if q in mid else "o",
                   facecolor="#f0f0f0" if q in mid else "white", edgecolor="black",
                   linewidths=1.2, hatch="////" if q in mid else None, zorder=4)
        ax.text(x, y, str(q), ha="center", va="center", fontsize=7.5, zorder=5,
                bbox=dict(boxstyle="circle,pad=0.05", fc="white", ec="none") if q in mid else None)
    zoom(ax, emb, pad=1.4)
    ax.set_title("(a) Rosenfeld et al. Fig. 2 cultivation circuit, as run", loc="left", pad=30)
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", mfc="white", mec="black", markersize=9,
               label="qubit (stim index from the Crumble link)"),
        Line2D([], [], marker="D", ls="", mfc="#f0f0f0", mec="black", markersize=8,
               label="measured mid-circuit (TICK 25: 1, 4, 6, 9;\nTICK 40: 6, 9)"),
        Line2D([], [], color=BLUE, lw=2.4, label="CZ on a coupler"),
        Line2D([], [], color=ORANGE, lw=1.2, ls=(0, (6, 3)),
               label="readout line r + c of a mid-circuit\nmeasured qubit (16 and 18)")],
        loc="upper left", bbox_to_anchor=(0.0, -0.13), ncol=2, fontsize=7.5)
    s_ex = g4["strict_exempt_zreset_live"][0]
    s_ck = g4["strict_check_zreset_live"][0]
    ax.text(0.0, 1.0, f"{g4['qubits']} qubits, all on Willow; neighbour/degree violations: "
            f"{sum(g4['neighbour_degree'].values())}; max partners {g4['max_degree']}\n"
            f"strict readout conflicts: {s_ex} (final layer exempt), {s_ck} (checked)",
            transform=ax.transAxes, fontsize=7.5, va="bottom", ha="left")

    # (b) the Chan et al. Sec. 5 circuit (= cliffordea d3a4) on Willow, best embedding.
    ch = gc["chan2609_sec5"]
    es = json.loads((RESULTS / "embed_search_d3a4.json").read_text())
    emb4 = {int(q): tuple(p) for q, p in es["example_min_embedding"]["exempt"].items()}
    dc4 = enum.circuits.DoubleCheck(distance=3, ancilla_count=4)
    v4 = C.check_circuit(dc4.INNER_CIRCUIT, emb4)
    draw_willow(axb, faint=True)
    _, ro = draw_embedding(axb, dc4, emb4, v4)
    zoom(axb, emb4, pad=1.4)
    axb.set_title("(b) Chan et al. Sec. 5 Crumble circuit (= cliffordea d3a4)", loc="left", pad=30)
    embedding_legend(axb, False, [", ".join(ro)], False, loc="upper left", anchor=(0.0, -0.13))
    T = ch["verify"]["T"]
    axb.text(0.0, 1.0, f"best of {es['embedding_count']:,} nearest-neighbour embeddings; every one "
             f"has exactly {es['min_violations']['exempt']} strict conflict\n"
             f"verify(): malignant T configurations with 2 faults = {T['2']['malignant']} "
             f"(fault distance 2)", transform=axb.transAxes, fontsize=7.5, va="bottom", ha="left")
    fig.suptitle("Google's experimental cultivation circuit on Willow under the strict readout rule",
                 x=0.01, ha="left", fontsize=11, y=1.02)
    fig.text(0.01, -0.12,
             "(a) Crumble link 'Figure 2: cultivation' in the appendix of Rosenfeld et al., arXiv:2512.13908, "
             "converted with nnflags/crumble.py; coordinates used as Willow (row, col).\n"
             "(b) Crumble link in Sec. 5 of Chan, Strikis, Sun & Cai, arXiv:2609.17706v3; identical to "
             "cliffordea's bundled d3a4/full.stim. verify(): max_fault_count 2, cultivated state T, "
             "noise cliffordea uniformly_depolarize, p = 0.001.\n" + READOUT_MODE,
             fontsize=7.5, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "google_circuits_on_willow")


# ---- F8: strict-violation histogram over all embeddings ---------------------

def fig_embedding_histogram(out):
    d6 = json.loads((RESULTS / "embed_search_d3a6.json").read_text())
    d4 = json.loads((RESULTS / "embed_search_d3a4.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), width_ratios=[2.2, 1])
    styles = {"exempt": dict(facecolor=BLUE, hatch="", edgecolor="black", linewidth=0.6),
              "check": dict(facecolor=ORANGE, hatch="\\\\\\\\", edgecolor="black", linewidth=0.6)}
    labels = {"exempt": "final measurement layer exempt (default)",
              "check": "final measurement layer checked too"}
    for ax, rec, name in ((axes[0], d6, "d3a6: DoubleCheck(3, 6)"),
                          (axes[1], d4, "d3a4: DoubleCheck(3, 4)\n(Chan et al. Sec. 5 circuit)")):
        n = rec["embedding_count"]
        ks = sorted({int(k) for h in rec["histogram"].values() for k in h})
        w = 0.4
        for j, fl in enumerate(("exempt", "check")):
            h = {int(k): v for k, v in rec["histogram"][fl].items()}
            xs = [k + (j - 0.5) * w for k in ks]
            vals = [100 * h.get(k, 0) / n for k in ks]
            rects = ax.bar(xs, vals, w, label=labels[fl], **styles[fl])
            bar_label(ax, rects, [h.get(k, 0) for k in ks], lambda v: f"{v:,}" if v else "")
        ax.set_xticks(ks, [str(k) for k in ks])
        ax.set_xlabel("strict readout conflicts in the embedding")
        ax.set_ylabel("share of embeddings (%)")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))
        ax.set_ylim(0, 112)
        ax.set_title(f"{name}: {n:,} embeddings", loc="left")
        ax.axvline(-0.5 if 0 not in ks else 0, color="none")
        ax.set_xlim(-0.6, max(ks) + 0.6)
        ax.set_xticks(range(0, max(ks) + 1), [str(k) for k in range(0, max(ks) + 1)])
    axes[0].legend(loc="upper right")
    m = d6["mrx5_argument"]
    fig.suptitle("Task B: strict readout conflicts over every injective nearest-neighbour "
                 "embedding onto Willow", x=0.01, ha="left", fontsize=11, y=1.02)
    fig.text(0.01, -0.07,
             "No embedding has 0 conflicts (the bar at 0 is empty in every panel). Labels are embedding "
             f"counts. d3a6: in all {m['with_mechanism']:,} of {m['embeddings']:,} embeddings, "
             "MRX 5 (TICK 6) hits one of 8, 10, 12 on the grid\npoint diagonal to 5 and adjacent to 9. "
             "Embeddings enumerated by backtracking over the interaction tree "
             "(nnflags/embed_search.py). " + READOUT_MODE.replace("; final measurement layer exempt", ""),
             fontsize=7.5, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "embedding_readout_histogram")


# ---- F9: Step 3 candidate counts --------------------------------------------

def fig_step3_candidates(out):
    from matplotlib.ticker import LogLocator
    S = json.loads((RESULTS / "step3_summary.json").read_text())
    st = S["stats"]
    cats = [(k, lab) for k, lab in (
        ("c", "(c) re-embeddings\n350 rigid placements"),
        ("b", "(b) fold re-layerings\n(primary placement)"),
        ("a1", "(a) 1 flag\n8 placements x 6 folds"),
        ("a2", "(a) 2 flags\nprimary placement"),
        ("a3 (sample)", "(a) 3 flags\nrandom sample")) if k in st]
    series = [("total", "generated", dict(facecolor=GREY, hatch="", edgecolor="black", linewidth=0.6)),
              ("hw_ok", "pass neighbour / degree / reuse\n(= pass with readout ignored)",
               dict(facecolor=BLUE, hatch="", edgecolor="black", linewidth=0.6)),
              ("pass_strict", "pass with strict readout",
               dict(facecolor=VERMILION, hatch="////", edgecolor="black", linewidth=0.6))]
    fig, ax = plt.subplots(figsize=(11.5, 4.2))
    w = 0.28
    for j, (key, lab, sty) in enumerate(series):
        xs = [i + (j - 1) * w for i in range(len(cats))]
        vals = [st[c].get(key, 0) for c, _ in cats]
        rects = ax.bar(xs, [max(v, 0.6) if v else 0 for v in vals], w, label=lab, **sty)
        for r, v in zip(rects, vals):
            ax.annotate(f"{v:,}", (r.get_x() + r.get_width() / 2, max(v, 1)), xytext=(0, 2),
                        textcoords="offset points", ha="center", va="bottom", fontsize=6.3)
    ax.set_yscale("log")
    ax.set_ylim(0.8, max(st[c]["total"] for c, _ in cats) * 6)
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}" if x >= 1 else ""))
    ax.set_xticks(range(len(cats)), [lab for _, lab in cats], fontsize=8)
    ax.set_ylabel("candidates (count, log scale)")
    ax.legend(loc="upper left", fontsize=7.5)
    ax.set_title("Step 3: candidates from d3a6 per category and how many pass each check", loc="left")
    hook = st.get("a2", {}).get("with_hook_flag", 0)
    fig.text(0.01, -0.04,
             "distance 3, ancilla_count 6 (d3a6) plus 0-3 new Z flags; flags on free Willow neighbours, "
             "CX(q -> f) at two fold/unfold slots; flag M either 'next' or in the final layer.\n"
             "Hook qubits 5 and 9 have no free neighbour in any embedding, so only qubit 3 can host a hook "
             f"flag (2-flag candidates containing one: {hook:,}).\n" + READOUT_MODE
             + " No candidate passes strict readout (task B).",
             fontsize=7.5, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "step3_candidates")


# ---- Option 1 (RESULTS_g4.md, RESULTS_option1.md) ----------------------------

OPTION1_RULE = ("Readout rule: strict r + c lines; live_rule='gate' (a qubit idling in |0> is not live until its "
                "first H-like or two-qubit gate; RX = R + H is live at once); final measurement layer exempt "
                "only if it is one TICK\nwith all basis changes before it (holds for every circuit shown). "
                "verify(): cliffordea uniformly_depolarize, p = 0.001, cultivated state T.")
FLAG_STYLE = dict(marker="^", s=230, facecolor="#e8e8e8", edgecolor="black", linewidths=1.2, hatch="////")


def _draw_line(ax, L, **kw):
    qs = sorted(q for q in WILLOW if readout_line(q) == L)
    (x0, y0), (x1, y1) = xy(qs[0]), xy(qs[-1])
    ax.plot([x0, x1], [y0, y1], zorder=1, **kw)


PARITY_LINE = dict(color=ORANGE, lw=1.3, ls=(0, (6, 3)))


def _draw_option1_circuit(ax, inner, emb, data, parity, hooks=(), flags=(), label=None):
    """Willow drawing of a CX-form double check: gates, roles, parity qubits and
    their readout lines, hook qubits (thick vermilion outline), flags."""
    draw_willow(ax, faint=True, line_labels=False)
    pairs = {tuple(sorted((a, b))) for _, _, a, b in C.two_qubit_gates(inner)}
    for a, b in sorted(pairs):
        (xa, ya), (xb, yb) = xy(emb[a]), xy(emb[b])
        if a in flags or b in flags:
            ax.plot([xa, xb], [ya, yb], color=SKY, lw=2.2, ls=(0, (3, 1.5)), zorder=3)
        else:
            ax.plot([xa, xb], [ya, yb], color=BLUE, lw=2.4, zorder=3)
    for L in sorted({readout_line(emb[q]) for q in parity}):
        _draw_line(ax, L, **PARITY_LINE)
        q0 = max((q for q in parity if readout_line(emb[q]) == L), key=lambda q: emb[q][1])
        x0, y0 = xy(emb[q0])
        ax.text(x0 + 0.75, y0 + 0.55, f"line {L}", fontsize=7, color="#8a5a00", zorder=1)
    for q, p in emb.items():
        x, y = xy(p)
        hook = q in hooks
        ec, lw = (VERMILION, 2.6) if hook else ("black", 1.2)
        if q in flags:
            ax.scatter([x], [y], **{**FLAG_STYLE, "edgecolor": ec, "linewidths": lw}, zorder=4)
        elif q in parity:
            ax.scatter([x], [y], s=250, marker="D", facecolor="#f0f0f0", edgecolor=ec,
                       linewidths=lw, hatch="....", zorder=4)
        else:
            ax.scatter([x], [y], s=220, marker="o" if q in data else "s", facecolor="white",
                       edgecolor=ec, linewidths=lw, zorder=4)
        ax.text(x, y, str(q), ha="center", va="center", fontsize=7.2, zorder=5,
                fontweight="bold" if q in data else "normal",
                bbox=dict(boxstyle="circle,pad=0.02", fc="white", ec="none") if q in parity or q in flags
                else None)
    zoom(ax, emb, pad=1.3)
    if label:
        ax.set_title(label, loc="left", fontsize=9, pad=34)


def _option1_legend(ax, has_flags, has_hooks, anchor=(0.0, -0.1), ncol=2):
    h = [Line2D([], [], marker="o", ls="", mfc="white", mec="black", markersize=9, label="data qubit"),
         Line2D([], [], marker="s", ls="", mfc="white", mec="black", markersize=8, label="ancilla"),
         Line2D([], [], marker="D", ls="", mfc="#f0f0f0", mec="black", markersize=8,
                label="parity qubit measured mid-circuit"),
         Line2D([], [], color=BLUE, lw=2.4, label="CX of the double check (coupler)"),
         Line2D([], [], **PARITY_LINE, label="readout line r + c of a parity qubit")]
    if has_flags:
        h += [Line2D([], [], marker="^", ls="", mfc="#e8e8e8", mec="black", markersize=9, label="Z flag"),
              Line2D([], [], color=SKY, lw=2.2, ls=(0, (3, 1.5)), label="flag CX (twice)")]
    if has_hooks:
        h.append(Line2D([], [], marker="o", ls="", mfc="white", mec=VERMILION, mew=2.6, markersize=9,
                        label="X-hook qubit (in a malignant\n2-fault T configuration)"))
    ax.legend(handles=h, loc="upper left", bbox_to_anchor=anchor, ncol=ncol, fontsize=7.2)


def _timeline(ax, inner, order, labels, parity=(), flags=()):
    """Compact circuit diagram: one row per qubit, one column per TICK."""
    rows = {q: i for i, q in enumerate(order)}
    layers = C.split_by_ticks(inner)
    for q, i in rows.items():
        ax.plot([0.5, len(layers) - 0.5], [-i, -i], color="#bbbbbb", lw=0.7, zorder=0)
    box = dict(boxstyle="square,pad=0.15", fc="white", ec="black", lw=0.6)
    for t, layer in enumerate(layers):
        for op in layer:
            if op.name in ("QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "TICK"):
                continue
            ts = [x.value for x in op.targets_copy() if x.is_qubit_target or x.is_x_target]
            if op.name == "CX":
                for a, b in zip(ts[::2], ts[1::2]):
                    ya, yb = -rows[a], -rows[b]
                    col = SKY if (a in flags or b in flags) else BLUE
                    ax.plot([t, t], [ya, yb], color=col, lw=1.1, zorder=1)
                    ax.scatter([t], [ya], s=14, color=col, zorder=2)
                    ax.scatter([t], [yb], s=46, facecolor="white", edgecolor=col, zorder=2, lw=1.1)
                    ax.plot([t - 0.13, t + 0.13], [yb, yb], color=col, lw=1.0, zorder=3)
                    ax.plot([t, t], [yb - 0.13, yb + 0.13], color=col, lw=1.0, zorder=3)
            elif op.name == "MPP":
                for q in ts:
                    ax.text(t, -rows[q], "X", ha="center", va="center", fontsize=5.5, color="#666666")
            else:
                for q in ts:
                    ax.text(t, -rows[q], op.name, ha="center", va="center", fontsize=5.2, bbox=box,
                            zorder=4)
    ax.set_yticks([-i for i in range(len(order))], [labels[q] for q in order], fontsize=6.5)
    ax.set_xticks(range(len(layers)), [str(t) for t in range(len(layers))], fontsize=6.5)
    ax.set_xlabel("TICK of the inner circuit (TICK 0: noiseless MPP marker)")
    ax.set_xlim(-0.6, len(layers) - 0.4)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)


def fig_option1_g4_extracted(out):
    from nnflags import g4
    res = json.loads((RESULTS / "g4_result.json").read_text())
    cx, _ = g4.inner_cx()
    emb = {q: (int(r), int(c)) for q, (r, c) in C.native_coords(cx).items()}
    hooks = (2, 4, 5, 9)
    fig, (ax, axb) = plt.subplots(1, 2, figsize=(12, 5.6), width_ratios=[1, 1.25])
    _draw_option1_circuit(ax, cx, emb, set(g4.DATA), parity=(9, 6), hooks=hooks,
                          label="(a) G4's double check (extracted, CX form) at G4's Willow coordinates")
    _option1_legend(ax, False, True, anchor=(0.0, -0.1))
    rows = {(r["variant"], r["max_fault_count"]): r for r in res["rows"]}
    p = rows[("G4-CX (cliffordea T_z convention)", 2)]
    p3 = rows[("G4-CX (cliffordea T_z convention)", 3)]
    pn = rows[("G4-native CZ+H (cliffordea T_z convention)", 2)]
    ax.text(0.0, 1.0, f"9: MRX = forward X_L check (line 18); 6: MR = Z7 check (line 18), measured together.\n"
            f"strict readout conflicts (final layer exempt): 0. Fault distance 2: malignant T configurations "
            f"{p['T']['1']['malignant']} / {p['T']['2']['malignant']} / {p3['T']['3']['malignant']} at 1 / 2 / 3 faults",
            transform=ax.transAxes, fontsize=7.3, va="bottom", ha="left")
    order = [3, 0, 8, 5, 11, 2, 10, 4, 1, 9, 6, 7]
    labels = {q: f"{q} {'data' if q in g4.DATA else 'anc'} {emb[q]}" for q in order}
    _timeline(axb, cx, order, labels)
    axb.set_title("(b) the same circuit in time (G4 TICKs 31-50 + ancilla readout, H frames absorbed)",
                  loc="left", fontsize=9)
    fig.suptitle("Google's as-run double check (Rosenfeld et al. Fig. 2, G4) in cliffordea's inner-circuit "
                 "conventions", x=0.01, ha="left", fontsize=11, y=1.03)
    fig.text(0.01, -0.02,
             f"Logical error per kept shot (state T, p = 0.001, max_fault_count 2): CX form {one_in(p['rate_T'])}, "
             f"native CZ + H form {one_in(pn['rate_T'])} (same configuration counts; the native form has 12 extra "
             "H-only TICKs).\nConversion steps and faithfulness checks: RESULTS_g4.md. X-hook qubits from "
             "FaultCombinator.index_to_events of the 7 malignant 2-fault configurations.\n" + OPTION1_RULE,
             fontsize=7.3, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "option1_g4_extracted")


def fig_option1_conflict_table(out):
    t = json.loads((RESULTS / "live_rule_table.json").read_text())
    circuits = [("d3a6", f"d3a6\nmin over {t['d3a6']['embedding_count']:,}\nembeddings"),
                ("d3a4", f"d3a4\nmin over {t['d3a4']['embedding_count']:,}\nembeddings"),
                ("G4", "G4 (Fig. 2)\nreal coordinates"), ("G5", "G5 (Fig. 3)\nreal coordinates")]
    series = [("new", "new rule: live_rule 'gate', final layer 'auto' (default)",
               dict(facecolor=BLUE, hatch="", edgecolor="black", linewidth=0.6)),
              ("new_check", "new rule, final layer always checked",
               dict(facecolor=SKY, hatch="....", edgecolor="black", linewidth=0.6)),
              ("old", "Step-3 rule: live from preparation, final layer exempt",
               dict(facecolor=VERMILION, hatch="////", edgecolor="black", linewidth=0.6))]
    val = lambda c, k: t[c][k]["min"] if "min" in t[c][k] else t[c][k]["count"]
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    w = 0.26
    for j, (k, lab, sty) in enumerate(series):
        xs = [i + (j - 1) * w for i in range(len(circuits))]
        vals = [val(c, k) for c, _ in circuits]
        rects = ax.bar(xs, vals, w, label=lab, **sty)
        bar_label(ax, rects, vals)
    ax.set_xticks(range(len(circuits)), [lab for _, lab in circuits], fontsize=8)
    ax.set_ylabel("strict readout conflicts")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylim(0, 14)
    ax.legend(loc="upper left", fontsize=7.5)
    ax.set_title("Strict readout conflicts under the refined live rule (task A)", loc="left")
    fig.text(0.01, -0.06, "d3a6 / d3a4: minimum over every injective nearest-neighbour embedding onto Willow "
             "(histograms in RESULTS_g4.md). G4 / G5: Rosenfeld et al. as-run circuits at their Willow "
             "coordinates.\nG5's 12 old conflicts are ancilla 4 idling in |0> after R; d3a6 / d3a4 victims are "
             "data or RX-prepared ancillas, which stay live.", fontsize=7.3, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "option1_conflict_table")


def _ranked_candidates():
    import csv
    path = RESULTS / "option1_candidates.csv"
    if not path.exists():
        return []
    rows = list(csv.DictReader(path.open()))
    key = lambda r: (int(r["malignant_T_2"]), int(r["n_flags"]), int(r["added_ticks"]),
                     int(r["malignant_T_3"]), int(r["id"]))
    return sorted(rows, key=key)


def fig_option1_best_candidates(out, k=3):
    import stim
    rows = _ranked_candidates()[:k]
    if not rows:
        return
    fig, axes = plt.subplots(1, len(rows), figsize=(5.0 * len(rows), 5.6))
    axes = [axes] if len(rows) == 1 else list(axes)
    for ax, r in zip(axes, rows):
        inner = stim.Circuit.from_file(r["stim_file"])
        emb = {q: (int(a), int(b)) for q, (a, b) in C.native_coords(inner).items()}
        n = int(r["n_qubits_tree"])
        # data = MPP targets (cliffordea's own definition), not parsed from the tree text
        data = {t.value for inst in inner if inst.name == "MPP" for t in inst.targets_copy()
                if t.is_x_target or t.is_y_target or t.is_z_target}
        flags = {q for q in emb if q >= n}
        parity = {int(q) for q in json.loads(r["parity_qubits"])}
        hooks = {int(q) for q in json.loads(r["hooks"])}
        _draw_option1_circuit(ax, inner, emb, data, parity, hooks=hooks, flags=flags,
                              label=f"candidate {r['id']}: {r['n_flags']} flag(s), "
                                    f"+{r['added_ticks']} TICK(s)")
        ax.text(0.0, 1.0, f"malignant T: {r['malignant_T_1']} / {r['malignant_T_2']} / {r['malignant_T_3']} "
                f"at 1 / 2 / 3 faults\nLER per kept shot (max_fault_count 2): "
                f"{one_in(float(r['ler_T_mfc2']))}; {r['n_cx']} CX, max degree {r['max_degree']}\n"
                f"flags: {r['flags'] or 'none'}", transform=ax.transAxes, fontsize=7, va="bottom",
                ha="left")
    _option1_legend(axes[0], True, True, anchor=(0.0, -0.1), ncol=3)
    fig.suptitle("Best valid Option-1 candidates on Willow (ranked by malignant T at 2 faults, flags, "
                 "added TICKs, malignant T at 3 faults)", x=0.01, ha="left", fontsize=11, y=1.06)
    fig.text(0.01, -0.16, "Valid = nearest-neighbour, degree <= 4, no reuse in a TICK, strict readout, "
             "equivalence checker (same code, same X_L double check, exact time reverse, deterministic "
             "detectors) and verify() at max_fault_count 2 and 3.\n" + OPTION1_RULE,
             fontsize=7.2, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "option1_best_candidates")


def fig_option1_malignant_bars(out, k=5):
    res = json.loads((RESULTS / "g4_result.json").read_text())
    rows = {(r["variant"], r["max_fault_count"]): r for r in res["rows"]}
    refs = [("d3a6", rows[("d3a6", 3)]), ("d3a4", rows[("d3a4", 3)]),
            ("G4 (CX form)", rows[("G4-CX (cliffordea T_z convention)", 3)])]
    names = [n for n, _ in refs]
    m2 = [r["T"]["2"]["malignant"] for _, r in refs]
    m3 = [r["T"]["3"]["malignant"] for _, r in refs]
    for r in _ranked_candidates()[:k]:
        names.append(f"cand. {r['id']}\n({r['n_flags']} flag{'s' if r['n_flags'] != '1' else ''})")
        m2.append(int(r["malignant_T_2"]))
        m3.append(int(r["malignant_T_3"]))
    styles = [dict(facecolor=ORANGE, hatch="", edgecolor="black", linewidth=0.6),
              dict(facecolor=GREY, hatch="xx", edgecolor="black", linewidth=0.6),
              dict(facecolor=VERMILION, hatch="////", edgecolor="black", linewidth=0.6)]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.9))
    for ax, vals, title in ((axes[0], m2, "2 faults"), (axes[1], m3, "3 faults")):
        for i, v in enumerate(vals):
            st = styles[i] if i < 3 else dict(facecolor=BLUE, hatch="", edgecolor="black", linewidth=0.6)
            rect = ax.bar([i], [v], 0.62, **st)
            bar_label(ax, rect, [v])
        ax.set_xticks(range(len(names)), names, fontsize=7.2)
        ax.set_ylabel("malignant T configurations")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_ylim(0, max(vals) * 1.18 + 1)
        ax.set_title(f"kept malignant configurations with {title}", loc="left")
    fig.suptitle("Malignant T configurations: baselines vs the top valid Option-1 candidates", x=0.01,
                 ha="left", fontsize=11, y=1.03)
    fig.text(0.01, -0.08, "d3a6, d3a4: cliffordea bundled double checks; G4: Google's as-run double check, "
             "extracted (RESULTS_g4.md). Candidates ranked as in RESULTS_option1.md. max_fault_count 3, "
             "cultivated state T,\ncliffordea uniformly_depolarize, p = 0.001.", fontsize=7.3, ha="left",
             va="top")
    fig.tight_layout()
    save(fig, out, "option1_malignant_comparison")


# ---- ZZ-flag round (RESULTS_zzflags.md) ----------------------------------------------

ZFLAG_STYLE = dict(marker="^", s=240, facecolor="#e8e8e8", edgecolor="black", linewidths=1.2, hatch="////")
XFLAG_STYLE = dict(marker="v", s=240, facecolor="#f6e3b4", edgecolor="black", linewidths=1.2, hatch="....")
ZZ_RULE = ("Hardware: nearest-neighbour CX only, degree <= 4, no qubit twice in a TICK, strict readout r + c "
           "with live_rule='gate' and final_layer='auto' (constraints.check_circuit). verify(): cliffordea "
           "uniformly_depolarize,\np = 0.001, distance 3, cultivated state T, max_fault_count 2 and 3. "
           "Data/ancilla roles from the circuit's MPP targets; parity qubits = qubits measured before the "
           "final layer.")


def _zz_rows(path=None, successes_only=True):
    import csv
    path = RESULTS / "zz_candidates.csv" if path is None else path
    if not path.exists():
        return []
    rows = [r for r in csv.DictReader(path.open()) if r.get("malignant_T_2") not in (None, "")]
    if successes_only:
        rows = [r for r in rows if r.get("success") == "True"]
    key = lambda r: (int(r["malignant_S_2"] or 0), int(r["n_flags"]), int(r["added_ticks"] or 0),
                     int(r["malignant_T_3"] or 10 ** 6), int(r["id"]))
    return sorted(rows, key=key)


def _circuit_roles(inner, n_flags):
    """data = MPP targets; parity = qubits measured before the final measurement TICK;
    flags = the last n_flags qubits; flag type and control CXs from the gates."""
    from nnflags import zzflags as Z
    data = set(C.find_data_indices(inner))
    layers = C.split_by_ticks(inner)
    meas = {}
    for t, layer in enumerate(layers):
        for op in layer:
            if op.name != "MPP" and stim_gate(op.name).produces_measurements:
                for x in op.targets_copy():
                    meas.setdefault(x.value, []).append(t)
    final = max(t for ts in meas.values() for t in ts)
    parity = {q for q, ts in meas.items() if min(ts) < final}
    nq = inner.num_qubits
    flags = list(range(nq - n_flags, nq))
    _, gates = Z.flag_specs(inner, flags)
    return data, parity, flags, gates


def stim_gate(name):
    import stim
    return stim.gate_data(name)


def _draw_zz_circuit(ax, inner, emb, data, parity, flags, gates, hooks=(), label=None):
    draw_willow(ax, faint=True, line_labels=False)
    pairs = {tuple(sorted((a, b))) for _, _, a, b in C.two_qubit_gates(inner)}
    for a, b in sorted(pairs):
        (xa, ya), (xb, yb) = xy(emb[a]), xy(emb[b])
        if a in flags or b in flags:
            f = a if a in flags else b
            col = SKY if gates[f][0][2] == "Z" else ORANGE
            ax.plot([xa, xb], [ya, yb], color=col, lw=2.4, ls=(0, (3, 1.5)), zorder=3)
            q = b if f == a else a
            ts = ",".join(str(t) for t, qq, _ in sorted(gates[f]) if qq == q)
            ax.text((xa + xb) / 2, (ya + yb) / 2, "t" + ts, fontsize=6.2, color="black", ha="center",
                    va="center", zorder=6, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec=col, lw=0.6))
        else:
            ax.plot([xa, xb], [ya, yb], color=BLUE, lw=2.4, zorder=3)
    for L in sorted({readout_line(emb[q]) for q in parity}):
        _draw_line(ax, L, **PARITY_LINE)
        q0 = max((q for q in parity if readout_line(emb[q]) == L), key=lambda q: emb[q][1])
        x0, y0 = xy(emb[q0])
        ax.text(x0 + 0.75, y0 + 0.55, f"line {L}", fontsize=7, color="#8a5a00", zorder=1)
    for q, p in emb.items():
        x, y = xy(p)
        ec, lw = (VERMILION, 2.6) if q in hooks else ("black", 1.2)
        if q in flags:
            st = ZFLAG_STYLE if gates[q][0][2] == "Z" else XFLAG_STYLE
            ax.scatter([x], [y], **{**st, "edgecolor": ec, "linewidths": lw}, zorder=4)
        elif q in parity:
            ax.scatter([x], [y], s=250, marker="D", facecolor="#f0f0f0", edgecolor=ec, linewidths=lw,
                       hatch="....", zorder=4)
        else:
            ax.scatter([x], [y], s=220, marker="o" if q in data else "s", facecolor="white",
                       edgecolor=ec, linewidths=lw, zorder=4)
        ax.text(x, y, str(q), ha="center", va="center", fontsize=7.2, zorder=5,
                fontweight="bold" if q in data else "normal",
                bbox=dict(boxstyle="circle,pad=0.02", fc="white", ec="none") if q in parity or q in flags
                else None)
    zoom(ax, emb, pad=1.3)
    if label:
        ax.set_title(label, loc="left", fontsize=9, pad=44)


def _zz_legend(ax, anchor=(0.0, -0.1), ncol=3):
    h = [Line2D([], [], marker="o", ls="", mfc="white", mec="black", markersize=9, label="data qubit"),
         Line2D([], [], marker="s", ls="", mfc="white", mec="black", markersize=8, label="ancilla"),
         Line2D([], [], marker="D", ls="", mfc="#f0f0f0", mec="black", markersize=8,
                label="parity qubit (mid-circuit MRX)"),
         Line2D([], [], color=BLUE, lw=2.4, label="CX of the double check"),
         Line2D([], [], **PARITY_LINE, label="readout line r + c of the parity qubit"),
         Line2D([], [], marker="^", ls="", mfc="#e8e8e8", mec="black", markersize=9,
                label="Z flag (R, CX q->f, M)"),
         Line2D([], [], color=SKY, lw=2.4, ls=(0, (3, 1.5)), label="Z-flag CX, label = its TICKs"),
         Line2D([], [], marker="v", ls="", mfc="#f6e3b4", mec="black", markersize=9,
                label="X flag (RX, CX f->q, MX)"),
         Line2D([], [], color=ORANGE, lw=2.4, ls=(0, (3, 1.5)), label="X-flag CX, label = its TICKs"),
         Line2D([], [], marker="o", ls="", mfc="white", mec=VERMILION, mew=2.6, markersize=9,
                label="X-hook qubit of the unflagged base")]
    ax.legend(handles=h, loc="upper left", bbox_to_anchor=anchor, ncol=ncol, fontsize=7.2)


def _base_design(name):
    from nnflags import search_zzflags as S
    from nnflags import zzflags as Z
    if name == "G4":
        return Z.design_g4()
    t = next(x for x in S.tasks({}) if x[0] == name)
    return Z.design_from_option1(t[1], t[2], name=name)


def fig_zz_best_circuits(out, k=3):
    import stim
    from nnflags import zzflags as Z
    rows = _zz_rows()[:k]
    if not rows:
        return
    n = len(rows)
    fig = plt.figure(figsize=(5.6 * n, 8.2))
    gs = fig.add_gridspec(2, n, height_ratios=[5.2, 1.0], left=0.05, right=0.98, top=0.8, bottom=0.08,
                          wspace=0.25, hspace=0.25)
    axes = [fig.add_subplot(gs[0, i]) for i in range(n)]
    embs = []
    for ax, r in zip(axes, rows):
        inner = stim.Circuit.from_file(r["stim_file"])
        emb = {q: (int(a), int(b)) for q, (a, b) in C.native_coords(inner).items()}
        embs.append(emb)
        data, parity, flags, gates = _circuit_roles(inner, int(r["n_flags"]))
        hooks = set(Z.hook_qubits(_base_design(r["base"])))
        _draw_zz_circuit(ax, inner, emb, data, parity, flags, gates, hooks=hooks,
                         label=f"{Path(r['stim_file']).name.split('.')[0]} (base {r['base']}): "
                               f"{r['n_flags']} flags, +{r['added_ticks']} TICKs")
        ax.text(0.0, 1.01, f"malignant T: {r['malignant_T_1']} / {r['malignant_T_2']} / {r['malignant_T_3']} "
                f"at 1 / 2 / 3 faults; malignant S at <= 2 faults: {r['malignant_S_2']}\n"
                f"T error per kept shot: 0 (max_fault_count 2), {one_in(float(r['ler_T_mfc3']))} "
                f"(max_fault_count 3)\n{r['n_qubits']} qubits, {r['n_cx']} CX, max degree {r['max_degree']}",
                transform=ax.transAxes, fontsize=7, va="bottom", ha="left")
    half = max(max(max(p[0] for p in e.values()) - min(p[0] for p in e.values()),
                   max(p[1] for p in e.values()) - min(p[1] for p in e.values())) for e in embs) / 2 + 1.0
    for ax, e in zip(axes, embs):
        rc = (max(p[0] for p in e.values()) + min(p[0] for p in e.values())) / 2
        cc = (max(p[1] for p in e.values()) + min(p[1] for p in e.values())) / 2
        ax.set_xlim(cc - half, cc + half)
        ax.set_ylim(-rc - half, -rc + half)
    lax = fig.add_subplot(gs[1, :])
    lax.axis("off")
    _zz_legend(lax, anchor=(0.0, 1.0), ncol=4)
    fig.suptitle("Best fault-distance-3 double checks on Willow (0 malignant T configurations with <= 2 "
                 "faults), two flags each", x=0.01, ha="left", fontsize=11, y=0.97)
    fig.text(0.01, 0.02, ZZ_RULE, fontsize=7.2, ha="left", va="bottom")
    save(fig, out, "zz_best_circuits")


def fig_zz_malignant_bars(out, k=3):
    import csv
    res = json.loads((RESULTS / "g4_result.json").read_text())
    rows = {(r["variant"], r["max_fault_count"]): r for r in res["rows"]}
    names, m2, m3, styles = [], [], [], []
    ref_styles = [dict(facecolor=ORANGE, hatch="", edgecolor="black", linewidth=0.6),
                  dict(facecolor=GREY, hatch="xx", edgecolor="black", linewidth=0.6),
                  dict(facecolor=VERMILION, hatch="////", edgecolor="black", linewidth=0.6)]
    for (n, key), st in zip((("d3a6", "d3a6"), ("d3a4", "d3a4"),
                             ("G4\n(CX form)", "G4-CX (cliffordea T_z convention)")), ref_styles):
        r = rows[(key, 3)]
        names.append(n)
        m2.append(r["T"]["2"]["malignant"])
        m3.append(r["T"]["3"]["malignant"])
        styles.append(st)
    o1 = _ranked_candidates()
    if o1:
        r = o1[0]
        names.append(f"Option-1\ncand. {r['id']}")
        m2.append(int(r["malignant_T_2"]))
        m3.append(int(r["malignant_T_3"]))
        styles.append(dict(facecolor=SKY, hatch="\\\\", edgecolor="black", linewidth=0.6))
    for r in _zz_rows()[:k]:
        names.append(f"{Path(r['stim_file']).name.split('.')[0]}\nZZ + X")
        m2.append(int(r["malignant_T_2"]))
        m3.append(int(r["malignant_T_3"]))
        styles.append(dict(facecolor=GREEN, hatch="", edgecolor="black", linewidth=0.6))
    zo = RESULTS / "zz_zonly_best.json"
    if zo.exists():
        b = json.loads(zo.read_text())
        names.append("best\nZ-only")
        m2.append(int(b["malignant_T_2"]))
        m3.append(int(b["malignant_T_3"]))
        styles.append(dict(facecolor=BLUE, hatch="..", edgecolor="black", linewidth=0.6))
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.1))
    for ax, vals, title in ((axes[0], m2, "2 faults"), (axes[1], m3, "3 faults")):
        for i, (v, st) in enumerate(zip(vals, styles)):
            rect = ax.bar([i], [v], 0.62, **st)
            bar_label(ax, rect, [v])
        ax.set_xticks(range(len(names)), names, fontsize=6.8)
        ax.set_ylabel("malignant T configurations")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.set_major_formatter(FuncFormatter(plain))
        ax.set_ylim(0, max(vals) * 1.18 + 1)
        ax.set_title(f"kept malignant configurations with {title}", loc="left")
    fig.suptitle("Malignant T configurations: baselines, best Option-1 candidate and the best ZZ-flag "
                 "circuits", x=0.01, ha="left", fontsize=11, y=1.03)
    fig.text(0.01, -0.1, "d3a6, d3a4: cliffordea bundled double checks (not Willow-compatible under the "
             "strict readout rule); G4: Google's as-run double check, extracted (RESULTS_g4.md); "
             "Option-1 candidate: RESULTS_option1.md.\nZZ-flag circuits: this round (RESULTS_zzflags.md). "
             "Cultivated state T, cliffordea uniformly_depolarize, p = 0.001, max_fault_count 3.",
             fontsize=7.3, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "zz_malignant_comparison")


def fig_zz_tick_diagram(out):
    import stim
    rows = _zz_rows()
    if not rows:
        return
    r = rows[0]
    inner = stim.Circuit.from_file(r["stim_file"])
    data, parity, flags, gates = _circuit_roles(inner, int(r["n_flags"]))
    nq = inner.num_qubits
    tree = [q for q in range(nq) if q not in flags]
    order = sorted(parity) + [q for q in tree if q not in parity and q not in data] + sorted(data) + flags
    labels = {}
    for q in range(nq):
        role = ("parity" if q in parity else "data" if q in data else
                ("Z flag" if gates[q][0][2] == "Z" else "X flag") if q in flags else "ancilla")
        labels[q] = f"{q} ({role})"
    fig, ax = plt.subplots(figsize=(11.5, 0.42 * nq + 1.6))
    _timeline(ax, inner, order, labels, parity=parity, flags=set(flags))
    base_ticks = int(r["ticks"]) - int(r["added_ticks"])
    ax.set_title(f"{Path(r['stim_file']).name.split('.')[0]} (base {r['base']}): {r['flags']}\n"
                 f"{r['ticks']} TICKs = {base_ticks} of the base + {r['added_ticks']} inserted for the "
                 f"flag CXs; light-blue gates belong to the flags (Z flag: CX q -> f; X flag: CX f -> q)", loc="left", fontsize=9)
    fig.text(0.01, -0.02, "TICK numbers as in the stim file. M f / MX f in the final layer with "
             "MX of the ancillas; flag detectors checked deterministic with stim.\n" + ZZ_RULE,
             fontsize=7, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "zz_tick_diagram")


# ---- comparison round (RESULTS_comparison.md) ---------------------------------

COMP_MAIN = [  # (key in results/comparison.json, label, colour, marker, hatch)
    ("d3a6", "d3a6", ORANGE, "o", ""),
    ("d3a6f2", "d3a6f2", SKY, "s", "\\\\\\\\"),
    ("G4-CX", "G4 (CX form)", VERMILION, "^", "////"),
    ("cand03", "Option-1 cand03", GREY, "D", "xx"),
    ("success03", "success03 (ZZ + X)", GREEN, "v", ""),
]


def one_in_tick(x, _pos=None):
    return f"{x:,.0f}"


def fig_comparison_acceptance(out):
    rec = json.loads((RESULTS / "comparison.json").read_text())
    D = rec["designs"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.4), gridspec_kw=dict(width_ratios=[1, 1.35]))
    styles = ["-", "--", "-", ":", "-"]
    for j, (key, label, col, mk, _) in enumerate(COMP_MAIN):
        mc = D[key]["mc"]
        ps = sorted(mc, key=float)
        x = [float(p) * 100 * (1 + 0.025 * (j - 2)) for p in ps]  # small dodge: d3a6 ~ cand03
        y = [mc[p]["acceptance"] * 100 for p in ps]
        e = [mc[p]["se"] * 100 for p in ps]
        a1.errorbar(x, y, yerr=e, color=col, marker=mk, ms=5, lw=1.3, capsize=2, ls=styles[j],
                    markeredgecolor="black", markeredgewidth=0.5, label=label)
    a1.set_xlabel("physical error rate p (%)")
    a1.set_ylabel("acceptance: shots with no detector event (%)")
    a1.set_xticks([0.05, 0.1, 0.2, 0.3])
    a1.xaxis.set_major_formatter(FuncFormatter(plain))
    a1.yaxis.set_major_formatter(FuncFormatter(plain))
    a1.set_title("(a) acceptance vs p (stim Monte Carlo)", loc="left")
    a1.legend(loc="lower left")
    a1.grid(alpha=0.3, lw=0.5)
    w = 0.38
    xs = range(len(COMP_MAIN))
    for i, (key, label, col, mk, hatch) in enumerate(COMP_MAIN):
        t = D[key]["table"]
        for dx, val, h in ((-w / 2, 1 / t["rate_T_mfc3"], ""), (w / 2, 1 / t["T_error_per_attempt"], "////")):
            rect = a2.bar([i + dx], [val], w, facecolor=col, hatch=h, edgecolor="black", linewidth=0.6)
            a2.text(i + dx, val * 1.04, f"{val / 1e6:.2f}", ha="center", va="bottom", fontsize=6.8)
    a2.set_xticks(list(xs), [lbl.replace(" (", "\n(") for _, lbl, *_ in COMP_MAIN], fontsize=7.5)
    a2.set_ylabel("T error: 1 in N, N in millions (higher is better)")
    a2.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: plain(round(v / 1e6, 2))))
    a2.set_ylim(0, max(1 / D[k]["table"]["T_error_per_attempt"] for k, *_ in COMP_MAIN) * 1.15)
    a2.legend(handles=[Patch(facecolor="white", edgecolor="black", label="per kept shot"),
                       Patch(facecolor="white", edgecolor="black", hatch="////", label="per attempt")],
              loc="upper left")
    a2.set_title("(b) T logical error at p = 0.1 %, max_fault_count 3", loc="left")
    fig.text(0.01, -0.06, "cliffordea uniformly_depolarize at p, CX form for all five designs. Acceptance: "
             "stim detector sampler on the same noisy inner circuit, 10,000,000 shots at p = 0.1 %, "
             "4,000,000 otherwise; error bars = 1 standard error (smaller than the markers);\n"
             "points dodged horizontally by up to 5 % of p for visibility (d3a6 and cand03 overlap). "
             "Per kept shot: cliffordea error_rates_per_kept_shot (truncated at 3 faults). Per attempt = "
             "per kept shot x acceptance. d3a6 and d3a6f2 are not Willow-compatible.",
             fontsize=7.3, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "comparison_acceptance")


def fig_comparison_willow_noise(out):
    rec = json.loads((RESULTS / "willow_noise.json").read_text())
    D = rec["designs"]
    names = list(D)
    models = [("uniform", "uniform p = 0.1 % (native)", BLUE, ""),
              ("spec", "Willow spec-sheet averages", ORANGE, "\\\\\\\\"),
              ("calibration", "Willow calibration (per qubit / coupler)", VERMILION, "////")]

    def val(n, m, what):
        r = D[n]
        if m == "uniform":
            u = r["uniform_native_p001"]
            return dict(rate=u["rate_T"], acc=u["acc"], att=1 / u["acc"],
                        per_att=u["rate_T"] * u["acc"])[what]
        x = r["models"][m]
        return dict(rate=x["rate_T"], acc=x["mc"]["acceptance"], att=x["attempts"],
                    per_att=x["T_error_per_attempt"])[what]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    w = 0.27
    labels = [n + ("\n(what if)" if n in ("d3a6", "d3a6f2") else "") for n in names]
    for ax, what, ylab, title in (
            (axes[0], "rate", "T error per kept shot: 1 in N (thousands)", "(a) T error per kept shot"),
            (axes[1], "acc", "acceptance (%)", "(b) acceptance (no detector event)"),
            (axes[2], "per_att", "T error per attempt: 1 in N (thousands)", "(c) T error per attempt")):
        for j, (m, lbl, col, h) in enumerate(models):
            for i, n in enumerate(names):
                v = val(n, m, what)
                y = v * 100 if what == "acc" else 1 / v / 1e3
                ax.bar([i + (j - 1) * w], [y], w, facecolor=col, hatch=h, edgecolor="black",
                       linewidth=0.6, label=lbl if i == 0 else None)
        ax.set_xticks(range(len(names)), labels, fontsize=7.2)
        ax.set_ylabel(ylab)
        ax.set_yscale("log" if what != "acc" else "linear")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:,.0f}"))
        ax.yaxis.set_minor_formatter(FuncFormatter(
            lambda v, _p: f"{v:,.0f}" if round(v) in (20, 50, 200, 500, 2000) else ""))
        ax.set_title(title, loc="left")
        ax.grid(axis="y", alpha=0.3, lw=0.5)
    axes[1].set_ylim(0, 100)
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.07), fontsize=8)
    fig.text(0.01, -0.07, "All circuits in native CZ + H form at their Willow positions; d3a6 and d3a6f2 are "
             "not Willow-compatible (\"what if\" placements). T error: cliffordea kept configurations "
             "(max_fault_count 3) weighted with per-location channel strengths.\nAcceptance: stim Monte Carlo, "
             "4,000,000 shots per bar (10,000,000 for uniform), asymmetric readout in the calibration "
             "model. Settings and every number: RESULTS_comparison.md, section \"Realistic Willow noise\".",
             fontsize=7.3, ha="left", va="top")
    fig.tight_layout()
    save(fig, out, "comparison_willow_noise")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="figures")
    parser.add_argument("--only", choices=["all", "option1", "zz", "comparison"], default="all",
                        help="option1: only the Option-1 figures (the older figures are tied to "
                             "results/step1.json, computed under the Step-3 readout rule)")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.only == "comparison":
        fig_comparison_acceptance(out)
        if (RESULTS / "willow_noise.json").exists():
            fig_comparison_willow_noise(out)
        return
    if args.only == "zz":
        fig_zz_best_circuits(out)
        fig_zz_malignant_bars(out)
        fig_zz_tick_diagram(out)
        return
    if args.only == "option1":
        fig_option1_g4_extracted(out)
        fig_option1_conflict_table(out)
        fig_option1_best_candidates(out)
        fig_option1_malignant_bars(out)
        return
    tables, records = load_step0()
    step1 = json.loads((RESULTS / "step1.json").read_text())
    fig_step0_configurations(out, tables, records)
    fig_step0_malignant_weight(out, tables, records)
    fig_willow_grid(out)
    fig_embedding_d3a6(out, step1)
    fig_embedding_d3a6f2(out, step1)
    fig_step2_verify_check(out, tables, records)
    fig_google_on_willow(out)
    fig_embedding_histogram(out)
    if (RESULTS / "step3_summary.json").exists():
        fig_step3_candidates(out)


if __name__ == "__main__":
    main()
