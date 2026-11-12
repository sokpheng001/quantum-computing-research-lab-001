"""Verification STEP 2: strong multi-seed d_circ search on [[144]], 4 cycles, for S and
alt S/S^-1, both bases, 5 independent seeds.  Settings as the earlier search: OSD-CS
order 20, serial min-sum, 10 BP iterations, random channel priors in [0.005, 0.1].

Work is split into 200-trial chunks and run round-robin (chunk k of every
circuit/basis/seed before chunk k+1), so at any moment all 20 streams have the same
number of trials.  Milestone: 12 chunks/seed = 2400 trials/seed = 12000 per
circuit/basis = 3x the previous 4000.  Continues to --max-chunks (default 60 = 12000
trials/seed).  Every chunk is one CSV row (results/strong_144.csv, resumable) and every
fault set of weight <= 11 is appended to results/strong_sets_144.jsonl with its
schedule-independent DEM column key [detectors, observables].
Optional early stop (--stop-alt): if alt reaches <= 10 in any basis on any seed.
"""
import argparse, csv, json, os, time
import multiprocessing as mp
from bb_code import BBCode, memory_circuit
from dcirc import dem_matrices, dem_columns, dcirc_bound
from sched_ids import table

CSV, SETS = 'results/strong_{n}.csv', 'results/strong_sets_{n}.jsonl'
F = ['n', 'cycles', 'circuit', 'basis', 'seed', 'chunk', 'rng_seed', 'trials', 'min_weight', 'hist', 'n_sets_le11', 'seconds']
# S^-1 appended last so the rng seeds of the first four configs are unchanged
CFGS = [('212', 'Z'), ('212', 'X'), ('212+1307', 'Z'), ('212+1307', 'X'), ('1307', 'Z'), ('1307', 'X')]
_C = {}

def _dem(circ, basis, cycles, n):
    k = (circ, basis, n)
    if k not in _C:
        c = memory_circuit(BBCode(n), [table()[int(i)] for i in circ.split('+')], cycles, 0.001, basis)
        dem = c.detector_error_model(flatten_loops=True)
        H, L, _ = dem_matrices(dem); keys = list(dem_columns(dem))
        assert len(keys) == H.shape[1]
        _C[k] = (H, L, keys)
    return _C[k]

def job(a):
    circ, basis, seed, chunk, rs, trials, cycles, n = a
    H, L, keys = _dem(circ, basis, cycles, n)
    r = dcirc_bound(H, L, trials=trials, osd_order=20, max_iter=10, seed=rs, keep_le=11)
    sets = [(w, [[list(keys[j][0]), list(keys[j][1])] for j in sorted(map(int, s))]) for w, ss in r['supports'].items() for s in ss]
    return circ, basis, seed, chunk, rs, r, sets

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nproc', type=int, default=8); ap.add_argument('--seeds', type=int, default=5)
    ap.add_argument('--chunk', type=int, default=200); ap.add_argument('--max-chunks', type=int, default=60)
    ap.add_argument('--cycles', type=int, default=4); ap.add_argument('--n', type=int, default=144); ap.add_argument('--stop-alt', action='store_true')
    a = ap.parse_args()
    global CSV, SETS; CSV, SETS = CSV.format(n=a.n), SETS.format(n=a.n)
    done = set()
    if os.path.exists(CSV):
        for r in csv.DictReader(open(CSV)): done.add((r['circuit'], r['basis'], int(r['seed']), int(r['chunk'])))
    jobs = [(c, b, s, k, 10**7 * s + 1000 * k + 10 * i, a.chunk, a.cycles, a.n)
            for k in range(a.max_chunks) for s in range(1, a.seeds + 1) for i, (c, b) in enumerate(CFGS)
            if (c, b, s, k) not in done]
    print(f'{len(done)} chunks done, {len(jobs)} to go, {a.chunk} trials each, {a.nproc} workers', flush=True)
    new = not os.path.exists(CSV); t0 = time.time(); n = 0
    with mp.get_context('fork').Pool(a.nproc) as pool, open(CSV, 'a', newline='') as f, open(SETS, 'a') as g:
        w = csv.DictWriter(f, fieldnames=F)
        if new: w.writeheader()
        for circ, basis, seed, chunk, rs, r, sets in pool.imap(job, jobs, chunksize=1):
            w.writerow(dict(n=a.n, cycles=a.cycles, circuit=circ, basis=basis, seed=seed, chunk=chunk, rng_seed=rs, trials=r['trials'],
                            min_weight=r['min_weight'], hist=json.dumps(r['hist']), n_sets_le11=len(sets), seconds=round(r['seconds'], 1)))
            for wt, st in sets:
                g.write(json.dumps(dict(circuit=circ, basis=basis, seed=seed, chunk=chunk, weight=wt, set=st)) + '\n')
            f.flush(); g.flush(); n += 1
            print(f'  {circ:9s} {basis} seed {seed} chunk {chunk:2d}: min {r["min_weight"]:2d}  sets<=11 {len(sets):3d}  '
                  f'({r["seconds"]:.0f}s)  [{n}/{len(jobs)}, {(time.time()-t0)/3600:.1f} h]', flush=True)
            if a.stop_alt and '+' in circ and r['min_weight'] <= 10:
                print(f'== STOP: alt reached {r["min_weight"]} in {basis} (seed {seed}, chunk {chunk}): no distance gain', flush=True)
                pool.terminate(); break
    print('done', flush=True)

if __name__ == '__main__':
    main()
