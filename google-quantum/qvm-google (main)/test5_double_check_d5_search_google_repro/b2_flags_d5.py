"""Test 5, Part B, step B2 (first stage): nearest-neighbour flags for Gidney's d = 5 double check.

Question: keeping Gidney's d = 5 double check (cliffordea d5a19, real-T fault distance 3, three
malignant 3-fault configurations) in its own square-grid layout, can flags placed on FREE grid
points next to their control qubits (so every flag gate is nearest-neighbour) detect all three
malignant configurations, giving fault distance 4? Then the same for the 601 malignant 4-fault
configurations (fault distance 5).

Method = the d = 3 flag machinery of nnflags/zzflags.py, unchanged except that a target is a
k-fault configuration instead of a pair:
  * probes (Z: CX q -> flag, X: CX flag -> q) at idle slots or new half TICKs;
  * a flag on control set Q must (i) give a deterministic detector and (ii) be flipped by an odd
    number of the configuration's faults, every equivalent event of a fault flipping it alike
    (GF(2) system, zzflags.Coverage.system generalised);
  * nearest-neighbour: a flag sits on a free lattice point adjacent to all its controls.
Candidates are then built (zzflags.build_flagged) and verified exactly (cliffordea, real T).

Readout lines and the Willow chip boundary are NOT applied in this stage (geometry only, on the
infinite square grid); B1 showed Gidney's rigid layout needs re-embedding for readout lines anyway.

    .venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b2_flags_d5.py" [--target 4]
    -> results/b2_flags_d5.json, RESULTS_B2_flags.md, results/b2_best_*.stim
"""
import argparse
import datetime as dt
import itertools
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import stim

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from cliffordea import accept, enum  # noqa: E402
from nnflags import constraints as C  # noqa: E402
from nnflags import zzflags as Z  # noqa: E402
from nnflags.verify import bundled_paths, load_measurement, verify  # noqa: E402

RES = HERE / "results"


def kst():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%b %d, %I:%M %p KST")


def log(*a):
    print(f"[{kst()}]", *a, flush=True)


def nbrs(p):
    r, c = p
    return ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))


# ---- the base design ----------------------------------------------------------------------

def design_d5(name="d5a19"):
    full_p, inner_p = bundled_paths(name)
    inner = stim.Circuit.from_file(str(inner_p))
    full = stim.Circuit.from_file(str(full_p))
    plaq, maj, mino = set(), [], []
    for op in full.flattened():
        if op.name == "MPP":
            for g in op.target_groups():
                qs = tuple(sorted(t.value for t in g))
                if all(t.is_x_target for t in g) and len(qs) < 19:
                    plaq.add(qs)
        if op.name == "S" and not maj and not mino:
            mino = [t.value for t in op.targets_copy()]
        elif op.name == "S_DAG" and mino and not maj:
            maj = [t.value for t in op.targets_copy()]
    plaq = sorted(plaq)
    data = sorted({q for p in plaq for q in p})
    assert len(plaq) == 9 and len(data) == 19 and len(maj) + len(mino) == 19, (len(plaq), len(data))
    emb = {q: (int(a), int(b)) for q, (a, b) in C.native_coords(inner).items()}
    d = Z.Design(name, inner, (tuple(plaq), tuple(maj), tuple(mino), tuple(data)), emb)
    return d, full


def malignant_configs(d, inner, full, k):
    """Malignant T configurations with exactly k faults, and the events of their faults."""
    m = load_measurement(full, inner)
    comb = enum.FaultCombinator(enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=Z.NOISE))
    an = accept.CliffordLogicalAnalyzer(data_indices=m.DATA_INDICES,
                                        stabilizer_generators=m.STABILIZER_GENERATORS, logical_s=m.LOGICAL_S)
    kept = comb.get_kept_effects(logical_analyzer=an, max_fault_count=k, cultivated_states=("T",))
    cfgs = sorted({tuple(sorted(cfg)) for eff in kept["T"] for pr, fid, cs in eff.values()
                   if pr > 0 and fid != 1 for cfg in cs if len(cfg) == k})
    nq = inner.num_qubits
    events = {i: [(ev[0], Z.event_pauli(ev, nq)) for ev in comb.index_to_events[i]]
              for cfg in cfgs for i in cfg}
    return cfgs, events


class ConfigCoverage(Z.Coverage):
    """zzflags.Coverage with k-fault configurations as targets (self.pairs holds the tuples)."""

    def system(self, cols, idx):
        def loc(r):
            return sum(1 << j for j, k in enumerate(cols) if r >> k & 1)
        eqs = []
        nbits = max(self.syn[k] for k in cols).bit_length() if cols else 0
        for b in range(nbits):
            msk = sum(1 << j for j, k in enumerate(cols) if self.syn[k] >> b & 1)
            if msk:
                eqs.append((msk, 0))
        for pi in idx:
            cfg = self.pairs[pi]
            acc = 0
            for f in cfg:
                r0 = self.rows[f][0]
                for r in self.rows[f][1:]:
                    msk = loc(r0 ^ r)
                    if msk:
                        eqs.append((msk, 0))
                acc ^= r0
            eqs.append((loc(acc), 1))
        return eqs


# ---- free points and control sets ------------------------------------------------------------

def flag_sites(d):
    used = {d.emb[q]: q for q in d.qubits}
    sites = {}
    for p in used:
        for w in nbrs(p):
            if w in used:
                continue
            ctrl = tuple(sorted(used[x] for x in nbrs(w) if x in used))
            if len(ctrl) >= 2:
                sites[w] = ctrl
    return sites


def site_options(cov, sites, n, bases=("Z", "X")):
    """[(site, basis, controls, mask of coverable targets)] for every site and control subset."""
    out = []
    for w, ctrl in sorted(sites.items()):
        for size in range(2, len(ctrl) + 1):
            for qs in itertools.combinations(ctrl, size):
                for b in bases:
                    cols = [k for k, p in enumerate(cov.pa.probes) if p.q in qs and p.basis == b]
                    if not cols:
                        continue
                    if n <= 12:
                        masks = Z.coverable_subsets(cov, cols, n)
                    else:
                        masks = [m for m in _greedy(cov, cols, n)]
                    for msk in masks:
                        out.append((w, b, qs, msk, cols))
    return out


def _greedy(cov, cols, n):
    single = [i for i in range(n) if Z.solve_gf2(cov.system(cols, [i]), len(cols)) is not None]
    out = set()
    for s in single:
        cur = [s]
        for i in single:
            if i not in cur and Z.solve_gf2(cov.system(cols, cur + [i]), len(cols)) is not None:
                cur.append(i)
        out.add(sum(1 << i for i in cur))
    return sorted(out)


def covers(options, n, max_flags):
    """Sets of <= max_flags options on distinct sites whose masks cover all n targets (smallest first)."""
    full = (1 << n) - 1
    by_mask = defaultdict(list)
    for o in options:
        by_mask[o[3]].append(o)
    masks = sorted(by_mask, key=lambda m: -bin(m).count("1"))
    for k in range(1, max_flags + 1):
        for combo in itertools.combinations(masks, k):
            acc = 0
            for m in combo:
                acc |= m
            if acc == full:
                yield [by_mask[m] for m in combo]


# ---- evaluation --------------------------------------------------------------------------------

def evaluate(d, full_base, cov, groups, target, limit_per=3):
    """Try concrete flags for one cover; return the best verified result."""
    best = None
    pools = []
    for g in groups:
        pool = []
        for (w, b, qs, msk, cols) in g:
            for fl in Z.concrete_flags(cov, cols, [i for i in range(len(cov.pairs)) if msk >> i & 1], limit=limit_per):
                pool.append((w, fl))
        pools.append(pool)
    tried = 0
    for choice in itertools.product(*pools):
        sites = [w for w, _ in choice]
        if len(set(sites)) != len(sites):
            continue
        flags = [fl for _, fl in choice]
        try:
            inner, fq = Z.build_flagged(d, flags)
        except ValueError:
            continue
        tried += 1
        emb = dict(d.emb)
        for f, w in zip(fq, sites):
            emb[f] = w
        geo = C.summarize(C.check_circuit(inner, emb, grid=None, readout="ignore"))
        full = d.full(inner)
        r = verify(full, inner, max_fault_count=target - 1, states=("T",))
        mal = {k: r["T"][k]["malignant"] for k in r["T"]}
        res = dict(flags=[str(f) for f in flags], sites=sites, geometry=dict(geo),
                   malignant_T=mal, qubits=inner.num_qubits, ticks=inner.num_ticks,
                   max_partners=max(map(len, C.partners(inner).values())),
                   rate_T_p01=r["error_rate_per_kept_shot"]["T"], inner=str(inner), emb=emb, full=str(full))
        ok = all(v == 0 for v in mal.values()) and not geo
        key = (not ok, sum(mal.values()), sum(geo.values()), res["ticks"])
        if best is None or key < best[0]:
            best = (key, res)
        if ok or tried >= 60:
            break
    return best[1] if best else None, tried


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=4, help="fault distance to reach (4 or 5)")
    ap.add_argument("--max-flags", type=int, default=4)
    ap.add_argument("--max-covers", type=int, default=40)
    a = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    d, full = design_d5()
    log(f"base {d.name}: {d.nq} qubits, {d.T} TICKs, data {len(d.data)}")
    cfgs, events = malignant_configs(d, d.inner, d.full(), a.target - 1)
    log(f"malignant {a.target - 1}-fault T configurations: {len(cfgs)}")
    sites = flag_sites(d)
    log(f"free grid points next to >= 2 circuit qubits: {len(sites)}")
    controls = sorted({q for qs in sites.values() for q in qs})
    pa = Z.ProbeAnalysis(d, controls=controls)
    cov = ConfigCoverage(pa, cfgs, events)
    opts = site_options(cov, sites, len(cfgs))
    single = sorted({i for o in opts for i in range(len(cfgs)) if o[3] >> i & 1})
    log(f"site options: {len(opts)}; targets coverable by some nearest-neighbour flag: {len(single)} / {len(cfgs)}")
    out = dict(base=d.name, target_fault_distance=a.target, n_targets=len(cfgs), n_sites=len(sites),
               n_options=len(opts), coverable_targets=len(single), uncoverable=[list(cfgs[i]) for i in range(len(cfgs)) if i not in single],
               results=[])
    best = None
    if len(single) == len(cfgs):
        for ci, groups in enumerate(covers(opts, len(cfgs), a.max_flags)):
            if ci >= a.max_covers:
                break
            res, tried = evaluate(d, full, cov, groups, a.target)
            if res is None:
                continue
            row = {k: v for k, v in res.items() if k not in ("inner", "full", "emb")}
            row["tried"] = tried
            out["results"].append(row)
            log(f"cover {ci}: flags {row['flags']} malignant {row['malignant_T']} geometry {row['geometry']}")
            ok = all(v == 0 for v in res["malignant_T"].values()) and not res["geometry"]
            if best is None or (ok and not best[0]):
                best = (ok, res)
            if ok:
                break
    if best:
        ok, res = best
        head = "\n".join(f"QUBIT_COORDS({res['emb'][q][0]}, {res['emb'][q][1]}) {q}" for q in sorted(res["emb"]))
        (RES / f"b2_best_fd{a.target}.inner.stim").write_text(head + "\n" + res["inner"])
        (RES / f"b2_best_fd{a.target}.full.stim").write_text(res["full"])
        out["success"] = ok
    else:
        out["success"] = False
    out["runtime_s"] = round(time.time() - t0, 1)
    (RES / f"b2_flags_d5_fd{a.target}.json").write_text(json.dumps(out, indent=1, default=str))
    L = [f"# Test 5, B2 (stage 1): nearest-neighbour flags on Gidney's d = 5 layout, target fault distance {a.target} "
         f"(written {kst()})", "",
         f"- base: `{d.name}` ({d.nq} qubits), malignant {a.target - 1}-fault T configurations: **{len(cfgs)}**",
         f"- free grid points next to >= 2 circuit qubits (possible nearest-neighbour flag sites): {len(sites)}",
         f"- configurations that at least one nearest-neighbour flag can detect: **{len(single)} / {len(cfgs)}**",
         f"- **success (all detected, verified, nearest-neighbour): {out['success']}**", ""]
    if out["results"]:
        L += ["| flags | malignant T by fault count | geometry violations | qubits | TICKs | max partners |", "|---|---|---|---|---|---|"]
        for r in out["results"]:
            L.append(f"| `{'; '.join(r['flags'])}` | {r['malignant_T']} | {r['geometry'] or 'none'} | {r['qubits']} | {r['ticks']} | {r['max_partners']} |")
    L += ["", "Readout lines and the chip boundary are not applied in this stage (see the script header).", ""]
    (HERE / f"RESULTS_B2_flags_fd{a.target}.md").write_text("\n".join(L))
    log(f"done in {out['runtime_s']} s; success {out['success']}")


if __name__ == "__main__":
    main()
