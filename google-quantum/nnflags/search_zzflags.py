"""ZZ-flag round: generalised Z / X flags (zzflags.py) on G4-type fold trees.

DESIGN SPACE
  * Bases: G4's extracted double check (CX form, results/g4/G4-CX.inner.stim)
    and the feasible abstract fold forests of the Option-1 screen
    (results/option1_screen.json, best code labelling per base), in order of
    best malignant 2-fault T count (then base rate).
  * Flags: generalised Z flags (R f, CX q_i -> f at chosen slots, M f in the
    final layer + DETECTOR) and, as the secondary family, X flags (RX f,
    CX f -> q_i, MX f). Controls of one flag: 1-4 tree qubits of the same grid
    colour (depth parity), each with tree degree <= 3 (it needs a free grid
    neighbour). Slots: existing TICKs where the control is idle, or new TICKs.
  * Two-level greedy search per base (exact prefilter, see zzflags.py):
      level 1: for every (basis, control set) every maximal set of malignant
               pairs one flag can remove; up to N1 concrete flags, best
               coverage first; each built, embedded (exists?) and verified;
      level 2: the K best realisable level-1 circuits become new bases (their
               own faults included exactly); a second flag must remove ALL
               their malignant pairs (else the best partial coverages are
               evaluated to record the best count reached).
      level 3 (--max-flags 3, the extra pass): same once more.
  * Every evaluated circuit gets verify(max_fault_count=2). Circuits with 0
    malignant T configurations at <= 2 faults ("successes") must also pass
    constraints.check_circuit (strict readout, live_rule="gate",
    final_layer="auto"; nearest-neighbour; degree <= 4; no reuse) under a Willow
    embedding, equivalence.check_equivalence (flags excluded from (iii)), and
    get verify(max_fault_count=3).

Usage: nohup .venv/bin/python -m nnflags.search_zzflags --workers 12 > logs/search_zzflags.log &
Outputs: results/zz_candidates.csv (every evaluated circuit), results/zz_bases.csv
(per base: pairs, coverage evidence), results/zz/*.stim, results/zz_state.json.
"""
import argparse
import csv
import itertools
import json
import time
import traceback
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from nnflags import constraints as C
from nnflags import equivalence as Q
from nnflags import zzflags as Z
from nnflags.verify import verify
from nnflags.willow import readout_line

SCREEN = Path("results/option1_screen.json")
INFEASIBLE = 10 ** 6
STOP_SUCCESSES = 10

FIELDS = ["id", "base", "base_T2", "level", "n_flags", "basis", "flags", "flag_controls",
          "flag_positions", "added_ticks", "n_qubits", "n_cx", "max_degree", "ticks",
          "predicted_removed", "malignant_T_1", "malignant_T_2", "malignant_S_2", "malignant_T_3",
          "ler_T_mfc2", "ler_T_mfc2_one_in", "ler_T_mfc3", "ler_T_mfc3_one_in",
          "realisable", "hardware_ok", "equivalence_ok", "success", "reason", "stim_file",
          "full_stim_file", "runtime_s"]
BASE_FIELDS = ["base", "base_T2", "tree", "labelling", "n_pairs", "pairs", "pair_hooks",
               "single_flag_separable", "unseparable_pairs", "best_level1_T2", "best_level2_T2",
               "best_level3_T2", "n_evaluated", "n_success", "seconds", "error"]


# ---- helpers ---------------------------------------------------------------------------

def control_sets(d: Z.Design, controls, maxsize=4):
    deg = {q: len(d.adj.get(q, ())) for q in controls}
    ok = [q for q in controls if deg[q] <= 3]
    out = []
    for size in range(1, maxsize + 1):
        for qs in itertools.combinations(ok, size):
            if len({d.colour[q] for q in qs}) == 1:
                out.append(qs)
    return out


def maximal(masks):
    return [m for m in masks if not any(o != m and o & m == m for o in masks)]


def greedy_masks(cov, cols, n):
    """Large pair counts: grow one mask greedily from every single coverable pair."""
    single = [i for i in range(n) if Z.solve_gf2(cov.system(cols, [i]), len(cols)) is not None]
    out = set()
    for s in single:
        cur = [s]
        for i in single:
            if i not in cur and Z.solve_gf2(cov.system(cols, cur + [i]), len(cols)) is not None:
                cur.append(i)
        out.add(sum(1 << i for i in cur))
    return sorted(out)


def flag_description(inner, fq):
    specs, gates = Z.flag_specs(inner, fq)
    parts = []
    for f in fq:
        g = sorted(gates[f])
        parts.append(f"{g[0][2]}f{f}[" + "+".join(f"q{q}@t{t}" for t, q, _ in g) + "]")
    return ";".join(parts), specs, gates


def hook_text(pa, events, i, nq):
    """Short text of a fault class: its events (tick: Pauli)."""
    evs = sorted({(t, str(ps)[1:].replace("_", "")) for t, ps in events[i]})
    return f"#{i}:" + ",".join(f"t{t}" for t, _ in evs[:4]) + ("…" if len(evs) > 4 else "")


class Evaluator:
    """Builds, embeds and verifies flagged circuits of one base."""

    def __init__(self, base: Z.Design, name):
        self.base = base
        self.name = name
        self.rows = []
        self.success = []
        self.best = []   # (T2, row, inner text, full text) of realisable non-successes

    def evaluate(self, d_on: Z.Design, flags, level, predicted, extra_fq=()):
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
        desc, specs, gates = flag_description(inner, fq)
        row.update(n_flags=len(fq), basis="".join(sorted({s for f in fq for _, _, s in gates[f]})),
                   flags=desc, flag_controls=json.dumps([list(s[0]) for s in specs]),
                   added_ticks=len(Q.to_layers(inner)) - self.base.T,
                   n_qubits=inner.num_qubits, n_cx=len(C.two_qubit_gates(inner)),
                   max_degree=max(map(len, C.partners(inner).values())), ticks=inner.num_ticks)
        emb = next(Z.embeddings(self.base, specs), None)
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
            self._validate(row, inner, full, fq, specs)
        elif emb is None:
            row["reason"] = "no Willow embedding (tree + flag points)"
        row["runtime_s"] = round(time.perf_counter() - t0, 3)
        self.rows.append(row)
        if emb is not None and not row.get("success"):
            self.best.append((row["malignant_T_2"], row["ler_T_mfc2"], len(self.rows) - 1,
                              str(inner), str(full)))
            self.best.sort(key=lambda x: (x[0], x[1]))
            del self.best[3:]
        return inner, fq, row

    def _validate(self, row, inner, full, fq, specs):
        emb, tried, last = Z.find_valid_embedding(self.base, specs, inner)
        row["hardware_ok"] = emb is not None
        if emb is None:
            row["reason"] = f"hardware: {tried} embeddings tried, last {json.dumps(C.summarize(last or []))}"
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


def level_candidates(d_on, cov, controls, n, n_max, realisable, all_only=False, bases=("Z", "X")):
    """[(n_removed, mask, basis, control set, Flag)], best coverage first, only
    control sets with a Willow embedding (``realisable(qs, basis)``), each
    concrete flag (probe set) once."""
    out = []
    full_mask = (1 << n) - 1
    for basis in bases:
        for qs in control_sets(d_on, controls):
            cols = [k for k, p in enumerate(cov.pa.probes) if p.q in qs and p.basis == basis]
            if not cols:
                continue
            if all_only:
                masks = [full_mask] if Z.solve_gf2(cov.system(cols, list(range(n))), len(cols)) else []
            elif n <= 10:
                masks = maximal(Z.coverable_subsets(cov, cols, n))
            else:
                masks = maximal(greedy_masks(cov, cols, n))
            for m in masks:
                out.append((bin(m).count("1"), m, basis, qs, cols))
    out.sort(key=lambda x: (-x[0], x[2] != "Z", len(x[3])))
    res, seen = [], set()
    mid = d_on.mid_ticks[0] if d_on.mid_ticks else 10 ** 9
    for k, m, basis, qs, cols in out:
        if realisable is not None and not realisable(qs, basis == "X"):
            continue   # not even with the flag dormant at the mid check
        for fl in Z.concrete_flags(cov, cols, [i for i in range(n) if m >> i & 1], limit=4):
            live = basis == "X" or min(p.slot for p in fl.probes) <= mid
            if fl.probes in seen or (realisable is not None and not realisable(qs, live)):
                continue
            seen.add(fl.probes)
            res.append((k, m, basis, qs, fl))
        if len(res) >= n_max:
            break
    return res[:n_max]


def realisability(d, specs):
    cache = {}

    def f(qs, live):
        key = (qs, live)
        if key not in cache:
            cache[key] = next(Z.embeddings(d, list(specs) + [(qs, live)]), None) is not None
        return cache[key]
    return None if specs is None else f


def process(task):
    """Worker: full two/three-level search on one base."""
    name, key, entry, opts = task
    t0 = time.perf_counter()
    info = dict(base=name)
    try:
        d = Z.design_g4() if key == "G4" else Z.design_from_option1(key, entry, name=name)
        tree_q = list(d.qubits)
        pa = Z.ProbeAnalysis(d, controls=tree_q)
        pairs, events, _, _ = Z.malignant_pairs(d)
        d.info["T2"] = len(pairs)
        n = len(pairs)
        cov = Z.Coverage(pa, pairs, events)
        ev = Evaluator(d, name)
        info.update(base_T2=n, tree=d.info.get("tree"), labelling=str(d.info.get("lab", "")),
                    n_pairs=n, pairs=json.dumps(pairs))
        real1 = realisability(d, [])
        filt = None if opts.get("abstract") else real1
        # coverage evidence: which pairs some single (basis, control set) flag can separate,
        # and which of those control sets have a Willow embedding
        sep, sep_real = defaultdict(int), defaultdict(int)
        for basis in ("Z", "X"):
            for qs in control_sets(d, tree_q):
                cols = [k for k, p in enumerate(pa.probes) if p.q in qs and p.basis == basis]
                for i in range(n):
                    if Z.solve_gf2(cov.system(cols, [i]), len(cols)) is not None:
                        sep[i] += 1
                        sep_real[i] += real1(qs, basis == "X")
        info["single_flag_separable"] = json.dumps({i: [sep[i], sep_real[i]] for i in range(n)})
        info["unseparable_pairs"] = json.dumps(dict(
            any_control_set=[pairs[i] for i in range(n) if not sep[i]],
            realisable_control_set=[pairs[i] for i in range(n) if not sep_real[i]]))
        info["pair_hooks"] = json.dumps({str(pairs[i]): [hook_text(pa, events, f, d.nq) for f in pairs[i]]
                                         for i in range(n)})
        # level 1
        lvl = defaultdict(list)
        for k, m, basis, qs, fl in level_candidates(d, cov, tree_q, n, opts["n1"], filt, bases=opts["bases"]):
            r = ev.evaluate(d, [fl], 1, k)
            if r:
                lvl[1].append((r[2]["malignant_T_2"], r[2]["ler_T_mfc2"], r[2]["realisable"], r[0], r[1]))
        info["best_level1_T2"] = min((x[0] for x in lvl[1] if x[2]), default="")
        frontier = sorted([x for x in lvl[1] if x[2] and x[0] > 0], key=lambda x: (x[0], x[1]))[:opts["k1"]]
        for level in range(2, opts["max_flags"] + 1):
            for _, _, _, inner, fq in frontier:
                if len(ev.success) >= opts["stop_per_base"]:
                    break
                d1 = Z.Design(name + f"+L{level - 1}", inner, d.full_args, {}, info=d.info)
                pa1 = Z.ProbeAnalysis(d1, controls=tree_q)
                pairs1, events1, _, _ = Z.malignant_pairs(d1)
                if not pairs1:
                    continue
                cov1 = Z.Coverage(pa1, pairs1, events1)
                n1 = len(pairs1)
                real = realisability(d, None if opts.get("abstract") else Z.flag_specs(inner, fq)[0])
                c2 = level_candidates(d1, cov1, tree_q, n1, opts["n2"], real, all_only=True, bases=opts["bases"])
                if not c2:   # no flag removes all: record / extend the best partial coverages
                    c2 = level_candidates(d1, cov1, tree_q, n1,
                                          opts["n2_partial"] if level < opts["max_flags"] else 2, real,
                                          bases=opts["bases"])
                for k, m, basis, qs, fl in c2:
                    r = ev.evaluate(d1, [fl], level, k, extra_fq=fq)
                    if r:
                        lvl[level].append((r[2]["malignant_T_2"], r[2]["ler_T_mfc2"], r[2]["realisable"],
                                           r[0], r[1]))
            info[f"best_level{level}_T2"] = min((x[0] for x in lvl[level] if x[2]), default="")
            frontier = sorted([x for x in lvl[level] if x[2] and x[0] > 0],
                              key=lambda x: (x[0], x[1]))[:opts["k1"]]
        info.update(n_evaluated=len(ev.rows), n_success=len(ev.success))
        info["seconds"] = round(time.perf_counter() - t0, 1)
        return info, ev.rows, ev.success, ev.best
    except Exception as e:  # keep the run alive; record the error
        info.update(error=f"{type(e).__name__}: {e} | {traceback.format_exc()[-600:]}",
                    seconds=round(time.perf_counter() - t0, 1))
        return info, [], [], []


def tasks(opts, limit=None):
    screen = json.loads(SCREEN.read_text())
    keys = [k for k, v in screen.items() if min(int(x) for x in v["hist"]) < INFEASIBLE]
    keys.sort(key=lambda k: (min(int(x) for x in screen[k]["hist"]), screen[k]["rate"]))
    out = [("G4", "G4", None, opts)]
    for i, k in enumerate(keys[:limit]):
        out.append((f"B{i:04d}", k, screen[k], opts))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--max-flags", type=int, default=2)
    ap.add_argument("--limit", type=int, default=None, help="number of Option-1 bases")
    ap.add_argument("--hours", type=float, default=6.0)
    ap.add_argument("--n1", type=int, default=40)
    ap.add_argument("--k1", type=int, default=8)
    ap.add_argument("--n2", type=int, default=16)
    ap.add_argument("--n2-partial", type=int, default=6)
    ap.add_argument("--tag", default="zz")
    ap.add_argument("--abstract", action="store_true",
                    help="evidence pass: no Willow-realisability filter on the flags")
    ap.add_argument("--stop-per-base", type=int, default=2)
    ap.add_argument("--only-bases", default=None, help="file with base names (one per line) to run")
    ap.add_argument("--bases", default="ZX", help="flag families: Z (generalised Z flags), X, or ZX")
    args = ap.parse_args()
    out = Path(args.out)
    sdir = out / args.tag
    sdir.mkdir(parents=True, exist_ok=True)
    opts = dict(max_flags=args.max_flags, n1=args.n1, k1=args.k1, n2=args.n2,
                n2_partial=args.n2_partial, stop_per_base=args.stop_per_base,
                abstract=args.abstract, bases=tuple(args.bases))
    t0 = time.time()
    log = lambda *a: print(f"[{time.time() - t0:8.1f} s]", *a, flush=True)
    todo = tasks(opts, args.limit)
    if args.only_bases:
        keep = set(Path(args.only_bases).read_text().split())
        todo = [t for t in todo if t[0] in keep]
    log(f"{len(todo)} bases queued (G4 + {len(todo) - 1} Option-1 bases), opts {opts}")
    suffix = "" if args.tag == "zz" else "_" + args.tag.removeprefix("zz_")
    fh = (out / f"zz_candidates{suffix}.csv").open("w", newline="")
    wr = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
    wr.writeheader()
    bh = (out / f"zz_bases{suffix}.csv").open("w", newline="")
    bw = csv.DictWriter(bh, fieldnames=BASE_FIELDS, extrasaction="ignore")
    bw.writeheader()
    state = dict(settings=dict(args=vars(args), noise="uniformly_depolarize", p=Z.NOISE,
                               max_fault_count=[2, 3], readout="strict", live_rule="gate",
                               final_layer="auto", max_degree=4), started=time.ctime())
    nid = n_succ = n_bases = 0
    best_global = []
    stop_reason = "design space exhausted"
    with Pool(args.workers) as pool:
        for info, rows, succ, best in pool.imap(process, todo, chunksize=1):
            n_bases += 1
            for k, row in enumerate(rows):
                row["id"] = nid + k
            for idx, inner, full, emb in succ:
                i = n_succ
                row = rows[idx]
                p = sdir / f"success{i:02d}.inner.stim"
                p.write_text(inner)
                (sdir / f"success{i:02d}.full.stim").write_text(full)
                row.update(stim_file=str(p), full_stim_file=str(sdir / f"success{i:02d}.full.stim"))
                n_succ += 1
                log(f"SUCCESS #{i} base {info['base']} flags {row['flags']} T3={row.get('malignant_T_3')} "
                    f"S2={row['malignant_S_2']} LER 1 in {row['ler_T_mfc2_one_in']}")
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
            log(f"base {info['base']} T2={info.get('base_T2')} eval={len(rows)} "
                f"L1={info.get('best_level1_T2')} L2={info.get('best_level2_T2')} "
                f"L3={info.get('best_level3_T2', '')} succ={len(succ)} {info.get('seconds')} s"
                + (f" ERROR {info['error'][:200]}" if info.get("error") else ""))
            if n_bases % 10 == 0 or succ:
                for k, (t2, rate, rid, b, inner, full) in enumerate(best_global):
                    (sdir / f"best{k}.inner.stim").write_text(inner)
                    (sdir / f"best{k}.full.stim").write_text(full)
                state.update(n_bases_done=n_bases, n_evaluated=nid, n_success=n_succ,
                             best_non_success=[dict(T2=t2, rate=rate, id=rid, base=b)
                                               for t2, rate, rid, b, _, _ in best_global],
                             elapsed_s=time.time() - t0)
                (out / f"{args.tag}_state.json").write_text(json.dumps(state, indent=1))
            if n_succ >= STOP_SUCCESSES:
                stop_reason = f"{STOP_SUCCESSES} successes"
                pool.terminate()
                break
            if time.time() - t0 > args.hours * 3600:
                stop_reason = f"time limit {args.hours} h"
                pool.terminate()
                break
    for k, (t2, rate, rid, b, inner, full) in enumerate(best_global):
        (sdir / f"best{k}.inner.stim").write_text(inner)
        (sdir / f"best{k}.full.stim").write_text(full)
    state.update(n_bases_done=n_bases, n_bases_queued=len(todo), n_evaluated=nid, n_success=n_succ,
                 stop_reason=stop_reason, finished=time.ctime(), elapsed_s=time.time() - t0,
                 best_non_success=[dict(T2=t2, rate=rate, id=rid, base=b)
                                   for t2, rate, rid, b, _, _ in best_global])
    (out / f"{args.tag}_state.json").write_text(json.dumps(state, indent=1))
    fh.close()
    bh.close()
    log("done:", stop_reason, f"bases {n_bases}, evaluated {nid}, successes {n_succ}")


if __name__ == "__main__":
    main()
