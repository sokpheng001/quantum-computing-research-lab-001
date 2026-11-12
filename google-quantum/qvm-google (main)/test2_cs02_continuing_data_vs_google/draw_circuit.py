"""Gate-level drawing of a cultivation double-check circuit given as a stim file
(default: cs02 = results/continuing/success02.inner.stim).

Qubit lines run left to right, one column per TICK; CNOTs of one TICK whose vertical
lines would overlap are split into sub-columns. Rows are grouped by role (data,
check ancillas, flags) and the fold / check / unfold sections are labelled.

    .venv/bin/python "qvm-google (main)/test2_cs02_continuing_data_vs_google/draw_circuit.py"
    -> figures/cs02_circuit.png
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import stim  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# cs02 roles (RESULTS_continuing_search.md, Successes table)
ROLES = {
    "data": [1, 2, 4, 5, 6, 8, 9],
    "check ancilla": [0, 3, 7],
    "ZZ flag": [10],
    "X flag": [11],
}
INK, MUTED = "black", "0.45"


def layers(circuit):
    """Split into TICK layers of (name, targets) keeping only drawable gates."""
    out, cur = [], []
    for op in circuit.flattened():
        if op.name == "TICK":
            out.append(cur)
            cur = []
        elif op.name not in ("DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS"):
            cur.append(op)
    if cur:
        out.append(cur)
    return [layer for layer in out if layer]


def columns(layer, row):
    """Turn one TICK layer into drawing columns; overlapping CX pairs go to new columns."""
    cols = [[]]
    spans = [[]]
    for op in layer:
        t = op.targets_copy()
        if op.name == "CX":
            for a, b in zip(t[::2], t[1::2]):
                lo, hi = sorted((row[a.value], row[b.value]))
                for c, s in zip(cols, spans):
                    if all(hi < l or lo > h for l, h in s):
                        c.append(("CX", a.value, b.value))
                        s.append((lo, hi))
                        break
                else:
                    cols.append([("CX", a.value, b.value)])
                    spans.append([(lo, hi)])
        elif op.name == "MPP":
            qs = [x.value for x in t if not x.is_combiner]
            cols[0].append(("MPP", qs))
        else:
            for x in t:
                cols[0].append((op.name, x.value))
    return cols


def draw(stim_file, out, title):
    c = stim.Circuit.from_file(str(stim_file))
    order = [q for qs in ROLES.values() for q in qs]
    row = {q: i for i, q in enumerate(order)}
    role_of = {q: r for r, qs in ROLES.items() for q in qs}
    co = c.get_final_qubit_coordinates()

    cols, tick_of = [], []
    for k, layer in enumerate(layers(c)):
        for col in columns(layer, row):
            cols.append(col)
            tick_of.append(k)

    dx = 0.75
    x_of = []
    x = 0.0
    for i in range(len(cols)):
        if i and tick_of[i] != tick_of[i - 1]:
            x += 0.35  # gap between TICKs
        x_of.append(x)
        x += dx
    width = x

    fig, ax = plt.subplots(figsize=(0.42 * width + 3.2, 0.52 * len(order) + 1.6))
    for q in order:
        y = -row[q]
        ax.plot([-0.4, width - 0.3], [y, y], color=MUTED, lw=0.8, zorder=0)
        ax.text(-0.6, y, f"q{q} {tuple(int(v) for v in co[q])}", ha="right", va="center", fontsize=9)
    # role brackets
    for r, qs in ROLES.items():
        ys = [-row[q] for q in qs]
        xb = -3.55
        ax.plot([xb, xb], [min(ys) - 0.25, max(ys) + 0.25], color=INK, lw=0.8)
        ax.text(xb - 0.15, sum(ys) / len(ys), r, ha="right", va="center", fontsize=9)

    box = dict(boxstyle="square,pad=0.15", fc="white", ec=INK, lw=0.8)
    mid_x = None
    for x, col in zip(x_of, cols):
        for g in col:
            if g[0] == "CX":
                _, a, b = g
                ya, yb = -row[a], -row[b]
                ax.plot([x, x], [ya, yb], color=INK, lw=1.0, zorder=1)
                ax.plot(x, ya, "o", color=INK, ms=5, zorder=2)
                ax.plot(x, yb, "o", mfc="white", mec=INK, ms=11, mew=1.0, zorder=2)
                ax.plot([x - 0.13, x + 0.13], [yb, yb], color=INK, lw=1.0, zorder=3)
                ax.plot([x, x], [yb - 0.13, yb + 0.13], color=INK, lw=1.0, zorder=3)
            elif g[0] == "MPP":
                ys = [-row[q] for q in g[1]]
                ax.add_patch(plt.Rectangle((x - 0.3, min(ys) - 0.3), 0.6, max(ys) - min(ys) + 0.6,
                                           fc="white", ec=INK, lw=0.8, zorder=2))
                ax.text(x, (min(ys) + max(ys)) / 2, "MPP\nX on\nall 7\ndata", ha="center", va="center",
                        fontsize=7, zorder=3)
            else:
                name, q = g
                label = {"R": "|0⟩", "RX": "|+⟩", "M": "M", "MX": "MX", "MRX": "MRX"}.get(name, name)
                ax.text(x, -row[q], label, ha="center", va="center", fontsize=7, bbox=box, zorder=3)
                if name == "MRX":
                    mid_x = x

    # section labels
    top = 0.9
    first_cx = next(x for x, col in zip(x_of, cols) if any(g[0] == "CX" for g in col))
    last_cx = max(x for x, col in zip(x_of, cols) if any(g[0] == "CX" for g in col))
    for a, b, lab in [(first_cx, mid_x - 0.5, "fold"), (mid_x - 0.3, mid_x + 0.3, "check"),
                      (mid_x + 0.5, last_cx, "unfold")]:
        ax.annotate("", (a - 0.2, top), (b + 0.2, top), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.8))
        ax.text((a + b) / 2, top + 0.3, lab, ha="center", va="bottom", fontsize=10)
    for x in (mid_x - 0.5, mid_x + 0.5):
        ax.axvline(x, color=MUTED, lw=0.6, ls=":", zorder=0)

    ax.set_title(title, fontsize=11, pad=24)
    ax.set_xlim(-6.6, width)
    ax.set_ylim(-len(order) + 0.4, top + 1.0)
    ax.axis("off")
    fig.tight_layout()
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=200)
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stim", default=str(ROOT / "results/continuing/success02.inner.stim"))
    ap.add_argument("--out", default=str(HERE / "figures/cs02_circuit.png"))
    ap.add_argument("--title", default="cs02: double check with ZZ flag (q10) and X flag (q11), "
                                       "12 qubits, 24 CNOTs, fault distance 3")
    a = ap.parse_args()
    draw(Path(a.stim), Path(a.out), a.title)


if __name__ == "__main__":
    main()
