"""Test 4, step A2: what Hirano et al.'s lattice-surgery escape needs from the hardware.

Reads their published stim circuits (references/msc-ls-src/repo/data, read only; their code
is not run) and lists, per circuit: the qubits used, every two-qubit pair that is not a
nearest neighbour in their diagonal coordinates (offset (1, 1)), the qubits with more than
4 partners, and whether those qubits sit in the colour-code or the surface-code region.
Writes RESULTS_hirano_escape.md.

    .venv/bin/python "qvm-google (main)/test4_cs02_lattice_surgery_escape_realT_clifft/analyze_hirano_escape.py"
"""
import collections
from pathlib import Path

import stim

HERE = Path(__file__).resolve().parent
DATA = HERE / "references" / "msc-ls-src" / "repo" / "data"
FILES = ["inject-check-3.stim", "lattice-surgery-error-detection-3-to-3.stim",
         "lattice-surgery-error-detection-3-to-5.stim"]
NOISE = ("DEPOLARIZE", "X_ERROR", "Y_ERROR", "Z_ERROR", "PAULI")


def analyse(path):
    c = stim.Circuit.from_file(str(path))
    co = {q: tuple(v) for q, v in c.get_final_qubit_coordinates().items()}
    used, pairs, first_tick = set(), collections.Counter(), {}
    ideal = collections.Counter()  # noiseless CX (no DEPOLARIZE2 right after): the test's ideal encoder
    tick = 0
    ops = list(c.flattened())
    for i, op in enumerate(ops):
        if op.name == "TICK":
            tick += 1
            continue
        if op.name in ("DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS") or op.name.startswith(NOISE):
            continue
        t = [x.value for x in op.targets_copy() if x.is_qubit_target]
        used |= set(t)
        if op.name in ("CX", "CZ"):
            nxt = ops[i + 1] if i + 1 < len(ops) else None
            if not (nxt is not None and nxt.name == "DEPOLARIZE2"):
                for a, b in zip(t[::2], t[1::2]):
                    ideal[tuple(sorted((a, b)))] += 1
                continue
            for a, b in zip(t[::2], t[1::2]):
                key = tuple(sorted((a, b)))
                pairs[key] += 1
                first_tick.setdefault(key, tick)
    partners = collections.defaultdict(set)
    for a, b in pairs:
        partners[a].add(b)
        partners[b].add(a)
    far = [(a, b) for a, b in pairs
           if sorted((abs(co[a][0] - co[b][0]), abs(co[a][1] - co[b][1]))) != [1.0, 1.0]]
    return dict(n_used=len(used), n_pairs=len(pairs), far=far, n_ideal=len(ideal), co=co, first_tick=first_tick,
                heavy={q: sorted(v) for q, v in partners.items() if len(v) > 4}, ticks=tick)


def main():
    L = ["# Test 4, step A2: hardware needs of Hirano et al.'s lattice-surgery escape", "",
         "Static analysis of the published stim circuits (`references/msc-ls-src/repo/data`, commit e4c90b0). "
         "Nearest neighbour = coordinate offset (1, 1) in their diagonal layout (the surface-code convention).", ""]
    for f in FILES:
        r = analyse(DATA / f)
        co = r["co"]
        L += [f"## {f}", "", f"- qubits used: {r['n_used']}; noisy (hardware) two-qubit pairs: {r['n_pairs']}; TICKs: {r['ticks']}",
              f"- noiseless two-qubit pairs left out (no DEPOLARIZE2 after them: the test's ideal colour-code encoder): {r['n_ideal']}",
              f"- pairs that are **not** nearest neighbours: {len(r['far'])}"]
        for a, b in sorted(r["far"], key=lambda ab: r["first_tick"][ab]):
            L.append(f"  - q{a} {co[a]} – q{b} {co[b]}, first at TICK {r['first_tick'][(a, b)]}")
        L.append(f"- qubits with more than 4 partners: {len(r['heavy'])}")
        for q, ps in sorted(r["heavy"].items()):
            L.append(f"  - q{q} {co[q]}: {len(ps)} partners " + ", ".join(f"q{p}{co[p]}" for p in ps))
        L.append("")
    L += ["## Reading (Nov 3): the earlier 10 non-neighbour pairs and the >4-partner qubits all came from the "
          "noiseless TICK-5 CNOTs, i.e. the test circuit's ideal encoding of |+>_L into the colour code, not from the escape.", "",
          "## Original reading note", "",
          "If the non-neighbour pairs and the >4-partner qubits all involve colour-code qubits, the issue is the "
          "colour-code part (Gidney's layout drawn in other coordinates, or qubits reused across stages); if they "
          "involve the merge boundary, the lattice surgery itself needs re-routing for Willow. Either way, every such "
          "pair must be removed (re-routed through a neighbour or re-placed) before the escape can run on Willow.", ""]
    (HERE / "RESULTS_hirano_escape.md").write_text("\n".join(L))
    print(HERE / "RESULTS_hirano_escape.md")


if __name__ == "__main__":
    main()
