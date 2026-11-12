"""Generalised (multi-control) Z / X flags on G4-type fold trees (ZZ-flag round).

A GENERALISED Z FLAG is a free Willow qubit f, prepared with R, that receives
CX(q_i -> f) from one or more grid neighbours q_i (tree qubits) at chosen
slots, and is measured with M in the final measurement layer; its DETECTOR is
the flag record (xor the MPP / mid-check records if needed, smallest
deterministic choice, checked with stim). An X FLAG is the dual: RX f,
CX(f -> q_i), MX f. Same-control flags (first-ex.md) and the two-control flags
of Chan et al.'s d3a6f2 are special cases.

PROBES. A flag is a set of probes (q, slot, basis): CX(q -> f) at slot s reads
Z_q there (X flag: X_q). Slot s is an existing TICK where q is idle (integer)
or a new TICK inserted after TICK k (k + 0.5). cliffordea puts all noise of a
TICK after its operations (enum/noise/_noise.py:396-407, idle noise :408), so
a probe at integer slot s sees the error events of TICKs < s, a probe at
k + 0.5 those of TICKs <= k. Each probe is back-propagated (stim
PauliString.before) to the start of the double check:
  * through a reset / measure-reset: the component that the fresh state fixes
    (Z after R/MR, X after RX/MRX) is dropped, the other one becomes a random
    variable (tick, qubit);
  * at the start: data part reduced modulo the allowed stabilisers (Z flags:
    Z plaquettes; X flags: X plaquettes and X_L, the latter through the MPP
    marker record).
  A set of probes is a deterministic flag iff the xor of their syndromes
  (reduced data part + random variables) is 0. stim confirms it on the built
  circuit (equivalence.is_deterministic).

COVERAGE (prefilter, exact for the base's own faults). A malignant 2-fault T
configuration (i, j) of the base is a pair of cliffordea fault classes
(FaultCombinator.index_to_events, enum/combinators/fault_combinator.py:374),
each a set of error events (tick, Pauli). After adding one flag, (i, j)
survives iff some event of i and some event of j have the same flag bit. So a
single flag removes (i, j) iff its bit is constant on i, constant on j, and
different: linear conditions over GF(2) on the probe-indicator vector x. With
two flags, a pair is counted as removed if one of them separates it (sufficient
condition; verify() decides). New faults (on the flag, on the flag CXs, and
idle noise in inserted TICKs) are not in the prefilter; verify() sees them.

GEOMETRY. The grid is bipartite and a tree edge is a grid edge, so all
controls of one flag have the same depth parity in the tree (a flag can never
touch a qubit and its parent). Realisability on Willow (free grid point next
to all controls, degree <= 4, readout lines) is decided by an explicit
embedding search (``embed``) after verify().
"""
from __future__ import annotations


import itertools
from collections import defaultdict
from dataclasses import dataclass, field

import stim

from cliffordea import accept, enum

from nnflags import equivalence as Q
from nnflags.verify import load_measurement

NOISE = 1e-3
FLAG_ID0 = 10 ** 8  # global measurement ids of flag records (equivalence.to_layers ids are small)


# ---- the base design ----------------------------------------------------------------

@dataclass
class Design:
    """A flag-free CX-form double check: cliffordea inner circuit + code info."""
    name: str
    inner: stim.Circuit
    full_args: tuple            # (plaquettes, majority, minority, data) for g4.full_for
    emb: dict                   # default embedding (circuit qubit -> Willow (r, c))
    info: dict = field(default_factory=dict)

    def __post_init__(self):
        self.layers = Q.to_layers(self.inner)
        self.nq = self.inner.num_qubits
        self.data = tuple(sorted(self.full_args[3]))
        self.T = len(self.layers)                     # TICKs 0 .. T-1
        meas_ticks = [t for t, items in enumerate(self.layers) for it in items
                      if isinstance(it, Q.Op) and it.name != "MPP" and it.ids]
        self.final = max(meas_ticks)
        self.mid_ticks = sorted({t for t in meas_ticks if t != self.final})
        self.mid_measured = sorted({q for t in self.mid_ticks for it in self.layers[t]
                                    if isinstance(it, Q.Op) and it.ids for q in it.targets})
        self.busy = defaultdict(set)                  # tick -> qubits with an op
        self.edges = set()
        for t, items in enumerate(self.layers):
            for it in items:
                if isinstance(it, Q.Op) and it.name != "MPP":
                    self.busy[t].update(it.targets)
                    if len(it.targets) == 2:
                        self.edges.add(tuple(sorted(it.targets)))
        # every qubit with an operation (a root may have no CX: a lone ancilla component)
        self.qubits = sorted({q for qs in self.busy.values() for q in qs} | set(self.data))
        adj = defaultdict(set)
        for a, b in self.edges:
            adj[a].add(b)
            adj[b].add(a)
        self.adj = dict(adj)
        # depth parity = grid colour of every embedding (the CX graph is a tree / forest)
        self.colour = {}
        for s in self.qubits:
            if s in self.colour:
                continue
            self.colour[s] = 0
            stack = [s]
            while stack:
                v = stack.pop()
                for w in adj[v]:
                    if w not in self.colour:
                        self.colour[w] = 1 - self.colour[v]
                        stack.append(w)
                    else:
                        assert self.colour[w] != self.colour[v], "CX graph is not bipartite"

    def full(self, inner=None):
        from nnflags.g4 import full_for
        return full_for(self.inner if inner is None else inner, *self.full_args)


def design_from_option1(key: str, screen_entry: dict, name=None) -> Design:
    """Design of an Option-1 abstract base (screen-cache key + entry)."""
    from nnflags import search_option1 as S
    base = base_from_key(key)
    lay = S.build(base)
    inner = S.to_circuit(lay)
    lab = tuple(screen_entry["lab"])
    data = lay["data"]
    L = [data[lab[j]] for j in range(7)]
    full_args = (tuple(tuple(L[j] for j in p) for p in S.CODE_PLAQ),
                 tuple(L[j] for j in S.CODE_MAJ), tuple(L[j] for j in S.CODE_MIN), tuple(data))
    return Design(name or key, inner, full_args, dict(lay["emb"]),
                  info=dict(key=key, lab=lab, roots=lay["roots"], tree=base.describe(),
                            depth=lay["depth"], screen_T2=min(int(k) for k in screen_entry["hist"])))


def design_g4() -> Design:
    from nnflags import g4
    inner, _ = g4.inner_cx("cliffordea")
    emb = {q: tuple(int(x) for x in c) for q, c in inner.get_final_qubit_coordinates().items()}
    return Design("G4-CX", inner, (g4.PLAQUETTES, g4.MAJORITY, g4.MINORITY, g4.DATA), emb,
                  info=dict(key="G4", roots=[9], tree="G4 extracted (CX form)", depth=4))


# ---- abstract bases from the Option-1 screen cache ------------------------------------

def parse_canon(s: str):
    """'A(D(),D(D()))' -> (role, [children])."""
    pos = 0

    def node():
        nonlocal pos
        role = s[pos]
        assert s[pos + 1] == "("
        pos += 2
        kids = []
        while s[pos] != ")":
            kids.append(node())
            if s[pos] == ",":
                pos += 1
        pos += 1
        return role, kids

    t = node()
    assert pos == len(s)
    return t


def base_from_key(key: str):
    """A Base (search_option1) with the abstract shape ``key``, embedded around
    Option-1's roots (where the screen found it) with nothing else on a root's
    readout line."""
    from nnflags import search_option1 as S
    from nnflags.willow import WILLOW, neighbours, readout_line
    parts = key.split("|")
    roots = S.ROOTS[len(parts)]
    lines = {readout_line(r) for r in roots}
    allowed = {p for p in WILLOW if readout_line(p) not in lines}
    trees = [parse_canon(p) for p in parts]
    # match tree parts to roots: try both orders for m = 2
    for perm in itertools.permutations(range(len(parts))):
        parent, roles = {}, {}
        used = set(roots)
        jobs = []  # (position, subtree)
        for k, r in zip(perm, roots):
            parent[r] = None
            roles[r] = trees[k][0]
            jobs.append((r, trees[k]))

        def place(pending):
            if not pending:
                return True
            (pos, (role, kids)), rest = pending[0], pending[1:]
            if not kids:
                return place(rest)
            free = [w for w in neighbours(pos) if w in allowed and w not in used]
            for spots in itertools.permutations(free, len(kids)):
                for w, (crole, _) in zip(spots, kids):
                    used.add(w)
                    parent[w] = pos
                    roles[w] = crole
                if place(rest + [(w, kid) for w, kid in zip(spots, kids)]):
                    return True
                for w in spots:
                    used.discard(w)
                    parent.pop(w)
                    roles.pop(w)
            return False

        if place(jobs):
            b = S.Base(parent, roles, roots)
            if b.abstract_key() == tuple(sorted(parts)):
                return b
    raise ValueError(f"cannot embed {key}")


# ---- probes ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Probe:
    q: int
    slot: float     # integer: existing TICK (q idle); k + 0.5: new TICK after TICK k
    basis: str      # "Z" (Z flag, CX q -> f) or "X" (X flag, CX f -> q)

    @property
    def boundary(self):
        """Probe sees the events of TICKs < boundary."""
        return int(self.slot) if self.slot == int(self.slot) else int(self.slot) + 1

    def __str__(self):
        return f"{self.basis}{self.q}@{self.slot:g}"


def _gf2_reduce(v, basis):
    for b in basis:
        if v ^ b < v:
            v ^= b
    return v


def _gf2_basis(vecs):
    basis = []
    for v in vecs:
        v = _gf2_reduce(v, basis)
        if v:
            basis.append(v)
            basis.sort(reverse=True)
    return basis


class ProbeAnalysis:
    """Probes of a design, their syndromes and their flip bits on error events."""

    def __init__(self, d: Design, bases=("Z", "X"), half_slots=True, controls=None):
        self.d = d
        nq = d.nq
        self.unitary = []
        self.collapse = []
        for items in d.layers:
            u = stim.Circuit()
            col = []
            for it in items:
                if not isinstance(it, Q.Op) or it.name == "MPP":
                    continue
                gd = stim.gate_data(it.name)
                if gd.is_unitary:
                    u.append(it.name, it.targets)
                else:
                    col += [(it.name, q) for q in it.targets]
            self.unitary.append(u)
            self.collapse.append(col)
        data = list(d.data)
        bit = {q: k for k, q in enumerate(data)}
        plaq = d.full_args[0]
        vec = lambda qs: sum(1 << bit[q] for q in qs)
        # deterministic both in the code state (full circuit) and in cliffordea's inner
        # circuit, whose data start in |0>^7 with the MPP marker fixing X_L: the
        # intersection is span(Z plaquettes) for Z-type and {1, X_L} for X-type.
        self.allowed = {"Z": _gf2_basis([vec(p) for p in plaq]),
                        "X": _gf2_basis([vec(data)])}
        self.data_bit = bit
        self.random_index = {}
        self.probes = []
        for q in (d.qubits if controls is None else controls):
            slots = [s for s in range(2, d.final) if q not in d.busy[s]]
            if half_slots:
                slots += [k + 0.5 for k in range(1, d.final)]
            for b in bases:
                for s in sorted(slots):
                    self.probes.append(Probe(q, s, b))
        self.ops_at = {}       # probe -> {boundary: PauliString}
        self.syndrome = {}
        for p in self.probes:
            self._analyse(p)

    def _rand(self, key):
        return 1 << (16 + self.random_index.setdefault(key, len(self.random_index)))

    def _analyse(self, p: Probe):
        nq = self.d.nq
        o = stim.PauliString(nq)
        o[p.q] = p.basis
        at = {}
        rnd = 0
        for t in range(p.boundary - 1, 0, -1):
            at[t + 1] = o.copy()
            o = o.before(self.unitary[t]) if len(self.unitary[t]) else o
            for name, q in self.collapse[t]:
                k = o[q]   # 0 I, 1 X, 2 Y, 3 Z
                if not k:
                    continue
                fixed = 3 if name in ("R", "MR", "M") else 1 if name in ("RX", "MRX", "MX") else None
                if name in ("M", "MX"):  # plain measurement before the probe: treat as random
                    fixed = None
                if k != fixed:
                    rnd ^= self._rand((t, q))
                o[q] = 0
        at[1] = o.copy()
        self.ops_at[p] = at
        # data part at the start
        v = 0
        for q in range(nq):
            k = o[q]
            if not k:
                continue
            if q not in self.data_bit or (k != (3 if p.basis == "Z" else 1)):
                rnd ^= self._rand(("start", q, k))
            else:
                v |= 1 << self.data_bit[q]
        self.syndrome[p] = _gf2_reduce(v, self.allowed[p.basis]) | rnd

    def flips(self, p: Probe, tick: int, pauli: stim.PauliString) -> int:
        """1 iff an error ``pauli`` after the ops of TICK ``tick`` flips probe p."""
        if tick + 1 > p.boundary or tick < 1:
            return 0
        return int(not self.ops_at[p][tick + 1].commutes(pauli))


def event_pauli(ev, nq) -> stim.PauliString:
    _, name, targets = ev
    ps = stim.PauliString(nq)
    if name not in ("E", "X_ERROR", "Y_ERROR", "Z_ERROR"):
        # measurement-result flip (M, MX, MRX, ...: cliffordea ONE_QUBIT_ERROR_EVENTS,
        # enum/constants.py:5): no Pauli on the qubits, so it flips no probe
        return ps
    if name == "E":
        for t in targets:
            ps[t.value] = "X" if t.is_x_target else "Y" if t.is_y_target else "Z"
    else:
        ps[targets[0].value] = name[0]
    return ps


# ---- malignant configurations of the base ---------------------------------------------

def malignant_pairs(d: Design, inner=None, full=None, max_fault_count=2):
    """(pairs, events, comb, kept): malignant 2-fault T configurations as pairs of
    fault indices, and {index: [(tick, PauliString)]} for the faults in them."""
    inner = d.inner if inner is None else inner
    full = d.full(inner) if full is None else full
    m = load_measurement(full, inner)
    comb = enum.FaultCombinator(enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=NOISE))
    an = accept.CliffordLogicalAnalyzer(data_indices=m.DATA_INDICES,
                                        stabilizer_generators=m.STABILIZER_GENERATORS,
                                        logical_s=m.LOGICAL_S)
    kept = comb.get_kept_effects(logical_analyzer=an, max_fault_count=max_fault_count,
                                 cultivated_states=("T",))
    pairs = sorted({tuple(sorted(cfg)) for k, eff in enumerate(kept["T"]) for pr, fid, cfgs in eff.values()
                    if pr > 0 and fid != 1 for cfg in cfgs if len(cfg) == 2})
    nq = inner.num_qubits
    events = {i: [(ev[0], event_pauli(ev, nq)) for ev in comb.index_to_events[i]]
              for pr in pairs for i in pr}
    return pairs, events, comb, kept


# ---- coverage as a GF(2) system ---------------------------------------------------------

class Coverage:
    """Flip rows of the malignant faults over a probe set, deduplicated."""

    def __init__(self, pa: ProbeAnalysis, pairs, events):
        self.pa = pa
        self.pairs = pairs
        self.col = {p: k for k, p in enumerate(pa.probes)}
        self.rows = {}      # fault index -> set of distinct row ints (bit k = flips probe k)
        for i, evs in events.items():
            rs = set()
            for tick, ps in evs:
                r = 0
                for k, p in enumerate(pa.probes):
                    if pa.flips(p, tick, ps):
                        r |= 1 << k
                rs.add(r)
            self.rows[i] = sorted(rs)
        self.syn = [pa.syndrome[p] for p in pa.probes]

    def system(self, cols, pair_idx):
        """Rows (mask over the local columns ``cols``, rhs) for: deterministic, and
        every pair in pair_idx separated by the flag."""
        def loc(r):
            return sum(1 << j for j, k in enumerate(cols) if r >> k & 1)
        eqs = []
        nbits = max(self.syn[k] for k in cols).bit_length() if cols else 0
        for b in range(nbits):
            m = sum(1 << j for j, k in enumerate(cols) if self.syn[k] >> b & 1)
            if m:
                eqs.append((m, 0))
        for pi in pair_idx:
            i, j = self.pairs[pi]
            for f in (i, j):
                r0 = self.rows[f][0]
                for r in self.rows[f][1:]:
                    m = loc(r0 ^ r)
                    if m:
                        eqs.append((m, 0))
            eqs.append((loc(self.rows[i][0] ^ self.rows[j][0]), 1))
        return eqs


def solve_gf2(eqs, ncols):
    """Gaussian elimination. Returns (particular solution, nullspace basis) or None."""
    piv = []   # (pivot col, mask, rhs)
    for m, r in eqs:
        for pc, pm, pr in piv:
            if m >> pc & 1:
                m ^= pm
                r ^= pr
        if not m:
            if r:
                return None
            continue
        pc = m.bit_length() - 1
        new = []
        for qc, qm, qr in piv:
            if qm >> pc & 1:
                qm ^= m
                qr ^= r
            new.append((qc, qm, qr))
        piv = new + [(pc, m, r)]
    x = 0
    pcs = {pc for pc, _, _ in piv}
    for pc, pm, pr in piv:
        if pr:
            x |= 1 << pc
    null = []
    for fc in range(ncols):
        if fc in pcs:
            continue
        v = 1 << fc
        for pc, pm, pr in piv:
            if pm >> fc & 1:
                v |= 1 << pc
        null.append(v)
    return x, null


# ---- building flagged circuits ----------------------------------------------------------

@dataclass(frozen=True)
class Flag:
    probes: tuple       # Probe, all of one basis, distinct slots
    at: tuple | None = None   # Willow position (None = not embedded yet)

    @property
    def basis(self):
        return self.probes[0].basis

    @property
    def controls(self):
        return tuple(sorted({p.q for p in self.probes}))

    def __str__(self):
        s = "+".join(f"q{p.q}@{p.slot:g}" for p in sorted(self.probes, key=lambda p: p.slot))
        return f"{self.basis}[{s}]" + (f"->{self.at}" if self.at else "")


def added_ticks(flags):
    return len({p.slot for f in flags for p in f.probes if p.slot != int(p.slot)})


def build_flagged(d: Design, flags, emb=None) -> tuple[stim.Circuit, list, list]:
    """Inner circuit with flags; returns (inner, flag qubit indices, flag detectors ok).
    Flags: prepared in TICK 1 (R / RX), probes at their slots, measured (M / MX) in
    the final measurement TICK with a DETECTOR (smallest deterministic choice of
    {flag}, {flag, MPP}, {flag, mid records}, {flag, mid, MPP}), reset in the
    trailing TICK. Raises ValueError if a flag detector is not deterministic or a
    qubit would be used twice in a TICK."""
    layers = [[Q.Op(it.name, list(it.targets), list(it.args), list(it.ids), it.tag)
               if isinstance(it, Q.Op) else (it[0], it[1], list(it[2]), list(it[3]))
               for it in items if isinstance(it, Q.Op) or it[0] == "det"]
              for items in d.layers]
    halfs = sorted({p.slot for f in flags for p in f.probes if p.slot != int(p.slot)})
    index = {}
    new = []
    for t, items in enumerate(layers):
        index[t] = len(new)
        new.append(items)
        for h in halfs:
            if int(h) == t:
                index[h] = len(new)
                new.append([])
    layers = new
    nq = d.nq
    fq = list(range(nq, nq + len(flags)))
    mpp_id = next(g for it in layers[0] if isinstance(it, Q.Op) and it.name == "MPP" for g in it.ids)
    mid_ids = [g for t in d.mid_ticks for it in layers[index[t]] if isinstance(it, Q.Op) for g in it.ids]
    fin = index[d.final]
    for k, (f, fl) in enumerate(zip(fq, flags)):
        z = fl.basis == "Z"
        layers[index[1]].append(Q.Op("R" if z else "RX", [f]))
        for p in fl.probes:
            layers[index[p.slot]].append(Q.Op("CX", [p.q, f] if z else [f, p.q]))
        layers[fin].append(Q.Op("M" if z else "MX", [f], ids=[FLAG_ID0 + k]))
        layers[-1].append(Q.Op("R", [f]))
    for items in layers:
        qs = [q for it in items if isinstance(it, Q.Op) and it.name != "MPP" for q in it.targets]
        if len(qs) != len(set(qs)):
            raise ValueError("qubit used twice in a TICK")
    # detectors, one flag at a time
    for k in range(len(flags)):
        opts = [[FLAG_ID0 + k], [FLAG_ID0 + k, mpp_id]] + [[FLAG_ID0 + k, g] for g in mid_ids] + [
            [FLAG_ID0 + k] + mid_ids, [FLAG_ID0 + k] + mid_ids + [mpp_id]]
        for ids in opts:
            layers[fin].append(("det", "DETECTOR", [], ids))
            if Q.is_deterministic(Q.from_layers(layers)):
                break
            layers[fin].pop()
        else:
            raise ValueError(f"flag {k} ({flags[k]}) is not deterministic")
    c = Q.from_layers(layers)
    if emb is not None:
        head = stim.Circuit()
        for q in sorted(emb):
            head.append("QUBIT_COORDS", [q], emb[q])
        c = head + c
    return c, fq


# ---- from a GF(2) solution to a concrete flag ---------------------------------------------

def _weight(v):
    return bin(v).count("1")


def concrete_flags(cov: Coverage, cols, pair_idx, max_null=14, limit=6):
    """Up to ``limit`` concrete flags (sorted by #controls, #probes, #added TICKs)
    realising the system for ``pair_idx`` on columns ``cols``: one probe per slot,
    identical columns merged (any member can stand in for its group)."""
    eqs = cov.system(cols, pair_idx)
    # merge identical columns
    colvec = defaultdict(int)
    for e, (m, _) in enumerate(eqs):
        for j in range(len(cols)):
            if m >> j & 1:
                colvec[j] |= 1 << e
    groups = defaultdict(list)
    for j in range(len(cols)):
        groups[colvec[j]].append(cols[j])
    keys = [k for k in groups if k]   # zero columns never matter
    reps = {i: k for i, k in enumerate(keys)}
    req = []
    for e, (_, r) in enumerate(eqs):
        m = sum(1 << i for i, k in reps.items() if k >> e & 1)
        req.append((m, r))
    sol = solve_gf2(req, len(keys))
    if sol is None:
        return []
    x0, null = sol
    if len(null) > max_null:
        null = sorted(null, key=_weight)[:max_null]
    xs = set()
    for bits in range(1 << len(null)):
        x = x0
        for k, v in enumerate(null):
            if bits >> k & 1:
                x ^= v
        if x:
            xs.add(x)
    out = []
    pa = cov.pa
    for x in sorted(xs, key=_weight)[:64]:
        chosen = [groups[keys[i]] for i in range(len(keys)) if x >> i & 1]
        if len(chosen) > 6:
            continue
        best = None
        for combo in itertools.islice(itertools.product(*chosen), 20000):
            ps = [pa.probes[k] for k in combo]
            slots = [p.slot for p in ps]
            if len(set(slots)) != len(slots):
                continue
            key = (len({p.q for p in ps}), len(ps), sum(s != int(s) for s in slots), tuple(sorted(slots)))
            if best is None or key < best[0]:
                best = (key, tuple(sorted(ps, key=lambda p: p.slot)))
        if best:
            out.append(best)
    out.sort(key=lambda b: b[0])
    seen, res = set(), []
    for key, ps in out:
        if ps not in seen:
            seen.add(ps)
            res.append(Flag(ps))
        if len(res) >= limit:
            break
    return res


def coverable_subsets(cov: Coverage, cols, npairs):
    """All subsets (bitmasks) of the malignant pairs one flag on ``cols`` can remove."""
    ok = {0}
    good = []
    for size in range(1, npairs + 1):
        for comb in itertools.combinations(range(npairs), size):
            mask = sum(1 << i for i in comb)
            if any((mask & ~(1 << i)) not in ok for i in comb):
                continue
            if solve_gf2(cov.system(cols, list(comb)), len(cols)) is not None:
                ok.add(mask)
                good.append(mask)
    return good


# ---- Willow embeddings of tree + flags ------------------------------------------------------

BULK_ROOT = (6, 7)   # every point within Manhattan distance 5 of (6, 7) is a Willow qubit


def tree_centre(d: Design):
    """Node of minimum eccentricity in the CX graph (ties: smallest index)."""
    def ecc(s):
        dist, front = {s: 0}, [s]
        while front:
            nxt = []
            for v in front:
                for w in d.adj.get(v, ()):
                    if w not in dist:
                        dist[w] = dist[v] + 1
                        nxt.append(w)
            front = nxt
        return max(dist.values()), -len(dist)
    return min(d.qubits, key=lambda q: (ecc(q)[1], ecc(q)[0], q))


def flag_specs(inner: stim.Circuit, flag_qubits, mid_tick=None):
    """[(controls, live at the mid-check TICK)] of the flags of a built circuit;
    also {flag: [(tick, control, "Z" | "X")]} (Z: CX q -> f, X: CX f -> q)."""
    from nnflags import constraints as C
    layers = Q.to_layers(inner)
    meas = [t for t, items in enumerate(layers) for it in items
            if isinstance(it, Q.Op) and it.name != "MPP" and it.ids]
    final = max(meas)
    mid = min(t for t in meas if t != final) if mid_tick is None else mid_tick
    gates = defaultdict(list)
    for t, _, a, b in C.two_qubit_gates(inner):
        if b in flag_qubits:
            gates[b].append((t, a, "Z"))
        elif a in flag_qubits:
            gates[a].append((t, b, "X"))
    specs = []
    for f in flag_qubits:
        g = sorted(gates[f])
        specs.append((tuple(sorted({q for _, q, _ in g})), g[0][2] == "X" or g[0][0] <= mid))
    return specs, dict(gates)


def embeddings(d: Design, flags, *, root_positions=None, grid=None, limit=None):
    """Yield embeddings {qubit: (r, c)} of the design's CX graph plus the flags
    (flag k = qubit d.nq + k, adjacent to all its controls) into Willow:
    injective, every CX on a coupler, and no other qubit live at the mid-check
    measurement on the readout line of a mid-measured qubit (all tree qubits are
    live there; a flag is, if it is an X flag or its first probe is at or before
    the mid TICK). ``root_positions``: list of {mid-measured qubit: position}
    (default: the centre of the CX graph at BULK_ROOT; when the graph is
    connected and its radius is <= 4, this is exhaustive up to translation:
    every flag is within distance 5 of the centre and the radius-5 diamond
    around BULK_ROOT lies inside Willow; readout lines r + c are translation
    covariant)."""
    from nnflags.willow import WILLOW, neighbours, readout_line
    grid = WILLOW if grid is None else grid
    adj = {q: set(v) for q, v in d.adj.items()}
    nodes = list(d.qubits)
    mid = d.mid_ticks[0] if d.mid_ticks else 10 ** 9
    live_mid = {q: True for q in nodes}
    for k, fl in enumerate(flags):
        f = d.nq + k
        nodes.append(f)
        if isinstance(fl, Flag):
            ctrl, live = fl.controls, fl.basis == "X" or min(p.slot for p in fl.probes) <= mid
        else:
            ctrl, live = fl
        adj[f] = set(ctrl)
        for q in ctrl:
            adj.setdefault(q, set()).add(f)
        live_mid[f] = live
    roots = list(d.mid_measured)
    if root_positions is None:
        root_positions = [{tree_centre(d): BULK_ROOT}]
    # order: BFS from the roots (flags right after their first control)
    count = 0
    for fixed in root_positions:
        order = []
        seen = set()
        queue = list(fixed)
        while queue or len(order) < len(nodes):
            if not queue:
                queue.append(next(q for q in nodes if q not in seen))
            v = queue.pop(0)
            if v in seen:
                continue
            seen.add(v)
            order.append(v)
            for w in sorted(adj.get(v, ()), key=lambda w: (w < d.nq, w)):
                if w not in seen:
                    queue.append(w)
        pos = {}
        used = set()
        lines = set()

        def ok_line(q, p):
            L = readout_line(p)
            if q in roots:
                return all(readout_line(pos[x]) != L or x in roots or not live_mid[x] for x in pos)
            return not (live_mid[q] and L in lines)

        def rec(i):
            nonlocal count
            if i == len(order):
                count += 1
                yield dict(pos)
                return
            v = order[i]
            placed = [w for w in adj.get(v, ()) if w in pos]
            if v in fixed:
                cands = [fixed[v]]
            elif placed:
                cands = [p for p in neighbours(pos[placed[0]], grid)]
            else:
                cands = sorted(grid)
            for p in cands:
                if p in used or not all(abs(p[0] - pos[w][0]) + abs(p[1] - pos[w][1]) == 1 for w in placed):
                    continue
                if not ok_line(v, p):
                    continue
                pos[v] = p
                used.add(p)
                added = v in roots and readout_line(p) not in lines
                if added:
                    lines.add(readout_line(p))
                yield from rec(i + 1)
                if limit is not None and count >= limit:
                    return
                del pos[v]
                used.discard(p)
                if added:
                    lines.discard(readout_line(p))

        yield from rec(0)
        if limit is not None and count >= limit:
            return


def find_valid_embedding(d: Design, flags, inner, *, max_tries=2000, root_positions=None):
    """First embedding (see ``embeddings``) under which ``inner`` passes the strict
    hardware check (constraints.check_circuit defaults). Returns (emb, n_tried,
    last violations) with emb None if none was found."""
    from nnflags import constraints as C
    tried, last = 0, None
    for emb in embeddings(d, flags, root_positions=root_positions):
        tried += 1
        v = C.check_circuit(inner, emb)
        if not v:
            return emb, tried, []
        last = v
        if tried >= max_tries:
            break
    return None, tried, last


def hook_qubits(d: Design):
    """X-hook qubits of a design (definition of search_option1.hooks_of, RESULTS_option1.md
    decision 6): qubits carrying the X/Y events of the faults with data weight >= 2 in the
    malignant 2-fault T configurations -> {qubit: [event ticks]}."""
    pairs, _, comb, _ = malignant_pairs(d)
    effect = {i: e for sig, dd in comb.basis.items() for e, i in dd.items()}
    nq = d.nq
    weight = lambda e: sum(1 for q in d.data if (e >> q) & 1 or (e >> (nq + q)) & 1)
    hooks = defaultdict(list)
    for cfg in pairs:
        for i in cfg:
            if weight(effect[i]) < 2:
                continue
            evs = comb.index_to_events[i]
            single = [(ev[0], ev[2][0].value) for ev in evs if ev[1] in ("X_ERROR", "Y_ERROR")]
            if not single:
                single = [(ev[0], t.value) for ev in evs if ev[1] == "E" for t in ev[2]
                          if t.is_x_target or t.is_y_target]
            cnt = defaultdict(int)
            for _, q in single:
                cnt[q] += 1
            if cnt:
                top = max(cnt.values())
                for q, k in cnt.items():
                    if k == top:
                        hooks[q] += [t for t, qq in single if qq == q]
    return {q: sorted(set(ts)) for q, ts in hooks.items()}
