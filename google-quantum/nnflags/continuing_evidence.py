"""Evidence for the continuing-data search: what the surviving malignant 2-fault T
pairs of the best 2-flag circuits are, and whether ONE more flag (a third; not
built, analysis only) could separate them, with and without the line rules.

For each saved best circuit (inner + full stim with Willow QUBIT_COORDS):
  * malignant pairs (zzflags.malignant_pairs) and their events (Pauli type of each
    fault: X-type = has X / Y on some qubit, Z-only);
  * for each pair, the number of (basis, control set) single flags that separate it
    (GF(2) test, zzflags.Coverage.system), over all control sets of tree qubits
    (same colour, tree degree <= 3), and how many of those have a free Willow point
    adjacent to all controls that is not on a data line (continuing-data rule) and,
    if the flag is live at the mid check, not on a root line (strict rule).

    .venv/bin/python -m nnflags.continuing_evidence results/continuing/best_s1_0 ...
"""
import json
import sys
from pathlib import Path

import stim

from nnflags import constraints as C
from nnflags import search_zzflags as SZ
from nnflags import zzflags as Z
from nnflags.continuing_data import data_qubits
from nnflags.willow import WILLOW, neighbours, readout_line


def plaquettes_from_full(full):
    out = []
    for inst in full:
        if inst.name == "MPP":
            ts = [t for t in inst.targets_copy() if not t.is_combiner]
            if len(ts) == 4 and all(t.is_z_target for t in ts):
                out.append(tuple(t.value for t in ts))
    return tuple(out)


def flag_qubits(inner, d):
    """Z flags = qubits measured in the Z basis (M); X flags = measured MX, never a CX
    target, not mid-measured (tree ancillas are CX targets of their parent, the root
    is mid-measured)."""
    meas = {}
    for layer in C.split_by_ticks(inner):
        for name, qs, gd in C._hardware_ops(layer):
            if gd.produces_measurements:
                for q in qs:
                    meas.setdefault(q, set()).add(name)
    targets = {b for _, _, a, b in C.two_qubit_gates(inner)}
    z = [q for q, n in meas.items() if "M" in n]
    x = [q for q, n in meas.items() if n == {"MX"} and q not in targets and q not in d.mid_measured]
    return sorted(z + x)


def evidence(prefix):
    inner = stim.Circuit.from_file(prefix + ".inner.stim")
    full = stim.Circuit.from_file(prefix + ".full.stim")
    emb = {q: (int(a), int(b)) for q, (a, b) in C.native_coords(inner).items()}
    data = sorted(data_qubits(inner))
    d = Z.Design(Path(prefix).name, inner, (plaquettes_from_full(full), (), (), tuple(data)), emb)
    flags = flag_qubits(inner, d)
    pairs, events, _, _ = Z.malignant_pairs(d, inner, full)
    tree_q = [q for q in d.qubits if q not in flags]
    pa = Z.ProbeAnalysis(d, controls=tree_q)
    cov = Z.Coverage(pa, pairs, events)
    dl = {readout_line(emb[q]) for q in data}
    rl = {readout_line(emb[q]) for q in d.mid_measured}
    used = set(emb.values())
    mid = d.mid_ticks[0] if d.mid_ticks else 10 ** 9
    out = dict(file=prefix, flags=flags, pairs=[list(p) for p in pairs], data_lines=sorted(dl), root_lines=sorted(rl),
               per_pair=[])
    for i, (a, b) in enumerate(pairs):
        kinds = []
        for f in (a, b):
            has_x = any(any(ps[q] in (1, 2) for q in range(len(ps))) for _, ps in events[f])
            kinds.append("X-type" if has_x else "Z-only")
        sep = {"Z": [0, 0], "X": [0, 0]}
        for basis in ("Z", "X"):
            for qs in SZ.control_sets(d, tree_q):
                cols = [k for k, p in enumerate(pa.probes) if p.q in qs and p.basis == basis]
                if not cols or Z.solve_gf2(cov.system(cols, [i]), len(cols)) is None:
                    continue
                sep[basis][0] += 1
                pts = set(neighbours(emb[qs[0]]))
                for q in qs[1:]:
                    pts &= set(neighbours(emb[q]))
                live = basis == "X"  # a Z flag can start after the mid check (dormant there)
                ok = [p for p in pts if p in WILLOW and p not in used and readout_line(p) not in dl
                      and not (live and readout_line(p) in rl)]
                sep[basis][1] += bool(ok)
        out["per_pair"].append(dict(pair=[a, b], fault_types=kinds,
                                    events=[[(t, str(ps)) for t, ps in events[f][:3]] for f in (a, b)],
                                    single_flag_sets={k: dict(any=v[0], placeable=v[1]) for k, v in sep.items()}))
    return out


if __name__ == "__main__":
    res = [evidence(p) for p in sys.argv[1:]]
    Path("results/continuing_evidence.json").write_text(json.dumps(res, indent=1, default=str))
    for r in res:
        print(r["file"], "pairs", len(r["pairs"]))
        for pp in r["per_pair"]:
            print("  ", pp["pair"], pp["fault_types"], pp["single_flag_sets"])


def cover_stats(task):
    """For one abstract key: does a 2-cover of its malignant base pairs by two single-flag
    coverage sets exist (a) abstractly (any same-colour control set, no geometry) and
    (b) with both flags placeable under the line rules on some embedding of the key?
    Also: can ONE flag cover everything, and the minimum number of flags of a greedy
    set cover (abstract and placeable), capped at 4."""
    from nnflags import search_continuing as SC
    key, insts, lab = task
    d, lay = SC.design_for(key, insts[0], tuple(lab))
    placer = SC.Placer(insts)
    tree_q = list(d.qubits)
    pa = Z.ProbeAnalysis(d, controls=tree_q)
    pairs, events, _, _ = Z.malignant_pairs(d)
    n = len(pairs)
    cov = Z.Coverage(pa, pairs, events)
    real = placer.realisability([])
    full = (1 << n) - 1
    masks = {"abstract": [], "placeable": []}
    for basis in ("Z", "X"):
        for qs in SZ.control_sets(d, tree_q):
            cols = [k for k, p in enumerate(pa.probes) if p.q in qs and p.basis == basis]
            if not cols:
                continue
            ms = (SZ.maximal(Z.coverable_subsets(cov, cols, n)) if n <= 12
                  else SZ.maximal(SZ.greedy_masks(cov, cols, n)))
            masks["abstract"] += [(m, basis, qs) for m in ms]
            if real(qs, basis == "X"):
                masks["placeable"] += [(m, basis, qs) for m in ms]
    out = dict(key=key, T2=n, n_embeddings=len(insts))
    for k, ms in masks.items():
        union = 0
        for m, _, _ in ms:
            union |= m
        one = any(m == full for m, _, _ in ms)
        two = one or any(a[0] | b[0] == full for i, a in enumerate(ms) for b in ms[i:])
        # greedy set cover size (upper bound on the flags needed in this model)
        left, k_ = full, 0
        while left and k_ < 4:
            best = max(ms, key=lambda x: bin(x[0] & left).count("1"), default=None)
            if best is None or not best[0] & left:
                break
            left &= ~best[0]
            k_ += 1
        out[k] = dict(options=len(ms), coverable_pairs=bin(union).count("1"), one_flag=one, two_flags=two,
                      greedy_cover=(k_ if not left else None))
    return out
