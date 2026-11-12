"""Method 4 (TASKS_nonuniform.md): non-uniform (class) depth-7 schedules.  Run from ours/:
    ../../../venv/bin/python nu.py --stage reg --n 90          regression: d1(S) at CONFIRM level, both fault types
    ../../../venv/bin/python nu.py --stage part0               control on [[72]] (0.1-0.4)
Every stage writes ../results_nonuniform/<n>/<stage>.json when done and is skipped on rerun; work units are
checkpointed row by row.  Exit code 3 = a PASS condition failed (driver stops and reports).

Distance search: ours/bravyi_d1.py (port of bravyi_ref/circuit_distance.py, validated identical to the
reference), unchanged: osd_cs order 20, max_iter 10000, min-sum, ms_scaling_factor 0, random logical
combinations.  SCREEN = 2,000 trials, CONFIRM = 100,000 trials per fault type.
"""
import argparse, csv, json, os, sys, time, datetime, collections, random, itertools, warnings
import multiprocessing as mp
import numpy as np
warnings.filterwarnings('ignore')
from bravyi_d1 import to_bravyi, decoding_matrices, d1_search, describe_set, CODES
from classsched import NBRef, homomorphisms, tables, uniform_tables, noiseless_ok, shift_maps, class_of
from bb_code import BRAVYI, reverse_schedule

ROOT = os.environ.get('NU_RES', '../results_nonuniform')
SCREEN, CONFIRM, CHUNK = 2000, 100000, 500
NPROC = int(os.environ.get('NU_NPROC', 6))
BRAVYI_D = {72: 6, 90: 8, 108: 8, 144: 10}
M3 = '../../bb-code-reordering-cnot-running/results_method3'       # Method 3 results (schedule ids, d1 tables)
def R(n, f=''): return os.path.join(ROOT, str(n), f)
def say(*a): print(*a, flush=True)
def stop(msg): say(f'== STOP: {msg}'); sys.exit(3)
def jdump(o, f): json.dump(o, open(f, 'w'), indent=1, default=str)
def jload(f): return json.load(open(f))
def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %I:%M %p KST')


# ------------------------------------------------------------------ schedules and circuit specs
_T = {}
def _make_schedules(n, f):
    """Enumerate the valid depth-7 uniform schedules exactly as the uniform work does (same order -> same ids)."""
    from bb_code import BBCode, LABELS
    code = BBCode(n); xq, zinc = {}, {}
    for lab in LABELS:
        pr = code.x_layer(lab); xq[lab] = {pr[2 * i]: pr[2 * i + 1] for i in range(code.half)}
    for lab in LABELS:
        pr = code.z_layer(lab)
        for i in range(code.half): zinc.setdefault(pr[2 * i], []).append((pr[2 * i + 1], lab))
    a0 = int(code.X[0])
    def ok(xo, zo, zf):
        xr = {l_: i + (2 if zf else 1) for i, l_ in enumerate(xo)}; zr = {l_: i + (1 if zf else 2) for i, l_ in enumerate(zo)}; fl = {}
        for l_ in LABELS:
            d = xq[l_][a0]; tx = xr[l_]
            for b_, lz in zinc[d]:
                if zr[lz] == tx: return False
                if zr[lz] < tx: fl[b_] = fl.get(b_, 0) ^ 1
        return not any(fl.values())
    perms = list(itertools.permutations(LABELS))
    V = [(list(xo), list(zo), zf) for zf in (True, False) for xo in perms for zo in perms if ok(xo, zo, zf)]
    tup = lambda s_: (tuple(s_[0]), tuple(s_[1]), bool(s_[2])); idx = {tup(s_): i for i, s_ in enumerate(V)}
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, 'w') as g:
        for i, s_ in enumerate(V):
            g.write(json.dumps(dict(id=i, x=s_[0], z=s_[1], z_first=s_[2], reverse_id=idx.get(tup(reverse_schedule(s_))))) + '\n')

def sched_table(n):
    if n not in _T:
        f = os.path.join(M3, str(n), 'schedules.jsonl')
        if not os.path.exists(f):                       # e.g. [[144]]: not run by the uniform work on this server
            f = R(n, 'schedules.jsonl')
            if not os.path.exists(f): _make_schedules(n, f)
        rows = [json.loads(l) for l in open(f)]
        _T[n] = ({r['id']: (r['x'], r['z'], r['z_first']) for r in rows}, {r['id']: r['reverse_id'] for r in rows})
    return _T[n]

def spec_tables(n, spec):
    """'u212' = uniform schedule 212; 'c3:1,0:212,40,40' = k=3 classes by hom (1,0), class orders 212,40,40."""
    T, _ = sched_table(n)
    if spec.startswith('u'): return uniform_tables(n, T[int(spec[1:])])
    k, hom, orders = spec[1:].split(':'); k = int(k); hom = tuple(map(int, hom.split(','))); orders = list(map(int, orders.split(',')))
    return tables(n, hom, k, [T[o] for o in orders])


# ------------------------------------------------------------------ distance search work units
_MC = {}
def matrices(n, spec, kind):
    key = (n, spec, kind)
    if key not in _MC:
        if len(_MC) > 60: _MC.clear()
        code = NBRef(n); tX, tZ = spec_tables(n, spec)
        _MC[key] = (code, decoding_matrices(code, tX, tZ, kind))
    return _MC[key]

def _job(a):
    n, spec, kind, chunk, seed, trials = a
    code, M = matrices(n, spec, kind)
    t = time.time(); r = d1_search(M, trials, seed=seed)
    sets = [dict(weight=w, cols=list(map(int, c)), faults=describe_set(M, c, code)) for w, ss in r['sets'].items() for c in sorted(ss)]
    return a, r, sets, time.time() - t

F = ['tag', 'spec', 'kind', 'chunk', 'seed', 'trials', 'min', 'hist', 'invalid', 'seconds']
def run_jobs(n, tag, jobs, nproc=None):
    """jobs: (spec, kind, chunk, seed, trials); rows already in search.csv for this tag are skipped."""
    f, g = R(n, 'search.csv'), R(n, 'sets.jsonl'); done = set()
    if os.path.exists(f):
        for r in csv.DictReader(open(f)):
            if r['tag'] == tag: done.add((r['spec'], r['kind'], int(r['chunk'])))
    todo = [(n,) + j for j in jobs if (j[0], j[1], j[2]) not in done]
    if not todo: return
    new = not os.path.exists(f); t0 = time.time()
    with mp.get_context('fork').Pool(nproc or NPROC) as pool, open(f, 'a', newline='') as fc, open(g, 'a') as fs:
        w = csv.DictWriter(fc, fieldnames=F)
        if new: w.writeheader()
        for i, (a, r, sets, sec) in enumerate(pool.imap_unordered(_job, todo, chunksize=1)):
            _, spec, kind, chunk, seed, trials = a
            for s in sets: fs.write(json.dumps(dict(tag=tag, spec=spec, kind=kind, chunk=chunk, **s)) + '\n')
            fs.flush()
            w.writerow(dict(tag=tag, spec=spec, kind=kind, chunk=chunk, seed=seed, trials=trials, min=r['min'], hist=json.dumps(r['hist']),
                            invalid=r['invalid'], seconds=round(sec, 1))); fc.flush()
            if (i + 1) % 20 == 0 or i + 1 == len(todo):
                el = time.time() - t0; say(f'    [{tag}] {i+1}/{len(todo)} units, {el/3600:.2f} h, ETA {el/(i+1)*(len(todo)-i-1)/3600:.1f} h')

def mins(n, tag):
    out = {}
    f = R(n, 'search.csv')
    if not os.path.exists(f): return out
    for r in csv.DictReader(open(f)):
        if r['tag'] != tag or r['min'] == '': continue
        k = (r['spec'], r['kind']); v = out.setdefault(k, [10**9, 0]); v[0] = min(v[0], int(r['min'])); v[1] += int(r['trials'])
    return out

def search(n, tag, specs, trials, seed0=0):
    nch = trials // CHUNK
    run_jobs(n, tag, [(s, k, c, seed0 + 100000 * c + 17 * j + (k == 'Z'), CHUNK) for c in range(nch) for j, s in enumerate(specs) for k in 'XZ'])
    return mins(n, tag)


# ------------------------------------------------------------------ stage: regression
def reg(n, a):
    T, rev = sched_table(n); S = [i for i, v in T.items() if (v[0], v[1], v[2]) == (BRAVYI[0], BRAVYI[1], BRAVYI[2])][0]
    sX, sZ = to_bravyi(T[S])
    assert sX == ['idle', 1, 4, 3, 5, 0, 2] and sZ == [3, 5, 0, 1, 2, 4, 'idle']
    say(f'  [[{n}]] regression: d1(S = #{S}) with the validated search (ours/bravyi_d1.py), CONFIRM = {CONFIRM} trials per fault type, {NPROC} workers')
    m = search(n, 'reg', [f'u{S}'], CONFIRM, seed0=1)
    dX, dZ = m[(f'u{S}', 'X')], m[(f'u{S}', 'Z')]
    res = dict(n=n, S=S, d1_X=dX, d1_Z=dZ, target=BRAVYI_D[n], PASS=(dX[0] == BRAVYI_D[n] and dZ[0] == BRAVYI_D[n]), date=now())
    jdump(res, R(n, 'reg.json'))
    say(f'  regression [[{n}]]: d1(S) X-type {dX[0]} ({dX[1]} trials), Z-type {dZ[0]} ({dZ[1]} trials); Bravyi {BRAVYI_D[n]} -> {"PASS" if res["PASS"] else "FAIL"}')
    if not res['PASS']: stop(f'[[{n}]] regression failed: d1(S) X {dX[0]}, Z {dZ[0]} vs {BRAVYI_D[n]}')


# ------------------------------------------------------------------ S's minimum-weight families and the exact screen (B4)
def fkey(info):
    return (info[0], tuple(info[1]), info[2], info[3], tuple(info[4]) if len(info) > 4 else None)

def tkey(k, mp):
    return (k[0], tuple(int(mp[q]) for q in k[1]), k[2], k[3], tuple(int(mp[q]) for q in k[4]) if k[4] is not None else None)

def s_sets(n, kind, S, weight):
    """Distinct minimum-weight sets of S from the regression run -> list of sets, each a list of columns, each
    column = list of physical fault keys (every representative of that DEM column)."""
    code, M = matrices(n, f'u{S}', kind); out = set()
    for line in open(R(n, 'sets.jsonl')):
        r = json.loads(line)
        if r['tag'] == 'reg' and r['kind'] == kind and r['weight'] == weight: out.add(tuple(r['cols']))
    return [[[fkey(M['fault_info'][f]) for f in M['faults'][j]] for j in cols] for cols in sorted(out)]

def families(n, sets):
    """Group sets into torus-translation families; return one representative per family + member count."""
    maps = [mp for _, mp in shift_maps(NBRef(n))]
    canon = lambda st, mp: tuple(sorted(tuple(sorted(tkey(k, mp) for k in col)) for col in st))
    fam = collections.OrderedDict()
    for st in sets:
        c = min(canon(st, mp) for mp in maps)
        fam.setdefault(c, []).append(st)
    return [dict(rep=v[0], members=len(v)) for v in fam.values()]

def copies(n, rep):
    """All distinct translated copies of a set (one per torus shift, duplicates removed)."""
    out, seen = [], set()
    for g, mp in shift_maps(NBRef(n)):
        st = [[tkey(k, mp) for k in col] for col in rep]
        c = tuple(sorted(tuple(sorted(col)) for col in st))
        if c not in seen: seen.add(c); out.append((g, st))
    return out

def effect_map(M):
    D = int(M["D"]); eff = {}
    for j, supp in enumerate(M['keys']):
        mask = 0
        for r_ in supp: mask |= 1 << int(r_)
        for f in M['faults'][j]: eff[fkey(M['fault_info'][f])] = mask
    return eff, D

def survives(st, eff, D, cap=100000):
    """Exact: some choice of representatives that exist in the candidate is undetected and flips a logical."""
    reach = {0}
    for col in st:
        opts = {eff[k] for k in col if k in eff}
        if not opts: return False                                     # broken: a fault location does not exist
        reach = {r ^ o for r in reach for o in opts}
        if len(reach) > cap: return True                              # unresolved: counted as surviving
    DM = (1 << D) - 1
    return any(not (r & DM) and (r >> D) for r in reach)

_FAM = {}
def b4_score(n, spec, fams):
    """fams: {kind: [list of copies (each a set)]} -> number of copies still undetected and logical."""
    score = {}
    for kind, cps in fams.items():
        code, M = matrices(n, spec, kind); eff, D = effect_map(M)
        score[kind] = sum(1 for st in cps if survives(st, eff, D))
    return score


# ------------------------------------------------------------------ candidates, validity (B2), screen (B4) in parallel
def _cand_job(a):
    n, spec = a
    t0 = time.time(); code = NBRef(n); tX, tZ = spec_tables(n, spec)
    if not code.check_cycle(tX, tZ): return spec, 'collision/stagger/sequential', None, time.time() - t0
    if not noiseless_ok(code, [(tX, tZ)]): return spec, 'noiseless detectors', None, time.time() - t0
    t1 = time.time(); sc = b4_score(n, spec, _FAM[n]); return spec, 'valid', sc, (t1 - t0, time.time() - t1)

def screen_candidates(n, specs, fams):
    """B2 + B4 for every spec, checkpointed in candidates.csv."""
    f = R(n, 'candidates.csv'); done = {}
    if os.path.exists(f):
        for r in csv.DictReader(open(f)): done[r['spec']] = r
    todo = [s for s in specs if s not in done]
    _FAM[n] = fams
    say(f'  B2/B4: {len(specs)} candidates, {len(done)} on file, {len(todo)} to check')
    new = not os.path.exists(f); t0 = time.time()
    if todo:
        with mp.get_context('fork').Pool(NPROC) as pool, open(f, 'a', newline='') as fc:
            w = csv.DictWriter(fc, fieldnames=['spec', 'status', 'b4_X', 'b4_Z', 'sec_b2', 'sec_b4']); new and w.writeheader()
            for i, (spec, st, sc, sec) in enumerate(pool.imap_unordered(_cand_job, [(n, s) for s in todo], chunksize=4)):
                row = dict(spec=spec, status=st, b4_X=sc['X'] if sc else '', b4_Z=sc['Z'] if sc else '',
                           sec_b2=round(sec[0] if isinstance(sec, tuple) else sec, 2), sec_b4=round(sec[1], 2) if isinstance(sec, tuple) else '')
                w.writerow(row); fc.flush(); done[spec] = row
                if (i + 1) % 500 == 0 or i + 1 == len(todo):
                    el = time.time() - t0; say(f'    [B2/B4] {i+1}/{len(todo)}, {el/60:.1f} min, ETA {el/(i+1)*(len(todo)-i-1)/60:.1f} min')
    return {s: done[s] for s in specs}

def d1_pool(n):
    """ids with d1 == max (from the uniform work's d1 table for this code).  If that table does not exist yet
    (e.g. [[108]] while its uniform ranking is unfinished), every schedule is used and this is reported."""
    f = os.path.join(M3, str(n), f'd1_{n}.csv')
    if not os.path.exists(f):
        T, _ = sched_table(n); say(f'  NOTE: no uniform d1 table for [[{n}]] yet: using all {len(T)} schedules as class orders')
        return sorted(T), None
    rows = list(csv.DictReader(open(f)))
    d1 = {int(r['id']): min(int(r['d1_Z']), int(r['d1_X'])) for r in rows}
    mx = max(d1.values()); return [i for i in sorted(d1) if d1[i] == mx], mx

def make_candidates(n, S, homs, fam1_per_hom, seed=0):
    pool, _ = d1_pool(n); pool = [o for o in pool if o != S]; rng = random.Random(seed); out = []
    for k, hom in homs:
        if k == 2:
            out += [(f'c2:{hom[0]},{hom[1]}:{S},{o}', 'F2', k, hom) for o in pool]
        else:
            out += [(f'c{k}:{hom[0]},{hom[1]}:{S},' + ','.join([str(o)] * (k - 1)), 'F2', k, hom) for o in pool]
            seen = set()
            while len(seen) < min(fam1_per_hom, len(pool) * (len(pool) - 1)):
                o1, o2 = rng.sample(pool, 2)
                if (o1, o2) in seen: continue
                seen.add((o1, o2)); out.append((f'c{k}:{hom[0]},{hom[1]}:{S},{o1},{o2}', 'F1', k, hom))
    return out


# ------------------------------------------------------------------ LER with Bravyi's decoder procedure
def ler_point(n, spec, p, target=50, batch=400, max_shots=400000, cycles=6, tag='ler'):
    """bravyi_ler.py (port of bravyi_ref/decoder_run.py): X-part failure = Z basis, Z-part failure = X basis.
    Runs batches until BOTH bases have >= target failures.  Returns dict(shots, fail_X, fail_Z, fail_any)."""
    import bravyi_ler as BL
    f = R(n, 'ler.csv'); FL = ['tag', 'spec', 'p', 'cycles', 'seed', 'shots', 'fail_X', 'fail_Z', 'fail_any', 'seconds']
    rows = [r for r in csv.DictReader(open(f))] if os.path.exists(f) else []
    mine = [r for r in rows if r['spec'] == spec and float(r['p']) == p and r['tag'] == tag and int(r['cycles']) == cycles]
    tot = {k: sum(int(r[k]) for r in mine) for k in ('shots', 'fail_X', 'fail_Z', 'fail_any')}
    model = None
    while min(tot['fail_X'], tot['fail_Z']) < target and tot['shots'] < max_shots:
        if model is None: model = BL.LerModel(NBRef(n), *spec_tables(n, spec), p, cycles)
        seed = 7919 * (len(mine) + 1) + int(p * 1e5); t0 = time.time()
        r = BL.run(model, batch, seed, NPROC)
        new = not os.path.exists(f)
        with open(f, 'a', newline='') as g:
            w = csv.DictWriter(g, fieldnames=FL); new and w.writeheader()
            w.writerow(dict(tag=tag, spec=spec, p=p, cycles=cycles, seed=seed, seconds=round(time.time() - t0), **r))
        mine.append(1)
        for k in tot: tot[k] += r[k]
        say(f'    LER {spec} p={p}: Z basis {tot["fail_X"]}/{tot["shots"]}, X basis {tot["fail_Z"]}/{tot["shots"]}  ({time.time()-t0:.0f}s per {batch})')
    return tot

def wilson(f, n, z=1.96):
    if n == 0: return 0, 1
    p = f / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


# ------------------------------------------------------------------ stage: Part 0 (control on [[72]])
B5_SAMPLE_72 = 60
FAM1_72 = 2000
def part0(n, a):
    n = 72; T, rev = sched_table(n)
    g = jload(R(n, 'reg.json')); S = g['S']
    if not g['PASS']: stop('0.1 regression failed')
    # S's weight-6 families (from the CONFIRM run), all translated copies
    fams, fam_info = {}, {}
    for kind in 'XZ':
        sets = s_sets(n, kind, S, 6); F_ = families(n, sets)
        fams[kind] = [st for f_ in F_ for _, st in copies(n, f_['rep'])]
        fam_info[kind] = dict(sets=len(sets), families=len(F_), copies=len(fams[kind]))
    say(f'  0.2 S weight-6 sets/families/copies: {fam_info}')
    sanity = b4_score(n, f'u{S}', fams)
    say(f'  sanity: S itself keeps {sanity} of {[len(fams[k]) for k in "XZ"]} copies (must be all)')
    if any(sanity[k] != len(fams[k]) for k in 'XZ'): stop(f'exact screen inconsistent on S: {sanity}')
    homs = [(2, h) for h in [(1, 0), (0, 1), (1, 1)]] + [(3, h) for h in [(1, 0), (0, 1)]]
    cands = make_candidates(n, S, homs, FAM1_72)
    res = screen_candidates(n, [c[0] for c in cands], fams)
    valid = [c for c in cands if res[c[0]]['status'] == 'valid']
    b4s = [c for c in valid if int(res[c[0]]['b4_X']) == 0 and int(res[c[0]]['b4_Z']) == 0]
    sec_b2 = np.mean([float(res[c[0]]['sec_b2']) for c in cands]); sec_b4 = np.mean([float(res[c[0]]['sec_b4']) for c in valid]) if valid else 0
    funnel = {}
    for k, hom in homs:
        cc = [c for c in cands if c[2] == k and c[3] == hom]
        funnel[f'Z{k} ({hom[0]},{hom[1]})'] = dict(generated=len(cc), valid=sum(res[c[0]]['status'] == 'valid' for c in cc),
                                                    pass_b4=sum(c in b4s for c in cc))
    say(f'  funnel: {funnel}')
    # B5: d1 screen on all B4 survivors (control: none expected) + a random sample of valid candidates
    rng = random.Random(1); samp = rng.sample(valid, min(B5_SAMPLE_72, len(valid)))
    b5 = list(dict.fromkeys([c[0] for c in b4s][:B5_SAMPLE_72] + [c[0] for c in samp]))
    t0 = time.time(); m = search(n, 'b5', b5, SCREEN, seed0=3); sec_b5 = (time.time() - t0) / max(1, len(b5))
    d1s = {s: min(m[(s, 'X')][0], m[(s, 'Z')][0]) for s in b5}
    above = [s for s in b5 if m[(s, 'X')][0] > 6 and m[(s, 'Z')][0] > 6]
    conf = {}
    if above:
        mc = search(n, 'b5confirm', above, CONFIRM, seed0=5)
        conf = {s: min(mc[(s, 'X')][0], mc[(s, 'Z')][0]) for s in above}
    bad = [s for s, v in conf.items() if v > 6]
    hist = dict(sorted(collections.Counter(d1s.values()).items()))
    say(f'  B5 screen ({SCREEN} trials/type) on {len(b5)} candidates: d1 histogram {hist}; screen > 6 in both types: {len(above)}; confirmed > 6: {bad}')
    out = dict(S=S, families=fam_info, sanity=sanity, homs=[[k, list(h)] for k, h in homs], funnel=funnel, n_candidates=len(cands),
               n_valid=len(valid), n_pass_b4=len(b4s), sec_b2=sec_b2, sec_b4=sec_b4, sec_b5_per_candidate=sec_b5, b5_specs=b5,
               b5_d1={s: [m[(s, 'X')][0], m[(s, 'Z')][0]] for s in b5}, b5_hist=hist, confirmed=conf, date=now())
    jdump(out, R(n, 'part0_screen.json'))
    if bad: out['PASS'] = False; jdump(out, R(n, 'part0.json')); stop(f'[[72]] control: class schedules with confirmed d1 > 6 (bug): {bad}')
    # 0.3 LER: S vs N72 (a valid class schedule with screen d1 = 6), p = 0.004, 0.006, both bases, Bravyi decoder
    n72 = next((s for s in b5 if d1s[s] == 6), None)
    if n72 is None: stop('no class schedule with screen d1 = 6 for 0.3')
    pts = {}
    for p in (0.006, 0.004):
        for spec in (f'u{S}', n72): pts[f'{spec}|{p}'] = ler_point(n, spec, p, tag='part0')
    agree = {}
    for p in (0.006, 0.004):
        for basis, key in (('Z', 'fail_X'), ('X', 'fail_Z')):
            A, B = pts[f'u{S}|{p}'], pts[f'{n72}|{p}']
            l1, h1 = wilson(A[key], A['shots']); l2, h2 = wilson(B[key], B['shots']); agree[f'{basis}|{p}'] = not (h1 < l2 or h2 < l1)
    out.update(N72=n72, ler=pts, ler_agree=agree, PASS=True, date=now())
    jdump(out, R(n, 'part0.json'))
    say(f'  0.3 LER S vs N72 = {n72}: agree within 95% intervals: {agree}')
    say(f'  0.4 control: regression {g["d1_X"][0]}/{g["d1_Z"][0]} (expect 6/6); confirmed d1 > 6: {len(bad)} (expect 0); '
        f'LER agree: {all(agree.values())} (expect True)')


# ------------------------------------------------------------------ Part A: S's weight-8 paths (on [[90]])
def _last_cnot_round(code, sched_tabs, q):
    tX, tZ = sched_tabs; n2 = code.n2
    if q < n2: row = tX[q]
    elif q >= 3 * n2: row = tZ[q - 3 * n2]
    else: return None
    return max(t for t in range(7) if row[t] != 'idle')

def partA(n, a):
    T, _ = sched_table(n); g = jload(R(n, 'reg.json')); S = g['S']; w = BRAVYI_D[n]
    code = NBRef(n); tabs = spec_tables(n, f'u{S}'); homs = homomorphisms(n, 3)
    cls = {h: class_of(n, h, 3) for h in homs}
    out = {}
    for kind in 'XZ':
        sets = s_sets(n, kind, S, w); F_ = families(n, sets); rows = []
        for fi, f_ in enumerate(F_):
            faults, anc = [], set()
            for col in f_['rep']:
                k = col[0]; op, qs, t, c, fq = k
                qn = [code.name(q) for q in qs]
                hook = False
                if op == 'CNOT' and fq is not None:
                    for q in fq:
                        lr = _last_cnot_round(code, tabs, q)
                        if lr is not None and t < lr: hook = True
                for q in qs:
                    if q < code.n2 or q >= 3 * code.n2: anc.add(int(q) % code.n2 if q < code.n2 else int(q) - 3 * code.n2)
                faults.append(dict(type=op, qubits=qn, faulted=[code.name(q) for q in fq] if fq else None, round=t,
                                   hook=hook, n_equivalent=len(col)))
            rows.append(dict(family=fi, copies=len(copies(n, f_['rep'])), members=f_['members'], faults=faults,
                             n_hook=sum(x['hook'] for x in faults), ancillas=sorted(anc),
                             ancilla_classes={f'{h[0]},{h[1]}': sorted({int(cls[h][i]) for i in anc}) for h in homs}))
        out[kind] = dict(sets=len(sets), families=rows)
        say(f'  Part A [[{n}]] {kind} faults: {len(sets)} weight-{w} sets in {len(rows)} families; hooks per family {[r["n_hook"] for r in rows]}')
    jdump(dict(n=n, S=S, weight=w, homs=[list(h) for h in homs], kinds=out, date=now()), R(n, 'partA.json'))


# ------------------------------------------------------------------ Part B: class schedules on [[90]] / [[108]]
FAM1_PER_HOM = 20000
B5_BUDGET = 1300            # ~2 days of d1 screening (B4b); above this keep 500 and ask
def _fams(n, S, w):
    fams = {}
    for kind in 'XZ':
        F_ = families(n, s_sets(n, kind, S, w)); fams[kind] = [st for f_ in F_ for _, st in copies(n, f_['rep'])]
    return fams

def partB4(n, a):
    """B1-B4 (+ B4b report): generate Z_3 (and Z_2 where it exists) class schedules, validity, exact screen."""
    g = jload(R(n, 'reg.json')); S = g['S']; w = BRAVYI_D[n]
    if not g['PASS']: stop('regression failed')
    fams = _fams(n, S, w)
    sanity = b4_score(n, f'u{S}', fams)
    say(f'  [[{n}]] S weight-{w} copies: X {len(fams["X"])}, Z {len(fams["Z"])}; S keeps {sanity}')
    if any(sanity[k] != len(fams[k]) for k in 'XZ'): stop(f'exact screen inconsistent on S: {sanity}')
    homs = [(2, h) for h in homomorphisms(n, 2)] + [(3, h) for h in homomorphisms(n, 3)]
    cands = make_candidates(n, S, homs, FAM1_PER_HOM, seed=11)
    say(f'  homomorphisms (image of x, image of y): {homs}; candidates: {len(cands)}')
    res = screen_candidates(n, [c[0] for c in cands], fams)
    valid = [c for c in cands if res[c[0]]['status'] == 'valid']
    surv = [c for c in valid if int(res[c[0]]['b4_X']) == 0 and int(res[c[0]]['b4_Z']) == 0]
    funnel = {}
    for k, hom in homs:
        for fam in ('F1', 'F2'):
            cc = [c for c in cands if c[2] == k and c[3] == hom and c[1] == fam]
            if cc: funnel[f'Z{k} ({hom[0]},{hom[1]}) {fam}'] = dict(generated=len(cc), valid=sum(res[c[0]]['status'] == 'valid' for c in cc),
                                                                    pass_b4=sum(c in surv for c in cc))
    best = sorted(valid, key=lambda c: int(res[c[0]]['b4_X']) + int(res[c[0]]['b4_Z']))[:20]
    out = dict(S=S, copies={k: len(v) for k, v in fams.items()}, homs=[[k, list(h)] for k, h in homs], funnel=funnel,
               n_candidates=len(cands), n_valid=len(valid), n_pass_b4=len(surv), survivors=[c[0] for c in surv],
               lowest_b4=[[c[0], int(res[c[0]]['b4_X']), int(res[c[0]]['b4_Z'])] for c in best],
               b5_budget=B5_BUDGET, date=now())
    jdump(out, R(n, 'partB4.json'))
    say(f'  funnel: {funnel}')
    say(f'  B4b: {len(surv)} candidates pass the exact screen (score 0 in both fault types); valid {len(valid)} of {len(cands)}')
    if not surv: say(f'  [[{n}]]: no class schedule of this kind breaks all of S\'s weight-{w} families (stop rule)')

def partB5(n, a):
    """B5: d1 screen (2000 trials per type) on the exact-screen survivors, in 500-trial rounds; a candidate is
    dropped as soon as either fault type reaches <= d1(S) (it can no longer pass 'screen d1 > d1(S) in both').
    Survivors of the full screen are CONFIRMED (100,000 trials per type)."""
    b4 = jload(R(n, 'partB4.json')); w = BRAVYI_D[n]; surv = b4['survivors']
    if len(surv) > B5_BUDGET:
        rng = random.Random(5); surv = rng.sample(surv, 500)
        say(f'  B4b: {len(b4["survivors"])} survivors exceed the ~2-day budget: screening a random 500 now; ASK before the rest')
    alive = list(surv); rounds = SCREEN // CHUNK
    for c in range(rounds):
        if not alive: break
        run_jobs(n, 'b5', [(s, k, c, 300000 + 100000 * c + 17 * i + (k == 'Z'), CHUNK) for i, s in enumerate(alive) for k in 'XZ'])
        m = mins(n, 'b5')
        alive = [s for s in alive if m[(s, 'X')][0] > w and m[(s, 'Z')][0] > w]
        say(f'  B5 round {c+1}/{rounds}: {len(alive)} of {len(surv)} still above {w} in both fault types')
    m = mins(n, 'b5')
    d1s = {s: min(m[(s, 'X')][0], m[(s, 'Z')][0]) for s in surv if (s, 'X') in m and (s, 'Z') in m}
    conf = {}
    if alive:
        mc = search(n, 'b5confirm', alive, CONFIRM, seed0=9)
        conf = {s: [mc[(s, 'X')][0], mc[(s, 'Z')][0]] for s in alive}
    winners = [s for s, v in conf.items() if min(v) > w]
    out = dict(screened=len(surv), of=len(b4['survivors']), screen_d1=d1s, hist=dict(sorted(collections.Counter(d1s.values()).items())),
               screen_above=alive, confirmed=conf, winners=winners, date=now())
    jdump(out, R(n, 'partB5.json'))
    say(f'  B5 [[{n}]]: screen d1 histogram {out["hist"]}; screen > {w} in both: {len(alive)}; CONFIRMED d1 > {w}: {winners or "none"}')


STAGES = {'reg': reg, 'part0': part0, 'partA': partA, 'partB4': partB4, 'partB5': partB5}


def lerB(n, a):
    """Extra (user request 2026-10-19): error rate of the valid class schedules that keep the fewest copies of S's
    minimum-weight paths, vs S.  Bravyi's decoder procedure (bravyi_ler.py), p = 0.005 and 0.004, 6 cycles,
    both bases, >= 50 failures per point; plus a d1 screen (2000 trials per type) for context."""
    b4 = jload(R(n, 'partB4.json')); S = jload(R(n, 'reg.json'))['S']
    cands = [c[0] for c in b4['lowest_b4'][:int(os.environ.get('NU_LERB_K', 4))]]
    say(f'  lerB [[{n}]]: S vs {cands} (exact-screen copies kept X/Z: {[c[1:] for c in b4["lowest_b4"][:len(cands)]]})')
    m = search(n, 'lerB_d1', cands, SCREEN, seed0=21)
    d1 = {c: [m[(c, 'X')][0], m[(c, 'Z')][0]] for c in cands}
    say(f'  d1 screen (X, Z): {d1}')
    pts = {}
    for p in (0.005, 0.004):
        for spec in [f'u{S}'] + cands: pts[f'{spec}|{p}'] = ler_point(n, spec, p, tag='lerB')
    jdump(dict(n=n, S=S, candidates=cands, b4=b4['lowest_b4'][:len(cands)], d1=d1, ler=pts, date=now()), R(n, 'lerB.json'))


STAGES['lerB'] = lerB


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--stage', required=True); ap.add_argument('--n', type=int, default=72)
    a = ap.parse_args(); os.makedirs(R(a.n), exist_ok=True)
    name = a.stage; out = R(a.n, f'{name}.json')
    if os.path.exists(out):
        if jload(out).get('PASS') is False: stop(f'[[{a.n}]] {name} failed its PASS condition earlier')
        say(f'[[{a.n}]] {name}: already done'); sys.exit(0)
    say(f'== [[{a.n}]] {name} start {now()}')
    STAGES[name](a.n, a)
    say(f'== [[{a.n}]] {name} done {now()}')
