"""Option-1 task D: fold forests + mid-circuit parity-measurement qubits on Willow
(G4-type double checks), then 1-2 Z flags on the X-hook qubits.

SEARCH SPACE (a generalisation of G4's double check, in canonical CX form):
  * A base is a forest F on Willow qubits (edges = couplers) with m = 1 or 2
    components. Each component is rooted at an ANCILLA "parity-measurement
    qubit"; all leaves are data; internal nodes are data or ancillas; exactly
    7 data (the d=3 colour code, as in d3a6 / G4).
  * Fold: every node X-collects its children by CX(node -> child), as late
    as its children are ready (ASAP from the leaves; one gate per qubit per
    TICK). Then the X parity of the whole forest = X_L sits on the roots,
    which are measured together (MRX, one TICK, detector = roots xor MPP).
    Unfold = the exact time reverse; then MX of every ancilla (each root's
    final MX xor its mid MRX = the time-reversed check). Ancillas are
    RX-prepared, the trailing layer resets them (cliffordea inner-circuit
    conventions, enum/circuits/main.py:42-54).
  * Roots: m = 1 at G4's root position (9, 9); m = 2 at G4's two measured
    positions (9, 9) and (8, 10), which share readout line 18. No other qubit
    of the forest may sit on a root's readout line (they are all live at the
    mid measurement); this is the "measured parity qubits have readout lines
    with nothing else live" rule (decision 5).
  * Code labelling: which data node plays which colour-code qubit. 7! = 5040
    labellings in 210 classes modulo the 24 code automorphisms that keep the
    plaquettes and the logical-S sublattice. For each abstract base the
    labelling with the fewest malignant 2-fault T configurations is used
    (all 210 verified).
  * Sizes: n = 7 + k qubits, enumerated by increasing n (connected vertex
    sets around the root(s) by Redelmeier's algorithm, then every spanning
    tree / root-separating spanning forest, then every data/ancilla role
    assignment).
  Translations and the r+c-line-preserving symmetries (transpose, rot180,
  antitranspose) do not change verify() or the readout rule, and the
  enumeration around a fixed root contains every orientation of every shape,
  so other regions differ only by Willow's boundary (free neighbours).

FILTERS AND FLAGS
  * Hook qubits = qubits carrying the X/Y events of the faults with data
    weight >= 2 in the base's malignant 2-fault T configurations
    (FaultCombinator.index_to_events, enum/combinators/fault_combinator.py:374).
  * Design rule (decision 5): every hook qubit has a free Willow neighbour.
    Bases with more than 2 hook qubits are deferred (2 flags cannot cover
    them); they are recorded but not flagged.
  * Z flag (first-ex.md): fresh qubit f on a free neighbour of the hook
    qubit q, R in the preparation TICK (dormant in |0> until its first CX
    under the new live rule), CX q->f at slots t1 < t2 with q only a CX
    control in between (Z_q unchanged), M f in the final measurement TICK
    (DETECTOR on it), f in the trailing reset. Slots: existing TICKs where
    q is idle, or new TICKs (counted as added TICKs). Per (hook, free
    neighbour) the slot pair covering most hook events is used; then pairs
    of single flags on two different hooks (or the same hook, different f).
  * VALID = strict hardware constraints (nearest neighbour, degree <= 4, no
    reuse in a TICK, strict readout with live_rule="gate" and the checked
    final-layer exemption) + equivalence.check_equivalence (flags excluded
    from the reverse check) + verify() runs (max_fault_count 2 and 3).
  STOP at 20 valid flagged candidates (bases with 0 malignant 2-fault T
  configurations would also count, with n_flags = 0).

Usage: nohup python -m nnflags.search_option1 --workers 12 > logs/search_option1.log &
Outputs: results/option1_candidates.csv, results/option1_bases.csv,
results/option1/*.stim, results/option1_state.json (checkpoint).
"""
import argparse
import csv
import itertools
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

import stim

from nnflags import constraints as C
from nnflags import equivalence as Q
from nnflags.g4 import full_for
from nnflags.verify import load_measurement, verify
from nnflags.willow import WILLOW, neighbours, readout_line

CODE_PLAQ = ((0, 1, 2, 3), (1, 2, 4, 5), (2, 3, 5, 6))  # canonical d=3 colour code
CODE_MAJ = (0, 2, 4, 6)   # centre 2 + corners (S targets of logical S)
CODE_MIN = (1, 3, 5)
ROOTS = {1: ((9, 9),), 2: ((9, 9), (8, 10))}
MAX_VALID = 20
INFEASIBLE = 10 ** 6  # marker: labelling breaks the code (no flow S -> S)
NOISE = 1e-3


# ---- code labellings ------------------------------------------------------------

def _stab_supports(plaq):
    out = set()
    for k in range(1, 8):
        s = set()
        for i in range(3):
            if k >> i & 1:
                s ^= set(plaq[i])
        out.add(frozenset(s))
    return out


def code_automorphisms():
    s0 = _stab_supports(CODE_PLAQ)
    return [p for p in itertools.permutations(range(7))
            if {frozenset(p[q] for q in s) for s in s0} == s0 and {p[q] for q in CODE_MAJ} == set(CODE_MAJ)]


def labelling_classes():
    """210 representatives lab (code qubit j -> j-th data node) of 7! / 24."""
    aut = code_automorphisms()
    reps = set()
    for lab in itertools.permutations(range(7)):
        reps.add(min(tuple(lab[a[j]] for j in range(7)) for a in aut))
    return sorted(reps)


# ---- enumeration of forests ---------------------------------------------------------

def connected_sets(roots, n, grid=WILLOW):
    """Redelmeier enumeration of connected vertex sets of size n containing all
    ``roots`` (several roots are treated as one merged start vertex), avoiding
    every other qubit on a root's readout line."""
    lines = {readout_line(r) for r in roots}
    allowed = {p for p in grid if readout_line(p) not in lines} | set(roots)
    nb = {p: [q for q in neighbours(p, grid) if q in allowed] for p in allowed}
    order = {p: i for i, p in enumerate(sorted(allowed))}
    start = set(roots)
    out = []

    def rec(current, untried, forbidden):
        if len(current) == n:
            out.append(frozenset(current))
            return
        untried = list(untried)
        while untried:
            v = untried.pop()
            new = [w for w in nb[v] if w not in forbidden and w not in current]
            rec(current | {v}, untried + new, forbidden | set(new))
            forbidden = forbidden | {v}

    init = sorted({w for r in roots for w in nb[r]} - start, key=order.get)
    rec(start, init, start | set(init))
    return out


def spanning_forests(vertices, roots):
    """Every spanning tree of the induced grid graph with the roots merged =
    every spanning forest whose components each contain exactly one root.
    Yields parent maps {v: parent or None}."""
    vs = sorted(vertices)
    rootset = set(roots)
    merged = lambda p: "R" if p in rootset else p
    edges = sorted({tuple(sorted((a, b))) for a in vs for b in neighbours(a) if b in vertices
                    and not (a in rootset and b in rootset)})
    nodes = {merged(v) for v in vs}
    need = len(nodes) - 1

    def find(par, x):
        while par[x] != x:
            x = par[x]
        return x

    def rec(i, chosen, par):
        if len(chosen) == need:
            yield list(chosen)
            return
        if len(edges) - i < need - len(chosen):
            return
        a, b = edges[i]
        ra, rb = find(par, merged(a)), find(par, merged(b))
        if ra != rb:
            p2 = dict(par)
            p2[ra] = rb
            yield from rec(i + 1, chosen + [(a, b)], p2)
        yield from rec(i + 1, chosen, par)

    for es in rec(0, [], {x: x for x in nodes}):
        adj = defaultdict(list)
        for a, b in es:
            adj[a].append(b)
            adj[b].append(a)
        parent = {r: None for r in roots}
        stack = list(roots)
        while stack:
            v = stack.pop()
            for w in adj[v]:
                if w not in parent:
                    parent[w] = v
                    stack.append(w)
        if len(parent) == len(vs):
            yield parent


def role_assignments(parent, roots):
    """Roots ancilla, leaves data, internal non-root nodes data or ancilla, 7 data."""
    kids = Counter(p for p in parent.values() if p is not None)
    leaves = [v for v in parent if v not in kids and v not in roots]
    internal = sorted(v for v in parent if v in kids and v not in roots)
    need = 7 - len(leaves)
    if need < 0 or need > len(internal):
        return
    for data_int in itertools.combinations(internal, need):
        data = set(leaves) | set(data_int)
        yield {v: ("D" if v in data else "A") for v in parent}


@dataclass
class Base:
    parent: dict      # position -> parent position (None for roots)
    roles: dict       # position -> "D" / "A"
    roots: tuple

    def _kids(self):
        kids = defaultdict(list)
        for v, p in self.parent.items():
            if p is not None:
                kids[p].append(v)
        return kids

    def canon(self):
        """{position: canonical string of its rooted subtree} (AHU encoding with
        roles); isomorphic trees get identical strings."""
        kids, memo = self._kids(), {}

        def c(v):
            if v not in memo:
                memo[v] = self.roles[v] + "(" + ",".join(sorted(c(w) for w in kids[v])) + ")"
            return memo[v]

        for r in self.roots:
            c(r)
        return memo

    def nodes(self):
        """Circuit qubit order = canonical DFS order (roots by canonical string,
        children by canonical string), so isomorphic bases give the same circuit
        up to QUBIT_COORDS and verify() can be cached per isomorphism class."""
        cs, kids = self.canon(), self._kids()
        order = []

        def dfs(v):
            order.append(v)
            for w in sorted(kids[v], key=lambda w: (cs[w], w)):
                dfs(w)

        for r in sorted(self.roots, key=lambda r: (cs[r], r)):
            dfs(r)
        return order

    def abstract_key(self):
        cs = self.canon()
        return tuple(sorted(cs[r] for r in self.roots))

    def describe(self):
        idx = {p: i for i, p in enumerate(self.nodes())}
        parts = []
        for p in self.nodes():
            par = self.parent[p]
            parts.append(f"{idx[p]}{self.roles[p]}{p}" + ("" if par is None else f"<{idx[par]}"))
        return " ".join(parts)


def schedule(parent_idx, roots_idx):
    """ASAP fold: [(tick, parent, child)], depth. Children of a node are eaten
    in order of readiness, ties by index (= canonical order, see Base.nodes)."""
    n = len(parent_idx)
    kids = defaultdict(list)
    for c, p in enumerate(parent_idx):
        if p >= 0:
            kids[p].append(c)
    fin, gates = {}, []

    def f(v):
        if v in fin:
            return fin[v]
        t = 0
        for c in sorted(kids[v], key=lambda c: (f(c), c)):
            t = max(t + 1, f(c) + 1)
            gates.append((t, v, c))
        fin[v] = t
        return t

    for r in roots_idx:
        f(r)
    return sorted(gates), max(fin[r] for r in roots_idx)


# ---- circuit construction ---------------------------------------------------------

@dataclass(frozen=True)
class Flag:
    q: int        # control (circuit qubit index)
    at: tuple     # Willow position of the flag
    t1: float     # slot: integer = existing TICK, k + 0.5 = new TICK after TICK k
    t2: float

    def __str__(self):
        return f"q{self.q}->{self.at} t{self.t1:g},{self.t2:g}"


def build(base: Base, flags=()):
    """CX-form inner circuit (no detectors yet) as TICK -> ops, plus layout.
    TICK 0 MPP, 1 RX ancillas (+ R flags), 2..D+1 fold, D+2 MRX roots,
    D+3..2D+2 unfold, 2D+3 MX ancillas (+ M flags), 2D+4 R."""
    nodes = base.nodes()
    idx = {p: i for i, p in enumerate(nodes)}
    parent_idx = [-1 if base.parent[p] is None else idx[base.parent[p]] for p in nodes]
    roots = [idx[r] for r in base.roots]
    data = [i for i, p in enumerate(nodes) if base.roles[p] == "D"]
    anc = [i for i, p in enumerate(nodes) if base.roles[p] == "A"]
    gates, D = schedule(parent_idx, roots)
    ticks = defaultdict(list)  # float slot -> [(name, targets)]
    ticks[0].append(("MPP", data))
    ticks[1].append(("RX", anc))
    for t, a, b in gates:
        ticks[1 + t].append(("CX", [a, b]))
        ticks[2 * D + 3 - t].append(("CX", [a, b]))
    mid, final = D + 2, 2 * D + 3
    ticks[mid].append(("MRX", roots))
    ticks[final].append(("MX", anc))
    ticks[final + 1].append(("R", anc))
    nq = len(nodes)
    emb = {i: p for i, p in enumerate(nodes)}
    fq = []
    for j, fl in enumerate(flags):
        f = nq + j
        fq.append(f)
        emb[f] = fl.at
        ticks[1].append(("R", [f]))
        ticks[fl.t1].append(("CX", [fl.q, f]))
        ticks[fl.t2].append(("CX", [fl.q, f]))
        ticks[final].append(("M", [f]))
        ticks[final + 1].append(("R", [f]))
    return dict(ticks=ticks, emb=emb, data=data, anc=anc, roots=roots, flags=fq, mid=mid,
                final=final, depth=D, gates=gates, nodes=nodes)


def to_circuit(layout) -> stim.Circuit:
    """Stim circuit with detectors: forward check (roots xor MPP), then for each
    final MX / M the smallest deterministic set among {itself, + one root's
    mid record, + all roots' mid records, + MPP} (stim determinism test)."""
    ticks, emb = layout["ticks"], layout["emb"]
    c = stim.Circuit()
    for q in sorted(emb):
        c.append("QUBIT_COORDS", [q], emb[q])
    rec = {}  # (tick, qubit) -> measurement index
    n = 0
    for i, t in enumerate(sorted(ticks)):
        if i:
            c.append("TICK")
        groups = defaultdict(list)
        for name, ts in ticks[t]:
            groups[name] += ts
        for name in sorted(groups, key=lambda x: ("MPP", "RX", "R", "CX", "MRX", "MX", "M").index(x)):
            ts = groups[name]
            if name == "MPP":
                c.append("MPP", [x for q in ts for x in (stim.target_x(q), stim.target_combiner())][:-1])
                rec[("MPP", 0)] = n
                n += 1
            else:
                c.append(name, ts)
                if stim.gate_data(name).produces_measurements:
                    for q in ts:
                        rec[(t, q)] = n
                        n += 1
        if t == layout["mid"]:
            ids = [rec[(t, r)] for r in layout["roots"]] + [rec[("MPP", 0)]]
            c.append("DETECTOR", [stim.target_rec(x - n) for x in ids])
        if t == layout["final"]:
            mids = [rec[(layout["mid"], r)] for r in layout["roots"]]
            for q in layout["anc"] + layout["flags"]:
                m = rec[(t, q)]
                options = [[m]] + [[m, x] for x in mids] + [[m] + mids] + [[m] + mids + [rec[("MPP", 0)]]]
                for ids in options:
                    test = c.copy()
                    test.append("DETECTOR", [stim.target_rec(x - n) for x in ids])
                    if Q.is_deterministic(test):
                        c = test
                        break
    return c


def full_circuit(inner, layout, lab):
    """Full circuit for verify(): plaquettes / sublattices via the labelling
    lab (code qubit j -> data node lab[j])."""
    data = layout["data"]
    L = [data[lab[j]] for j in range(7)]
    return full_for(inner, tuple(tuple(L[j] for j in p) for p in CODE_PLAQ),
                    tuple(L[j] for j in CODE_MAJ), tuple(L[j] for j in CODE_MIN), data)


# ---- workers --------------------------------------------------------------------------

def _verify_labelling(args):
    inner_text, layout_light, lab = args
    inner = stim.Circuit(inner_text)
    try:
        full = full_circuit(inner, layout_light, lab)
    except AssertionError:
        # The fold does not preserve the code for this labelling (m = 2: a Z
        # plaquette with odd overlap with one root's component): not a double check.
        return lab, INFEASIBLE, float("inf")
    r = verify(full, inner, max_fault_count=2)
    return lab, r["T"][2]["malignant"], r["error_rate_per_kept_shot"]["T"]


def hooks_of(inner, full, layout):
    """X-hook qubits: qubits carrying X/Y events of the faults with data weight
    >= 2 in the malignant 2-fault T configurations -> {qubit: [event ticks]}."""
    from cliffordea import enum
    m = load_measurement(full, inner)
    comb = enum.FaultCombinator(enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=NOISE))
    from cliffordea import accept
    an = accept.CliffordLogicalAnalyzer(data_indices=m.DATA_INDICES,
                                        stabilizer_generators=m.STABILIZER_GENERATORS,
                                        logical_s=m.LOGICAL_S)
    kept = comb.get_kept_effects(logical_analyzer=an, max_fault_count=2, cultivated_states=("T",))
    mal = [cfg for k, eff in enumerate(kept["T"]) for p, fid, cfgs in eff.values()
           if p > 0 and fid != 1 for cfg in cfgs if len(cfg) == 2]
    effect = {i: e for sig, d in comb.basis.items() for e, i in d.items()}
    nq = inner.num_qubits
    data = set(layout["data"])
    weight = lambda e: sum(1 for q in data if (e >> q) & 1 or (e >> (nq + q)) & 1)
    hooks = defaultdict(list)
    for cfg in mal:
        for i in cfg:
            if weight(effect[i]) < 2:
                continue
            evs = comb.index_to_events[i]
            single = [(ev[0], ev[2][0].value) for ev in evs if ev[1] in ("X_ERROR", "Y_ERROR")]
            if not single:
                single = [(ev[0], t.value) for ev in evs if ev[1] == "E" for t in ev[2]
                          if t.is_x_target or t.is_y_target]
            cnt = Counter(q for _, q in single)
            if not cnt:
                continue
            top = max(cnt.values())
            for q, k in cnt.items():
                if k == top:
                    hooks[q] += [t for t, qq in single if qq == q]
    return {q: sorted(set(ts)) for q, ts in hooks.items()}, len(mal)


def q_ops(layout):
    """{qubit: {slot: role}} with role control / target / other."""
    ops = defaultdict(dict)
    for t, items in layout["ticks"].items():
        for name, ts in items:
            if name == "CX":
                ops[ts[0]][t] = "control"
                ops[ts[1]][t] = "target"
            elif name != "MPP":
                for q in ts:
                    ops[q][t] = "other"
    return ops


def flag_options(layout, q, events, used_positions):
    """Best slot pair per free neighbour of q (most hook events covered,
    then fewest added TICKs, then shortest)."""
    ops = q_ops(layout)[q]
    lo, hi = 2, layout["final"] - 1
    slots = [t for t in range(lo, hi + 1) if t not in ops] + [k + 0.5 for k in range(1, hi + 1)]
    best = None
    for t1, t2 in itertools.combinations(sorted(slots), 2):
        if not all(r == "control" for t, r in ops.items() if t1 < t < t2):
            continue
        cover = sum(1 for e in events if t1 <= e < t2)
        added = sum(1 for s in (t1, t2) if s != int(s))
        key = (-cover, added, t2 - t1, t1)
        if cover and (best is None or key < best[0]):
            best = (key, t1, t2)
    if best is None:
        return []
    free = [p for p in neighbours(layout["emb"][q]) if p not in used_positions]
    return [(Flag(q, p, best[1], best[2]), -best[0][0]) for p in free]


def added_ticks(flags):
    return len({s for f in flags for s in (f.t1, f.t2) if s != int(s)})


def evaluate(inner, full, layout, flags):
    """Full validity check of a candidate; returns (row fields, valid, reason)."""
    t0 = time.perf_counter()
    emb = layout["emb"]
    v = C.check_circuit(inner, emb)  # defaults: strict, live_rule="gate", final_layer="auto"
    if v:
        return dict(reason="constraints: " + json.dumps(C.summarize(v))), False
    eq = Q.check_equivalence(inner, full, flag_qubits=tuple(layout["flags"]))
    if not eq["ok"]:
        return dict(reason="equivalence: " + json.dumps(
            {k: eq[k]["ok"] for k in ("i_code", "ii_check", "iii_reverse", "iv_deterministic")})), False
    r2 = verify(full, inner, max_fault_count=2)
    r3 = verify(full, inner, max_fault_count=3)
    rate2, rate3 = r2["error_rate_per_kept_shot"]["T"], r3["error_rate_per_kept_shot"]["T"]
    return dict(
        malignant_T_1=r2["T"][1]["malignant"], malignant_T_2=r2["T"][2]["malignant"],
        malignant_T_3=r3["T"][3]["malignant"], benign_T_2=r2["T"][2]["benign"],
        malignant_S_2=r2["S"][2]["malignant"],
        ler_T_mfc2=rate2, ler_T_mfc2_one_in=round(1 / rate2) if rate2 > 0 else "",
        ler_T_mfc3=rate3, ler_T_mfc3_one_in=round(1 / rate3) if rate3 > 0 else "",
        n_cx=len(C.two_qubit_gates(inner)), max_degree=max(map(len, C.partners(inner).values())),
        ticks=inner.num_ticks, runtime_s=round(time.perf_counter() - t0, 3), reason=""), True


# ---- main ---------------------------------------------------------------------------

FIELDS = ["id", "base_id", "m_roots", "n_qubits_tree", "k_ancillas", "tree", "labelling",
          "parity_qubits", "parity_lines", "hooks", "n_flags", "flags", "added_ticks", "n_cx",
          "max_degree", "ticks", "malignant_T_1", "malignant_T_2", "malignant_T_3", "benign_T_2",
          "malignant_S_2", "ler_T_mfc2", "ler_T_mfc2_one_in", "ler_T_mfc3", "ler_T_mfc3_one_in",
          "runtime_s", "stim_file", "full_stim_file"]
BASE_FIELDS = ["base_id", "m_roots", "n_qubits_tree", "k_ancillas", "depth", "tree", "labelling",
               "malignant_T_2_best", "malignant_T_2_hist", "ler_T_best", "hooks", "hook_free_nbrs",
               "design_rule_ok", "status", "seconds"]


def depth_of(parent, roots):
    """Fold depth of a forest {position: parent} under the ASAP schedule."""
    kids = defaultdict(list)
    for v, par in parent.items():
        if par is not None:
            kids[par].append(v)
    fin = {}

    def f(v):
        if v not in fin:
            t = 0
            for c in sorted(kids[v], key=f):
                t = max(t + 1, f(c) + 1)
            fin[v] = t
        return fin[v]

    return max(f(r) for r in roots)


def grow_forests(roots, dmax, nmax, grid=WILLOW):
    """Every forest of grid edges containing the roots (one component per root),
    no other qubit on a root's readout line, fold depth <= dmax, up to nmax
    qubits; built leaf by leaf, deduplicated by edge set. Yields parent maps."""
    lines = {readout_line(r) for r in roots}
    allowed = {p for p in grid if readout_line(p) not in lines}
    level = {frozenset(): {r: None for r in roots}}
    for _ in range(len(roots), nmax):
        nxt = {}
        for es, parent in level.items():
            for v in parent:
                for w in neighbours(v, grid):
                    if w in parent or w not in allowed:
                        continue
                    e2 = es | {(v, w)}
                    if e2 in nxt:
                        continue
                    p2 = dict(parent)
                    p2[w] = v
                    if depth_of(p2, roots) <= dmax:
                        nxt[e2] = p2
        level = nxt
        yield from level.values()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--dmax", type=int, default=4)
    parser.add_argument("--nmax", type=int, default=12)
    parser.add_argument("--max-embeddings-per-base", type=int, default=60)
    parser.add_argument("--max-valid", type=int, default=MAX_VALID)
    args = parser.parse_args()
    out = Path(args.out)
    (out / "option1").mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    log = lambda *a: print(f"[{time.perf_counter() - t0:8.1f} s]", *a, flush=True)
    labs = labelling_classes()
    log("labelling classes", len(labs))

    # ---- the search space, grouped by (fold depth, n, m) ----------------------------
    groups = defaultdict(dict)   # (d, n, m) -> {abstract key: [Base, ...] (capped)}
    space = Counter()
    for m in (1, 2):
        for par in grow_forests(ROOTS[m], args.dmax, args.nmax):
            n = len(par)
            space[f"m{m}_forests_n{n}"] += 1
            if n < 7 + m:
                continue
            d = depth_of(par, ROOTS[m])
            for roles in role_assignments(par, ROOTS[m]):
                base = Base(par, roles, ROOTS[m])
                key = base.abstract_key()
                space[f"m{m}_d{d}_n{n}_embedded_bases"] += 1
                lst = groups[(d, n, m)].setdefault(key, [])
                if len(lst) < args.max_embeddings_per_base:
                    lst.append(base)
        log("enumerated m =", m)
    for g, keys in sorted(groups.items()):
        space[f"m{g[2]}_d{g[0]}_n{g[1]}_abstract_bases"] = len(keys)
    space = dict(sorted(space.items()))
    tot_abs = sum(len(k) for k in groups.values())
    log("space", json.dumps(space))
    log("abstract bases in the space:", tot_abs, "; x 210 labellings =", tot_abs * len(labs))
    state = dict(space=space, abstract_bases_total=tot_abs,
                 abstract_bases_x_labellings=tot_abs * len(labs), settings=dict(
                     roots=ROOTS, dmax=args.dmax, nmax=args.nmax, noise="uniformly_depolarize",
                     p=NOISE, max_fault_count=[2, 3], readout="strict", live_rule="gate",
                     final_layer="auto", max_degree=4, labelling_classes=len(labs),
                     max_embeddings_per_base=args.max_embeddings_per_base, max_valid=args.max_valid,
                     order="groups by (depth, n, m); inside a group by (best malignant T2, #hooks, LER)"))

    fh = (out / "option1_candidates.csv").open("w", newline="")
    wr = csv.DictWriter(fh, fieldnames=FIELDS)
    wr.writeheader()
    bh = (out / "option1_bases.csv").open("w", newline="")
    bw = csv.DictWriter(bh, fieldnames=BASE_FIELDS)
    bw.writeheader()
    screen = {}  # key -> dict(lab, hist, rate, hooks)
    n_valid = n_eval = n_bases = 0
    invalid = Counter()
    groups_done = []
    stop = False
    pool = Pool(args.workers)

    def checkpoint(final=False):
        state.update(n_abstract_screened=len(screen), n_bases_flag_tried=n_bases,
                     n_evaluated=n_eval, n_valid=n_valid, invalid_reasons=dict(invalid),
                     groups_done=groups_done, elapsed_s=time.perf_counter() - t0)
        if final:
            state["exhausted"] = not stop
        (out / "option1_state.json").write_text(json.dumps(state, indent=1, default=str))

    cache_path = out / "option1_screen.json"
    if cache_path.exists():  # resume
        for k, v in json.loads(cache_path.read_text()).items():
            screen[tuple(k.split("|"))] = dict(v, lab=tuple(v["lab"]),
                                               hist={int(x): y for x, y in v["hist"].items()},
                                               hooks={int(x): y for x, y in v["hooks"].items()})
        log("resumed screen cache:", len(screen))

    def save_screen():
        cache_path.write_text(json.dumps({"|".join(k): v for k, v in screen.items()}, default=str))

    # ---- phase S: screen every abstract base (best of 210 labellings, hooks) ---------
    where = {}
    for g in sorted(groups):
        d, n, m = g
        keys = groups[g]
        log(f"--- screening group depth {d}, n {n}, m {m}: {len(keys)} abstract bases")
        for i, (key, bases) in enumerate(keys.items()):
            where[key] = g
            if key in screen:
                continue
            layout = build(bases[0])
            inner = to_circuit(layout)
            light = dict(data=layout["data"])
            res = pool.map(_verify_labelling, [(str(inner), light, lab) for lab in labs], chunksize=6)
            res.sort(key=lambda x: (x[1], x[2]))
            lab = res[0][0]
            hooks = ({} if res[0][1] == INFEASIBLE else
                     hooks_of(inner, full_circuit(inner, light, lab), layout)[0])
            screen[key] = dict(lab=lab, hist=dict(sorted(Counter(r[1] for r in res).items())),
                               rate=res[0][2], hooks=hooks)
            if (i + 1) % 100 == 0:
                log(f"   screened {i + 1}/{len(keys)}")
                save_screen()
        save_screen()
        groups_done.append(dict(depth=d, n=n, m=m, abstract=len(keys)))
        checkpoint()
    best_hist = Counter(min(v["hist"]) for v in screen.values())
    state["screen_best_malignant_T2_histogram"] = dict(sorted(best_hist.items()))
    log("screen done; best-labelling malignant T2 histogram:", dict(sorted(best_hist.items())))

    # ---- phase F: flag bases in global order ------------------------------------------
    order = sorted(where, key=lambda k: (min(screen[k]["hist"]), len(screen[k]["hooks"]),
                                         where[k][1], where[k][0], screen[k]["rate"]))
    if True:
        for key in order:
            if stop:
                break
            d, n, m = where[key]
            keys = groups[where[key]]
            sc = screen[key]
            lab, hist, rate, hooks = sc["lab"], sc["hist"], sc["rate"], sc["hooks"]
            if min(hist) == INFEASIBLE:
                continue  # no labelling makes this forest a double check of the code
            status, chosen = "design_rule_fail", None
            for base in keys[key]:
                layout = build(base)
                used = set(layout["emb"].values())
                free = {q: [p for p in neighbours(layout["emb"][q]) if p not in used] for q in hooks}
                if min(hist) == 0 or all(free[q] for q in hooks):
                    status = "zero_malignant" if min(hist) == 0 else "flagged"
                    chosen = (base, layout, used, free)
                    break
            base = chosen[0] if chosen else keys[key][0]
            layout0 = chosen[1] if chosen else build(base)
            free = chosen[3] if chosen else {}
            bid = n_bases
            n_bases += 1
            row = dict(base_id=bid, m_roots=m, n_qubits_tree=n, k_ancillas=len(layout0["anc"]),
                       depth=d, tree=base.describe(), labelling=lab, malignant_T_2_best=min(hist),
                       malignant_T_2_hist=json.dumps(hist), ler_T_best=rate, hooks=json.dumps(hooks),
                       hook_free_nbrs=json.dumps({q: len(v) for q, v in free.items()}),
                       design_rule_ok=chosen is not None, status=status, seconds="")
            if not chosen:
                bw.writerow(row)
                bh.flush()
                continue
            _, layout, used, _ = chosen
            light = dict(data=layout["data"])
            cand_groups = []
            if status == "zero_malignant":
                cand_groups.append([()])
            else:
                per_hook = {q: flag_options(layout, q, hooks[q], used)
                            for q in sorted(hooks, key=lambda q: (-len(hooks[q]), q))}
                for q, opts in per_hook.items():
                    cand_groups.append([(f,) for f, _ in opts])
                qs = list(per_hook)
                if len(qs) == 1:
                    cand_groups.append([(a, b) for (a, _), (b, _) in
                                        itertools.combinations(per_hook[qs[0]], 2)])
                for q1, q2 in itertools.combinations(qs, 2):
                    cand_groups.append([(a, b) for a, _ in per_hook[q1] for b, _ in per_hook[q2]
                                        if a.at != b.at])
            got = 0
            for cg in cand_groups:
                for flags in cg:
                    lay = build(base, flags)
                    ci = to_circuit(lay)
                    fc = full_circuit(ci, light, lab)
                    n_eval += 1
                    r, ok = evaluate(ci, fc, lay, flags)
                    if not ok:
                        invalid[r["reason"].split(":")[0]] += 1
                        continue
                    cid = n_valid
                    pth = out / "option1" / f"cand{cid:02d}.inner.stim"
                    pth.write_text(str(ci))
                    pf = out / "option1" / f"cand{cid:02d}.full.stim"
                    pf.write_text(str(fc))
                    roots_pos = [lay["emb"][x] for x in lay["roots"]]
                    wr.writerow(dict(
                        id=cid, base_id=bid, m_roots=m, n_qubits_tree=n, k_ancillas=len(lay["anc"]),
                        tree=base.describe(), labelling=lab,
                        parity_qubits=json.dumps({x: lay["emb"][x] for x in lay["roots"]}),
                        parity_lines=json.dumps(sorted({readout_line(x) for x in roots_pos})),
                        hooks=json.dumps(hooks), n_flags=len(flags),
                        flags=";".join(map(str, flags)), added_ticks=added_ticks(flags),
                        stim_file=str(pth), full_stim_file=str(pf),
                        **{k: v for k, v in r.items() if k != "reason"}))
                    fh.flush()
                    n_valid += 1
                    got += 1
                    log(f"VALID #{cid} base {bid} d{d} n{n} m{m} flags={[str(f) for f in flags]} "
                        f"malT1={r['malignant_T_1']} malT2={r['malignant_T_2']} "
                        f"malT3={r['malignant_T_3']} LER 1 in {r['ler_T_mfc2_one_in']}")
                    if n_valid >= args.max_valid:
                        stop = True
                    break  # at most one valid candidate per flag group
                if stop:
                    break
            row["status"] = status + f" ({got} valid)"
            bw.writerow(row)
            bh.flush()
            if n_bases % 10 == 0 or stop:
                checkpoint()
        log(f"flag phase: bases tried {n_bases}, evaluated {n_eval}, valid {n_valid}, "
            f"invalid {dict(invalid)}")
    pool.close()
    checkpoint(final=True)
    fh.close()
    bh.close()
    log("done", n_valid, "valid;", "exhausted" if not stop else "stopped at max-valid")


if __name__ == "__main__":
    main()
