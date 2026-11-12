"""Test 5, Part B: our double-check method (the one that found cs02) at code distance 5.

Same construction as at d = 3 (nnflags/search_option1.py, Base / build / to_circuit, unchanged):
  * a fold TREE on the square grid (edges = couplers), rooted at an ANCILLA parity qubit; leaves are
    data; internal nodes are data or ancillas; here exactly 19 data (the d = 5 colour code);
  * fold = ASAP CX(node -> child) from the leaves, MRX of the root (mid check), unfold = time
    reverse, final MX of every ancilla;
  * readout rule (strict, data measured at the end): nothing else on the root's line r + c;
  * code labelling: which data node plays which of the 19 colour-code qubits.

The d = 5 colour code (9 plaquettes, logical-S sublattices) is Gidney et al.'s, read from cliffordea's
bundled d5a19 full circuit and relabelled 0..18 (code qubit j = j-th data qubit of d5a19 by index).
The search is randomised (the d = 3 search enumerated everything; at d = 5 that is impossible):
random trees, then a local search over labellings (swap moves) on cliffordea's exact count.
"""
import random
from collections import defaultdict

import stim

import b2_flags_d5 as F  # sets sys.path / cwd
from nnflags import search_option1 as S  # noqa: E402
from nnflags.g4 import full_for  # noqa: E402
from nnflags.verify import verify  # noqa: E402

ROOT0 = (0, 0)


def line(p):
    return p[0] + p[1]


def nbrs(p):
    r, c = p
    return ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))


def d5_code():
    """(plaquettes, majority, minority) on code qubits 0..18."""
    d, _ = F.design_d5()
    data = sorted(d.data)
    j = {q: k for k, q in enumerate(data)}
    plaq, maj, mino = d.full_args[0], d.full_args[1], d.full_args[2]
    return (tuple(tuple(sorted(j[q] for q in p)) for p in plaq),
            tuple(sorted(j[q] for q in maj)), tuple(sorted(j[q] for q in mino)))


CODE = d5_code()


# ---- random trees ---------------------------------------------------------------------------------

def random_tree(rng, n_data=19, max_anc=14, max_depth=8, max_tries=200):
    """A random rooted tree around ROOT0 (an ancilla) whose ASAP fold depth <= max_depth,
    with nothing else on the root's line, leaves = data, exactly n_data data.
    Returns Base or None."""
    for _ in range(max_tries):
        n_target = n_data + rng.randint(4, max_anc)
        parent = {ROOT0: None}
        depth = {ROOT0: 0}
        frontier = [ROOT0]
        while len(parent) < n_target:
            v = rng.choice(frontier)
            opts = [w for w in nbrs(v) if w not in parent and line(w) != line(ROOT0)]
            if not opts or depth[v] >= max_depth:
                frontier.remove(v)
                if not frontier:
                    break
                continue
            w = rng.choice(opts)
            parent[w] = v
            depth[w] = depth[v] + 1
            frontier.append(w)
        kids = defaultdict(list)
        for v, p in parent.items():
            if p is not None:
                kids[p].append(v)
        leaves = [v for v in parent if v != ROOT0 and not kids[v]]
        if len(leaves) > n_data:
            continue
        internal = [v for v in parent if v != ROOT0 and kids[v]]
        need = n_data - len(leaves)
        if need > len(internal):
            continue
        dat = set(leaves) | set(rng.sample(internal, need))
        roles = {v: ("D" if v in dat else "A") for v in parent}
        base = S.Base(parent, roles, (ROOT0,))
        if S.depth_of(parent, (ROOT0,)) > max_depth:
            continue
        return base
    return None


def circuits(base, lab):
    """(inner, full, layout) for code labelling lab (code qubit j -> lab[j]-th data qubit)."""
    lay = S.build(base)
    inner = S.to_circuit(lay)
    data = lay["data"]
    L = [data[lab[j]] for j in range(len(data))]
    plaq, maj, mino = CODE
    full = full_for(inner, tuple(tuple(L[j] for j in p) for p in plaq),
                    tuple(L[j] for j in maj), tuple(L[j] for j in mino), tuple(data))
    return inner, full, lay


def score(base, lab, max_faults=3):
    """(malignant T at <= 2 faults, malignant T at 3 faults, T rate) - lower is better."""
    inner, full, _ = circuits(base, lab)
    r = verify(full, inner, max_fault_count=max_faults, states=("T",))
    m = r["T"]
    low = sum(m[k]["malignant"] for k in m if k < max_faults)
    return (low, m[max_faults]["malignant"], r["error_rate_per_kept_shot"]["T"])


def labelling_search(base, rng, evals=150, max_faults=3):
    n = 19
    lab = list(range(n))
    rng.shuffle(lab)
    best = score(base, lab, max_faults)
    used = 1
    while used < evals:
        i, j = rng.sample(range(n), 2)
        lab[i], lab[j] = lab[j], lab[i]
        s = score(base, lab, max_faults)
        used += 1
        if s[:2] <= best[:2]:
            best = s
        else:
            lab[i], lab[j] = lab[j], lab[i]
        if best[:2] == (0, 0):
            break
    return tuple(lab), best, used
