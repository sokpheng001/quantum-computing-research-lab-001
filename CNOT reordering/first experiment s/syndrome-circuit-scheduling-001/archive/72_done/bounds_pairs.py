"""d_circ bound (+ saved fault sets) for arbitrary schedule specs, e.g. single '5',
alternating pair '5+931', on [[72]] or [[144]].  Trials are split into chunks across
workers.  Appends to --out (resumable: finished (spec, basis) rows are skipped).

usage: bounds_pairs.py --n 144 --cycles 4 --trials 4000 --nproc 12 --specs 212,212+1307,5+931 --out results/exp_144_bounds.csv
"""
import argparse, csv, json, os, time
import multiprocessing as mp
from bb_code import BBCode, memory_circuit
from dcirc import dem_matrices, dem_columns, dcirc_bound
from sched_ids import table

FIELDS = ['n', 'basis', 'cycles', 'p', 'trials', 'seed', 'sched', 'bound', 'n_min_paths', 'hist', 'seconds']
_A = {}

def job(args):
    spec, basis, seed, trials = args
    code = BBCode(_A['n']); ids = [int(t) for t in spec.split('+')]
    circ = memory_circuit(code, [table()[i] for i in ids], _A['cycles'], _A['p'], basis)
    H, L, _ = dem_matrices(circ)
    r = dcirc_bound(H, L, trials=trials, osd_order=20, max_iter=10, seed=seed)
    return spec, basis, r['min_weight'], r['hist'], [sorted(map(int, s)) for s in r['min_supports']], r['trials'], r['seconds']

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=72); ap.add_argument('--cycles', type=int, default=4)
    ap.add_argument('--p', type=float, default=0.001); ap.add_argument('--trials', type=int, default=600)
    ap.add_argument('--nproc', type=int, default=os.cpu_count()); ap.add_argument('--specs', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--chunks', type=int, default=12)
    ap.add_argument('--tag', default='', help='suffix for results/faultsets/<n>_<basis>_<spec><tag>.json')
    a = ap.parse_args(); _A.update(n=a.n, cycles=a.cycles, p=a.p)
    specs = [s for s in a.specs.split(',') if s]
    done = set()
    if os.path.exists(a.out):
        for r in csv.DictReader(open(a.out)):
            if int(r['n']) == a.n and int(r['cycles']) == a.cycles: done.add((r['sched'], r['basis']))
    cfgs = [(s, b) for s in specs for b in 'ZX' if (s, b) not in done]
    print(f'{len(cfgs)} configs x {a.chunks} chunks, {a.trials} trials each, {a.nproc} workers', flush=True)
    per = max(1, a.trials // a.chunks)
    jobs = [(s, b, 7919 * k + 13 * len(s) + (b == 'X'), per) for s, b in cfgs for k in range(a.chunks)]
    acc = {c: dict(best=10**9, hist={}, sets={}, trials=0, seconds=0.0) for c in cfgs}
    t0 = time.time(); k = 0
    with mp.get_context('fork').Pool(a.nproc) as pool:
        for spec, basis, mw, hist, sets, tr, sec in pool.imap_unordered(job, jobs, chunksize=1):
            g = acc[(spec, basis)]
            for w, c in hist.items(): g['hist'][w] = g['hist'].get(w, 0) + c
            if mw <= g['best']:
                if mw < g['best']: g['sets'] = {}
                g['best'] = mw
                for s in sets: g['sets'][tuple(s)] = 1
            g['trials'] += tr; g['seconds'] += sec; k += 1
            if k % a.chunks == 0: print(f'  {k}/{len(jobs)} chunks, {(time.time()-t0)/60:.0f} min', flush=True)
    os.makedirs('results/faultsets', exist_ok=True)
    new = not os.path.exists(a.out)
    with open(a.out, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        for (spec, basis), g in acc.items():
            code = BBCode(a.n); ids = [int(t) for t in spec.split('+')]
            keys = list(dem_columns(memory_circuit(code, [table()[i] for i in ids], a.cycles, a.p, basis)))
            sets = [[[list(keys[j][0]), list(keys[j][1])] for j in s] for s in g['sets']]
            json.dump(dict(n=a.n, basis=basis, cycles=a.cycles, p=a.p, sched=spec, trials=g['trials'], bound=g['best'],
                           n_min_paths=len(sets), sets=sets), open(f'results/faultsets/{a.n}_{basis}_{spec}{a.tag}.json', 'w'))
            w.writerow(dict(n=a.n, basis=basis, cycles=a.cycles, p=a.p, trials=g['trials'], seed='chunked', sched=spec,
                            bound=f"<= {g['best']}", n_min_paths=len(sets), hist=json.dumps(dict(sorted(g['hist'].items()))), seconds=round(g['seconds'], 1)))
            print(f'  {spec:12s} {basis}  d_circ <= {g["best"]}  min-weight sets {len(sets)}  hist {dict(sorted(g["hist"].items()))}', flush=True)
    print('done', flush=True)

if __name__ == '__main__':
    main()
