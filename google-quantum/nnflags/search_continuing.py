"""Continuing-data search round: ZZ / X-flag double checks on Willow whose data
readout lines are disjoint from the lines of every measured qubit.

RULE ("continuing-data strict", constraints.continuing_data_violations): the 7
data qubits continue into escape / grafting, so every measurement of a non-data
qubit (parity roots mid-check, ancillas and flags at the end) is a violation
against every data qubit on its readout line r + c. On top: the strict rule
(constraints.check_circuit defaults: live_rule="gate", final_layer="auto"),
nearest neighbour, degree <= 4, no reuse in a TICK.

BASES (fold forests, CX form, search_option1.build / to_circuit conventions)
  * Enumerated directly as EMBEDDED forests on the square lattice Z^2, root(s)
    at the origin, grown leaf by leaf, with a LINE LABEL per readout line
    (r + c): "R" (root line: only the parity root(s) may sit there; strict
    rule at the mid-check measurement), "D" (data line) or "M" (line of
    measured ancillas). A qubit's role follows from its line: data on D, a
    measured ancilla on M. So the line-disjointness is enforced while growing
    (pruning), not afterwards. Variant "U" (Google's G6 pattern, see
    nnflags/g6_continuing.py): an internal node on a D line may instead be an
    ancilla that is never measured (RX, CXs, trailing R only), at most --umax.
  * Leaves are data; every ancilla has a child; exactly 7 data; n <= --nmax
    qubits; fold depth (ASAP schedule) <= --dmax; m = 1 root, or m = 2 roots
    on the same line at diagonal neighbours (0, 0), (-1, 1) (G4 / G6 pattern).
  * Embedded forests are deduplicated modulo translation and the four
    line-preserving lattice symmetries (id, transpose, rot180, antitranspose),
    then grouped by abstract key (Base.canon, roles D / A / U). verify() depends
    only on the key; the line pattern depends on the embedding, so EVERY
    embedding of a key is kept for flag placement.
  * Screen: per key, best of the 210 code labellings (verify, max_fault_count 2,
    T only); cached in results/continuing_screen.json.
FLAGS: as search_zzflags (generalised Z / X flags, <= 2, two-level greedy with
the exact GF(2) prefilter), but realisability = some embedding of the key plus
free lattice points for the flags such that
  * each flag is adjacent to all its controls,
  * no flag sits on a D line (continuing-data rule),
  * a flag live at the mid check is not on a root line (strict rule),
  * tree + flags fit on Willow after a translation.
SUCCESS = constraints.check_circuit(..., data_continue=True) == [] at the chosen
Willow placement, equivalence.check_equivalence ok, 0 malignant T at <= 2 faults.

Usage: nohup .venv/bin/python -m nnflags.search_continuing --workers 12 > logs/search_continuing.log &
"""
import argparse
import csv
import json
import time
import traceback
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import stim

from nnflags import constraints as C
from nnflags import equivalence as Q
from nnflags import search_option1 as S
from nnflags import search_zzflags as SZ
from nnflags import zzflags as Z
from nnflags.verify import verify
from nnflags.willow import WILLOW

ROOTS = {1: ((0, 0),), 2: ((0, 0), (-1, 1))}
SYMS = (lambda r, c: (r, c), lambda r, c: (c, r), lambda r, c: (-r, -c), lambda r, c: (-c, -r))
STOP_SUCCESSES = 10
INFEASIBLE = S.INFEASIBLE


def line(p):
    return p[0] + p[1]


def nbrs(p):
    r, c = p
    return ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))


# ---- enumeration of line-labelled embedded forests ----------------------------------

def patterns(m, dmax):
    """Line-label patterns: (a, labels of lines a..b) with root line 0 = "R", every other
    line "D" or "M", a <= 0 <= b, |a|, |b| <= dmax + (m == 2). Mirror images (rot180:
    line L -> -L) are skipped (canonical() identifies them)."""
    import itertools
    hi = dmax + (1 if m == 2 else 0)
    out = []
    for a in range(-hi, 1):
        for b in range(0, hi + 1):
            if a == b == 0:
                continue
            others = [L for L in range(a, b + 1) if L != 0]
            for labs in itertools.product("DM", repeat=len(others)):
                lab = dict(zip(others, labs))
                lab[0] = "R"
                mir = {-L: x for L, x in lab.items()}
                key = tuple(sorted(lab.items()))
                if tuple(sorted(mir.items())) < key:
                    continue
                out.append((a, b, key))
    return out


def grow_pattern(task):
    """All (parent, roles) with roots ROOTS[m] whose used lines are exactly a..b with the
    given labels (worker; see module doc)."""
    m, a, b, labkey, dmax, nmax, umax = task
    lab = dict(labkey)
    roots = ROOTS[m]
    nmax_anc = nmax - 7
    dmax_nodes = 7 + umax
    level = {frozenset(): {r: None for r in roots}}
    found = []
    for size in range(m, nmax):
        nxt = {}
        for es, parent in level.items():
            kids = set(parent.values())
            nd = sum(1 for v in parent if lab[line(v)] == "D")
            nm = len(parent) - nd
            childless_m = sum(1 for v in parent if lab[line(v)] != "D" and v not in kids)
            lmin = min(line(v) for v in parent)
            lmax = max(line(v) for v in parent)
            for v in parent:
                lv = lab[line(v)] != "D" and v not in kids
                for w in nbrs(v):
                    L = line(w)
                    if w in parent or L == 0 or L < a or L > b:
                        continue
                    isd = lab[L] == "D"
                    if isd and nd + 1 > dmax_nodes or not isd and nm + 1 > nmax_anc:
                        continue
                    if size + 1 + childless_m - lv + (not isd) > nmax:
                        continue
                    # remaining capacity: 7 data lines nodes in total, and both ends a, b of
                    # the line interval must still be reached
                    rem = nmax - size - 1
                    if 7 - nd - isd > rem:
                        continue
                    lo, hi = min(lmin, L), max(lmax, L)
                    if (lo - a) + (b - hi) > rem:
                        continue
                    e2 = es | {(v, w)}
                    if e2 in nxt:
                        continue
                    p2 = dict(parent)
                    p2[w] = v
                    if S.depth_of(p2, roots) > dmax:
                        continue
                    nxt[e2] = p2
        level = nxt
        for parent in level.values():
            ls = {line(v) for v in parent}
            if min(ls) == a and max(ls) == b:
                for par, roles in _roles(parent, lab, roots, umax):
                    found.append((canonical(par, roles), par, roles))
    return m, found


def _roles(parent, lab, roots, umax):
    kids = set(p for p in parent.values() if p is not None)
    if any(v not in kids for v in parent if lab[line(v)] in ("M", "R")):
        return
    dline = [v for v in parent if lab[line(v)] == "D"]
    if any(v not in kids and lab[line(v)] != "D" for v in parent):
        return
    extra = len(dline) - 7
    if extra < 0 or extra > umax:
        return
    internal = sorted(v for v in dline if v in kids)
    import itertools
    for us in itertools.combinations(internal, extra):
        roles = {v: ("U" if v in us else "D" if lab[line(v)] == "D" else "A") for v in parent}
        yield parent, roles


def canonical(parent, roles):
    """Key modulo translation and the 4 line-preserving symmetries."""
    best = None
    for f in SYMS:
        mp = {v: f(*v) for v in parent}
        r0 = min(mp.values())
        sh = lambda p: (p[0] - r0[0], p[1] - r0[1])
        k = tuple(sorted((sh(mp[v]), roles[v], () if parent[v] is None else sh(mp[parent[v]]))
                         for v in parent))
        if best is None or k < best:
            best = k
    return best


def abstract_key(parent, roles, roots):
    b = S.Base(parent, {v: roles[v] for v in parent}, roots)
    return "|".join(b.abstract_key())


def enumerate_space(ms, dmax, nmax, umax, log=print, workers=12, pool=None, cap=None):
    """{abstract key: [(parent, roles, roots)]} (one entry per embedding modulo symmetry;
    at most ``cap`` kept per key, all counted in the stats and in ``n_embeddings``)."""
    groups = defaultdict(list)
    n_emb = Counter()
    seen = set()
    stats = Counter()
    tasks = [(m, a, b, k, dmax, nmax, umax) for m in ms for a, b, k in patterns(m, dmax)]
    log(f"{len(tasks)} line-label patterns")
    own = pool is None
    if own:
        pool = Pool(workers)
    try:
        for i, (m, found) in enumerate(pool.imap_unordered(grow_pattern, tasks, chunksize=4)):
            roots = ROOTS[m]
            for ck, parent, roles in found:
                if ck in seen:
                    continue
                seen.add(ck)
                nu = sum(r == "U" for r in roles.values())
                stats[f"m{m}_n{len(parent)}_u{nu}_embedded"] += 1
                k = abstract_key(parent, roles, roots)
                n_emb[k] += 1
                if cap is None or len(groups[k]) < cap:
                    groups[k].append((parent, roles, roots))
            if (i + 1) % 500 == 0:
                log(f"patterns {i + 1}/{len(tasks)}: {sum(stats.values())} embedded bases")
    finally:
        if own:
            pool.close()
    del seen
    log(f"enumerated: {dict(sorted(stats.items()))}")
    return groups, dict(sorted(stats.items())), n_emb


# ---- circuits ------------------------------------------------------------------------

def build_u(parent, roles, roots, flags=()):
    """search_option1.build with "U" ancillas (prepared, used, reset, NOT measured)."""
    # The role-aware Base fixes the canonical node order (Base.nodes), so every
    # embedding of one abstract key gives the same circuit up to QUBIT_COORDS.
    # build() puts only "D" in data and only "A" in anc; U nodes get RX, their CXs
    # and the trailing R here, and no final MX (not in lay["anc"]).
    lay = S.build(S.Base(parent, roles, roots), flags)
    u = [i for i, p in enumerate(lay["nodes"]) if roles[p] == "U"]
    if u:
        lay["ticks"][1].append(("RX", u))
        lay["ticks"][lay["final"] + 1].append(("R", u))
    lay["unmeasured"] = u
    return lay


def design_for(key, inst, lab):
    parent, roles, roots = inst
    lay = build_u(parent, roles, roots)
    inner = S.to_circuit(lay)
    data = lay["data"]
    L = [data[lab[j]] for j in range(7)]
    full_args = (tuple(tuple(L[j] for j in p) for p in S.CODE_PLAQ),
                 tuple(L[j] for j in S.CODE_MAJ), tuple(L[j] for j in S.CODE_MIN), tuple(data))
    d = Z.Design(key, inner, full_args, dict(lay["emb"]),
                 info=dict(key=key, lab=lab, roots=lay["roots"], depth=lay["depth"],
                           unmeasured=lay["unmeasured"]))
    return d, lay


# ---- screen ---------------------------------------------------------------------------

def _screen_one(args):
    inner_text, data, lab = args
    inner = stim.Circuit(inner_text)
    try:
        full = S.full_circuit(inner, dict(data=data), lab)
    except AssertionError:
        return lab, INFEASIBLE, float("inf")
    r = verify(full, inner, max_fault_count=2, states=("T",))
    return lab, r["T"][2]["malignant"] + r["T"][1]["malignant"], r["error_rate_per_kept_shot"]["T"]


# ---- placement (realisability) -----------------------------------------------------------

class Placer:
    """Embeddings of one abstract key (qubit index -> lattice point) and flag placement
    under the continuing-data + strict line rules, with a Willow translation."""

    def __init__(self, instances):
        self.inst = []
        for parent, roles, roots in instances:
            lay = build_u(parent, roles, roots)
            emb = dict(lay["emb"])
            data = set(lay["data"])
            dl = {line(emb[q]) for q in data}
            rl = {line(emb[q]) for q in lay["roots"]}
            tr = self.translations(emb.values())
            if tr:
                self.inst.append(dict(emb=emb, dl=dl, rl=rl, used=set(emb.values()), tr=tr))

    @staticmethod
    def translations(points, need=None):
        points = list(points)
        p0 = points[0]
        out = []
        for w in WILLOW:
            dr, dc = w[0] - p0[0], w[1] - p0[1]
            if all((p[0] + dr, p[1] + dc) in WILLOW for p in points):
                out.append((dr, dc))
        return out

    def place(self, specs, want=1):
        """Yield up to ``want`` Willow embeddings {qubit: (r, c)} of tree + flags
        (flag k = qubit nq + k), specs = [(controls, live_at_mid)]."""
        got = 0
        for I in self.inst:
            emb = I["emb"]
            nq = len(emb)
            cands = []
            for ctrl, live in specs:
                ps = set(nbrs(emb[ctrl[0]]))
                for q in ctrl[1:]:
                    ps &= set(nbrs(emb[q]))
                ps = [p for p in sorted(ps) if p not in I["used"] and line(p) not in I["dl"]
                      and not (live and line(p) in I["rl"])]
                cands.append(ps)

            def rec(k, chosen):
                if k == len(specs):
                    yield list(chosen)
                    return
                for p in cands[k]:
                    if p not in chosen:
                        chosen.append(p)
                        yield from rec(k + 1, chosen)
                        chosen.pop()

            for ch in rec(0, []):
                pts = list(emb.values()) + ch
                for dr, dc in I["tr"]:
                    if all((p[0] + dr, p[1] + dc) in WILLOW for p in ch):
                        e = {q: (p[0] + dr, p[1] + dc) for q, p in emb.items()}
                        for k, p in enumerate(ch):
                            e[nq + k] = (p[0] + dr, p[1] + dc)
                        yield e
                        got += 1
                        if got >= want:
                            return
                        break

    def realisability(self, specs):
        cache = {}

        def f(qs, live):
            k = (qs, live)
            if k not in cache:
                cache[k] = next(self.place(list(specs) + [(qs, live)]), None) is not None
            return cache[k]
        return f


def full_check(inner, emb):
    return C.check_circuit(inner, emb, data_continue=True)


# ---- per-key worker -----------------------------------------------------------------

class Evaluator(SZ.Evaluator):
    def __init__(self, base, name, placer):
        super().__init__(base, name)
        self.placer = placer

    def evaluate(self, d_on, flags, level, predicted, extra_fq=()):
        t0 = time.perf_counter()
        row = dict(base=self.name, base_T2=self.base.info.get("T2"), level=level,
                   predicted_removed=predicted)
        try:
            inner, fq_new = Z.build_flagged(d_on, flags)
        except ValueError as e:
            row.update(reason=f"build: {e}", n_flags=len(extra_fq) + len(flags),
                       flags=";".join(map(str, flags)))
            self.rows.append(row)
            return None
        fq = list(extra_fq) + list(fq_new)
        desc, specs, gates = SZ.flag_description(inner, fq)
        row.update(n_flags=len(fq), basis="".join(sorted({s for f in fq for _, _, s in gates[f]})),
                   flags=desc, flag_controls=json.dumps([list(s[0]) for s in specs]),
                   added_ticks=len(Q.to_layers(inner)) - self.base.T,
                   n_qubits=inner.num_qubits, n_cx=len(C.two_qubit_gates(inner)),
                   max_degree=max(map(len, C.partners(inner).values())), ticks=inner.num_ticks)
        emb = next(self.placer.place(specs), None)
        row["realisable"] = emb is not None
        full = self.base.full(inner)
        r2 = verify(full, inner, max_fault_count=2)
        row.update(malignant_T_1=r2["T"][1]["malignant"], malignant_T_2=r2["T"][2]["malignant"],
                   malignant_S_2=r2["S"][2]["malignant"] + r2["S"][1]["malignant"],
                   ler_T_mfc2=r2["error_rate_per_kept_shot"]["T"])
        rate = row["ler_T_mfc2"]
        row["ler_T_mfc2_one_in"] = round(1 / rate) if rate > 0 else ""
        ok_fd3 = row["malignant_T_1"] == 0 and row["malignant_T_2"] == 0
        if emb is not None and ok_fd3:
            self._validate_c(row, inner, full, fq, specs)
        elif emb is None:
            row["reason"] = "no placement (continuing-data + strict lines, Willow)"
        row["runtime_s"] = round(time.perf_counter() - t0, 3)
        self.rows.append(row)
        if emb is not None and not row.get("success"):
            head = "\n".join(f"QUBIT_COORDS({emb[q][0]}, {emb[q][1]}) {q}" for q in sorted(emb))
            self.best.append((row["malignant_T_2"] + row["malignant_T_1"], row["ler_T_mfc2"],
                              len(self.rows) - 1, head + "\n" + str(inner), str(full)))
            self.best.sort(key=lambda x: (x[0], x[1]))
            del self.best[3:]
        return inner, fq, row

    def _validate_c(self, row, inner, full, fq, specs):
        tried, last, emb = 0, None, None
        for e in self.placer.place(specs, want=400):
            tried += 1
            v = full_check(inner, e)
            if not v:
                emb = e
                break
            last = v
        row["hardware_ok"] = emb is not None
        if emb is None:
            row["reason"] = f"hardware: {tried} placements tried, last {json.dumps(C.summarize(last or []))}"
            return
        eq = Q.check_equivalence(inner, full, flag_qubits=tuple(fq))
        row["equivalence_ok"] = eq["ok"]
        if not eq["ok"]:
            row["reason"] = "equivalence: " + json.dumps(
                {k: eq[k]["ok"] for k in ("i_code", "ii_check", "iii_reverse", "iv_deterministic")})
            return
        r3 = verify(full, inner, max_fault_count=3)
        rate3 = r3["error_rate_per_kept_shot"]["T"]
        row.update(malignant_T_3=r3["T"][3]["malignant"], ler_T_mfc3=rate3,
                   ler_T_mfc3_one_in=round(1 / rate3) if rate3 > 0 else "",
                   flag_positions=json.dumps({f: emb[f] for f in fq}), success=True)
        head = "\n".join(f"QUBIT_COORDS({emb[q][0]}, {emb[q][1]}) {q}" for q in sorted(emb))
        self.success.append((len(self.rows), head + "\n" + str(inner), str(full), emb))


def process(task):
    """Two-level greedy flag search on one abstract key (search_zzflags.process with
    the continuing-data placement)."""
    name, key, insts, lab, opts = task
    t0 = time.perf_counter()
    info = dict(base=name, key=key, n_embeddings=len(insts))
    try:
        d, lay = design_for(key, insts[0], tuple(lab))
        placer = Placer(insts)
        info["n_embeddings_on_willow"] = len(placer.inst)
        info["unmeasured"] = json.dumps(lay["unmeasured"])
        tree_q = list(d.qubits)
        pa = Z.ProbeAnalysis(d, controls=tree_q)
        pairs, events, _, _ = Z.malignant_pairs(d)
        d.info["T2"] = len(pairs)
        n = len(pairs)
        info.update(base_T2=n, tree=S.Base(*insts[0]).describe(), labelling=str(lab), n_pairs=n)
        ev = Evaluator(d, name, placer)
        if not placer.inst:
            info.update(error="no embedding fits on Willow", seconds=round(time.perf_counter() - t0, 1))
            return info, [], [], []
        if n == 0:   # base alone has fault distance 3
            ev.evaluate(d, [], 0, 0)
        cov = Z.Coverage(pa, pairs, events)
        real1 = placer.realisability([])
        sep, sep_real = defaultdict(int), defaultdict(int)
        for basis in ("Z", "X"):
            for qs in SZ.control_sets(d, tree_q):
                cols = [k for k, p in enumerate(pa.probes) if p.q in qs and p.basis == basis]
                for i in range(n):
                    if Z.solve_gf2(cov.system(cols, [i]), len(cols)) is not None:
                        sep[i] += 1
                        sep_real[i] += real1(qs, basis == "X")
        info["single_flag_separable"] = json.dumps({i: [sep[i], sep_real[i]] for i in range(n)})
        info["unseparable_pairs"] = json.dumps(dict(
            any_control_set=sum(1 for i in range(n) if not sep[i]),
            realisable_control_set=sum(1 for i in range(n) if not sep_real[i])))
        lvl = defaultdict(list)
        for k, mk, basis, qs, fl in SZ.level_candidates(d, cov, tree_q, n, opts["n1"], real1):
            r = ev.evaluate(d, [fl], 1, k)
            if r:
                lvl[1].append((r[2]["malignant_T_2"], r[2]["ler_T_mfc2"], r[2]["realisable"], r[0], r[1]))
        info["best_level1_T2"] = min((x[0] for x in lvl[1] if x[2]), default="")
        frontier = sorted([x for x in lvl[1] if x[2] and x[0] > 0], key=lambda x: (x[0], x[1]))[:opts["k1"]]
        for _, _, _, inner, fq in frontier:
            if len(ev.success) >= opts["stop_per_base"]:
                break
            d1 = Z.Design(name + "+L1", inner, d.full_args, {}, info=d.info)
            pa1 = Z.ProbeAnalysis(d1, controls=tree_q)
            pairs1, events1, _, _ = Z.malignant_pairs(d1)
            if not pairs1:
                continue
            cov1 = Z.Coverage(pa1, pairs1, events1)
            n1 = len(pairs1)
            real = placer.realisability(Z.flag_specs(inner, fq)[0])
            c2 = SZ.level_candidates(d1, cov1, tree_q, n1, opts["n2"], real, all_only=True)
            if not c2:
                c2 = SZ.level_candidates(d1, cov1, tree_q, n1, 2, real)
            for k, mk, basis, qs, fl in c2:
                r = ev.evaluate(d1, [fl], 2, k, extra_fq=fq)
                if r:
                    lvl[2].append((r[2]["malignant_T_2"], r[2]["ler_T_mfc2"], r[2]["realisable"], r[0], r[1]))
        info["best_level2_T2"] = min((x[0] for x in lvl[2] if x[2]), default="")
        info.update(n_evaluated=len(ev.rows), n_success=len(ev.success),
                    seconds=round(time.perf_counter() - t0, 1))
        return info, ev.rows, ev.success, ev.best
    except Exception as e:
        info.update(error=f"{type(e).__name__}: {e} | {traceback.format_exc()[-600:]}",
                    seconds=round(time.perf_counter() - t0, 1))
        return info, [], [], []


def process_cover(task):
    """Deep pass on one key: exact 2-cover. Every (basis, control set) single flag that
    is placeable under the line rules gets its maximal sets of base malignant pairs it
    separates (GF(2), zzflags.coverable_subsets for <= 12 pairs, else greedy); every
    two such sets whose union is all pairs gives a candidate pair of flags, built and
    verified together (new flag faults are seen by verify only)."""
    name, key, insts, lab, opts = task
    t0 = time.perf_counter()
    info = dict(base=name, key=key, n_embeddings=len(insts), mode="cover")
    try:
        d, lay = design_for(key, insts[0], tuple(lab))
        placer = Placer(insts)
        info["n_embeddings_on_willow"] = len(placer.inst)
        info["unmeasured"] = json.dumps(lay["unmeasured"])
        tree_q = list(d.qubits)
        pa = Z.ProbeAnalysis(d, controls=tree_q)
        pairs, events, _, _ = Z.malignant_pairs(d)
        n = len(pairs)
        d.info["T2"] = n
        info.update(base_T2=n, tree=S.Base(*insts[0]).describe(), labelling=str(lab), n_pairs=n)
        ev = Evaluator(d, name, placer)
        cov = Z.Coverage(pa, pairs, events)
        real1 = placer.realisability([])
        mid = d.mid_ticks[0] if d.mid_ticks else 10 ** 9
        full = (1 << n) - 1
        opts_l = []   # (mask, basis, qs, cols)
        for basis in ("Z", "X"):
            for qs in SZ.control_sets(d, tree_q):
                if not real1(qs, basis == "X"):
                    continue
                cols = [k for k, p in enumerate(pa.probes) if p.q in qs and p.basis == basis]
                if not cols:
                    continue
                masks = (SZ.maximal(Z.coverable_subsets(cov, cols, n)) if n <= opts.get("exact_max", 12)
                         else SZ.maximal(SZ.greedy_masks(cov, cols, n)))
                opts_l += [(m, basis, qs, cols) for m in masks]
        combos = []
        for i in range(len(opts_l)):
            for j in range(i, len(opts_l)):
                if opts_l[i][0] | opts_l[j][0] == full:
                    a, b = opts_l[i], opts_l[j]
                    combos.append((abs((a[1] == "X") + (b[1] == "X") - 1) + 0.01 * (len(a[2]) + len(b[2])), a, b))
        combos.sort(key=lambda x: x[0])
        info["cover_options"] = len(opts_l)
        info["cover_combos"] = len(combos)
        tried = 0
        best = None
        for _, a, b in combos:
            if tried >= opts.get("max_combos", 40) or len(ev.success) >= opts["stop_per_base"]:
                break
            fa = Z.concrete_flags(cov, a[3], [i for i in range(n) if a[0] >> i & 1], limit=2)
            fb = Z.concrete_flags(cov, b[3], [i for i in range(n) if b[0] >> i & 1], limit=2)
            for f1 in fa:
                for f2 in fb:
                    if f1.probes == f2.probes:
                        continue
                    specs = [(f1.controls, f1.basis == "X" or min(p.slot for p in f1.probes) <= mid),
                             (f2.controls, f2.basis == "X" or min(p.slot for p in f2.probes) <= mid)]
                    if next(placer.place(specs), None) is None:
                        continue
                    tried += 1
                    r = ev.evaluate(d, [f1, f2], 2, n)
                    if r:
                        t2 = r[2]["malignant_T_2"] + r[2]["malignant_T_1"]
                        best = t2 if best is None else min(best, t2)
                    break
        info["best_level2_T2"] = "" if best is None else best
        info["cover_built"] = tried
        info.update(n_evaluated=len(ev.rows), n_success=len(ev.success),
                    seconds=round(time.perf_counter() - t0, 1))
        return info, ev.rows, ev.success, ev.best
    except Exception as e:
        info.update(error=f"{type(e).__name__}: {e} | {traceback.format_exc()[-600:]}",
                    seconds=round(time.perf_counter() - t0, 1))
        return info, [], [], []


def process_key(task):
    """Worker: screen one key (best code labelling, verify mfc 2, T only) unless cached,
    then the flag search if its best malignant T count is <= max_t2."""
    name, key, insts, sc, opts = task
    t0 = time.perf_counter()
    if sc is None:
        lay = build_u(*insts[0])
        inner = S.to_circuit(lay)
        res = [_screen_one((str(inner), lay["data"], lab)) for lab in S.labelling_classes()]
        res.sort(key=lambda x: (x[1], x[2]))
        sc = dict(lab=list(res[0][0]), T2=res[0][1], rate=res[0][2],
                  hist={str(k): v for k, v in Counter(r[1] for r in res).items()},
                  n=len(insts[0][0]), screen_s=round(time.perf_counter() - t0, 1))
    if sc["T2"] >= INFEASIBLE or sc["T2"] > opts["max_t2"]:
        return dict(base=name, key=key, screened_out=True), [], [], [], sc
    args = (name, key, insts, tuple(sc["lab"]), opts)
    if opts.get("cover") == "both":   # exact 2-cover first, then the greedy two-level search
        info, rows, succ, best = process_cover(args)
        if not succ:
            i2, r2, s2, b2 = process(args)
            off = len(rows)
            rows += r2
            succ += [(idx + off, *rest) for idx, *rest in s2]
            best = sorted(best + [(t, r, idx + off, a, b) for t, r, idx, a, b in b2], key=lambda x: (x[0], x[1]))[:3]
            info.update({k: v for k, v in i2.items() if k not in ("best_level2_T2", "seconds", "n_evaluated", "n_success")})
            cands = [x for x in (info.get("best_level2_T2"), i2.get("best_level2_T2")) if x != "" and x is not None]
            info["best_level2_T2"] = min(cands) if cands else ""
            info["mode"] = "cover+greedy"
            info.update(n_evaluated=len(rows), n_success=len(succ))
    elif opts.get("cover"):
        info, rows, succ, best = process_cover(args)
    else:
        info, rows, succ, best = process(args)
    sc = dict(sc, flagged=True, best_level1_T2=info.get("best_level1_T2"),
              best_level2_T2=info.get("best_level2_T2"), n_success=len(succ), error=info.get("error"))
    return info, rows, succ, best, sc


# ---- main ----------------------------------------------------------------------------------

FIELDS = SZ.FIELDS + ["key", "unmeasured", "continuing_violations"]
BASE_FIELDS = ["base", "key", "mode", "cover_options", "cover_combos", "cover_built", "n_embeddings", "n_embeddings_on_willow", "unmeasured", "base_T2", "tree",
               "labelling", "n_pairs", "single_flag_separable", "unseparable_pairs", "best_level1_T2",
               "best_level2_T2", "n_evaluated", "n_success", "seconds", "error"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--dmax", type=int, default=5)
    ap.add_argument("--nmax", type=int, default=13)
    ap.add_argument("--umax", type=int, default=1)
    ap.add_argument("--ms", default="1,2")
    ap.add_argument("--hours", type=float, default=4.0)
    ap.add_argument("--n1", type=int, default=40)
    ap.add_argument("--k1", type=int, default=8)
    ap.add_argument("--n2", type=int, default=16)
    ap.add_argument("--stop-per-base", type=int, default=2)
    ap.add_argument("--max-embeddings", type=int, default=3000)
    ap.add_argument("--count-only", action="store_true")
    ap.add_argument("--tag", default="s1")
    ap.add_argument("--cover", default="", choices=["", "only", "both"],
                    help="'only': exact 2-cover (process_cover); 'both': 2-cover then the greedy search")
    ap.add_argument("--max-combos", type=int, default=40)
    ap.add_argument("--keys-file", default=None,
                    help="deep pass: run exactly these abstract keys (one per line), even if flagged before")
    ap.add_argument("--screen-max-t2", type=int, default=12,
                    help="flag only keys whose best labelling has at most this many malignant T pairs")
    args = ap.parse_args()
    out = Path(args.out)
    sdir = out / "continuing"
    sdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log = lambda *a: print(f"[{time.time() - t0:8.1f} s]", *a, flush=True)
    # one pool, forked before the (large) enumeration result exists, for everything
    pool = Pool(args.workers)
    groups, stats, n_emb = enumerate_space([int(x) for x in args.ms.split(",")], args.dmax, args.nmax,
                                           args.umax, log, pool=pool, cap=args.max_embeddings)
    log(f"abstract keys: {len(groups)}; embedded bases: {sum(n_emb.values())}")
    state = dict(settings=dict(args=vars(args), rule="continuing-data strict + strict (gate, auto)",
                               noise="uniformly_depolarize", p=Z.NOISE, max_fault_count=[2, 3], max_degree=4),
                 space=stats, abstract_keys=len(groups),
                 abstract_keys_by_m_u=dict(Counter(f"m{k.count('|') + 1}_u{k.count('U')}" for k in groups)),
                 abstract_keys_by_u=dict(Counter(k.count("U") for k in groups)),
                 started=time.ctime())
    (out / f"continuing_state_{args.tag}.json").write_text(json.dumps(state, indent=1))
    if args.count_only:
        pool.close()
        return
    # ---- per key: screen (best of 210 labellings) then, if promising, the flag search ----
    cache_p = out / "continuing_screen.json"
    screen = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    if args.keys_file:   # a deep pass reads the stage-1 labellings but writes its own cache
        cache_p = out / f"continuing_screen_{args.tag}.json"
    opts = dict(n1=args.n1, k1=args.k1, n2=args.n2, stop_per_base=args.stop_per_base,
                max_t2=args.screen_max_t2, cover=args.cover, max_combos=args.max_combos)
    keys = sorted(groups, key=lambda k: (k.count("|"), k.count("U"), len(groups[k][0][0]), k))
    if args.keys_file:
        want = [x for x in Path(args.keys_file).read_text().split() if x]
        keys = [k for k in want if k in groups]
        log(f"deep pass: {len(keys)} of {len(want)} keys found in the enumerated space")
    else:
        keys = [k for k in keys if not screen.get(k, {}).get("flagged")
                and not (k in screen and (screen[k]["T2"] >= INFEASIBLE or screen[k]["T2"] > args.screen_max_t2))]
    names = {k: f"{args.tag}-{i:05d}" for i, k in enumerate(keys)}
    todo = [(names[k], k, groups[k][:args.max_embeddings], screen.get(k), opts) for k in keys]
    state["queue"] = len(todo)
    log(f"queue: {len(todo)} keys (already done or screened out: {len(groups) - len(todo)})")
    fh = (out / f"continuing_candidates_{args.tag}.csv").open("w", newline="")
    wr = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
    wr.writeheader()
    bh = (out / f"continuing_bases_{args.tag}.csv").open("w", newline="")
    bw = csv.DictWriter(bh, fieldnames=BASE_FIELDS, extrasaction="ignore")
    bw.writeheader()
    nid = n_done = 0
    n_succ = len(list(sdir.glob("success*.inner.stim")))
    best_global = []
    stop_reason = "design space exhausted (flag queue)"
    with pool:
        for info, rows, succ, best, sc in pool.imap_unordered(process_key, todo, chunksize=1):
            n_done += 1
            if args.keys_file:   # keep the stage-1 screen entry, record the deep result separately
                sc = dict(screen.get(info["key"], sc), **{f"deep_{args.tag}_L2": info.get("best_level2_T2"),
                                                          f"deep_{args.tag}_L1": info.get("best_level1_T2")})
            screen[info["key"]] = sc
            info["n_embeddings"] = n_emb.get(info["key"])
            if n_done % 20 == 0:
                cache_p.write_text(json.dumps(screen))
            for k, row in enumerate(rows):
                row["id"] = nid + k
                row["key"] = info.get("key")
                row["unmeasured"] = info.get("unmeasured")
            for idx, inner, full, emb in succ:
                i = n_succ
                row = rows[idx]
                p = sdir / f"success{i:02d}.inner.stim"
                p.write_text(inner)
                (sdir / f"success{i:02d}.full.stim").write_text(full)
                row.update(stim_file=str(p), full_stim_file=str(sdir / f"success{i:02d}.full.stim"),
                           continuing_violations=0)
                n_succ += 1
                log(f"SUCCESS #{i} base {info['base']} U={info.get('unmeasured')} flags {row['flags']} "
                    f"T3={row.get('malignant_T_3')} S2={row['malignant_S_2']} 1 in {row.get('ler_T_mfc3_one_in')}")
            for t2, rate, idx, inner, full in best:
                best_global.append((t2, rate, rows[idx]["id"], info["base"], inner, full))
            best_global.sort(key=lambda x: (x[0], x[1]))
            del best_global[5:]
            for row in rows:
                wr.writerow(row)
            fh.flush()
            nid += len(rows)
            bw.writerow(info)
            bh.flush()
            if info.get("screened_out"):
                continue
            log(f"base {info['base']} T2={info.get('base_T2')} emb={info.get('n_embeddings_on_willow')} "
                f"eval={len(rows)} L1={info.get('best_level1_T2')} L2={info.get('best_level2_T2')} "
                f"succ={len(succ)} {info.get('seconds')} s" + (f" ERROR {info['error'][:300]}" if info.get("error") else ""))
            if n_done % 10 == 0 or succ:
                for k, (t2, rate, rid, b, inner, full) in enumerate(best_global):
                    (sdir / f"best_{args.tag}_{k}.inner.stim").write_text(inner)
                    (sdir / f"best_{args.tag}_{k}.full.stim").write_text(full)
                state.update(n_bases_done=n_done, n_evaluated=nid, n_success=n_succ,
                             best_non_success=[dict(T2=t2, rate=rate, id=rid, base=b)
                                               for t2, rate, rid, b, _, _ in best_global],
                             elapsed_s=time.time() - t0)
                (out / f"continuing_state_{args.tag}.json").write_text(json.dumps(state, indent=1))
            if n_succ >= STOP_SUCCESSES:
                stop_reason = f"{STOP_SUCCESSES} successes"
                pool.terminate()
                break
            if time.time() - t0 > args.hours * 3600:
                stop_reason = f"time limit {args.hours} h"
                pool.terminate()
                break
    cache_p.write_text(json.dumps(screen))
    for k, (t2, rate, rid, b, inner, full) in enumerate(best_global):
        (sdir / f"best_{args.tag}_{k}.inner.stim").write_text(inner)
        (sdir / f"best_{args.tag}_{k}.full.stim").write_text(full)
    hist = Counter(v["T2"] for v in screen.values())
    state["screen_T2_hist_all_keys"] = {str(k): v for k, v in sorted(hist.items())}
    state.update(n_flagged=sum(1 for k in screen if screen[k].get("flagged")), n_bases_done=n_done, n_bases_queued=len(todo), n_evaluated=nid, n_success=n_succ,
                 stop_reason=stop_reason, finished=time.ctime(), elapsed_s=time.time() - t0,
                 best_non_success=[dict(T2=t2, rate=rate, id=rid, base=b)
                                   for t2, rate, rid, b, _, _ in best_global])
    (out / f"continuing_state_{args.tag}.json").write_text(json.dumps(state, indent=1))
    fh.close()
    bh.close()
    log("done:", stop_reason, f"bases {n_done}, evaluated {nid}, successes {n_succ}")


if __name__ == "__main__":
    main()
