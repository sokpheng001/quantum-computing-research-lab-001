"""Test 5, Part B, step B2 (stage 2): re-lay Gidney's d = 5 fold tree on the grid so that
nearest-neighbour flags fit, under the readout-line rule, on Willow.

Gidney's d = 5 double check (cliffordea d5a19) is a spanning TREE of CX gates (38 qubits, 37
edges), so its circuit (gates, timing, code labelling) can stay exactly as it is while its qubits
are placed differently on the square grid: every tree edge on a grid edge keeps every gate
nearest-neighbour. Stage 1 (b2_flags_d5.py) showed Gidney's own layout leaves only 4 flag sites.

Steps:
 1. geometry-free flag options: for every target configuration (malignant T configurations with
    target-1 faults) every control set (2 qubits of one grid colour, each with <= 3 tree partners)
    and basis whose flag detects it (exact GF(2) system, as in b2_flags_d5.py);
 2. flag covers: sets of <= --max-flags (control set, basis) detecting every target;
 3. for each cover, a randomised depth-first embedding of the tree on the grid (root fixed at the
    origin) such that
      - every flag's controls have a common FREE grid neighbour (reserved for the flag),
      - readout lines (line = r + c): the mid-check root measurement (MRX) is alone on its line
        (every qubit is live at the mid check), and no flag sits on the root line,
      - the whole layout fits on the 105-qubit Willow grid (translation + the 4 line-preserving
        symmetries);
 4. build the flagged circuit (zzflags.build_flagged), check it with constraints.check_circuit on
    Willow (strict readout rule, data measured at the end), verify fault distance with real T.

    .venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b2_reembed_d5.py" \
        [--target 4] [--max-flags 4] [--seconds 3600]
    -> results/b2_reembed_fd<t>.json, results/b2_reembed_fd<t>.{inner,full}.stim, RESULTS_B2_reembed_fd<t>.md
"""
import argparse
import itertools
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b2_flags_d5 as F  # noqa: E402  (sets sys.path / cwd to google-quantum)

from nnflags import constraints as C  # noqa: E402
from nnflags import zzflags as Z  # noqa: E402
from nnflags import search_zzflags as SZ  # noqa: E402
from nnflags.verify import verify  # noqa: E402
from nnflags.willow import WILLOW  # noqa: E402

RES = HERE / "results"
SYMS = (lambda r, c: (r, c), lambda r, c: (c, r), lambda r, c: (-r, -c), lambda r, c: (-c, -r))
log, kst = F.log, F.kst


def line(p):
    return p[0] + p[1]


def willow_fit(points):
    """(symmetry index, offset) placing all points on Willow, or None."""
    for si, f in enumerate(SYMS):
        mp = [f(*p) for p in points]
        p0 = mp[0]
        for w in sorted(WILLOW):
            dr, dc = w[0] - p0[0], w[1] - p0[1]
            if all((r + dr, c + dc) in WILLOW for r, c in mp):
                return si, (dr, dc)
    return None


# ---- 1-2: geometry-free flag options and covers -------------------------------------------------

def free_options(d, cov, n, max_ctrl=2):
    deg = {q: len(d.adj.get(q, ())) for q in d.qubits}
    ok = [q for q in d.qubits if deg[q] <= 3]
    out = []
    for size in range(2, max_ctrl + 1):
        for qs in itertools.combinations(ok, size):
            if len({d.colour[q] for q in qs}) != 1:
                continue
            for b in ("Z", "X"):
                cols = [k for k, p in enumerate(cov.pa.probes) if p.q in qs and p.basis == b]
                if not cols:
                    continue
                masks = Z.coverable_subsets(cov, cols, n) if n <= 12 else F._greedy(cov, cols, n)
                for m in (SZ.maximal(masks) if n <= 12 else masks):
                    out.append(dict(qs=qs, basis=b, mask=m, cols=cols))
    return out


def tree_dist(d, a, b):
    seen, fr, k = {a}, [a], 0
    while fr:
        if b in fr:
            return k
        nxt = []
        for v in fr:
            for w in d.adj.get(v, ()):
                if w not in seen:
                    seen.add(w)
                    nxt.append(w)
        fr, k = nxt, k + 1
    return 99


def covers(options, n, max_flags, d, limit=200):
    full = (1 << n) - 1
    # prefer control sets close in the tree (easier to embed with a free common neighbour)
    opts = sorted(options, key=lambda o: (-bin(o["mask"]).count("1"), tree_dist(d, *o["qs"][:2])))
    opts = opts[:400]
    out = []
    for k in range(1, max_flags + 1):
        for combo in itertools.combinations(range(len(opts)), k):
            acc = 0
            for i in combo:
                acc |= opts[i]["mask"]
            if acc != full:
                continue
            ctrl = [opts[i]["qs"] for i in combo]
            if len({q for qs in ctrl for q in qs}) < sum(len(qs) for qs in ctrl) and False:
                continue
            out.append([opts[i] for i in combo])
            if len(out) >= limit:
                return out
        if out:
            return out
    return out


# ---- 3: randomised tree embedding -----------------------------------------------------------------

def nbrs(p):
    r, c = p
    return ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))


def embed(d, root, flag_ctrls, rng, deadline, node_limit=200000):
    """Randomised DFS. Returns (emb, flag sites) or None."""
    order, parent = [root], {root: None}
    for v in order:
        for w in sorted(d.adj.get(v, ())):
            if w not in parent:
                parent[w] = v
                order.append(w)
    pos, used = {}, {}
    reserved = {}            # site -> flag index
    flag_site = [None] * len(flag_ctrls)
    need = defaultdict(list)  # qubit -> flag indices that become checkable when it is placed
    for fi, qs in enumerate(flag_ctrls):
        last = max(qs, key=order.index)
        need[last].append(fi)
    nodes = [0]

    def ok_flags(v):
        """Reserve sites for the flags completed by placing v (in place), or False."""
        done = []
        for fi in need[v]:
            qs = flag_ctrls[fi]
            cand = set(nbrs(pos[qs[0]]))
            for q in qs[1:]:
                cand &= set(nbrs(pos[q]))
            cand = [s for s in cand if s not in used and s not in reserved and line(s) != 0]
            if not cand:
                for f2 in done:
                    del reserved[flag_site[f2]]
                    flag_site[f2] = None
                return False
            s = rng.choice(sorted(cand))
            reserved[s] = fi
            flag_site[fi] = s
            done.append(fi)
        return done

    def rec(i):
        nodes[0] += 1
        if nodes[0] > node_limit or time.time() > deadline:
            return False
        if i == len(order):
            return True
        v = order[i]
        if v == root:
            cands = [(0, 0)]
        else:
            cands = [w for w in nbrs(pos[parent[v]]) if w not in used and w not in reserved and line(w) != 0]
            rng.shuffle(cands)
        for w in cands:
            pos[v] = w
            used[w] = v
            done = ok_flags(v)
            if done is not False:
                # cheap Willow-size prune: bounding box of a 105-qubit diamond
                rs = [p[0] for p in used] + [p[0] for p in reserved]
                cs = [p[1] for p in used] + [p[1] for p in reserved]
                ls = [line(p) for p in used] + [line(p) for p in reserved]
                ds = [p[0] - p[1] for p in used] + [p[0] - p[1] for p in reserved]
                if max(ls) - min(ls) <= 20 and max(ds) - min(ds) <= 20 and max(rs) - min(rs) <= 14 and max(cs) - min(cs) <= 14:
                    if rec(i + 1):
                        return True
                for fi in done:
                    del reserved[flag_site[fi]]
                    flag_site[fi] = None
            del used[w]
            del pos[v]
        return False

    if rec(0):
        return dict(pos), list(flag_site)
    return None


# ---- 4: build and check ---------------------------------------------------------------------------------

def try_cover(d, cov, cover, root, target, rng, deadline, attempts):
    n = len(cov.pairs)
    pools = []
    for o in cover:
        fls = Z.concrete_flags(cov, o["cols"], [i for i in range(n) if o["mask"] >> i & 1], limit=3)
        pools.append([(o, fl) for fl in fls])
    best = None
    for choice in itertools.islice(itertools.product(*pools), 12):
        flags = [fl for _, fl in choice]
        try:
            inner, fq = Z.build_flagged(d, flags)
        except ValueError:
            continue
        full = d.full(inner)
        r = verify(full, inner, max_fault_count=target - 1, states=("T",))
        mal = {k: r["T"][k]["malignant"] for k in r["T"]}
        if any(mal.values()):
            if best is None:
                best = dict(flags=[str(f) for f in flags], malignant_T=mal, stage="flags do not reach the target")
            continue
        ctrls = [tuple(sorted({p.q for p in fl.probes})) for fl in flags]
        for att in range(attempts):
            if time.time() > deadline:
                break
            e = embed(d, root, ctrls, rng, min(deadline, time.time() + 20))
            if e is None:
                continue
            pos, sites = e
            emb = dict(pos)
            for f, s in zip(fq, sites):
                emb[f] = s
            fit = willow_fit([emb[q] for q in sorted(emb)])
            if fit is None:
                continue
            si, (dr, dc) = fit
            g = SYMS[si]
            wemb = {q: (g(*p)[0] + dr, g(*p)[1] + dc) for q, p in emb.items()}
            data = tuple(sorted(d.data))
            v = C.check_circuit(inner, wemb, data_qubits=data)
            res = dict(flags=[str(f) for f in flags], malignant_T=mal, violations=dict(C.summarize(v)),
                       qubits=inner.num_qubits, ticks=inner.num_ticks,
                       max_partners=max(map(len, C.partners(inner).values())),
                       rate_T_p01=r["error_rate_per_kept_shot"]["T"], attempt=att,
                       inner=str(inner), full=str(full), emb=wemb, stage="embedded")
            if not v:
                res["stage"] = "success"
                return res
            if best is None or best.get("stage") != "embedded" or sum(res["violations"].values()) < sum(best["violations"].values()):
                best = res
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=4)
    ap.add_argument("--max-flags", type=int, default=4)
    ap.add_argument("--seconds", type=int, default=3600)
    ap.add_argument("--attempts", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    deadline = t0 + a.seconds
    rng = random.Random(a.seed)
    d, _ = F.design_d5()
    root = d.mid_measured[0]
    cfgs, events = F.malignant_configs(d, d.inner, d.full(), a.target - 1)
    log(f"target FD {a.target}: {len(cfgs)} malignant {a.target - 1}-fault configurations; root q{root}")
    pa = Z.ProbeAnalysis(d)
    cov = F.ConfigCoverage(pa, cfgs, events)
    opts = free_options(d, cov, len(cfgs))
    coverable = sorted({i for o in opts for i in range(len(cfgs)) if o["mask"] >> i & 1})
    log(f"geometry-free 2-control flag options: {len(opts)}; coverable targets {len(coverable)} / {len(cfgs)}")
    out = dict(target=a.target, n_targets=len(cfgs), n_options=len(opts), coverable=len(coverable), tried=[])
    result = None
    if len(coverable) == len(cfgs):
        cs = covers(opts, len(cfgs), a.max_flags, d)
        log(f"covers with <= {a.max_flags} flags: {len(cs)}")
        for ci, cover in enumerate(cs):
            if time.time() > deadline:
                break
            res = try_cover(d, cov, cover, root, a.target, rng, deadline, a.attempts)
            desc = [f"{o['basis']}{o['qs']}" for o in cover]
            out["tried"].append(dict(cover=desc, stage=res and res["stage"],
                                     violations=res and res.get("violations")))
            log(f"cover {ci} {desc}: {res and res['stage']} {res and res.get('violations')}")
            if res and (result is None or res["stage"] == "success" or
                        (result["stage"] != "embedded" and res["stage"] == "embedded")):
                result = res
            if res and res["stage"] == "success":
                break
    out["result"] = {k: v for k, v in (result or {}).items() if k not in ("inner", "full", "emb")}
    out["runtime_s"] = round(time.time() - t0, 1)
    if result and "inner" in result:
        emb = result["emb"]
        head = "\n".join(f"QUBIT_COORDS({emb[q][0]}, {emb[q][1]}) {q}" for q in sorted(emb))
        (RES / f"b2_reembed_fd{a.target}.inner.stim").write_text(head + "\n" + result["inner"])
        (RES / f"b2_reembed_fd{a.target}.full.stim").write_text(result["full"])
    (RES / f"b2_reembed_fd{a.target}.json").write_text(json.dumps(out, indent=1, default=str))
    r = out["result"]
    L = [f"# Test 5, B2 (stage 2): Gidney's d = 5 tree re-laid on Willow with nearest-neighbour flags, "
         f"target fault distance {a.target} (written {kst()})", "",
         f"- malignant {a.target - 1}-fault T configurations of Gidney's circuit: **{len(cfgs)}**",
         f"- detectable by some 2-control flag (geometry-free): **{len(coverable)} / {len(cfgs)}**",
         f"- covers tried: {len(out['tried'])}; run time {out['runtime_s']:,} s",
         f"- **outcome: {r.get('stage', 'no cover')}**", ""]
    if r:
        L += [f"- flags: `{'; '.join(r.get('flags', []))}`",
              f"- malignant T configurations by fault count (after flags): {r.get('malignant_T')}",
              f"- Willow check (nearest-neighbour, <= 4 partners, strict readout rule): {r.get('violations') or 'no violations'}",
              f"- qubits {r.get('qubits')}, TICKs {r.get('ticks')}, max partners {r.get('max_partners')}"]
        if r.get("rate_T_p01"):
            L.append(f"- T error per kept shot at uniform p = 0.1 % (counted up to {a.target - 1} faults): 1 in {1 / r['rate_T_p01']:,.0f}")
    L += ["", "Readout rule here: data measured at the end (strict rule, as in test 1). The continuing-data "
          "rule is a later step: Gidney's root is a data qubit measured mid-check, which that rule forbids.", ""]
    (HERE / f"RESULTS_B2_reembed_fd{a.target}.md").write_text("\n".join(L))
    log(f"done: {r.get('stage')} in {out['runtime_s']} s")


if __name__ == "__main__":
    main()
