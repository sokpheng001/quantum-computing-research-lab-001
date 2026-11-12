"""Test 5, Part B, step B2: randomised search for a nearest-neighbour d = 5 double check with
fault distance 4 (then 5) with real T, on Willow, with our method (d5_method.py).

Per worker, repeatedly:
 1. a random fold tree (d5_method.random_tree: ancilla root alone on its readout line, 19 data);
 2. code labelling by local search (swap moves) minimising cliffordea's exact malignant T counts
    (first at <= 2 faults, then at 3 faults);
 3. if fault distance >= 3: greedy nearest-neighbour flags. Each round: the malignant 3-fault T
    configurations of the current circuit; every free grid point next to >= 2 qubits of one grid
    colour (each with <= 3 partners, not on the root's line); the flag (Z or X, on a subset of those
    neighbours) detecting most of them (exact GF(2) system, b2_flags_d5); build it and keep the
    flag that lowers the exact malignant count most (no new malignant configurations at <= 2
    faults). Up to --max-flags flags;
 4. success = 0 malignant T configurations at <= 3 faults (fault distance >= 4), every gate
    nearest-neighbour, <= 4 partners, strict readout rule, fits on Willow (constraints.check_circuit
    on a Willow placement).
Results: results/b2_search/ (one JSON line per tree, successes as stim files), RESULTS_B2_search.md.

    .venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b2_search_d5.py" \
        --workers 12 --hours 8
"""
import argparse
import json
import random
import sys
import time
import traceback
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b2_flags_d5 as F  # noqa: E402
import d5_method as M  # noqa: E402
from b2_reembed_d5 import SYMS, willow_fit  # noqa: E402

from nnflags import constraints as C  # noqa: E402
from nnflags import zzflags as Z  # noqa: E402
from nnflags.verify import verify  # noqa: E402

OUT = HERE / "results" / "b2_search"
log, kst = F.log, F.kst


def flag_sites(d, root_line):
    used = {d.emb[q]: q for q in d.qubits}
    deg = {q: len(d.adj.get(q, ())) for q in d.qubits}
    sites = {}
    for p in used:
        for w in M.nbrs(p):
            if w in used or M.line(w) == root_line:
                continue
            ctrl = tuple(sorted(used[x] for x in M.nbrs(w) if x in used and deg[used[x]] <= 3))
            if len(ctrl) >= 2:
                sites[w] = ctrl
    return sites


def exact(d, inner, max_faults):
    r = verify(d.full(inner), inner, max_fault_count=max_faults, states=("T",))
    m = r["T"]
    return [m[k]["malignant"] for k in sorted(m)], r["error_rate_per_kept_shot"]["T"]


def greedy_flags(d, root_line, max_flags, rng, max_options=40):
    """Returns (design with flags, list of (flag, site), malignant counts)."""
    placed = []
    mal, rate = exact(d, d.inner, 3)
    for _ in range(max_flags):
        if sum(mal) == 0:
            break
        cfgs, events = F.malignant_configs(d, d.inner, d.full(), 3)
        sites = flag_sites(d, root_line)
        if not sites or not cfgs:
            break
        controls = sorted({q for qs in sites.values() for q in qs})
        pa = Z.ProbeAnalysis(d, controls=controls)
        cov = F.ConfigCoverage(pa, cfgs, events)
        opts = F.site_options(cov, sites, len(cfgs))
        opts.sort(key=lambda o: -bin(o[3]).count("1"))
        best = None
        for (w, b, qs, msk, cols) in opts[:max_options]:
            for fl in Z.concrete_flags(cov, cols, [i for i in range(len(cfgs)) if msk >> i & 1], limit=2):
                try:
                    inner, fq = Z.build_flagged(d, [fl])
                except ValueError:
                    continue
                m2, r2 = exact(d, inner, 3)
                if m2[0] or m2[1] or m2[2]:
                    continue
                key = (m2[3], len(fl.probes), r2)
                if best is None or key < best[0]:
                    best = (key, inner, fq, fl, w, m2, r2)
            if best and best[0][0] == 0:
                break
        if best is None or best[0][0] >= mal[3]:
            break
        _, inner, fq, fl, w, m2, r2 = best
        emb = dict(d.emb)
        emb[fq[0]] = w
        d = Z.Design(d.name, inner, d.full_args, emb)
        placed.append((str(fl), w))
        mal, rate = m2, r2
    return d, placed, mal, rate


def one_tree(seed, opts):
    rng = random.Random(seed)
    t0 = time.time()
    base = M.random_tree(rng, max_anc=opts["max_anc"], max_depth=opts["max_depth"])
    if base is None:
        return dict(seed=seed, stage="no tree")
    lab, s, used = M.labelling_search(base, rng, evals=opts["evals"])
    row = dict(seed=seed, qubits=len(base.parent), depth=M.S.depth_of(base.parent, (M.ROOT0,)),
               bare_malignant_le2=s[0], bare_malignant_3=s[1], bare_rate=s[2], label_evals=used)
    if s[0] > 0:
        row.update(stage="bare FD < 3", seconds=round(time.time() - t0, 1))
        return row
    inner, full, lay = M.circuits(base, lab)
    emb = dict(lay["emb"])
    d = Z.Design(f"t{seed}", inner, (tuple(tuple(lay['data'][lab[j]] for j in p) for p in M.CODE[0]),
                                     tuple(lay["data"][lab[j]] for j in M.CODE[1]),
                                     tuple(lay["data"][lab[j]] for j in M.CODE[2]), tuple(lay["data"])), emb)
    root_line = M.line(emb[lay["roots"][0]])
    d2, placed, mal, rate = greedy_flags(d, root_line, opts["max_flags"], rng)
    row.update(flags=placed, malignant=mal, rate=rate, n_flags=len(placed), qubits_total=d2.nq)
    fd4 = sum(mal) == 0
    if fd4:
        fit = willow_fit([d2.emb[q] for q in sorted(d2.emb)])
        if fit is None:
            row["stage"] = "FD>=4, does not fit Willow"
        else:
            si, (dr, dc) = fit
            g = SYMS[si]
            wemb = {q: (g(*p)[0] + dr, g(*p)[1] + dc) for q, p in d2.emb.items()}
            v = C.check_circuit(d2.inner, wemb, data_qubits=d2.data)
            row["violations"] = dict(C.summarize(v))
            row["stage"] = "SUCCESS" if not v else "FD>=4, Willow violations"
            if not v:
                m4, r4 = exact(d2, d2.inner, 4)
                row.update(malignant_4=m4[4], rate_mfc4=r4, ticks=d2.inner.num_ticks,
                           max_partners=max(map(len, C.partners(d2.inner).values())))
                head = "\n".join(f"QUBIT_COORDS({wemb[q][0]}, {wemb[q][1]}) {q}" for q in sorted(wemb))
                (OUT / f"success_seed{seed}.inner.stim").write_text(head + "\n" + str(d2.inner))
                (OUT / f"success_seed{seed}.full.stim").write_text(str(d2.full()))
    else:
        row["stage"] = f"FD 3, {mal[3]} malignant 3-fault left"
    row["seconds"] = round(time.time() - t0, 1)
    return row


def worker(args):
    seed, opts = args
    try:
        return one_tree(seed, opts)
    except Exception as e:  # keep the search alive; record the error
        return dict(seed=seed, stage="error", error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-800:])


def report(rows, t0, opts):
    from collections import Counter
    st = Counter(r["stage"].split(",")[0] if r["stage"].startswith("FD 3") else r["stage"] for r in rows)
    succ = [r for r in rows if r["stage"] == "SUCCESS"]
    fd3 = [r for r in rows if "malignant" in r]
    L = [f"# Test 5, B2: randomised d = 5 search, our method (written {kst()})", "",
         f"Settings: {json.dumps(opts)}. Trees tried: **{len(rows)}** in {(time.time() - t0) / 3600:.1f} h.", "",
         "| outcome | trees |", "|---|---|"] + [f"| {k} | {v} |" for k, v in st.most_common()]
    if fd3:
        bestleft = min(fd3, key=lambda r: (sum(r["malignant"]), r["rate"]))
        L += ["", f"- fewest malignant 3-fault T configurations left after flags: {sum(bestleft['malignant'])} "
              f"(seed {bestleft['seed']}, {bestleft['n_flags']} flags, {bestleft['qubits_total']} qubits)"]
    if succ:
        L += ["", "## Successes: fault distance >= 4 with real T, nearest-neighbour, strict readout rule, on Willow", "",
              "| seed | qubits | flags | TICKs | max partners | malignant at 4 faults | T error per kept shot, p = 0.1 % (to 4 faults) |",
              "|---|---|---|---|---|---|---|"]
        for r in sorted(succ, key=lambda r: r["rate_mfc4"]):
            L.append(f"| {r['seed']} | {r['qubits_total']} | {r['n_flags']} | {r['ticks']} | {r['max_partners']} | "
                     f"{r['malignant_4']} | 1 in {1 / r['rate_mfc4']:,.0f} |")
        L += ["", "Reference (B0, same counting): Gidney d5a19 (FD 3) 1 in 974,523,423; Chan d5a19f3 (FD 4, not "
              "nearest-neighbour) 1 in 3,487,408,846."]
    (HERE / "RESULTS_B2_search.md").write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--hours", type=float, default=8)
    ap.add_argument("--max-anc", type=int, default=14)
    ap.add_argument("--max-depth", type=int, default=8)
    ap.add_argument("--evals", type=int, default=120)
    ap.add_argument("--max-flags", type=int, default=6)
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("--stop-after", type=int, default=20, help="stop after this many successes")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    opts = dict(max_anc=a.max_anc, max_depth=a.max_depth, evals=a.evals, max_flags=a.max_flags)
    t0 = time.time()
    deadline = t0 + a.hours * 3600
    rows = []
    log(f"start: {opts}, {a.workers} workers, {a.hours} h")
    seeds = iter(range(a.seed0, a.seed0 + 10 ** 7))
    with Pool(a.workers) as pool, open(OUT / "trees.jsonl", "a") as fh:
        pending = [pool.apply_async(worker, ((next(seeds), opts),)) for _ in range(a.workers * 2)]
        while pending:
            r = pending.pop(0).get()
            rows.append(r)
            fh.write(json.dumps(r, default=str) + "\n")
            fh.flush()
            if r["stage"] == "SUCCESS":
                log(f"SUCCESS seed {r['seed']}: {r['qubits_total']} qubits, {r['n_flags']} flags, "
                    f"malignant at 4: {r['malignant_4']}, rate 1 in {1 / r['rate_mfc4']:,.0f}")
            if len(rows) % 24 == 0:
                report(rows, t0, opts)
                log(f"{len(rows)} trees; successes {sum(x['stage'] == 'SUCCESS' for x in rows)}")
            n_succ = sum(x["stage"] == "SUCCESS" for x in rows)
            if time.time() < deadline and n_succ < a.stop_after:
                pending.append(pool.apply_async(worker, ((next(seeds), opts),)))
    report(rows, t0, opts)
    log("done")


if __name__ == "__main__":
    main()
