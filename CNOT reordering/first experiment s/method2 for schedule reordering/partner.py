"""Path-targeted partner search, stages 0-5 of docs/task.md.

usage:  ../venv/bin/python partner.py --n 90 --stage 0|1|2|3|4|control|5 [--nproc 12]
Every stage is resumable: bound-search chunks are CSV rows (results_partner/<n>/bounds.csv, skipped
when present) and a finished stage writes results_partner/<n>/stage<k>.json.  Exit code 3 = a PASS
condition failed (the driver stops and reports).

Distance search (identical for every circuit of a code): randomised BP-OSD (Bravyi Eq. 12), serial
min-sum scaling 0.625, 10 BP iterations, OSD-CS order 20, random channel priors in [0.005, 0.1],
chunks of 100 trials, rng seed depends only on (seed, chunk, basis, cycles), not on the circuit.
LER decoder (stage 5): serial min-sum scaling 0.625, 100 iterations, OSD-CS order 7, DEM priors.
"""
import argparse, csv, json, os, sys, time, collections, datetime
import multiprocessing as mp
import numpy as np
from bb_code import BBCode, BRAVYI, reverse_schedule, memory_circuit, gf2_rank
from dcirc import dem_matrices, dem_columns, dcirc_bound
import partner_lib as PL

BRAVYI_D = {72: 6, 90: 8, 108: 8}          # Bravyi Table 1 d_circ(S) (upper bound) = PASS target
CODE_D = {72: 6, 90: 10, 108: 10}
TRIALS = {72: (3, 3), 90: (6, 12), 108: (6, 12)}   # chunks of 100 per seed: (default, max if Stage 0 needs more)
SEEDS, CYCLES, CHUNK = 5, (4, 6), int(os.environ.get('PARTNER_CHUNK', 100))
MS, OSD_SEARCH, ITER_SEARCH = 0.625, 20, 10
FB = ['stage', 'circuit', 'basis', 'cycles', 'seed', 'chunk', 'rng_seed', 'trials', 'min_weight', 'hist', 'n_sets', 'seconds']

def say(*a): print(*a, flush=True)
RES = os.environ.get('PARTNER_RES', 'results_partner')     # test runs use another folder
def R(n, f=''): return os.path.join(RES, str(n), f)
def jdump(o, f): json.dump(o, open(f, 'w'), indent=1, default=str)
def jload(f): return json.load(open(f))
def stop(msg):
    say(f'== STOP: {msg}'); sys.exit(3)
def workers(n, want):
    """Up to `want` workers; on [[108]] keep memory under ~70%."""
    tot = int(open('/proc/meminfo').readline().split()[1]) / 1e6
    avail = [int(l.split()[1]) / 1e6 for l in open('/proc/meminfo') if l.startswith('MemAvailable')][0]
    used = tot - avail; per = 0.4 if n == 108 else 0.3
    k = int(max(1, min(want, (0.70 * tot - used) // per)))
    say(f'  [workers] RAM {used:.1f}/{tot:.1f} GB used -> {k} workers (asked {want})'); return k


# ------------------------------------------------------------------ bound search
_DEM = {}
def _dem(n, spec, basis, cycles):
    k = (n, spec, basis, cycles)
    if k not in _DEM:
        c = PL.circuit(n, spec, cycles, basis, PL.load_table(n))
        dem = c.detector_error_model(flatten_loops=True)
        H, L, _ = dem_matrices(dem); keys = list(dem_columns(dem)); assert len(keys) == H.shape[1]
        _DEM[k] = (H, L, keys)
    return _DEM[k]

def _job(a):
    n, stage, spec, basis, cycles, seed, chunk, rs, keep = a
    H, L, keys = _dem(n, spec, basis, cycles)
    r = dcirc_bound(H, L, trials=CHUNK, osd_order=OSD_SEARCH, max_iter=ITER_SEARCH, seed=rs, ms_scale=MS, keep_le=keep)
    sets = [(w, [[list(keys[j][0]), list(keys[j][1])] for j in sorted(map(int, s))]) for w, ss in r['supports'].items() for s in ss]
    return a, r, sets

def rng_seed(seed, chunk, basis, cycles): return 10**7 * seed + 1000 * chunk + 10 * (basis == 'X') + cycles

def run_bounds(n, stage, specs, nchunks, nproc):
    """Round-robin: chunk k of every (circuit, basis, cycles, seed) before chunk k+1."""
    f_csv, f_sets = R(n, 'bounds.csv'), R(n, 'sets.jsonl'); keep = BRAVYI_D[n] + 1
    done = set()
    if os.path.exists(f_csv):
        for r in csv.DictReader(open(f_csv)):
            if r['stage'] == stage: done.add((r['circuit'], r['basis'], int(r['cycles']), int(r['seed']), int(r['chunk'])))
    jobs = [(n, stage, s, b, cy, sd, k, rng_seed(sd, k, b, cy), keep)
            for k in range(nchunks) for sd in range(1, SEEDS + 1) for cy in CYCLES for s in specs for b in 'ZX'
            if (s, b, cy, sd, k) not in done]
    say(f'  bounds [{stage}] {len(specs)} circuits: {len(done)} chunks on file, {len(jobs)} to run ({CHUNK} trials each)')
    if not jobs: return
    new = not os.path.exists(f_csv); t0 = time.time()
    with mp.get_context('fork').Pool(nproc) as pool, open(f_csv, 'a', newline='') as f, open(f_sets, 'a') as g:
        w = csv.DictWriter(f, fieldnames=FB)
        if new: w.writeheader()
        for i, (a, r, sets) in enumerate(pool.imap_unordered(_job, jobs)):
            _, stg, s, b, cy, sd, k, rs, _ = a
            for wt, st in sets:
                g.write(json.dumps(dict(stage=stg, circuit=s, basis=b, cycles=cy, seed=sd, chunk=k, weight=wt, set=st)) + '\n')
            g.flush()
            w.writerow(dict(stage=stg, circuit=s, basis=b, cycles=cy, seed=sd, chunk=k, rng_seed=rs, trials=r['trials'],
                            min_weight=r['min_weight'], hist=json.dumps(r['hist']), n_sets=len(sets), seconds=round(r['seconds'], 1)))
            f.flush()
            if (i + 1) % 20 == 0 or i + 1 == len(jobs):
                el = time.time() - t0
                say(f'    {i+1}/{len(jobs)} chunks, {el/3600:.2f} h, ETA {el/(i+1)*(len(jobs)-i-1)/3600:.1f} h  (last: {s} {b} {cy}c seed {sd} chunk {k}: min {r["min_weight"]})')

def bounds_table(n, specs, nchunks, stage):
    """min weight per (circuit, basis, cycles, seed) over chunks < nchunks of one stage."""
    out = collections.defaultdict(lambda: 10**9)
    for r in csv.DictReader(open(R(n, 'bounds.csv'))):
        if r['stage'] == stage and r['circuit'] in specs and int(r['chunk']) < nchunks:
            k = (r['circuit'], r['basis'], int(r['cycles']), int(r['seed']))
            out[k] = min(out[k], int(r['min_weight']))
    return dict(out)

def sets_of(n, spec, weight=None, nchunks=None, stage=None):
    out = []
    for line in open(R(n, 'sets.jsonl')):
        r = json.loads(line)
        if stage is not None and r['stage'] != stage: continue
        if r['circuit'] != spec or (weight is not None and r['weight'] != weight): continue
        if nchunks is not None and r['chunk'] >= nchunks: continue
        out.append(r)
    return out

def key(st): return tuple(sorted((tuple(d), tuple(o)) for d, o in st))


# ------------------------------------------------------------------ stages
def stage0(n, a):
    code = BBCode(n); Hx, Hz = code.hx(), code.hz()
    comm = not ((Hx.astype(int) @ Hz.T.astype(int)) % 2).any()
    k = n - gf2_rank(Hx) - gf2_rank(Hz)
    say(f'[[{n}]] l={code.l} m={code.m}: n={n} k={k} Hx Hz^T = 0: {comm}')
    if not comm or k != {72: 12, 90: 8, 108: 8}[n]: stop(f'code construction wrong (k={k}, commute={comm})')
    nz = {cy: PL.noiseless_ok(code, [BRAVYI], cy) for cy in (2, 6)}
    say(f'  S noiseless detectors all zero (both bases): {nz}')
    if not all(nz.values()): stop('S has nonzero noiseless detectors')
    # Stage 0 needs the schedule table for circuit specs: build it here (Stage 1 re-checks every schedule)
    if not os.path.exists(R(n, 'schedules.jsonl')): stage1(n, a, table_only=True)
    S = str(PL.named(n)['S'])
    d0, dmax = TRIALS[n]; nch = d0
    while True:
        run_bounds(n, 'stage0', [S], nch, workers(n, a.nproc))
        tb = bounds_table(n, [S], nch, 'stage0'); m = min(tb.values())
        say(f'  S after {nch*CHUNK} trials/seed: min {m} (target {BRAVYI_D[n]})')
        if m <= BRAVYI_D[n] or nch >= dmax: break
        nch += 2
    res = dict(n=n, k=k, commute=comm, noiseless=nz, S=S, trials_per_seed=nch * CHUNK, chunks=nch,
               table={f'{c}|{b}|{cy}|{sd}': v for (c, b, cy, sd), v in tb.items()}, min=m, target=BRAVYI_D[n],
               PASS=(m == BRAVYI_D[n]), date=str(datetime.datetime.now()))
    jdump(res, R(n, 'stage0.json'))
    if m != BRAVYI_D[n]:
        stop(f'[[{n}]] Stage 0: S minimum found {m} != Bravyi {BRAVYI_D[n]} ({nch*CHUNK} trials/seed, 5 seeds, both bases, 4+6 cycles)')
    say(f'  Stage 0 PASS: S min = {m} = Bravyi ({nch*CHUNK} trials/seed x 5 seeds x 2 bases x cycles 4,6)')


def stage1(n, a, table_only=False):
    code = BBCode(n); t0 = time.time()
    V = PL.enumerate_schedules(code)
    tup = lambda s: (tuple(s[0]), tuple(s[1]), bool(s[2]))
    idx = {tup(s): i for i, s in enumerate(V)}
    rows = []
    for i, s in enumerate(V):
        r = reverse_schedule(s)
        rows.append(dict(id=i, x=list(s[0]), z=list(s[1]), z_first=s[2], reverse_id=idx.get(tup(r))))
    os.makedirs(R(n), exist_ok=True)
    with open(R(n, 'schedules.jsonl'), 'w') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    ids = dict(S=idx.get(tup(BRAVYI)), Sinv=idx.get(tup(reverse_schedule(BRAVYI))), Smirror=idx.get(tup(PL.S_MIRROR)))
    jdump(ids, R(n, 'named_ids.json'))
    if table_only: return
    if ids['S'] is None or ids['Sinv'] is None: stop(f'S or S^-1 not among the valid schedules: {ids}')
    if ids['Smirror'] is None: stop('S_mirror is not a valid depth-7 schedule on this code')
    # ground truth: stim noiseless detectors (both bases, 2 cycles) + no collision, for EVERY schedule
    bad = [i for i, s in enumerate(V) if not PL.noiseless_ok(code, [s], 2)]
    nz = sum(1 for s in V if s[2]); nx = len(V) - nz
    res = dict(n=n, count=len(V), z_first=nz, x_first=nx, stim_rejects=bad, ids=ids,
               reverse_ids={k: rows[v]['reverse_id'] for k, v in ids.items()},
               seconds=round(time.time() - t0), date=str(datetime.datetime.now()))
    say(f'  valid schedules: {len(V)} (Z-first {nz}, X-first {nx}); stim rejects among them: {len(bad)}')
    say(f'  ids: {ids}; their time-reverse ids: {res["reverse_ids"]}')
    if bad: stop(f'{len(bad)} algebraically valid schedules fail the stim noiseless test: {bad[:10]}')
    jdump(res, R(n, 'stage1.json'))


def _collect_S_sets(n, w):
    """distinct S sets of weight w per (basis, cycles), all seeds, stage-0 chunks."""
    st0 = jload(R(n, 'stage0.json')); S = st0['S']
    out = collections.defaultdict(set)
    for r in sets_of(n, S, w, st0['chunks'], 'stage0'):
        out[(r['basis'], r['cycles'])].add(key(r['set']))
    return out


def families(n, sets_by, T, spec):
    """group sets by torus translation; returns {(basis,cycles): [dict(rep, members, span), ...]}"""
    fam = {}
    for (b, cy), ss in sorted(sets_by.items()):
        c = PL.circuit(n, spec, cy, b, T); maps = PL.det_shift_maps(n, c)
        locs = PL.explain_columns(c, {col for s in ss for col in s})
        g = collections.defaultdict(list)
        for s in sorted(ss): g[PL.canonical(s, maps)].append(s)
        fl = []
        for can, mem in sorted(g.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            rep = mem[0]
            fl.append(dict(rep=rep, members=len(mem), span=PL.cycle_span(rep, locs),
                           spans=sorted({PL.cycle_span(s, locs) for s in mem}),
                           physical=[[PL.describe(l, BBCode(n)) for l in locs[col][:1]][0] for col in rep]))
        fam[(b, cy)] = fl
    return fam


def stage2(n, a):
    T = PL.load_table(n); st0 = jload(R(n, 'stage0.json')); S = st0['S']; w = st0['min']
    res = {}
    for weight, tag in ((w, 'min'), (w + 1, 'next')):
        F = families(n, _collect_S_sets(n, weight), T, S)
        res[tag] = dict(weight=weight, groups={f'{b}|{cy}': fl for (b, cy), fl in F.items()})
        for (b, cy), fl in F.items():
            say(f'  S weight-{weight} sets, basis {b}, {cy} cycles: {sum(f["members"] for f in fl)} sets in {len(fl)} families; '
                f'spans {collections.Counter(f["span"] for f in fl)}')
    nmin = sum(len(v) for v in res['min']['groups'].values())
    if nmin == 0: stop('no minimum-weight S sets saved')
    res['date'] = str(datetime.datetime.now())
    jdump(res, R(n, 'stage2.json'))
    say(f'  Stage 2: {sum(f["members"] for v in res["min"]["groups"].values() for f in v)} distinct weight-{w} sets, {nmin} families')


def _fam_list(n, tag):
    st2 = jload(R(n, 'stage2.json'))
    out = []
    for g, fl in st2[tag]['groups'].items():
        b, cy = g.split('|')
        for i, f in enumerate(fl):
            out.append((b, int(cy), i, [(tuple(d), tuple(o)) for d, o in f['rep']]))
    return out


_S3 = {}
NEXT_CAP = 300          # tie-break families (weight min+1): the 300 largest per (basis, cycles)

def _s3_init(n):
    """Partner-independent part of the screen.  Families are placed only in S cycles of alt [S, S'], where
    alt runs exactly S's instructions, so candidate locations and their S-circuit flips are computed once;
    each partner then needs one FlipSimulator pass per (basis, cycles)."""
    T = PL.load_table(n); S = str(PL.named(n)['S'])
    fams = {tag: _fam_list(n, tag) for tag in ('min', 'next')}
    cnt = collections.Counter(); fams['next'] = [f for f in fams['next'] if (cnt.update([(f[0], f[1])]) or cnt[(f[0], f[1])] <= NEXT_CAP)]
    plan = {}
    for b in 'ZX':
        for cy in CYCLES:
            src = PL.circuit(n, S, cy, b, T)
            mine = [(tag, f) for tag in fams for f in fams[tag] if (f[0], f[1]) == (b, cy)]
            locs = PL.explain_columns(src, {col for _, f in mine for col in f[3]})
            ok = {t for t in range(cy) if t % 2 == 0}
            uniq, ix, entries = [], {}, []
            for tag, (_, _, i, rep) in mine:
                ent = []
                for sh in range(-(cy - 1), cy):
                    pc = PL.candidates(rep, locs, src, src, sh, ok)
                    if pc is None: continue
                    cols = []
                    for cand in pc:
                        cols.append([ix.setdefault((o, pp), len(ix)) for o, pp, _ in cand])
                    ent.append((sh, cols))
                entries.append((tag, i, ent))
            uniq = sorted(ix, key=ix.get)
            plan[(b, cy)] = dict(uniq=uniq, src_bits=PL.flips(src, uniq), entries=entries,
                                 D=src.num_detectors, K=src.num_observables)
    _S3.update(n=n, T=T, S=S, fams=fams, plan=plan)


def screen(partner, which=('min', 'next')):
    """Exact status of every S family inside alt [S, partner]: {tag: [(basis, cycles, i, status, shift)]}."""
    n, T, S = _S3['n'], _S3['T'], _S3['S']; out = {tag: [] for tag in which}
    for (b, cy), P in _S3['plan'].items():
        dst = memory_circuit(BBCode(n), [T[int(S)], T[int(partner)]], cy, PL.P_STRUCT, b)
        src = PL.circuit(n, S, cy, b, T)
        assert all(dst[o] == src[o] for o in {o for o, _ in P['uniq']}), 'alt differs from S at an S-cycle location'
        dbits = PL.flips(dst, P['uniq']); sb = P['src_bits']; W = P['D'] + P['K']
        for tag, i, ent in P['entries']:
            if tag not in which: continue
            best = ('broken', None)
            for sh, cols in ent:
                st = PL.status_from([{sb[u] | (dbits[u] << W) for u in c} for c in cols], P['D'], P['K'])
                if st is None: continue
                if PL.ORDER[st] > PL.ORDER[best[0]]: best = (st, sh)
                if st == 'survives': break
            out[tag].append((b, cy, i, best[0], best[1]))
    return out

def _s3_job(pid):
    return pid, screen(pid)


def stage3(n, a):
    T = PL.load_table(n); ids = PL.named(n); S = ids['S']
    f_out = R(n, 'stage3_rows.jsonl'); done = set()
    if os.path.exists(f_out):
        done = {json.loads(l)['partner'] for l in open(f_out)}
    partners = [i for i in sorted(T) if i != S]
    todo = [i for i in partners if i not in done]
    say(f'  Stage 3: {len(partners)} partners (S excluded), {len(done)} on file, {len(todo)} to screen')
    _s3_init(n)
    nf = {tag: len(_S3['fams'][tag]) for tag in _S3['fams']}
    say(f'  families: {nf}')
    # sanity: with S itself as the partner every family must survive (alt [S,S] = S)
    chk = screen(S, which=('min',)); cc = collections.Counter(s[3] for s in chk['min'])
    say(f'  sanity alt[S,S]: {dict(cc)}')
    if set(cc) - {'survives', 'broken'}: stop(f'exact screen inconsistent: alt[S,S] detects an S path {dict(cc)}')
    t0 = time.time()
    if todo:
        with mp.get_context('fork').Pool(workers(n, a.nproc)) as pool, open(f_out, 'a') as f:
            for j, (pid, r) in enumerate(pool.imap_unordered(_s3_job, todo, chunksize=4)):
                sc = {tag: sum(1 for s in r[tag] if s[3] in ('survives', 'unresolved')) for tag in r}
                f.write(json.dumps(dict(partner=pid, score=sc['min'], score_next=sc['next'], status=r)) + '\n'); f.flush()
                if (j + 1) % 100 == 0 or j + 1 == len(todo):
                    el = time.time() - t0; say(f'    {j+1}/{len(todo)} partners, {el/60:.1f} min, ETA {el/(j+1)*(len(todo)-j-1)/60:.1f} min')
    rows = {r['partner']: r for r in map(json.loads, open(f_out))}
    sc = {p: rows[p]['score'] for p in partners}
    hist = dict(sorted(collections.Counter(sc.values()).items()))
    zero = sorted(p for p in partners if sc[p] == 0)
    st_counts = collections.Counter(s[3] for p in partners for s in rows[p]['status']['min'])
    # survivors for stage 4: all score-0 partners (if none, the 10 lowest); ties broken by the exact score
    # on S's next-lightest (weight min+1) families, then by id; capped at 10 circuits.
    # stage-4 survivors: every score-0 partner (if none: the 10 lowest scores).  Ties are broken by the exact
    # score on S's next-lightest (weight min+1) families; if more than 10 remain tied, take 10 evenly spaced
    # ids from the tied list (covers Z-first and X-first partners instead of 10 near-identical ids).
    pool_ = zero if zero else partners
    kf = lambda p: (sc[p], rows[p]['score_next'])
    rank = sorted(pool_, key=lambda p: (kf(p), p)); surv = []
    for kv in sorted({kf(p) for p in rank}):
        tied = [p for p in rank if kf(p) == kv]; need = 10 - len(surv)
        if len(tied) <= need: surv += tied
        else: surv += [tied[round(i * (len(tied) - 1) / max(need - 1, 1))] for i in range(need)]
        if len(surv) >= 10: break
    if zero and len(zero) <= 10: surv = zero
    fams = _S3['fams']['min']
    per_fam = collections.Counter()
    for p in partners:
        for (b, cy, i, s, _) in rows[p]['status']['min']:
            if s in ('survives', 'unresolved'): per_fam[f'{b}|{cy}|{i}'] += 1
    res = dict(n=n, partners=len(partners), families=len(fams), hist=hist, zero=zero, n_zero=len(zero),
               score_Sinv=sc[ids['Sinv']], score_Smirror=sc[ids['Smirror']],
               status_Sinv=rows[ids['Sinv']]['status'], status_Smirror=rows[ids['Smirror']]['status'],
               status_counts=dict(st_counts), survivors=surv, survivors_score={p: [sc[p], rows[p]['score_next']] for p in surv},
               survive_count_per_family=dict(per_fam), sanity_SS=chk, seconds=round(time.time() - t0),
               date=str(datetime.datetime.now()))
    jdump(res, R(n, 'stage3.json'))
    say(f'  Stage 3 scores (number of S weight-{jload(R(n,"stage2.json"))["min"]["weight"]} families still undetected+logical, of {len(fams)}): {hist}')
    say(f'  score 0: {len(zero)} partners {zero[:20]}; S^-1 ({ids["Sinv"]}) score {sc[ids["Sinv"]]}, S_mirror ({ids["Smirror"]}) score {sc[ids["Smirror"]]}')
    say(f'  stage-4 survivors: {surv}')


def stage4_specs(n):
    ids = PL.named(n); S = str(ids['S']); st3 = jload(R(n, 'stage3.json'))
    specs = [S, str(ids['Sinv']), str(ids['Smirror']), f'{S}+{ids["Sinv"]}', f'{S}+{ids["Smirror"]}']
    specs += [f'{S}+{p}' for p in st3['survivors'] if f'{S}+{p}' not in specs]
    return specs


def verify_min_sets(n, spec, cy_b_sets, T):
    """exactly verify that found sets are undetected logicals of their own circuit (physical injection)."""
    ok = bad = 0
    for (b, cy), ss in cy_b_sets.items():
        c = PL.circuit(n, spec, cy, b, T); locs = PL.explain_columns(c, {col for s in ss for col in s})
        for s in ss:
            st, _ = PL.transfer(s, locs, c, c)
            ok += st in ('survives', 'unresolved'); bad += st not in ('survives', 'unresolved')
    return ok, bad


def cross_check(n, src_spec, dst_spec, sets_by, T):
    cnt = collections.Counter()
    for (b, cy), ss in sets_by.items():
        src = PL.circuit(n, src_spec, cy, b, T); dst = PL.circuit(n, dst_spec, cy, b, T)
        locs = PL.explain_columns(src, {col for s in ss for col in s})
        for s in ss:
            cnt[PL.transfer(s, locs, src, dst, shifts=range(-(cy - 1), cy))[0]] += 1
    return dict(cnt)


def stage4(n, a):
    T = PL.load_table(n); st0 = jload(R(n, 'stage0.json')); nch = st0['chunks']
    specs = stage4_specs(n); S = specs[0]
    say(f'  Stage 4 circuits: {specs}')
    run_bounds(n, 'stage4', specs, nch, workers(n, a.nproc))
    tb = bounds_table(n, specs, nch, 'stage4')
    mins = {s: min(v for (c, b, cy, sd), v in tb.items() if c == s) for s in specs}
    # exact checks: min-weight sets of every alt circuit -> S, and S sets -> every alt circuit
    xs = {}; ver = {}
    def sets_by(spec, w):
        d = collections.defaultdict(set)
        for r in sets_of(n, spec, w, nch, 'stage4'): d[(r['basis'], r['cycles'])].add(key(r['set']))
        return d
    Ssets = sets_by(S, mins[S])
    for s in specs:
        own = sets_by(s, mins[s])
        ver[s] = verify_min_sets(n, s, own, T)
        if '+' in s:
            xs[s] = dict(alt_to_S=cross_check(n, s, S, own, T), S_to_alt=cross_check(n, S, s, Ssets, T))
        say(f'    {s:12s} min {mins[s]}  exact self-check of its min sets ok/bad {ver[s]}' + (f'  cross {xs[s]}' if s in xs else ''))
    beats = [s for s in specs if s != S and mins[s] > mins[S]]
    res = dict(n=n, specs=specs, trials_per_seed=nch * CHUNK, mins=mins,
               table={f'{c}|{b}|{cy}|{sd}': v for (c, b, cy, sd), v in tb.items()},
               verified=ver, cross=xs, beats=beats, date=str(datetime.datetime.now()))
    jdump(res, R(n, 'stage4.json'))
    say(f'  Stage 4: S min {mins[S]}; circuits that beat S: {beats or "none"}')


def control(n, a):
    st4 = jload(R(n, 'stage4.json')); st3 = jload(R(n, 'stage3.json')); ids = PL.named(n)
    S = str(ids['S']); m = st4['mins']
    alts = {s: v for s, v in m.items() if '+' in s}
    ok_S = m[S] == 6; ok_alt = all(v <= 6 for v in alts.values())
    prev = dict(S=m[S], Sinv=m[str(ids['Sinv'])], alt=m[f'{S}+{ids["Sinv"]}'])
    ok_prev = all(v == 6 for v in prev.values())
    caught_all = st3['n_zero']
    res = dict(S_gives_6=ok_S, every_alt_le_6=ok_alt, alt_values=alts, agrees_with_001=ok_prev, values_001_check=prev,
               partners_catching_all_families=caught_all, PASS=ok_S and ok_alt and ok_prev, date=str(datetime.datetime.now()))
    jdump(res, R(n, 'control.json'))
    say(f'  control: S=6 {ok_S}; every alt <= 6 {ok_alt} {alts}; agrees with 001 {ok_prev} {prev}; '
        f'partners catching all S weight-6 families in Stage 3: {caught_all}')
    if not ok_alt: stop(f'an alternating circuit on [[72]] gives > 6: {alts} (bug)')
    if not res['PASS']: stop(f'[[72]] control check failed: {res}')


# ------------------------------------------------------------------ stage 5
def run_ler_point(n, spec, basis, p, nproc, target=50, batch=500, max_shots=400_000):
    from dcirc import logical_error_rate
    T = PL.load_table(n); f = R(n, 'ler.csv'); F = ['circuit', 'basis', 'p', 'cycles', 'seed', 'shots', 'fails', 'seconds']
    rows = [r for r in csv.DictReader(open(f))] if os.path.exists(f) else []
    mine = [r for r in rows if r['circuit'] == spec and r['basis'] == basis and float(r['p']) == p]
    shots = sum(int(r['shots']) for r in mine); fails = sum(int(r['fails']) for r in mine)
    c = memory_circuit(BBCode(n), PL.scheds_of(spec, T), 6, p, basis)
    os.makedirs(R(n, 'samples'), exist_ok=True)
    while fails < target and shots < max_shots:
        seed = 1000003 * len(mine) + int(p * 1e5) + (basis == 'X')
        r = logical_error_rate(c, batch, osd_order=7, max_iter=100, ms_scale=MS, nproc=nproc, seed=seed)
        np.savez_compressed(R(n, f'samples/{spec}_{basis}_{p}_{seed}.npz'), dets=r['dets'], obs=r['obs'], preds=r['preds'])
        new = not os.path.exists(f)
        with open(f, 'a', newline='') as g:
            w = csv.DictWriter(g, fieldnames=F)
            if new: w.writeheader()
            w.writerow(dict(circuit=spec, basis=basis, p=p, cycles=6, seed=seed, shots=batch, fails=r['fails'], seconds=round(r['seconds'])))
        mine.append(1); shots += batch; fails += r['fails']
        say(f'    LER {spec} {basis} p={p}: {fails}/{shots}')
    return fails, shots


def stage5(n, a):
    st4 = jload(R(n, 'stage4.json'))
    if not st4['beats']:
        jdump(dict(ran=False, reason='no circuit beats S'), R(n, 'stage5.json')); say('  Stage 5 skipped: no circuit beats S'); return
    S = st4['specs'][0]
    win = max(st4['beats'], key=lambda s: (st4['mins'][s], -st4['specs'].index(s)))
    nproc = workers(n, a.nproc); pts = {}
    for b in 'ZX':
        for p in (0.005, 0.004):
            for s in (S, win): pts[(s, b, p)] = run_ler_point(n, s, b, p, nproc)
    from dcirc import per_cycle
    better = all(pts[(win, b, 0.004)][0] / pts[(win, b, 0.004)][1] <= pts[(S, b, 0.004)][0] / pts[(S, b, 0.004)][1] for b in 'ZX')
    if better:
        for b in 'ZX':
            for s in (S, win): pts[(s, b, 0.003)] = run_ler_point(n, s, b, 0.003, nproc)
    jdump(dict(ran=True, S=S, winner=win, points={f'{s}|{b}|{p}': v for (s, b, p), v in pts.items()},
               date=str(datetime.datetime.now())), R(n, 'stage5.json'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, required=True); ap.add_argument('--stage', required=True)
    ap.add_argument('--nproc', type=int, default=12); ap.add_argument('--force', action='store_true')
    a = ap.parse_args(); os.makedirs(R(a.n), exist_ok=True)
    fn = {'0': stage0, '1': stage1, '2': stage2, '3': stage3, '4': stage4, 'control': control, '5': stage5}[a.stage]
    out = R(a.n, f'stage{a.stage}.json' if a.stage != 'control' else 'control.json')
    if os.path.exists(out) and not a.force:
        if json.load(open(out)).get('PASS') is False:
            stop(f'[[{a.n}]] stage {a.stage} failed its PASS condition earlier ({out})')
        say(f'[[{a.n}]] stage {a.stage}: already done ({out})'); sys.exit(0)
    say(f'== [[{a.n}]] stage {a.stage} start {datetime.datetime.now()}')
    fn(a.n, a)
    say(f'== [[{a.n}]] stage {a.stage} done {datetime.datetime.now()}')
