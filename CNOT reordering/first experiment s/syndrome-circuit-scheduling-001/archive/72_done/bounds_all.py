"""
Phase 3.1 + 3.2 (TASK2 task A): d_circ upper bound and number of distinct
min-weight fault sets for every schedule in results/schedules.jsonl, both
bases, [[72]], cycles = 4.  Appends to results/bounds_936.csv (resumable).
Every min-weight fault set is also saved to results/faultsets/<n>_<basis>_<id>.json
with the schedule-independent DEM column key (detector ids, observable ids)
so that fault sets of different schedules can be intersected (Phase 4.2).

usage: python bounds_all.py [--cycles 4] [--trials 60] [--nproc 12] [--ids 0-935]
"""
import argparse, csv, json, os, time
import multiprocessing as mp
from bb_code import BBCode, memory_circuit
from dcirc import dem_matrices, dem_columns, dcirc_bound
from sched_ids import table

CSV = 'results/bounds_936.csv'
FIELDS = ['n', 'basis', 'cycles', 'p', 'trials', 'seed', 'sched', 'bound', 'n_min_paths', 'hist', 'min_paths', 'seconds']
_A = {}


def job(args):
    sid, basis = args
    code = BBCode(_A['n'])
    circ = memory_circuit(code, [table()[sid]], _A['cycles'], _A['p'], basis)
    H, L, _ = dem_matrices(circ)
    keys = list(dem_columns(circ))
    seed = 1000 * sid + (basis == 'X')
    r = dcirc_bound(H, L, trials=_A['trials'], osd_order=20, max_iter=10, seed=seed, keep_le=8)
    paths = [sorted(map(int, s)) for s in list(r['min_supports'])[:200]]
    os.makedirs('results/faultsets', exist_ok=True)
    sets = [[[list(keys[j][0]), list(keys[j][1])] for j in sorted(map(int, s))] for s in r['min_supports']]
    json.dump(dict(n=_A['n'], basis=basis, cycles=_A['cycles'], p=_A['p'], sched=sid, trials=r['trials'],
                   bound=r['min_weight'], n_min_paths=r['n_min_paths'], sets=sets),
              open(f"results/faultsets/{_A['n']}_{basis}_{sid}.json", 'w'))
    return dict(n=_A['n'], basis=basis, cycles=_A['cycles'], p=_A['p'], trials=r['trials'], seed=seed, sched=sid,
                bound=f"<= {r['min_weight']}", n_min_paths=r['n_min_paths'],
                hist=json.dumps({int(k): v for k, v in r['hist'].items()}), min_paths=json.dumps(paths),
                seconds=round(r['seconds'], 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=72); ap.add_argument('--cycles', type=int, default=4)
    ap.add_argument('--p', type=float, default=0.001); ap.add_argument('--trials', type=int, default=60)
    ap.add_argument('--nproc', type=int, default=os.cpu_count()); ap.add_argument('--ids', default='0-1871')
    a = ap.parse_args(); _A.update(n=a.n, cycles=a.cycles, p=a.p, trials=a.trials)
    lo, hi = map(int, a.ids.split('-'))
    done = set()
    if os.path.exists(CSV):
        for r in csv.DictReader(open(CSV)):
            if int(r['n']) == a.n and int(r['cycles']) == a.cycles:
                done.add((int(r['sched']), r['basis']))
    jobs = [(i, b) for i in range(lo, hi + 1) for b in 'ZX' if (i, b) not in done]
    print(f'{len(done)} done, {len(jobs)} jobs, cycles={a.cycles}, trials={a.trials}, {a.nproc} workers', flush=True)
    new = not os.path.exists(CSV); t0 = time.time(); k = 0
    with mp.get_context('fork').Pool(a.nproc) as pool, open(CSV, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        for r in pool.imap_unordered(job, jobs, chunksize=1):
            w.writerow(r); f.flush(); k += 1
            if k % 24 == 0 or k == len(jobs):
                el = time.time() - t0
                print(f'  {k}/{len(jobs)}  {el/60:.0f} min elapsed, eta {el/k*(len(jobs)-k)/60:.0f} min', flush=True)
    print('done', flush=True)


if __name__ == '__main__':
    main()
