"""Test 3, step 0: can our fault-distance-3 double checks be spliced into Google's
grafting circuit G6 (Rosenfeld et al. arXiv:2512.13908, Fig. 4) in place of Google's
own double check?

For that, our circuit's 7 data qubits must sit on G6's 7 data positions AND carry
the same colour code there (the same weight-4 stabilisers), because G6's grafting
steps (TICKs 57-124) are built for that code. This script checks, for cs00-cs09:

  1. the G6 layout: data = targets of I[T_gate]; the code = weight-4 X and Z
     stabilisers of the noiseless state at the end of cultivation (TICK 56);
  2. every nearest-neighbour Willow placement of the circuit with data and measured
     qubits on disjoint readout lines (continuing_data.reembed_search) whose data
     land on G6's positions;
  3. for those, whether the code lands as in G6;
  4. sanity check: the number of code-preserving maps of the 7 data onto G6's
     positions (must be 168, the automorphism group of the 7-qubit code).

    .venv/bin/python "qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6/check_g6_fit.py"
    -> results/g6_fit.json
"""
import itertools
import json
import os
import sys
from pathlib import Path

import stim

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # google-quantum/
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from cliffordea.enum.circuit_tools import split_by_ticks  # noqa: E402

from nnflags.continuing_data import data_qubits, reembed_search  # noqa: E402

G6_FILE = ROOT / "nnflags/data/google_circuits/rosenfeld2512_G6.stim"
END_OF_CULTIVATION = 56  # last cultivation TICK of G6 (nnflags/g6_continuing.py)
RES = HERE / "results"


def g6_layout():
    g = stim.Circuit.from_file(str(G6_FILE))
    co = {q: tuple(int(x) for x in p) for q, p in g.get_final_qubit_coordinates().items()}
    data = sorted({t.value for op in g.flattened() if op.tag == "T_gate" for t in op.targets_copy()})
    pre = stim.Circuit()
    for layer in split_by_ticks(g)[:END_OF_CULTIVATION + 1]:
        for op in layer:
            if op.name not in ("DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS"):
                pre.append(op)
        pre.append("TICK")
    sim = stim.TableauSimulator()
    sim.do(pre.without_noise())
    code = {}
    for P in "XZ":
        code[P] = []
        for S in itertools.combinations(data, 4):
            ps = stim.PauliString(g.num_qubits)
            for q in S:
                ps[q] = P
            if abs(sim.peek_observable_expectation(ps)) == 1:
                code[P].append(frozenset(co[q] for q in S))
    return g, co, data, code


def weight4_elements(full: stim.Circuit, P: str):
    """All weight-4 elements of the P-type stabiliser group given by the MPP checks of a full circuit."""
    gens = []
    for op in full.flattened():
        if op.name == "MPP":
            ts = op.targets_copy()
            qs = {t.value for t in ts if not t.is_combiner}
            if len(qs) == 4 and all(t.is_combiner or (t.is_x_target if P == "X" else t.is_z_target) for t in ts):
                gens.append(frozenset(qs))
    out = set()
    for k in range(1, len(gens) + 1):
        for c in itertools.combinations(gens, k):
            s = frozenset()
            for g in c:
                s ^= g
            if len(s) == 4:
                out.add(s)
    return out


def main():
    RES.mkdir(exist_ok=True)
    g, co, g6data, g6code = g6_layout()
    g6pos = {co[q] for q in g6data}
    assert set(g6code["X"]) == set(g6code["Z"]) and len(g6code["X"]) == 7
    W4 = set(g6code["X"])
    out = dict(g6=dict(data_positions=sorted(g6pos), weight4_stabilisers=[sorted(s) for s in W4]), circuits={})
    print(f"G6 data positions: {sorted(g6pos)}; 7 weight-4 X and Z stabilisers at TICK {END_OF_CULTIVATION}")
    for i in range(10):
        name, f = f"cs{i:02d}", f"results/continuing/success{i:02d}"
        inner, full = stim.Circuit.from_file(f + ".inner.stim"), stim.Circuit.from_file(f + ".full.stim")
        d = data_qubits(inner)
        w4 = weight4_elements(full, "X")
        assert w4 == weight4_elements(full, "Z") and len(w4) == 7
        embs = reembed_search(inner, limit=2_000_000)
        on_g6 = [e for e in embs if {tuple(e[q]) for q in d} == g6pos]
        same_code = [e for e in on_g6 if all(frozenset(tuple(e[q]) for q in s) in W4 for s in w4)]
        n_maps = sum(all(frozenset(m[q] for q in s) in W4 for s in w4)
                     for m in (dict(zip(sorted(d), p)) for p in itertools.permutations(sorted(g6pos))))
        out["circuits"][name] = dict(placements=len(embs), data_on_g6=len(on_g6), same_code_as_g6=len(same_code),
                                     code_preserving_maps=n_maps,
                                     data_on_g6_ancillas=[{str(q): list(e[q]) for q in e if q not in d} for e in on_g6],
                                     same_code_placements=[{str(q): list(p) for q, p in e.items()} for e in same_code])
        print(f"{name}: {len(embs)} placements, {len(on_g6)} with data on G6's positions, "
              f"{len(same_code)} with G6's code (code-preserving maps: {n_maps})", flush=True)
    (RES / "g6_fit.json").write_text(json.dumps(out, indent=1))
    print(RES / "g6_fit.json")


if __name__ == "__main__":
    main()
