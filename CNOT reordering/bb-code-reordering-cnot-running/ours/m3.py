"""Method 3, Track B (docs/task.md): one-cycle distance ranking with Bravyi's reference setup.

usage: ../../venv/bin/python m3.py --n 90 --stage b0|screen|b3 [--nproc 12]
Run from ours/.  Outputs in ../results_method3/<n>/ ; every finished stage writes <stage>.json and is skipped
on rerun; work units are checkpointed row by row (chunks.csv), so a restarted stage repeats nothing.
Exit code 3 = a PASS condition failed: the driver stops and reports.

d1 naming: d1_X = minimum over X-type faults (Bravyi's 'minimum X weight', HX), d1_Z = over Z-type faults.
Search (Bravyi circuit_distance.py, unchanged decoder call): osd_cs order 20, max_iter 10000, min-sum,
ms_scaling_factor 0; target = random combination of [Hdec; logical rows] with a nonzero logical part.
Trial plan: B0 = S with 3000 trials per fault type (12 seeds x 250); every schedule 200 per fault type
(fixed budget, used for the histogram); a schedule still above d1(S) gets 500-trial chunks until it reaches
d1(S) (then it cannot beat S) or has 9000 per fault type (3x S's B0 budget) = confirmed above d1(S).
"""
import argparse, csv, json, os, sys, time, datetime, itertools, warnings, collections
import multiprocessing as mp
import numpy as np
warnings.filterwarnings('ignore')
from bravyi_d1 import BBRef, to_bravyi, decoding_matrices, d1_search, describe_set
from bb_code import BBCode, memory_circuit, LABELS, BRAVYI, reverse_schedule

BRAVYI_D = {72: 6, 90: 8, 108: 8}; CODE_D = {72: 6, 90: 10, 108: 10}
B0_SEEDS, B0_TRIALS = 12, 250          # 3000 per fault type
BASE, EXT, CONFIRM = 200, 500, 9000
B3_SEEDS, B3_TRIALS = 5, 1000
if os.environ.get('M3_TEST'):          # quick end-to-end test only (writes to M3_RES)
    B0_TRIALS, BASE, EXT, CONFIRM, B3_TRIALS = 5, 3, 3, 9, 3
ROOT = os.environ.get('M3_RES', '../results_method3')
def R(n, f=''): return os.path.join(ROOT, str(n), f)
def say(*a): print(*a, flush=True)
def stop(msg): say(f'== STOP: {msg}'); sys.exit(3)
def jdump(o, f): json.dump(o, open(f, 'w'), indent=1, default=str)
def jload(f): return json.load(open(f))
def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %I:%M %p KST')


# ------------------------------------------------------------------ schedules (same ids as folders 001 / method2)
def _incidence(code):
    xq, zinc = {}, {}
    for lab in LABELS:
        pr = code.x_layer(lab); xq[lab] = {pr[2 * i]: pr[2 * i + 1] for i in range(code.half)}
    for lab in LABELS:
        pr = code.z_layer(lab)
        for i in range(code.half): zinc.setdefault(pr[2 * i], []).append((pr[2 * i + 1], lab))
    return xq, zinc

def _alg_valid(xo, zo, zf, xq, zinc, a):
    xr = {lab: i + (2 if zf else 1) for i, lab in enumerate(xo)}; zr = {lab: i + (1 if zf else 2) for i, lab in enumerate(zo)}
    fl = {}
    for lab in LABELS:
        d = xq[lab][a]; tx = xr[lab]
        for b, lz in zinc[d]:
            if zr[lz] == tx: return False
            if zr[lz] < tx: fl[b] = fl.get(b, 0) ^ 1
    return not any(fl.values())

def schedules(n):
    f = R(n, 'schedules.jsonl')
    if not os.path.exists(f):
        code = BBCode(n); xq, zinc = _incidence(code); a0 = int(code.X[0]); perms = list(itertools.permutations(LABELS))
        V = [(list(xo), list(zo), zf) for zf in (True, False) for xo in perms for zo in perms if _alg_valid(xo, zo, zf, xq, zinc, a0)]
        tup = lambda s: (tuple(s[0]), tuple(s[1]), bool(s[2])); idx = {tup(s): i for i, s in enumerate(V)}
        os.makedirs(R(n), exist_ok=True)
        with open(f, 'w') as g:
            for i, s in enumerate(V):
                g.write(json.dumps(dict(id=i, x=s[0], z=s[1], z_first=s[2], reverse_id=idx.get(tup(reverse_schedule(s))))) + '\n')
    rows = [json.loads(l) for l in open(f)]
    return {r['id']: (r['x'], r['z'], r['z_first']) for r in rows}, {r['id']: r['reverse_id'] for r in rows}

def sid(T, s):
    for i, v in T.items():
        if (list(v[0]), list(v[1]), bool(v[2])) == (list(s[0]), list(s[1]), bool(s[2])): return i


# ------------------------------------------------------------------ work units
_MC = {}
def _mat(n, ids, kind, cycles):
    k = (n, ids, kind, cycles)
    if k not in _MC:
        if len(_MC) > 40: _MC.clear()
        T, _ = schedules(n); code = BBRef(n)
        sch = [to_bravyi(T[i]) for i in ids]
        _MC[k] = (code, decoding_matrices(code, *sch[0], kind, num_cycles=cycles, schedules=sch))
    return _MC[k]

def _job(a):
    n, ids, kind, cycles, chunk, seed, trials = a
    code, M = _mat(n, ids, kind, cycles)
    t = time.time(); r = d1_search(M, trials, seed=seed)
    sets = [dict(weight=w, cols=list(map(int, c)), faults=describe_set(M, c, code)) for w, ss in r['sets'].items() for c in sorted(ss)]
    return a, r, sets, time.time() - t

F = ['tag', 'circuit', 'kind', 'cycles', 'chunk', 'seed', 'trials', 'min', 'hist', 'invalid', 'seconds']
def run_jobs(n, tag, jobs, nproc):
    """jobs: (ids tuple, kind, cycles, chunk, seed, trials).  Skips rows already in chunks.csv."""
    f = R(n, 'chunks.csv'); g = R(n, 'sets.jsonl'); done = set()
    if os.path.exists(f):
        for r in csv.DictReader(open(f)):
            if r['tag'] == tag: done.add((r['circuit'], r['kind'], int(r['cycles']), int(r['chunk']), int(r['seed'])))
    todo = [(n,) + j for j in jobs if ('+'.join(map(str, j[0])), j[1], j[2], j[3], j[4]) not in done]
    if not todo: return
    new = not os.path.exists(f); t0 = time.time()
    with mp.get_context('fork').Pool(nproc) as pool, open(f, 'a', newline='') as fc, open(g, 'a') as fs:
        w = csv.DictWriter(fc, fieldnames=F)
        if new: w.writeheader()
        for i, (a, r, sets, sec) in enumerate(pool.imap_unordered(_job, todo, chunksize=1)):
            _, ids, kind, cycles, chunk, seed, trials = a; circ = '+'.join(map(str, ids))
            for s in sets: fs.write(json.dumps(dict(tag=tag, circuit=circ, kind=kind, cycles=cycles, chunk=chunk, seed=seed, **s)) + '\n')
            fs.flush()
            w.writerow(dict(tag=tag, circuit=circ, kind=kind, cycles=cycles, chunk=chunk, seed=seed, trials=trials, min=r['min'],
                            hist=json.dumps(r['hist']), invalid=r['invalid'], seconds=round(sec, 1))); fc.flush()
            if (i + 1) % 200 == 0 or i + 1 == len(todo):
                el = time.time() - t0
                say(f'    [{tag}] {i+1}/{len(todo)} units, {el/3600:.2f} h, ETA {el/(i+1)*(len(todo)-i-1)/3600:.1f} h')

def table(n, tag):
    """(circuit, kind, cycles) -> [min, trials] over all rows of a tag."""
    out = {}
    f = R(n, 'chunks.csv')
    if not os.path.exists(f): return out
    for r in csv.DictReader(open(f)):
        if r['tag'] != tag or r['min'] == '': continue
        k = (r['circuit'], r['kind'], int(r['cycles'])); m = int(r['min'])
        v = out.setdefault(k, [10**9, 0]); v[0] = min(v[0], m); v[1] += int(r['trials'])
    return out


# ------------------------------------------------------------------ stages
def b0(n, a):
    code = BBRef(n); T, rev = schedules(n); S = sid(T, BRAVYI); Sinv = sid(T, reverse_schedule(BRAVYI))
    sX, sZ = to_bravyi(T[S])
    ref_map = (sX == ['idle', 1, 4, 3, 5, 0, 2] and sZ == [3, 5, 0, 1, 2, 4, 'idle'])
    if not ref_map: stop(f'S does not map to Bravyi sX/sZ: {sX} {sZ}')
    if not code.check_cycle(sX, sZ): stop('S fails the reference circuit test')
    nz = sum(1 for v in T.values() if v[2]); say(f'[[{n}]] k={code.k}; {len(T)} valid schedules (Z-first {nz}); S = #{S}, S^-1 = #{Sinv}')
    run_jobs(n, 'b0', [((S,), k, 1, 0, 1000 + s, B0_TRIALS) for k in 'XZ' for s in range(B0_SEEDS)], a.nproc)
    tb = table(n, 'b0'); d = {k: tb[(str(S), k, 1)] for k in 'XZ'}; d1S = min(v[0] for v in d.values())
    res = dict(n=n, k=code.k, S=S, Sinv=Sinv, schedules=len(T), map_ok=ref_map, d1S_X=d['X'], d1S_Z=d['Z'], d1S=d1S,
               bravyi=BRAVYI_D[n], PASS=d1S == BRAVYI_D[n], date=now())
    jdump(res, R(n, 'b0.json'))
    say(f'  B0: d1(S) X-type {d["X"][0]}, Z-type {d["Z"][0]} ({d["X"][1]} / {d["Z"][1]} trials) -> {d1S} vs Bravyi {BRAVYI_D[n]}')
    if not res['PASS']: stop(f'[[{n}]] B0: d1(S) = {d1S} != Bravyi {BRAVYI_D[n]} (3000 trials per fault type)')


def screen(n, a):
    T, rev = schedules(n); b = jload(R(n, 'b0.json')); d1S = b['d1S']
    ids = sorted(T)
    say(f'  screen: {len(ids)} schedules x 2 fault types x {BASE} trials (d1(S) = {d1S})')
    run_jobs(n, 'base', [((i,), k, 1, 0, 7 * i + (k == 'Z'), BASE) for i in ids for k in 'XZ'], a.nproc)
    rnd = 0
    while True:
        base = table(n, 'base'); ext = table(n, 'ext')
        cur = {}
        for i in ids:
            for k in 'XZ':
                m0, t0 = base[(str(i), k, 1)]; m1, t1 = ext.get((str(i), k, 1), [10**9, 0]); cur[(i, k)] = [min(m0, m1), t0 + t1]
        cand = [i for i in ids if min(cur[(i, 'X')][0], cur[(i, 'Z')][0]) > d1S]
        need = [(i, k) for i in cand for k in 'XZ' if cur[(i, k)][1] < CONFIRM]
        say(f'  round {rnd}: {len(cand)} schedules above d1(S) = {d1S}; {len(need)} (schedule, fault type) pairs below {CONFIRM} trials')
        if not need: break
        nxt = {}
        f = R(n, 'chunks.csv')
        for r in csv.DictReader(open(f)):
            if r['tag'] == 'ext': nxt[(int(r['circuit']), r['kind'])] = max(nxt.get((int(r['circuit']), r['kind']), -1), int(r['chunk']))
        run_jobs(n, 'ext', [((i,), k, 1, nxt.get((i, k), -1) + 1, 100000 + 7 * i + (k == 'Z') + 13 * (nxt.get((i, k), -1) + 1), EXT)
                            for i, k in need], a.nproc)
        rnd += 1
    # final table
    with open(R(n, f'd1_{n}.csv'), 'w', newline='') as g:
        w = csv.writer(g); w.writerow(['id', 'd1_Z', 'd1_X', 'trials_Z', 'trials_X', 'd1_Z_base200', 'd1_X_base200', 'reverse_id', 'x_order', 'z_order', 'z_first'])
        for i in ids:
            w.writerow([i, cur[(i, 'Z')][0], cur[(i, 'X')][0], cur[(i, 'Z')][1], cur[(i, 'X')][1], base[(str(i), 'Z', 1)][0],
                        base[(str(i), 'X', 1)][0], rev[i], ' '.join(T[i][0]), ' '.join(T[i][1]), T[i][2]])
    d1 = {i: min(cur[(i, 'X')][0], cur[(i, 'Z')][0]) for i in ids}
    mx = max(d1.values()); top = sorted(i for i in ids if d1[i] == mx)
    conf = sorted(i for i in ids if d1[i] > d1S)
    res = dict(n=n, d1S=d1S, hist=dict(sorted(collections.Counter(d1.values()).items())),
               hist_base200=dict(sorted(collections.Counter(min(base[(str(i), 'X', 1)][0], base[(str(i), 'Z', 1)][0]) for i in ids).items())),
               max=mx, at_max=top[:200], n_at_max=len(top), above_S=conf, n_above_S=len(conf), date=now())
    jdump(res, R(n, 'screen.json'))
    say(f'  screen: d1 histogram {res["hist"]}; max {mx} reached by {len(top)} schedules; confirmed above d1(S): {len(conf)} {conf[:20]}')
    if n == 72 and conf: stop(f'[[72]] control: {len(conf)} schedules have d1 > 6 after {CONFIRM} trials per fault type (bug): {conf[:20]}')


def _noiseless_ok(n, scheds):
    code = BBCode(n)
    for basis in 'ZX':
        try: c = memory_circuit(code, scheds, 4, 0.0, basis)
        except ValueError: return False
        if c.compile_detector_sampler().sample(4).any(): return False
    return True


def verify_set(n, ids, kind, cycles, cols):
    """Exact re-simulation of the set's physical faults inserted TOGETHER (one representative per column):
    returns (syndrome all zero, logical flipped)."""
    code, M = _mat(n, ids, kind, cycles)
    from bravyi_d1 import joint_effect
    syn, log = joint_effect(code, n, [to_bravyi(schedules(n)[0][i]) for i in ids], kind, cycles, [M['faults'][j][0] for j in cols])
    return (not syn.any()), bool(log.any())


def b3(n, a):
    T, rev = schedules(n); s = jload(R(n, 'screen.json')); b = jload(R(n, 'b0.json')); S = b['S']; d1S = b['d1S']
    cands = s['above_S']; out = dict(n=n, candidates=cands, circuits={}, date=now())
    if not cands:
        out['note'] = 'no schedule has a confirmed d1 above d1(S): B3 not needed'
        jdump(out, R(n, 'b3.json')); say('  B3: no candidates'); return
    circs = [(S,)] + [(A, rev[A]) for A in cands]
    for c in circs:
        ok = _noiseless_ok(n, [T[i] for i in c]); out['circuits']['+'.join(map(str, c))] = dict(noiseless_ok=ok)
        if not ok: stop(f'alt {c}: nonzero noiseless detectors')
    jobs = [(c, k, cy, sd, 5000 + 100 * sd + cy + (k == 'Z'), B3_TRIALS) for c in circs for k in 'XZ' for cy in (4, 6) for sd in range(1, B3_SEEDS + 1)]
    run_jobs(n, 'b3', jobs, a.nproc)
    tb = table(n, 'b3')
    for c in circs:
        key = '+'.join(map(str, c)); mins = {f'{k}{cy}': tb[(key, k, cy)][0] for k in 'XZ' for cy in (4, 6)}
        out['circuits'][key].update(mins=mins, min=min(mins.values()))
    # exact check of every minimum-weight set of each circuit
    for line in open(R(n, 'sets.jsonl')):
        r = json.loads(line)
        if r['tag'] != 'b3' or r['weight'] != out['circuits'][r['circuit']]['min']: continue
        ids = tuple(int(x) for x in r['circuit'].split('+'))
        und, logi = verify_set(n, ids, r['kind'], r['cycles'], r['cols'])
        v = out['circuits'][r['circuit']].setdefault('exact', collections.Counter()); v['ok' if und and logi else 'FAIL'] += 1
    Smin = out['circuits'][str(S)]['min']
    out['beats'] = [k for k, v in out['circuits'].items() if '+' in k and v['min'] > Smin]
    jdump(out, R(n, 'b3.json'))
    say(f'  B3: S min {Smin}; ' + '; '.join(f'{k}: {v["min"]}' for k, v in out['circuits'].items()) + f'; beats S: {out["beats"] or "none"}')
    if out['beats']: ler(n, a, S, out['beats'])


def ler_points(n, a, circuits, ps=(0.005, 0.004)):
    """LER: our stim builder, full circuit-level depolarising noise, BP-OSD (min-sum 0.625, 100 iterations,
    OSD-CS 7), 6 cycles, Z basis first, >= 50 failures per point, raw samples saved.  Resumable (ler.csv)."""
    from dcirc import logical_error_rate
    T, _ = schedules(n); f = R(n, 'ler.csv'); os.makedirs(R(n, 'samples'), exist_ok=True)
    FL = ['circuit', 'basis', 'p', 'cycles', 'seed', 'shots', 'fails', 'seconds']
    for basis in 'ZX':
        for p in ps:
            for circ in circuits:
                rows = list(csv.DictReader(open(f))) if os.path.exists(f) else []
                mine = [r for r in rows if r['circuit'] == circ and r['basis'] == basis and float(r['p']) == p]
                fails = sum(int(r['fails']) for r in mine); shots = sum(int(r['shots']) for r in mine)
                c = memory_circuit(BBCode(n), [T[int(i)] for i in circ.split('+')], 6, p, basis)
                while fails < 50 and shots < 400000:
                    seed = 7919 * (len(mine) + 1) + int(p * 1e5) + (basis == 'X')
                    r = logical_error_rate(c, 500, osd_order=7, max_iter=100, ms_scale=0.625, nproc=a.nproc, seed=seed)
                    np.savez_compressed(R(n, f'samples/{circ}_{basis}_{p}_{seed}.npz'), dets=r['dets'], obs=r['obs'], preds=r['preds'])
                    new = not os.path.exists(f)
                    with open(f, 'a', newline='') as g:
                        w = csv.DictWriter(g, fieldnames=FL)
                        if new: w.writeheader()
                        w.writerow(dict(circuit=circ, basis=basis, p=p, cycles=6, seed=seed, shots=500, fails=r['fails'], seconds=round(r['seconds'])))
                    mine.append(1); fails += r['fails']; shots += 500
                    say(f'    LER {circ} {basis} p={p}: {fails}/{shots}')


def ler(n, a, S, beats):
    """B3 LER (only if a circuit beats S): S vs the best alternating circuit."""
    best = max(beats, key=lambda k: jload(R(n, 'b3.json'))['circuits'][k]['min'])
    ler_points(n, a, [str(S), best])


def extra(n, a):
    """Extra stage (user request 2026-10-18, not in task.md): circuit-level distance and LER for
    S, alt[S, S^-1], A* and alt[A*, A*^-1].  A* = the schedule at the maximum d1 whose search needed the most
    trials to reach that value (fewest minimum-weight one-cycle paths found); ties -> lowest id.
    Distance: Bravyi setup, 4 and 6 noisy cycles + 2 noiseless, X and Z faults, 5 seeds x 1000 trials, minimum
    paths exactly re-simulated.  LER: ler_points (6 cycles, p = 0.5% and 0.4%, both bases, >= 50 failures)."""
    circs, out = extra_circuits(n)
    T, _ = schedules(n)
    for c in circs:
        ok = _noiseless_ok(n, [T[i] for i in c]); out['circuits']['+'.join(map(str, c))] = dict(noiseless_ok=ok)
        if not ok: stop(f'{c}: nonzero noiseless detectors')
    jobs = [(c, k, cy, sd, 5000 + 100 * sd + cy + (k == 'Z'), B3_TRIALS) for c in circs for k in 'XZ' for cy in (4, 6) for sd in range(1, B3_SEEDS + 1)]
    run_jobs(n, 'dcirc', jobs, a.nproc)
    tb = table(n, 'dcirc')
    for c in circs:
        key = '+'.join(map(str, c)); mins = {f'{k}{cy}': tb[(key, k, cy)][0] for k in 'XZ' for cy in (4, 6)}
        out['circuits'][key].update(mins=mins, min=min(mins.values()))
    for line in open(R(n, 'sets.jsonl')):
        r = json.loads(line)
        if r['tag'] != 'dcirc' or r['weight'] != out['circuits'][r['circuit']]['min']: continue
        und, logi = verify_set(n, tuple(int(x) for x in r['circuit'].split('+')), r['kind'], r['cycles'], r['cols'])
        v = out['circuits'][r['circuit']].setdefault('exact', collections.Counter()); v['ok' if und and logi else 'FAIL'] += 1
    say('  extra distance: ' + '; '.join(f'{k}: {v["min"]} {v["mins"]}' for k, v in out['circuits'].items()))
    jdump(out, R(n, 'extra_dcirc.json'))
    ler_points(n, a, list(out['circuits']))
    jdump(out, R(n, 'extra.json'))


def extra_circuits(n):
    """S, alt[S,S^-1], A*, alt[A*,A*^-1] (A* = at the maximum d1, most search trials to reach it; ties -> lowest id)."""
    T, rev = schedules(n); b = jload(R(n, 'b0.json')); s = jload(R(n, 'screen.json')); S = b['S']
    trials = collections.Counter()
    for r in csv.DictReader(open(R(n, 'chunks.csv'))):
        if r['tag'] in ('base', 'ext'): trials[int(r['circuit'])] += int(r['trials'])
    top = [i for i in s['at_max']] if s['n_at_max'] <= len(s['at_max']) else None
    d1 = {}
    for r in csv.DictReader(open(R(n, f'd1_{n}.csv'))): d1[int(r['id'])] = min(int(r['d1_Z']), int(r['d1_X']))
    mx = max(d1.values()); pool = [i for i in d1 if d1[i] == mx and i != S]
    Astar = max(pool, key=lambda i: (trials[i], -i))
    circs = [(S,), (S, rev[S]), (Astar,), (Astar, rev[Astar])]
    out = dict(n=n, A_star=Astar, A_star_trials=trials[Astar], A_star_d1=mx, circuits={}, date=now())
    say(f'  extra: A* = #{Astar} (d1 {mx}, {trials[Astar]} search trials before reaching it); circuits {circs}')
    return circs, out


def ler_stage(n, a):
    """LER first (user request 2026-10-18): the four extra circuits, see ler_points."""
    circs, out = extra_circuits(n)
    ler_points(n, a, ['+'.join(map(str, c)) for c in circs])
    jdump(dict(out, circuits=['+'.join(map(str, c)) for c in circs]), R(n, 'ler.json'))



if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, required=True); ap.add_argument('--stage', required=True)
    ap.add_argument('--nproc', type=int, default=12); a = ap.parse_args(); os.makedirs(R(a.n), exist_ok=True)
    out = R(a.n, f'{a.stage}.json')
    if os.path.exists(out):
        if jload(out).get('PASS') is False: stop(f'[[{a.n}]] {a.stage} failed its PASS condition earlier')
        say(f'[[{a.n}]] {a.stage}: already done'); sys.exit(0)
    say(f'== [[{a.n}]] {a.stage} start {now()}')
    {'b0': b0, 'screen': screen, 'b3': b3, 'extra': extra, 'ler': ler_stage}[a.stage](a.n, a)
    say(f'== [[{a.n}]] {a.stage} done {now()}')
