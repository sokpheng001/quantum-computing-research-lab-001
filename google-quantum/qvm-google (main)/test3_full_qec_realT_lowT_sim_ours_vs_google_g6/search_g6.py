"""Test 3, step 1: search for a fault-distance-3 double check that fits Google's G6
grafting circuit (Rosenfeld et al. arXiv:2512.13908, Fig. 4) in place of Google's own.

Same method as the continuing-data search that found cs02 (nnflags/search_continuing.py,
reused unchanged), with the data FIXED to G6's (step 0b showed no existing circuit fits):

  * fold forests are grown on the lattice exactly as before (line-labelled, roots on
    an "R" line, data on "D" lines, measured ancillas on "M" lines, at most --umax
    never-measured "U" ancillas, the G6 pattern), but only line patterns with exactly
    three data lines two apart (G6's data lines are 9, 11, 13);
  * every embedded forest is kept only if one of the 4 line-preserving lattice
    symmetries plus a translation puts its 7 data exactly on G6's data positions;
    it is then fixed at that Willow placement (no other translation is allowed);
  * the code labelling is forced: the one whose 7 weight-4 stabilisers are G6's
    (which of the 7 data get T or T-dagger does not matter: all 7 choices give the
    same malignant counts, checked on G4);
  * screen (malignant T pairs of the bare tree), then the flag search: exact 2-cover
    then the two-level greedy search (--cover both), ZZ / X / multi-control flags,
    at most 2 flags, flags adjacent to their controls, off the data lines, fitting
    on Willow at the fixed placement.

G6's grafting qubits are first used at TICK 57 or later, so during cultivation every
other Willow qubit is free for our ancillas and flags.

SUCCESS = same as cs02: fault distance 3 (0 malignant T at 1 and 2 faults), strict and
continuing-data readout rules satisfied, equivalence ok, degree <= 4, nearest neighbour.

    .venv/bin/python "qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6/search_g6.py" --workers 11
    -> results/g6_search/ (success*.stim, candidates.csv, bases.csv, state.json),
       RESULTS_search.md (written by this script at the end)
"""
import argparse
import csv
import itertools
import json
import os
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
os.chdir(ROOT)

from check_g6_fit import g6_layout  # noqa: E402

from nnflags import search_continuing as SC  # noqa: E402
from nnflags import search_option1 as S  # noqa: E402
from nnflags.willow import WILLOW  # noqa: E402

RES = HERE / "results" / "g6_search"
STOP_SUCCESSES = 10

_, _co, _g6data, _code = g6_layout()
G6_POS = frozenset(_co[q] for q in _g6data)
G6_W4 = set(_code["X"])
G6_LINES = sorted({SC.line(p) for p in G6_POS})
# sanity check: the tree positions of cs02's placements with data on G6's positions (step 0,
# results/g6_fit.json; flags q10, q11 left out). Google's own G6 double check is not a fold
# forest of this space (its never-measured q12 at (5, 8) touches no data), so it cannot serve.
CS02_TREES = [frozenset(tuple(p) for q, p in a.items() if q not in ("10", "11")) | G6_POS
              for a in json.loads((HERE / "results/g6_fit.json").read_text())["circuits"]["cs02"]["data_on_g6_ancillas"]]


# The forest is placed once, at G6's data: flags may use no other translation.
def _fixed_translation(points, need=None):
    return [(0, 0)] if all(p in WILLOW for p in points) else []


SC.Placer.translations = staticmethod(_fixed_translation)


def g6_patterns(m, dmax):
    """Line patterns with exactly three data lines two apart, as G6's 9, 11, 13."""
    out = []
    for a, b, key in SC.patterns(m, dmax):
        d = sorted(L for L, x in key if x == "D")
        if len(d) == 3 and d[1] - d[0] == 2 and d[2] - d[1] == 2:
            out.append((a, b, key))
    return out


def place_on_g6(parent, roles, roots):
    """All placements (parent, roles, roots) of one embedded forest with its data on G6's
    positions, via the 4 line-preserving symmetries and a translation."""
    out = []
    data = [v for v in parent if roles[v] == "D"]
    for f in SC.SYMS:
        mp = {v: f(*v) for v in parent}
        dpos = [mp[v] for v in data]
        lo, glo = min(dpos), min(G6_POS)
        sh = (glo[0] - lo[0], glo[1] - lo[1])
        T = {v: (p[0] + sh[0], p[1] + sh[1]) for v, p in mp.items()}
        if {T[v] for v in data} != G6_POS or not all(p in WILLOW for p in T.values()):
            continue
        par = {T[v]: (None if parent[v] is None else T[parent[v]]) for v in parent}
        rol = {T[v]: roles[v] for v in parent}
        rts = tuple(T[r] for r in roots)
        out.append((par, rol, rts))
    return out


def g6_labelling(inst):
    """The code labelling (code qubit j -> j-th data node) that gives G6's stabilisers."""
    lay = SC.build_u(*inst)
    emb, data = lay["emb"], lay["data"]
    for lab in itertools.permutations(range(7)):
        L = [emb[data[lab[j]]] for j in range(7)]
        if all(frozenset(L[j] for j in p) in G6_W4 for p in S.CODE_PLAQ):
            return min(tuple(lab[a[j]] for j in range(7)) for a in S.code_automorphisms())
    return None


def grow_task(task):
    m, found = SC.grow_pattern(task)
    keep = []
    for ck, parent, roles in found:
        for inst in place_on_g6(parent, roles, SC.ROOTS[m]):
            keep.append((ck, inst))
    return m, keep


def enumerate_g6(ms, dmax, nmax, umax, pool, log):
    tasks = [(m, a, b, k, dmax, nmax, umax) for m in ms for a, b, k in g6_patterns(m, dmax)]
    log(f"{len(tasks)} line patterns with three data lines two apart")
    seen, groups, stats = set(), defaultdict(list), Counter()
    for i, (m, keep) in enumerate(pool.imap_unordered(grow_task, tasks, chunksize=2)):
        for ck, inst in keep:
            par, rol, rts = inst
            sig = tuple(sorted((v, rol[v]) for v in par))
            if sig in seen:
                continue
            seen.add(sig)
            lab = g6_labelling(inst)
            nu = sum(r == "U" for r in rol.values())
            stats[f"m{m}_n{len(par)}_u{nu}"] += 1
            if lab is None:
                stats["no_g6_labelling"] += 1
                continue
            key = SC.abstract_key(par, rol, rts)
            groups[(key, lab)].append(inst)
        if (i + 1) % 100 == 0:
            log(f"patterns {i + 1}/{len(tasks)}: {sum(stats.values())} placements on G6's data")
    return groups, dict(sorted(stats.items()))


def screen_and_flag(task):
    name, key, insts, lab, opts = task
    lay = SC.build_u(*insts[0])
    inner = S.to_circuit(lay)
    _, t2, rate = SC._screen_one((str(inner), lay["data"], lab))
    sc = dict(lab=list(lab), T2=t2, rate=rate, n=len(insts[0][0]))
    return SC.process_key((name, key, insts, sc, opts))


def write_report(state, succ_rows, path, out, logname):
    L = ["# Test 3, step 1: a fault-distance-3 double check on G6's data (search_g6.py)", "",
         f"Written automatically by `search_g6.py` at the end of the run ({state.get('finished')}).", "",
         "## Settings", "",
         f"- fold depth <= {state['args']['dmax']}, qubits <= {state['args']['nmax']} (tree), "
         f"never-measured ancillas <= {state['args']['umax']}, roots m in {state['args']['ms']}, flags <= 2",
         f"- data fixed to G6's positions {sorted(G6_POS)} with G6's code; flag search: exact 2-cover, then greedy",
         "", "## Space", "",
         f"- line patterns: {state.get('n_patterns')}",
         f"- forest placements with the data on G6's positions: {state.get('n_placements')}",
         f"- distinct (tree, labelling) groups: {state.get('n_groups')}",
         f"- sanity check, cs02's tree (placed on G6's data in step 0) found among them: **{state.get('g6_tree_found')}**",
         f"- screen: malignant T pairs of the bare trees: {state.get('screen_T2_hist')}",
         "", "## Result", "",
         f"- stop reason: {state.get('stop_reason')}",
         f"- groups flagged: {state.get('n_done')}, circuits evaluated: {state.get('n_evaluated')}",
         f"- **successes: {state.get('n_success')}**", ""]
    if succ_rows:
        L += ["| # | base | qubits | CX | max partners | flags | malignant T at 3 faults | T error per kept shot (p = 0.1 %, mfc 3) |",
              "|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(succ_rows):
            L.append(f"| {i} | {r.get('base')} | {r.get('n_qubits')} | {r.get('n_cx')} | {r.get('max_degree')} | "
                     f"`{r.get('flags')}` | {r.get('malignant_T_3')} | 1 in {int(r.get('ler_T_mfc3_one_in') or 0):,} |")
    else:
        best = state.get("best_non_success") or []
        L += ["No circuit reached fault distance 3 on G6's data under the rules.",
              f"Best placeable circuits (malignant T pairs at <= 2 faults): {[b['T2'] for b in best]}"]
    L += ["", "## Files", "",
          f"- `results/{out.name}/success*.{{inner,full}}.stim`: the successes (Willow coordinates = G6's)",
          f"- `results/{out.name}/best_*.stim`: best non-successes",
          f"- `results/{out.name}/candidates.csv`, `bases.csv`, `state.json`",
          f"- log: `logs/{logname}`", "",
          "Next (not run): splice a success into G6 in place of TICKs 31-56 and compare with G6 as run (stim)."]
    path.write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--dmax", type=int, default=5)
    ap.add_argument("--nmax", type=int, default=13)
    ap.add_argument("--umax", type=int, default=1)
    ap.add_argument("--ms", default="1,2")
    ap.add_argument("--hours", type=float, default=7.0)
    ap.add_argument("--screen-max-t2", type=int, default=14)
    ap.add_argument("--stop-per-base", type=int, default=2)
    ap.add_argument("--max-combos", type=int, default=40)
    ap.add_argument("--count-only", action="store_true")
    ap.add_argument("--out", default=str(RES))
    ap.add_argument("--report", default=str(HERE / "RESULTS_search.md"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log = lambda *a: print(f"[{time.time() - t0:8.1f} s]", *a, flush=True)
    state = dict(args=vars(args), started=time.ctime(), g6_positions=sorted(G6_POS), g6_lines=G6_LINES)
    pool = Pool(args.workers)
    ms = [int(x) for x in args.ms.split(",")]
    groups, stats = enumerate_g6(ms, args.dmax, args.nmax, args.umax, pool, log)
    found_g6 = any(frozenset(inst[0]) in CS02_TREES for v in groups.values() for inst in v)
    state.update(n_patterns=sum(len(g6_patterns(m, args.dmax)) for m in ms), space=stats,
                 n_placements=sum(len(v) for v in groups.values()), n_groups=len(groups),
                 g6_tree_found=found_g6)
    log(f"groups: {len(groups)}, placements: {state['n_placements']}, cs02's tree among them: {found_g6}")
    (out / "state.json").write_text(json.dumps(state, indent=1))
    if args.count_only:
        pool.close()
        return
    opts = dict(n1=40, k1=8, n2=16, stop_per_base=args.stop_per_base, max_t2=args.screen_max_t2,
                cover="both", max_combos=args.max_combos)
    keys = sorted(groups, key=lambda k: (len(groups[k][0][0]), k))
    todo = [(f"g6-{i:05d}", k[0], groups[k], k[1], opts) for i, k in enumerate(keys)]
    fh = (out / "candidates.csv").open("w", newline="")
    wr = csv.DictWriter(fh, fieldnames=SC.FIELDS, extrasaction="ignore")
    wr.writeheader()
    bh = (out / "bases.csv").open("w", newline="")
    bw = csv.DictWriter(bh, fieldnames=SC.BASE_FIELDS + ["screen_T2"], extrasaction="ignore")
    bw.writeheader()
    n_done = nid = n_succ = 0
    hist, best_global, succ_rows = Counter(), [], []
    stop_reason = "design space exhausted"
    with pool:
        for info, rows, succ, best, sc in pool.imap_unordered(screen_and_flag, todo, chunksize=1):
            n_done += 1
            hist[sc["T2"]] += 1
            info["screen_T2"] = sc["T2"]
            for k, row in enumerate(rows):
                row["id"] = nid + k
                row["key"] = info.get("key")
            for idx, inner, full, emb in succ:
                p = out / f"success{n_succ:02d}.inner.stim"
                p.write_text(inner)
                (out / f"success{n_succ:02d}.full.stim").write_text(full)
                rows[idx]["stim_file"] = str(p)
                succ_rows.append(rows[idx])
                log(f"SUCCESS #{n_succ} base {info['base']} flags {rows[idx]['flags']} "
                    f"T3={rows[idx].get('malignant_T_3')} 1 in {rows[idx].get('ler_T_mfc3_one_in')}")
                n_succ += 1
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
            if not info.get("screened_out"):
                log(f"base {info['base']} T2={info.get('base_T2')} eval={len(rows)} L1={info.get('best_level1_T2')} "
                    f"L2={info.get('best_level2_T2')} succ={len(succ)}" + (f" ERROR {info['error'][:300]}" if info.get("error") else ""))
            if n_done % 50 == 0:
                log(f"{n_done}/{len(todo)} groups, {nid} circuits, {n_succ} successes")
                state.update(n_done=n_done, n_evaluated=nid, n_success=n_succ, elapsed_s=time.time() - t0)
                (out / "state.json").write_text(json.dumps(state, indent=1))
            if n_succ >= STOP_SUCCESSES:
                stop_reason = f"{STOP_SUCCESSES} successes"
                pool.terminate()
                break
            if time.time() - t0 > args.hours * 3600:
                stop_reason = f"time limit {args.hours} h"
                pool.terminate()
                break
    fh.close()
    bh.close()
    for k, (t2, rate, rid, b, inner, full) in enumerate(best_global):
        (out / f"best_{k}.inner.stim").write_text(inner)
        (out / f"best_{k}.full.stim").write_text(full)
    state.update(n_done=n_done, n_queued=len(todo), n_evaluated=nid, n_success=n_succ, stop_reason=stop_reason,
                 screen_T2_hist={str(k): v for k, v in sorted(hist.items())},
                 best_non_success=[dict(T2=t2, rate=rate, id=rid, base=b) for t2, rate, rid, b, _, _ in best_global],
                 finished=time.strftime("%b %d, %I:%M %p KST", time.localtime(time.time() + 9 * 3600 + time.timezone)), elapsed_s=time.time() - t0)
    (out / "state.json").write_text(json.dumps(state, indent=1, default=str))
    write_report(state, succ_rows, Path(args.report), out, Path(args.report).stem.replace("RESULTS_search", "search_g6") + ".log")
    log("done:", stop_reason, f"groups {n_done}, evaluated {nid}, successes {n_succ}")


if __name__ == "__main__":
    main()
