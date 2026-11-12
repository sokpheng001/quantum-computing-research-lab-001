"""
Circuit figures (PNG + PDF in figures/). Builds circuits only; no simulation is run.
  F6  logical programs of full_stack_sim.py, as written and after Clifford+T compilation
  F7  physical Stim circuits behind the logical error rates: d = 5 surface-code memory
      and the end-to-end cultivation factory (d1 = 3 color code grown to d2 = 15)
python plot_circuits.py
"""

import os
import sys

import matplotlib.pyplot as plt
import stim
from matplotlib.patches import FancyBboxPatch, Rectangle

import full_stack_sim as fs
from plot_results import AQUA, BLUE, FIG, HERE, INK, MUTED, ORANGE, YELLOW, save

sys.path.insert(0, os.path.join(HERE, "Magic state cultivation", "code", "src"))
import cultiv  # noqa: E402

GATE_COLOR = {"t": ORANGE, "tdg": ORANGE, "h": BLUE, "x": BLUE, "measure": MUTED}
LABEL = {"t": "T", "tdg": "T†", "h": "H", "x": "X", "measure": "M"}


# ------------------------------------------------------------------ F6 logical programs
def layers(qc) -> list:
    """Greedy ASAP columns: [(column, gate name, [qubit indices])]."""
    free, out = {}, []
    for inst in qc.data:
        qs = [qc.find_bit(q).index for q in inst.qubits]
        span = range(min(qs), max(qs) + 1)
        col = max(free.get(q, 0) for q in span)
        for q in span:
            free[q] = col + 1
        out.append((col, inst.operation.name, qs))
    return out


def draw_circuit(ax, qc, title: str, columns: int = 4, rows: int = 3, all_wires: bool = False) -> None:
    """Draw on a fixed columns x rows canvas so panels share one gate size."""
    gates = layers(qc)
    wires = list(range(qc.num_qubits)) if all_wires else sorted({q for _, _, qs in gates for q in qs})
    row = {q: -i for i, q in enumerate(wires)}
    width = max(c for c, _, _ in gates) + 1
    for q in wires:
        ax.plot([-0.6, width - 0.4], [row[q]] * 2, color=MUTED, lw=1, zorder=1)
        ax.text(-0.8, row[q], f"q{q}", ha="right", va="center", fontsize=9)
    for col, name, qs in gates:
        if name in ("cx", "ccx"):
            *ctrls, tgt = qs
            ax.plot([col, col], [row[min(qs)], row[max(qs)]], color=INK, lw=1.2, zorder=2)
            for c in ctrls:
                ax.plot(col, row[c], "o", color=INK, ms=6, zorder=3)
            ax.plot(col, row[tgt], "o", mfc="white", mec=INK, ms=13, mew=1.2, zorder=3)
            ax.plot([col - 0.17, col + 0.17], [row[tgt]] * 2, color=INK, lw=1.2, zorder=4)
            ax.plot([col, col], [row[tgt] - 0.17, row[tgt] + 0.17], color=INK, lw=1.2, zorder=4)
            continue
        color = GATE_COLOR.get(name, INK)
        ax.add_patch(FancyBboxPatch((col - 0.3, row[qs[0]] - 0.3), 0.6, 0.6, boxstyle="round,pad=0.02",
                                    fc=color if name != "measure" else "white", ec=color, lw=1.2, zorder=3))
        ax.text(col, row[qs[0]], LABEL.get(name, name), ha="center", va="center", fontsize=9,
                color="white" if name != "measure" else INK, fontweight="bold", zorder=4)
    ax.set_xlim(-1.6, max(width, columns) - 0.2)
    ax.set_ylim(-max(len(wires), rows) + 0.4, 0.6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=10, loc="left")


def f6() -> None:
    progs = [(name, fs.load(q)) for name, q in fs.EXAMPLES.items()]
    widest = max(max(c for c, _, _ in layers(fs.compile_clifford_t(qc))) + 1 for _, qc in progs)
    fig = plt.figure(figsize=(11, 5.6))
    grid = fig.add_gridspec(2, 3, width_ratios=[1, 1, 3.2])
    for r, (name, qc) in enumerate(progs):
        comp = fs.compile_clifford_t(qc)
        info = fs.analyse(comp)
        draw_circuit(fig.add_subplot(grid[r, 0]), qc, f"{name}: input")
        arrow = fig.add_subplot(grid[r, 1])
        arrow.axis("off")
        arrow.annotate("", (0.9, 0.5), (0.1, 0.5), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.5))
        arrow.text(0.5, 0.6, "compile to\nClifford + T", ha="center", va="bottom", fontsize=8, color=MUTED)
        note = "T removed (no effect before measurement)" if name == "useless T" else \
            f"{info['t_count']} T/T† = {info['t_count']} magic states from the factory"
        draw_circuit(fig.add_subplot(grid[r, 2]), comp, f"compiled: T count {info['t_count']} · {note}",
                     columns=widest)
    fig.suptitle("F6 · Logical programs run by the pipeline", fontweight="bold")
    save(fig, "F6_programs", "full_stack_sim.EXAMPLES, compiled by full_stack_sim.compile_clifford_t (Qiskit transpile + "
         "dropping diagonal gates before measurement). Orange = T/T† (each consumes one cultivated magic state); "
         "blue = Clifford; M = measurement. Unused qubits are not drawn.")


# ------------------------------------------------------------------ F7 physical circuits
def memory_roles(c: stim.Circuit) -> dict:
    """Role of each qubit in Stim's rotated memory circuit: data, X-check or Z-check."""
    flat = c.flattened()
    measured_last = [op for op in flat if op.name == "M"][-1]
    data = {t.value for t in measured_last.targets_copy()}
    hadamard = {t.value for op in flat if op.name == "H" for t in op.targets_copy()}
    roles = {}
    for q in c.get_final_qubit_coordinates():
        roles[q] = "data" if q in data else ("X check" if q in hadamard else "Z check")
    return roles


def touched_before(c: stim.Circuit, ticks: int) -> set:
    qs, tick = set(), 0
    for op in c.flattened():
        if op.name == "TICK":
            tick += 1
            if tick >= ticks:
                break
        elif op.name not in ("DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS", "SHIFT_COORDS"):
            qs |= {t.value for t in op.targets_copy() if t.is_qubit_target}
    return qs


def f7() -> None:
    mem = stim.Circuit.generated("surface_code:rotated_memory_z", distance=5, rounds=5)
    ungrown = cultiv.make_inject_and_cultivate_circuit(dcolor=3, inject_style="unitary", basis="Y")
    e2e = cultiv.make_end2end_cultivation_circuit(dcolor=3, dsurface=15, basis="Y", r_growing=3, r_end=5,
                                                  inject_style="unitary")
    fig = plt.figure(figsize=(12, 7.4))
    grid = fig.add_gridspec(2, 2, height_ratios=[2.4, 1], width_ratios=[1, 1.35])

    # (a) surface-code memory
    ax = fig.add_subplot(grid[0, 0])
    coords, roles = mem.get_final_qubit_coordinates(), memory_roles(mem)
    style = {"data": (INK, "o", 9), "X check": (BLUE, "s", 8), "Z check": (ORANGE, "s", 8)}
    for role, (color, m, ms) in style.items():
        pts = [coords[q] for q in coords if roles[q] == role]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], m, color=color, ms=ms, ls="none",
                label=f"{role} qubits ({len(pts)})")
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.axis("off")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=3)
    ax.set_title(f"(a) Data memory: surface code d = 5, {len(coords)} qubits\n"
                 f"5 QEC cycles per shot · {mem.num_detectors} detectors · decoded by PyMatching\n"
                 "p = 0.1% → 1 in 38,000 logical error per cycle", fontsize=9.5, loc="left")

    # (b) end-to-end factory layout
    ax = fig.add_subplot(grid[0, 1])
    ec = e2e.get_final_qubit_coordinates()
    seed = touched_before(e2e, ungrown.num_ticks)
    grow = [q for q in ec if q not in seed]
    ax.plot([ec[q][0] for q in grow], [ec[q][1] for q in grow], "o", color=AQUA, ms=3.2, ls="none",
            label=f"grown surface code d2 = 15 ({len(grow)} qubits)")
    ax.plot([ec[q][0] for q in seed], [ec[q][1] for q in seed], "*", color=ORANGE, mec=INK, mew=0.5, ms=7,
            ls="none", label=f"injection + cultivation, color code d1 = 3 ({len(seed)} qubits)")
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.axis("off")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=1)
    ax.set_title(f"(b) Magic-state factory (end-to-end): {e2e.num_qubits} qubits, {e2e.num_detectors:,} detectors\n"
                 "p = 0.1% → 1 in 479,000 error per T state, 77.5% discarded", fontsize=9.5, loc="left")

    # (c) factory timeline
    ax = fig.add_subplot(grid[1, :])
    t_cult, t_all = ungrown.num_ticks, e2e.num_ticks
    stages = [(0, t_cult, ORANGE, f"inject + cultivate\ncolor code d1 = 3, {len(seed)} qubits\n"
                                  "any detector fires → discard"),
              (t_cult, t_all - t_cult, AQUA, "escape: grow into surface code d2 = 15 (3 cycles), then hold (5 cycles)\n"
                                             f"{e2e.num_qubits} qubits · decoder gap < 69 dB → discard")]
    for x0, w, color, text in stages:
        ax.add_patch(Rectangle((x0, 0), w, 1, fc=color, ec="white", lw=2, alpha=0.9))
        ax.text(x0 + w / 2, 0.5, text, ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")
    ax.annotate("T state\n(S state in Stim, error ×2)", (t_all + 1, 0.5), (t_all + 14, 0.5), ha="left",
                va="center", fontsize=8.5, arrowprops=dict(arrowstyle="<|-", color=INK))
    ax.set_xlim(-1, t_all + 32)
    ax.set_xticks([0, t_cult, t_all])
    ax.spines["bottom"].set_bounds(0, t_all)
    ax.set_ylim(-0.1, 1.1)
    ax.set_yticks([])
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("circuit time step (Stim TICK)")
    ax.set_title(f"(c) One factory shot over time: {t_all} time steps", fontsize=9.5, loc="left")

    fig.suptitle("F7 · Physical circuits simulated with Stim (uniform depolarizing p = 0.1%)", fontweight="bold")
    save(fig, "F7_physical", "Layouts from the circuits' own QUBIT_COORDS. (a) stim.Circuit.generated('surface_code:"
         "rotated_memory_z', distance=5, rounds=5). (b, c) cultiv.make_end2end_cultivation_circuit(dcolor=3, dsurface=15, "
         "basis='Y', r_growing=3, r_end=5, inject_style='unitary'); stars = qubits used in the first "
         f"{ungrown.num_ticks} time steps (= length of the injection + cultivation circuit).")


# ------------------------------------------------------------------ F8 injection + cultivation, gate level
STIM_LABEL = {"R": "|0⟩", "RX": "|+⟩", "M": "M", "MX": "Mx", "S": "S", "S_DAG": "S†"}
# (first tick, last tick, color, title) for cultiv.make_inject_and_cultivate_circuit(dcolor=3, 'unitary', 'Y')
F8_STAGES = [(0, 14, ORANGE, "1. injection: S† on q3 (the T stand-in),\nthen encoded into the d1 = 3 color code"),
             (15, 24, BLUE, "2. stabilizer check\n7 detectors"),
             (25, 38, AQUA, "3. cultivation: double-check of the\nlogical state (H_XY), 7 detectors"),
             (39, 39, MUTED, "noiseless\nreadout")]


def stim_ticks(c: stim.Circuit) -> list:
    """[(tick, gate name, [targets])] for the gate instructions of a flat circuit."""
    out, tick = [], 0
    for op in c.flattened():
        if op.name == "TICK":
            tick += 1
        elif op.name not in ("DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS", "SHIFT_COORDS"):
            out.append((tick, op.name, [t.value for t in op.targets_copy() if t.is_qubit_target]))
    return out


def f8() -> None:
    c = cultiv.make_inject_and_cultivate_circuit(dcolor=3, inject_style="unitary", basis="Y")
    ops = stim_ticks(c)
    data = sorted({q for _, name, qs in ops if name == "S_DAG" and len(qs) > 1 for q in qs})
    helpers = sorted(set(range(c.num_qubits)) - set(data))
    row = {q: -i for i, q in enumerate(data + helpers)}

    # CXs that share a tick but overlap vertically get their own sub-column
    xs, x = {}, 0.0
    for tick in range(c.num_ticks + 1):
        lanes = []                                   # occupied row spans per sub-column
        for k, (t, name, qs) in enumerate(ops):
            if t != tick:
                continue
            for a, b in (zip(qs[::2], qs[1::2]) if name == "CX" else [(q, q) for q in qs] if name != "MPP" else []):
                lo, hi = sorted((row[a], row[b]))
                lane = next((i for i, spans in enumerate(lanes)
                             if all(hi < s0 - 0.1 or lo > s1 + 0.1 for s0, s1 in spans)), None)
                if lane is None:
                    lanes.append([])
                    lane = len(lanes) - 1
                lanes[lane].append((lo, hi))
                xs[(k, a, b)] = x + lane * 0.55
        xs[("tick", tick)] = x
        x += max(1, len(lanes)) * 0.55 + 0.45

    fig, ax = plt.subplots(figsize=(17, 5.4))
    end = x
    for q in data + helpers:
        ax.plot([-0.4, end], [row[q]] * 2, color=MUTED, lw=0.8, zorder=1)
        ax.text(-0.6, row[q], f"q{q}", ha="right", va="center", fontsize=8.5,
                color=INK if q in data else MUTED, fontweight="bold" if q in data else "normal")
    ax.text(-3.2, (row[data[0]] + row[data[-1]]) / 2, "color-code\ndata qubits (7)", ha="right", va="center",
            fontsize=9, color=INK)
    ax.text(-3.2, (row[helpers[0]] + row[helpers[-1]]) / 2, "helper\nqubits (8)", ha="right", va="center",
            fontsize=9, color=MUTED)
    bottom = row[helpers[-1]] - 0.7
    for t0, t1, color, title in F8_STAGES:
        x0, x1 = xs[("tick", t0)] - 0.4, (xs[("tick", t1 + 1)] if t1 + 1 <= c.num_ticks else end) - 0.6
        ax.add_patch(Rectangle((x0, bottom), x1 - x0, 1.2 - bottom, fc=color, alpha=0.08, ec="none", zorder=0))
        ax.text((x0 + x1) / 2, 1.0, title, ha="center", va="bottom", fontsize=9, color=color if color != MUTED else INK,
                fontweight="bold")

    for k, (t, name, qs) in enumerate(ops):
        if name == "CX":
            for a, b in zip(qs[::2], qs[1::2]):
                cx = xs[(k, a, b)]
                ax.plot([cx, cx], [row[a], row[b]], color=INK, lw=0.9, zorder=2)
                ax.plot(cx, row[a], "o", color=INK, ms=3.5, zorder=3)
                ax.plot(cx, row[b], "o", mfc="white", mec=INK, ms=8, mew=0.9, zorder=3)
                ax.plot([cx - 0.11, cx + 0.11], [row[b]] * 2, color=INK, lw=0.9, zorder=4)
                ax.plot([cx, cx], [row[b] - 0.11, row[b] + 0.11], color=INK, lw=0.9, zorder=4)
        elif name == "MPP":
            span = [row[q] for q in data]
            x0 = xs[("tick", t)]
            ax.add_patch(FancyBboxPatch((x0 - 0.35, min(span) - 0.3), 0.7, max(span) - min(span) + 0.6,
                                        boxstyle="round,pad=0.02", fc="white", ec=MUTED, lw=1, ls="--", zorder=3))
            ax.text(x0, (max(span) + min(span)) / 2, "ideal logical readout", ha="center", va="center",
                    fontsize=7.5, color=INK, rotation=90, zorder=4)
        else:
            color = {"S_DAG": ORANGE, "S": ORANGE, "M": MUTED, "MX": MUTED}.get(name, BLUE)
            filled = name in ("S_DAG", "S")
            for q in qs:
                gx = xs[(k, q, q)]
                ax.add_patch(FancyBboxPatch((gx - 0.24, row[q] - 0.3), 0.48, 0.6, boxstyle="round,pad=0.02",
                                            fc=color if filled else "white", ec=color, lw=1, zorder=3))
                ax.text(gx, row[q], STIM_LABEL.get(name, name), ha="center", va="center", fontsize=6.5,
                        color="white" if filled else INK, fontweight="bold", zorder=4)
    ax.set_xlim(-6.5, end + 0.2)
    ax.set_ylim(bottom, 2.3)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.suptitle("F8 · Magic-state injection + cultivation circuit, color code d1 = 3 (15 qubits, 40 time steps)",
                 fontweight="bold")
    save(fig, "F8_injection", "cultiv.make_inject_and_cultivate_circuit(dcolor=3, inject_style='unitary', basis='Y'), "
         "drawn before noise is added. Orange = S/S† (Stim cannot simulate T, so S stands in for it; T error = 2 × S "
         "error). |0⟩/|+⟩ = reset, M/Mx = measurement. If any of the 14 detectors fires, the shot is discarded "
         "(31.3% at p = 0.1%); kept shots have logical error 1 in 1,390,000.")


# ------------------------------------------------------------------ F9 user input circuits
def f9() -> None:
    progs = [(name, q.strip(), fs.load(q)) for name, q in fs.EXAMPLES.items()]
    fig = plt.figure(figsize=(10, 6.4))
    grid = fig.add_gridspec(len(progs), 2, width_ratios=[1.1, 1])
    for r, (name, qasm, qc) in enumerate(progs):
        code = fig.add_subplot(grid[r, 0])
        code.axis("off")
        code.text(0, 0.5, qasm, family="monospace", fontsize=9.5, va="center", ha="left",
                  bbox=dict(boxstyle="round,pad=0.6", fc="#f4f3ee", ec="#e4e3dc"))
        code.set_title(f"({'ab'[r]}) {name}: OpenQASM 3 input", fontsize=10, loc="left")
        draw_circuit(fig.add_subplot(grid[r, 1]), qc, "as a circuit", columns=4, rows=4, all_wires=True)
    fig.suptitle("F9 · Input circuits given to the pipeline (before compilation)", fontweight="bold")
    save(fig, "F9_inputs", "full_stack_sim.EXAMPLES exactly as written. (a) q1-q3 are declared but unused; the T right "
         "before the measurement cannot change the result. (b) Toffoli (CCX): q2 = q0 AND q1, with q0 and q1 put in "
         "superposition by H, so all four input pairs occur. Compiled versions: F6.")


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    f9()
    f6()
    f7()
    f8()
