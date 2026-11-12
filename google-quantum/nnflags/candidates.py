"""Step 3: candidate generator (first-ex.md), starting from d3a6 on Willow.

Categories
  (a) 1..3 Z flags. A flag f is a FREE Willow qubit adjacent to a circuit
      qubit q; it gets CX(q -> f) at two slots t1 < t2 inside the fold/unfold
      (TICKs 2..10 of d3a6's inner circuit). A slot is either an existing TICK
      where q is idle ("in place", an integer), or a NEW TICK inserted between
      existing TICKs k and k+1 (written k + 0.5, k = 2..9); every distinct
      inserted slot counts as one added layer. The pair must leave Z_q
      unchanged between t1 and t2 (q is only a CX control strictly between
      them), otherwise the flag is not a deterministic detector. As in
      d3a6f2: R f in the layer right before t1; M f either in the layer right
      after t2 ("next", d3a6f2's convention) or in the final MX layer
      ("final"); a DETECTOR on M f; and f joins the trailing R layer
      (cliffordea's inner-circuit convention, enum/circuits/main.py:44-56).
  (b) the plan's "permutations of commuting CX layers": orders of the fold
      layers (TICKs 2..5) with the same fold unitary, unfold = exact time
      reverse. Only the identity exists for d3a6, so the generator also uses
      the gate-level version: every assignment of the 12 fold CXs to 4 layers
      (no qubit twice per layer) with the same fold unitary (6, including the
      original), unfold = time reverse.
  (c) re-embeddings: the 8 lattice symmetries x translations
      (constraints.grid_embeddings), 350 placements.
Flags on the qubits that carry the X hook errors of Step 0 (3, 5, 9) are
generated first.

Every candidate goes through constraints.check_circuit (strict readout and
readout ignored). The inner circuit gets QUBIT_COORDS = Willow position.
For verify(), the full circuit is cliffordea's bundled d3a6 full.stim:
cliffordea reads only its MPPs (stabilisers) and S/S_DAG layers (logical S)
(enum/circuits/main.py:58-74), and flags change neither.

Usage: python -m nnflags.candidates [--out results] [--workers 12] [--verify-sample 20]
"""
import argparse
import csv
import itertools
import json
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from multiprocessing import Pool
from pathlib import Path

import stim

from cliffordea import enum

from nnflags import constraints as C
from nnflags.willow import neighbours

HOOK_QUBITS = (3, 5, 9)  # carry the X hook errors of the 4 malignant Step 0 configurations
FOLD = (2, 3, 4, 5)      # fold TICKs of d3a6's inner circuit
UNFOLD = (10, 9, 8, 7)   # unfold TICK mirroring FOLD[i] (time reverse)
SPAN = range(2, 11)      # fold/unfold TICKs where flag CXs may go
GAPS = tuple(k + 0.5 for k in range(2, 10))
PRIMARY = ("id", (4, 4))


def d3a6():
    return enum.circuits.DoubleCheck(distance=3, ancilla_count=6).INNER_CIRCUIT


@dataclass(frozen=True)
class Flag:
    q: int            # control (existing circuit qubit)
    at: tuple         # Willow position of the flag qubit
    t1: float         # slot: int = existing TICK, k + 0.5 = new TICK after TICK k
    t2: float
    measure: str = "final"  # "next" (layer after t2) or "final" (final MX layer)

    def __str__(self):
        return f"q{self.q}->{self.at} t{self.t1:g},{self.t2:g} M{self.measure}"


@dataclass
class Candidate:
    category: str
    embedding: dict
    flags: tuple = ()
    fold: int = 0             # index into fold_variants(); 0 = original
    symmetry: str = "id"
    offset: tuple = (4, 4)
    circuit: stim.Circuit = field(default=None, repr=False)

    @property
    def added_ticks(self):
        return added_ticks(self.flags)


def added_ticks(flags):
    return len({s for f in flags for s in (f.t1, f.t2) if s != int(s)})


# ---- circuit surgery --------------------------------------------------------

def _layers(circuit):
    """Layers as lists of ('op', instruction, first measurement id) and
    ('det', instruction, [measurement ids]); global measurement ids let
    DETECTOR lookbacks be rebuilt after measurements or layers are added."""
    layers, n = [], 0
    for layer in C.split_by_ticks(circuit):
        items = []
        for op in layer:
            if op.name in ("DETECTOR", "OBSERVABLE_INCLUDE"):
                items.append(("det", op, [n + t.value for t in op.targets_copy()]))
            else:
                items.append(("op", op, n))
                n += op.num_measurements
        layers.append(items)
    return layers, n


def _emit(layers):
    out, n, pos = stim.Circuit(), 0, {}
    for i, items in enumerate(layers):
        if i:
            out.append("TICK")
        for kind, op, ref in items:
            if kind == "op":
                for k in range(op.num_measurements):
                    pos[ref + k] = n + k
                n += op.num_measurements
                out.append(op)
            else:
                out.append(op.name, [stim.target_rec(pos[x] - n) for x in ref], op.gate_args_copy())
    return out


def _cx(gates):
    return stim.CircuitInstruction("CX", [q for g in gates for q in g])


def build(base: stim.Circuit, embedding: dict, flags=(), fold=None) -> tuple[stim.Circuit, dict]:
    """Inner circuit of a candidate and its embedding (flags included).
    ``fold``: 4 tuples of CX gates for TICKs 2..5 (None = original); the
    unfold TICKs 7..10 become their exact time reverse."""
    layers, nmeas = _layers(base)
    if fold is not None:
        for t, u, gates in zip(FOLD, UNFOLD, fold):
            assert all(it[1].name == "CX" for it in layers[t] + layers[u])
            layers[t] = [("op", _cx(gates), 0)]
            layers[u] = [("op", _cx(gates), 0)]
    emb = dict(embedding)
    nq = base.num_qubits
    gaps = sorted({s for f in flags for s in (f.t1, f.t2) if s != int(s)})
    index, new = {}, []
    for k, items in enumerate(layers):
        index[k] = len(new)
        new.append(list(items))
        for g in gaps:
            if int(g) == k:
                index[g] = len(new)
                new.append([])
    final_m = max(i for i, items in enumerate(new)
                  if any(kind == "op" and op.num_measurements and op.name != "MPP"
                         for kind, op, _ in items))
    for j, f in enumerate(flags):
        fq = nq + j
        emb[fq] = f.at
        a, b = index[f.t1], index[f.t2]
        new[a - 1].append(("op", stim.CircuitInstruction("R", [fq]), 0))
        new[a].append(("op", stim.CircuitInstruction("CX", [f.q, fq]), 0))
        new[b].append(("op", stim.CircuitInstruction("CX", [f.q, fq]), 0))
        m = b + 1 if f.measure == "next" else final_m
        new[m].append(("op", stim.CircuitInstruction("M", [fq]), nmeas))
        new[m].append(("det", stim.CircuitInstruction("DETECTOR", [], [*f.at, 9]), [nmeas]))
        nmeas += 1
        new[-1].append(("op", stim.CircuitInstruction("R", [fq]), 0))
    new[0] = ([("op", stim.CircuitInstruction("QUBIT_COORDS", [q], list(emb[q])), 0)
               for q in sorted(emb)]
              + [it for it in new[0] if not (it[0] == "op" and it[1].name == "QUBIT_COORDS")])
    return _emit(new), emb


def is_deterministic(circuit: stim.Circuit) -> bool:
    """All detectors deterministic in the noiseless circuit (stim raises otherwise)."""
    try:
        circuit.detector_error_model()
        return True
    except ValueError:
        return False


# ---- (b) --------------------------------------------------------------------

def _fold_gates(base):
    layers = C.split_by_ticks(base)
    return [tuple(tuple(g) for op in layers[t] if op.name == "CX"
                  for g in zip(*[iter([x.value for x in op.targets_copy()])] * 2)) for t in FOLD]


def _tableau(nq, fold):
    c = stim.Circuit(f"I {nq - 1}")
    for gates in fold:
        if gates:
            c.append(_cx(gates))
    return stim.Tableau.from_circuit(c)


def layer_permutations(base):
    """Fold-layer orders with the same fold unitary (unfold = time reverse)."""
    orig = _fold_gates(base)
    ref = _tableau(base.num_qubits, orig)
    return [p for p in itertools.permutations(range(4))
            if _tableau(base.num_qubits, [orig[i] for i in p]) == ref]


def fold_variants(base):
    """Gate-level re-layerings of the fold at the same depth (4 layers, no
    qubit twice per layer) with the same fold unitary; index 0 = original."""
    orig = _fold_gates(base)
    gates = [g for layer in orig for g in layer]
    ref = _tableau(base.num_qubits, orig)
    found = []

    def rec(i, assign, busy):
        if i == len(gates):
            fold = tuple(tuple(g for g, l in zip(gates, assign) if l == L) for L in range(4))
            if _tableau(base.num_qubits, fold) == ref:
                found.append(fold)
            return
        a, b = gates[i]
        for L in range(4):
            if a not in busy[L] and b not in busy[L]:
                busy[L] |= {a, b}
                rec(i + 1, assign + [L], busy)
                busy[L] -= {a, b}

    rec(0, [], [set() for _ in range(4)])
    key = lambda f: tuple(sorted(x) for x in f)
    found.sort(key=lambda f: key(f) != key(tuple(orig)))
    assert key(found[0]) == key(tuple(orig))
    return found


# ---- (a) flag slots ---------------------------------------------------------

def _q_ops(circuit):
    """{qubit: {tick: (name, role)}} with role control / target / other."""
    ops = defaultdict(dict)
    for t, layer in enumerate(C.split_by_ticks(circuit)):
        for name, qs, gd in C._hardware_ops(layer):
            if gd.is_two_qubit_gate:
                for a, b in zip(qs[::2], qs[1::2]):
                    ops[a][t] = (name, "control")
                    ops[b][t] = (name, "target")
            else:
                for q in qs:
                    ops[q][t] = (name, "other")
    return ops


def slot_pairs(circuit, q):
    """Valid (t1, t2) for a flag on q (circuit = base with its fold applied)."""
    ops = _q_ops(circuit)[q]
    slots = [t for t in SPAN if t not in ops] + list(GAPS)
    out = []
    for t1, t2 in itertools.combinations(sorted(slots), 2):
        if all(ops[t] == ("CX", "control") for t in SPAN if t1 < t < t2 and t in ops):
            out.append((t1, t2))
    return out


def single_flags(circuit, emb, measures=("final", "next")):
    """All single Z flags for one placement, hook qubits first."""
    used = set(emb.values())
    for q in list(HOOK_QUBITS) + [q for q in sorted(emb) if q not in HOOK_QUBITS]:
        for at in neighbours(emb[q]):
            if at not in used:
                for t1, t2 in slot_pairs(circuit, q):
                    for m in measures:
                        yield Flag(q, at, t1, t2, m)


def count_flag_sets(singles, k):
    """Number of k-subsets with distinct flag positions (elementary symmetric
    polynomial of the per-position counts)."""
    e = [1] + [0] * k
    for n in Counter(f.at for f in singles).values():
        for j in range(k, 0, -1):
            e[j] += e[j - 1] * n
    return e[k]


# ---- evaluation ---------------------------------------------------------------

def evaluate(circuit, emb):
    """Constraint summary of one candidate (strict and ignore readout)."""
    v = C.check_circuit(circuit, emb, readout="ignore")
    s = C.summarize(v)
    strict = len(C.readout_violations(circuit, emb))
    return dict(
        hw_ok=not s, hw_violations=json.dumps(s),
        n_cx=len(C.two_qubit_gates(circuit)),
        max_degree=max(map(len, C.partners(circuit).values())),
        readout_strict=strict,
        readout_strict_final_check=len(C.readout_violations(circuit, emb, final_layer="check")),
        readout_strict_zreset_not_live=len(C.readout_violations(circuit, emb,
                                                                z_reset_idle="not_live")),
    )


def _tally(st, row, flags):
    st["total"] += 1
    st["hw_ok"] += row["hw_ok"]
    st["pass_ignore"] += row["hw_ok"]
    st["pass_strict"] += row["hw_ok"] and row["readout_strict"] == 0
    st["pass_strict_final_check"] += row["hw_ok"] and row["readout_strict_final_check"] == 0
    st["pass_strict_zreset_not_live"] += row["hw_ok"] and row["readout_strict_zreset_not_live"] == 0
    st[f"readout_strict={row['readout_strict']}"] += 1
    if any(f.q in HOOK_QUBITS for f in flags):
        st["with_hook_flag"] += 1
        st["with_hook_flag_hw_ok"] += row["hw_ok"]


_W = {}


def _init(placement, fold_index):
    base = d3a6()
    folds = fold_variants(base)
    emb = placement[2]
    circ = build(base, C.native_coords(base), (), folds[fold_index] if fold_index else None)[0]
    _W.update(base=base, emb=emb, fold=folds[fold_index] if fold_index else None,
              singles=list(single_flags(circ, emb)), placement=placement, fold_index=fold_index)


def _row(flags, category, cid=None):
    circ, emb = build(_W["base"], _W["emb"], flags, _W["fold"])
    row = dict(id=cid, category=category, symmetry=_W["placement"][0],
               offset=_W["placement"][1], fold=_W["fold_index"], n_flags=len(flags),
               flags=";".join(map(str, flags)), added_ticks=added_ticks(flags), **evaluate(circ, emb))
    return row


def _work_pairs(i):
    """All pairs (i, j > i) with distinct positions; rows kept if a hook flag is involved."""
    singles = _W["singles"]
    st, rows = Counter(), []
    for j in range(i + 1, len(singles)):
        combo = (singles[i], singles[j])
        if combo[0].at == combo[1].at:
            continue
        row = _row(combo, "a2")
        _tally(st, row, combo)
        if any(f.q in HOOK_QUBITS for f in combo):
            rows.append(row)
    return st, rows


def _work_singles(_):
    st, rows = Counter(), []
    for f in _W["singles"]:
        row = _row((f,), "a1")
        _tally(st, row, (f,))
        rows.append(row)
    return st, rows


def _work_a1(task):
    """All single flags for one (placement, fold variant); also checks that each
    is a deterministic detector."""
    placement, k = task
    _init(placement, k)
    singles = _W["singles"]
    info = {"singles": len(singles), "by_q": dict(Counter(f.q for f in singles)),
            "pairs": count_flag_sets(singles, 2), "triples": count_flag_sets(singles, 3)}
    bad = [str(f) for f in singles
           if not is_deterministic(build(_W["base"], placement[2], (f,), _W["fold"])[0])]
    st, rows = _work_singles(None)
    return f"{placement[0]} {placement[1]} fold{k}", placement[0], info, bad, st, rows


def placements_by_symmetry(base):
    """One central placement per lattice symmetry (plus the primary one)."""
    best = {}
    for sym, off, emb in C.grid_embeddings(base):
        centre = sum(abs(r - 6) + abs(c - 7) for r, c in emb.values())
        if (sym, off) == PRIMARY:
            centre = -1
        if sym not in best or centre < best[sym][0]:
            best[sym] = (centre, (sym, off, emb))
    return [p for _, p in best.values()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--triple-sample", type=int, default=20000)
    parser.add_argument("--verify-sample", type=int, default=20)
    parser.add_argument("--skip-pairs", action="store_true")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    base = d3a6()
    embs = C.grid_embeddings(base)
    primary = next(p for p in embs if p[:2] == PRIMARY)
    folds = fold_variants(base)
    S = {"settings": dict(distance=3, ancilla_count=6, flag_count="0 + new Z flags",
                          base="DoubleCheck(3, 6) inner circuit", grid="Willow, 105 qubits",
                          flag_measure=["final", "next"], slots="in place TICKs 2..10 + new TICKs k+0.5, k=2..9",
                          readout_modes=["strict (final layer exempt)", "ignore"],
                          extra_readout_columns=["strict, final layer checked",
                                                 "strict, Z-reset idle not live"])}
    S["b_layer_permutations"] = [list(p) for p in layer_permutations(base)]
    S["b_fold_variants"] = [[list(map(list, layer)) for layer in f] for f in folds]
    S["free_neighbours_per_qubit_over_350_placements"] = {
        q: dict(sorted(Counter(sum(n not in set(e.values()) for n in neighbours(e[q]))
                               for _, _, e in embs).items())) for q in range(base.num_qubits)}
    S["slot_pairs_per_qubit_original_fold"] = {
        q: len(slot_pairs(base, q)) for q in range(base.num_qubits)}

    stats = defaultdict(Counter)
    log = lambda *a: print(f"[{time.perf_counter() - t0:7.0f} s]", *a, flush=True)
    fields = ["id", "category", "symmetry", "offset", "fold", "n_flags", "flags", "added_ticks",
              "hw_ok", "hw_violations", "n_cx", "max_degree", "readout_strict",
              "readout_strict_final_check", "readout_strict_zreset_not_live"]
    fh = (out / "step3_candidates.csv").open("w", newline="")
    writer = csv.DictWriter(fh, fieldnames=fields)
    writer.writeheader()
    nid = 0

    def write(rows):
        nonlocal nid
        for r in rows:
            r["id"] = nid
            nid += 1
            writer.writerow(r)
        fh.flush()

    def checkpoint():
        (out / "step3_summary.json").write_text(json.dumps(
            {**S, "stats": {k: dict(v) for k, v in stats.items()},
             "elapsed_s": time.perf_counter() - t0}, indent=1, default=str))

    # (c) 350 rigid re-embeddings, (b) fold variants on the primary placement.
    rows = []
    for sym, off, emb in embs:
        circ, e = build(base, emb)
        rows.append(dict(category="c", symmetry=sym, offset=off, fold=0, n_flags=0, flags="",
                         added_ticks=0, **evaluate(circ, e)))
        _tally(stats["c"], rows[-1], ())
    for k in range(1, len(folds)):
        circ, e = build(base, primary[2], (), folds[k])
        assert is_deterministic(circ)
        rows.append(dict(category="b", symmetry="id", offset=(4, 4), fold=k, n_flags=0, flags="",
                         added_ticks=0, **evaluate(circ, e)))
        _tally(stats["b"], rows[-1], ())
    write(rows)
    log("c and b done", dict(stats["c"]), dict(stats["b"]))

    # (a1) every single flag on one placement per symmetry x every fold variant.
    singles_count = {}
    tasks = [(p, k) for p in placements_by_symmetry(base) for k in range(len(folds))]
    with Pool(args.workers) as pool:
        for key, sym, info, bad, st, rows in pool.imap_unordered(_work_a1, tasks):
            assert not bad, bad
            singles_count[key] = info
            stats["a1"] += st
            stats[f"a1 {sym}"] += st
            write(rows)
    S["flag_set_counts"] = singles_count
    log("a1 done", dict(stats["a1"]))
    checkpoint()

    # (a2) every pair on the primary placement, original fold (parallel).
    if not args.skip_pairs:
        _init(primary, 0)
        n = len(_W["singles"])
        with Pool(args.workers, initializer=_init, initargs=(primary, 0)) as pool:
            for done, (st, rows) in enumerate(pool.imap_unordered(_work_pairs, range(n), chunksize=4)):
                stats["a2"] += st
                write(rows)
                if done % 200 == 0:
                    log(f"a2 {done}/{n} first-flag indices", stats["a2"]["total"])
                    checkpoint()
        log("a2 done", dict(stats["a2"]))
        checkpoint()

    # (a3) random sample of triples on the primary placement (count is exact above).
    _init(primary, 0)
    singles = _W["singles"]
    rng = random.Random(20261031)
    hooks = [f for f in singles if f.q in HOOK_QUBITS]
    seen = 0
    while seen < args.triple_sample:
        combo = tuple(rng.sample(singles, 3)) if seen % 2 else (rng.choice(hooks), *rng.sample(singles, 2))
        if len({f.at for f in combo}) < 3:
            continue
        row = _row(combo, "a3 (sample)")
        _tally(stats["a3 (sample)"], row, combo)
        seen += 1
    log("a3 sample done", dict(stats["a3 (sample)"]))
    fh.close()

    # verify() on a small sample: only to show the generated circuits are accepted.
    from nnflags.verify import bundled_paths, verify
    full, _ = bundled_paths("d3a6")
    picks = ([(f,) for f in hooks[:6]]
             + [(hooks[0], f) for f in rng.sample([f for f in singles if f.at != hooks[0].at], 6)]
             + [(f,) for f in rng.sample(singles, 4)])
    vs = []
    for k, combo in enumerate(picks[:args.verify_sample - 4]):
        circ, emb = build(base, primary[2], combo)
        vs.append((f"primary flags {k}", combo, circ, emb))
    for k in range(1, min(len(folds), 5)):
        circ, emb = build(base, primary[2], (), folds[k])
        vs.append((f"fold variant {k}", (), circ, emb))
    S["verify_sample"] = []
    (out / "step3_sample").mkdir(exist_ok=True)
    for name, combo, circ, emb in vs:
        path = out / "step3_sample" / (name.replace(" ", "_") + ".stim")
        path.write_text(str(circ))
        r = verify(full, circ, max_fault_count=2)
        S["verify_sample"].append(dict(
            name=name, flags=[str(f) for f in combo], deterministic=is_deterministic(circ),
            T=r["T"], S=r["S"], fault_count=r["fault_count"], runtime_s=r["runtime_s"],
            check=C.summarize(C.check_circuit(circ, emb)), stim=str(path)))
        log("verify", name, [str(f) for f in combo], "T malignant (k=2):", r["T"][2]["malignant"])
    S["runtime_s"] = time.perf_counter() - t0
    checkpoint()
    log("done")


if __name__ == "__main__":
    main()
