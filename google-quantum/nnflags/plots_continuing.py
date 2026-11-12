"""Figures of the continuing-data search round (RESULTS_continuing_search.md). PNG only.

    .venv/bin/python -m nnflags.plots_continuing [--out figures]

  * continuing_circuits.png: Google's G6 cultivation patch and the best new
    circuit(s) on Willow; readout lines r + c of data qubits (blue bands) and of
    measured qubits (orange dashed bands) drawn separately, roles from the MPP
    targets and from the measurements.
  * continuing_comparison.png: G4, G4 as run in G6 (q7 unmeasured), success03 and
    the new best: malignant T at 2 / 3 faults, continuing-data conflicts, T error
    per kept shot (uniform p = 0.1 % and Willow calibration model).
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import stim
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

from nnflags import constraints as C
from nnflags import g6_continuing as G6
from nnflags.plots import (BLUE, GREEN, GREY, ORANGE, SKY, VERMILION, draw_willow, one_in, save, xy)
from nnflags.willow import readout_line

R = Path("results")


def roles(inner):
    """data (MPP targets), measured non-data qubits, mid-measured (parity) qubits,
    unmeasured ancillas, flags {q: 'Z'|'X'} (qubits whose every 2q gate is a probe:
    R + CX q->f + M or RX + CX f->q + MX, measured only in the final layer)."""
    data = set(C.find_data_indices(inner))
    meas_t = {}
    for t, layer in enumerate(C.split_by_ticks(inner)):
        for name, qs, gd in C._hardware_ops(layer):
            if gd.produces_measurements:
                for q in qs:
                    meas_t.setdefault(q, []).append((t, name))
    final = max(t for v in meas_t.values() for t, _ in v)
    used = {q for _, _, a, b in C.two_qubit_gates(inner) for q in (a, b)}
    parity = {q for q, v in meas_t.items() if min(t for t, _ in v) < final}
    unmeasured = used - data - set(meas_t)
    return data, set(meas_t) - data, parity, unmeasured


def flag_types(inner, n_flags):
    nq = inner.num_qubits
    out = {}
    for f in range(nq - n_flags, nq):
        g = [(a, b) for _, _, a, b in C.two_qubit_gates(inner) if f in (a, b)]
        out[f] = "Z" if g and g[0][1] == f else "X"
    return out


def band(ax, L, lo, hi, kind):
    xs = [lo, hi]
    ys = [x - L for x in xs]
    if kind == "data":
        ax.plot(xs, ys, color=BLUE, lw=11, alpha=0.16, solid_capstyle="butt", zorder=0.5)
    else:
        ax.plot(xs, ys, color=ORANGE, lw=3.0, alpha=0.9, ls=(0, (4, 3)), zorder=0.5)


def draw_circuit(ax, inner, emb, flags=None, title=""):
    flags = flags or {}
    data, measured, parity, unmeasured = roles(inner)
    draw_willow(ax, faint=True, line_labels=False)
    xs = [xy(p)[0] for p in emb.values()]
    lo, hi = min(xs) - 2.5, max(xs) + 2.5
    dl = sorted({readout_line(emb[q]) for q in data})
    ml = sorted({readout_line(emb[q]) for q in measured})
    for L in dl:
        band(ax, L, lo, hi, "data")
    for L in ml:
        band(ax, L, lo, hi, "measured")
    pairs = {tuple(sorted((a, b))) for _, _, a, b in C.two_qubit_gates(inner)}
    for a, b in sorted(pairs):
        (xa, ya), (xb, yb) = xy(emb[a]), xy(emb[b])
        f = a if a in flags else b if b in flags else None
        if f is None:
            ax.plot([xa, xb], [ya, yb], color="black", lw=1.8, zorder=3)
        else:
            ax.plot([xa, xb], [ya, yb], color=SKY if flags[f] == "Z" else VERMILION, lw=2.0,
                    ls=(0, (3, 1.5)), zorder=3)
    for q, p in emb.items():
        if q not in data | measured | unmeasured:
            continue
        x, y = xy(p)
        if q in flags:
            ax.scatter([x], [y], s=210, marker="^" if flags[q] == "Z" else "v", facecolor="#e8e8e8",
                       edgecolor="black", linewidths=1.2, zorder=4)
        elif q in parity:
            ax.scatter([x], [y], s=230, marker="D", facecolor=ORANGE, edgecolor="black", linewidths=1.2,
                       hatch="....", zorder=4)
        elif q in measured:
            ax.scatter([x], [y], s=200, marker="s", facecolor="#fbe3b0", edgecolor="black",
                       linewidths=1.2, zorder=4)
        elif q in unmeasured:
            ax.scatter([x], [y], s=200, marker="s", facecolor="white", edgecolor="black",
                       linewidths=1.2, linestyle="--", zorder=4)
        else:
            ax.scatter([x], [y], s=200, marker="o", facecolor="#cfe3f3", edgecolor="black",
                       linewidths=1.2, zorder=4)
        ax.text(x, y, str(q), ha="center", va="center", fontsize=6.5, zorder=5)
    ys = [xy(p)[1] for p in emb.values()]
    half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 1.4
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    ax.set_xlim(cx - half, cx + half)
    ax.set_ylim(cy - half, cy + half)
    ax.set_title(title, loc="left", fontsize=8.5)
    ax.text(0.0, -0.13, f"data lines r + c: {', '.join(map(str, dl))}\n"
            f"measured-qubit lines: {', '.join(map(str, ml))}  (disjoint: "
            f"{'yes' if not set(dl) & set(ml) else 'NO'})", transform=ax.transAxes, fontsize=7.2, va="top")


def legend(fig):
    h = [Line2D([], [], marker="o", ls="", mfc="#cfe3f3", mec="black", markersize=9, label="data qubit (continues)"),
         Line2D([], [], marker="D", ls="", mfc=ORANGE, mec="black", markersize=8, label="parity root (mid-check readout)"),
         Line2D([], [], marker="s", ls="", mfc="#fbe3b0", mec="black", markersize=8, label="ancilla, read out at the end"),
         Line2D([], [], marker="s", ls="", mfc="white", mec="black", markersize=8, label="ancilla never read out (reset only)"),
         Line2D([], [], marker="^", ls="", mfc="#e8e8e8", mec="black", markersize=9, label="Z flag"),
         Line2D([], [], marker="v", ls="", mfc="#e8e8e8", mec="black", markersize=9, label="X flag"),
         Line2D([], [], color=BLUE, lw=9, alpha=0.25, label="readout line of a data qubit"),
         Line2D([], [], color=ORANGE, lw=3, ls=(0, (4, 3)), label="readout line of a measured qubit"),
         Line2D([], [], color="black", lw=1.8, label="CX / CZ of the double check"),
         Line2D([], [], color=SKY, lw=2, ls=(0, (3, 1.5)), label="Z-flag CX"),
         Line2D([], [], color=VERMILION, lw=2, ls=(0, (3, 1.5)), label="X-flag CX")]
    fig.legend(handles=h, loc="lower left", ncol=4, fontsize=7.2, frameon=False, bbox_to_anchor=(0.01, 0.0))


def fig_circuits(out, new, with_g6=False):
    """new = [(label, inner stim path, n_flags, stats text)]; with_g6 adds Google's G6 panel first"""
    g, emb6 = G6.load_g6()
    data6 = G6.tagged_targets(g, "T_gate")
    cult = G6.sub_circuit(g, 31, 57)   # double check + its readout (TICKs 31-56)
    # the G6 double check as an inner-like circuit with an MPP marker on the data, so that
    # roles() finds the data
    c6 = stim.Circuit()
    for q, p in emb6.items():
        if q in set(data6) | {3, 9, 11, 12, 19}:
            c6.append("QUBIT_COORDS", [q], p)
    c6.append("MPP", [x for q in data6 for x in (stim.target_x(q), stim.target_combiner())][:-1])
    c6.append("TICK")
    c6 += cult
    e6 = {q: p for q, p in emb6.items() if q in set(data6) | {3, 9, 11, 12, 19}}
    n = int(with_g6) + len(new)
    fig, axes = plt.subplots(1, n, figsize=(max(4.6 * n, 8.6), 6.0 if n > 1 else 7.6))
    axes = list(axes) if n > 1 else [axes]
    if with_g6:
        draw_circuit(axes[0], c6, e6, title="Google G6 (Rosenfeld et al. Fig. 4):\ncultivation double check, as run")
    for ax, (label, path, nf, stats) in zip(axes[int(with_g6):], new):
        inner = stim.Circuit.from_file(path)
        emb = {q: (int(a), int(b)) for q, (a, b) in C.native_coords(inner).items()}
        draw_circuit(ax, inner, emb, flags=flag_types(inner, nf), title=label)
        ax.text(0.0, -0.25, stats, transform=ax.transAxes, fontsize=7.2, va="top")
    fig.subplots_adjust(left=0.04 if n > 1 else 0.1, right=0.99, top=0.9 if n > 1 else 0.84,
                        bottom=0.3, wspace=0.18)
    legend(fig)
    fig.suptitle("Readout lines when the data continue: data lines (blue) and\nmeasured-qubit lines "
                 "(orange) must be disjoint", x=0.01, ha="left", fontsize=10)
    # layout figure lives with the QVM test of the same circuits (Google device check passes there)
    save(fig, Path("qvm-google (main)/test2_cs02_continuing_data_vs_google/figures"), "continuing_circuits")


def fig_comparison(out, val, names, labels):
    D = val["designs"]
    styles = [dict(facecolor=VERMILION, hatch="////"), dict(facecolor=ORANGE, hatch="\\\\\\\\"),
              dict(facecolor=GREY, hatch="xx"), dict(facecolor=GREEN, hatch=""),
              dict(facecolor=SKY, hatch=".."), dict(facecolor=BLUE, hatch="--")]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.9))
    x = list(range(len(names)))

    def bars(ax, vals, title, ylabel, fmt=str):
        rs = ax.bar(x, vals, width=0.7, edgecolor="black", linewidth=0.6)
        for r, st in zip(rs, styles):
            r.set_facecolor(st["facecolor"])
            r.set_hatch(st["hatch"])
        for xi, v in zip(x, vals):
            ax.text(xi, v, fmt(v), ha="center", va="bottom", fontsize=7)
        ax.set_xticks(x, labels, rotation=30, ha="right", fontsize=7.5)
        ax.set_title(title, fontsize=9, loc="left")
        ax.set_ylabel(ylabel)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:,.0f}"))

    bars(axes[0], [D[n]["mfc3"]["T"]["2"]["malignant"] for n in names], "(a) malignant T, 2 faults",
         "configurations")
    bars(axes[1], [D[n]["mfc3"]["T"]["3"]["malignant"] for n in names], "(b) malignant T, 3 faults",
         "configurations")
    bars(axes[2], [D[n]["continuing"] for n in names], "(c) continuing-data conflicts", "violations")
    ax = axes[3]
    w = 0.38
    u = [1 / D[n]["uniform"]["rate_T_mfc3"] for n in names]
    c = [1 / D[n]["willow"]["calibration"]["rate_T"] for n in names]
    r1 = ax.bar([i - w / 2 for i in x], u, width=w, facecolor=BLUE, edgecolor="black", linewidth=0.6,
                label="uniform p = 0.1 %, CX")
    r2 = ax.bar([i + w / 2 for i in x], c, width=w, facecolor=ORANGE, hatch="////", edgecolor="black",
                linewidth=0.6, label="Willow calibration, CZ + H")
    ax.set_yscale("log")
    ticks = [10_000, 100_000, 1_000_000, 10_000_000]
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"1 in {v:,.0f}"))
    ax.set_ylim(8_000, 30_000_000)
    ax.set_xticks(x, labels, rotation=30, ha="right", fontsize=7.5)
    ax.set_title("(d) T error per kept shot (mfc 3)", fontsize=9, loc="left")
    ax.set_ylabel("higher is better")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    save(fig, out, "continuing_comparison")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="figures")
    ap.add_argument("--val", default="results/continuing_validation.json")
    ap.add_argument("--new", nargs="*", help="label=path=n_flags entries", default=[
        r"cs02 (best): ZZ + X flag,\nfault distance 3, 12 qubits=results/continuing/success02.inner.stim=2"])
    ap.add_argument("--with-g6", action="store_true", help="add Google's G6 panel to continuing_circuits")
    a = ap.parse_args()
    out = Path(a.out)
    val = json.loads(Path(a.val).read_text())
    new = []
    for s in a.new:
        label, path, nf = s.split("=")
        label = label.replace("\\n", "\n")
        name = Path(path).name.split(".")[0]
        d = val["designs"].get(name)
        stats = ""
        if d:
            stats = (f"malignant T at 1 / 2 / 3 faults: {d['mfc3']['T']['1']['malignant']} / "
                     f"{d['mfc3']['T']['2']['malignant']} / {d['mfc3']['T']['3']['malignant']}\n"
                     f"T error per kept shot (p = 0.1 %, mfc 3): {one_in(d['uniform']['rate_T_mfc3'])}\n"
                     f"{d['qubits']} qubits, {d['n_2q']} CX, continuing conflicts {d['continuing']}, "
                     f"strict {sum(d['strict'].values())}")
        new.append((label, path, int(nf), stats))
    fig_circuits(out, new, with_g6=a.with_g6)
    names = [n for n in val["designs"]]
    order = ["G4-CX", "G4-G6style", "success03"] + [n for n in names if n not in ("G4-CX", "G4-G6style", "success03")]
    # cs = results/continuing/success*; "old success03" = results/zz/success03 (same names, different rounds)
    lab = {"G4-CX": "G4 (as run)", "G4-G6style": "G4 G6-style", "success03": "old success03"}
    fig_comparison(out, val, order, [lab.get(n, n.replace("success", "cs")) for n in order])


if __name__ == "__main__":
    main()
