"""
Experiment 1: Bravyi schedule S vs its time-reverse S^-1 vs alternating
(S, S^-1, S, S^-1, ...) on the [[72,12,6]] BB code, both memory bases.

Stage A: randomized upper bound on circuit-level distance for each config.
Stage B: logical error rate vs p with BP-OSD.

Results are appended to a JSON file as they are produced, so a killed run
keeps its partial output.

usage: python run_experiment1.py [--n 72] [--cycles 6] [--bound-trials 1000]
         [--shots 2000] [--pvals 0.002 0.004 0.006 0.008] [--out results/exp1.json]
         [--skip-bounds] [--skip-ler] [--nproc 12]
"""
import argparse, json, os, time, sys
import numpy as np
import multiprocessing as mp
from bb_code import BBCode, BRAVYI, reverse_schedule, memory_circuit
from dcirc import dem_matrices, dcirc_bound, logical_error_rate, per_cycle, wilson

CONFIGS = {
    'S':     [BRAVYI],
    'Sinv':  [reverse_schedule(BRAVYI)],
    'alt':   [BRAVYI, reverse_schedule(BRAVYI)],
}


def save(out, data):
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    tmp = out + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=1, default=lambda o: sorted(map(int, o)) if isinstance(o, frozenset) else str(o))
    os.replace(tmp, out)


def _bound_job(args):
    n, name, basis, cycles, p, trials, seed, osd_order, bound_iter = args
    code = BBCode(n)
    circ = memory_circuit(code, CONFIGS[name], cycles, p, basis)
    H, L, pri = dem_matrices(circ)
    r = dcirc_bound(H, L, trials=trials, osd_order=osd_order, seed=seed, max_iter=bound_iter)
    r['min_supports'] = [sorted(map(int, s)) for s in list(r['min_supports'])[:20]]
    return name, basis, seed, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=72)
    ap.add_argument('--cycles', type=int, default=6)
    ap.add_argument('--bound-trials', type=int, default=1000)
    ap.add_argument('--bound-p', type=float, default=0.001)
    ap.add_argument('--bound-osd', type=int, default=20)
    ap.add_argument('--shots', type=int, nargs='+', default=[2000])
    ap.add_argument('--pvals', type=float, nargs='+', default=[0.002, 0.004, 0.006, 0.008])
    ap.add_argument('--osd-order', type=int, default=7)
    ap.add_argument('--max-iter', type=int, default=100)
    ap.add_argument('--bound-iter', type=int, default=10)
    ap.add_argument('--schedule', default='serial')
    ap.add_argument('--ms-scale', type=float, default=1.0)
    ap.add_argument('--nproc', type=int, default=os.cpu_count())
    ap.add_argument('--out', default='results/exp1_72.json')
    ap.add_argument('--skip-bounds', action='store_true')
    ap.add_argument('--skip-ler', action='store_true')
    ap.add_argument('--configs', nargs='+', default=list(CONFIGS))
    ap.add_argument('--bases', nargs='+', default=['Z', 'X'])
    a = ap.parse_args()

    data = {'args': vars(a), 'bounds': {}, 'ler': []}
    if os.path.exists(a.out):
        with open(a.out) as f:
            data = json.load(f)
        data['args'] = vars(a)
    save(a.out, data)
    shots_of = {p: (a.shots[i] if i < len(a.shots) else a.shots[-1]) for i, p in enumerate(a.pvals)}

    # ---------------- Stage A: distance bounds (parallel over seeds) --------
    if not a.skip_bounds:
        print(f'== Stage A: d_circ bounds, n={a.n}, cycles={a.cycles}, '
              f'{a.bound_trials} trials/config split over {a.nproc} workers', flush=True)
        jobs = []
        per = max(1, a.bound_trials // a.nproc)
        for name in a.configs:
            for basis in a.bases:
                for s in range(a.nproc):
                    jobs.append((a.n, name, basis, a.cycles, a.bound_p, per, s, a.bound_osd, a.bound_iter))
        t0 = time.time()
        with mp.get_context('fork').Pool(a.nproc) as pool:
            results = pool.map(_bound_job, jobs)
        agg = {}
        for name, basis, seed, r in results:
            key = f'{name}/{basis}'
            g = agg.setdefault(key, dict(min_weight=10**9, hist={}, min_supports=set(), trials=0))
            for w, c in r['hist'].items():
                g['hist'][int(w)] = g['hist'].get(int(w), 0) + c
            g['trials'] += r['trials']
            if r['min_weight'] < g['min_weight']:
                g['min_weight'] = r['min_weight']; g['min_supports'] = set(map(tuple, r['min_supports']))
            elif r['min_weight'] == g['min_weight']:
                g['min_supports'] |= set(map(tuple, r['min_supports']))
        for key, g in agg.items():
            g['n_min_paths_found'] = len(g['min_supports'])
            g['min_supports'] = [list(s) for s in list(g['min_supports'])[:20]]
            g['hist'] = dict(sorted(g['hist'].items()))
            data['bounds'][key] = g
            print(f'  {key:8s}: d_circ <= {g["min_weight"]}  hist={g["hist"]}  '
                  f'distinct min-weight paths found={g["n_min_paths_found"]}', flush=True)
        print(f'  stage A took {time.time()-t0:.0f}s', flush=True)
        save(a.out, data)

    # ---------------- Stage B: LER vs p ------------------------------------
    if not a.skip_ler:
        print(f'== Stage B: LER, cycles={a.cycles}, osd_order={a.osd_order}, max_iter={a.max_iter}', flush=True)
        done = {(r['config'], r['basis'], r['p']) for r in data['ler']}
        code = BBCode(a.n)
        for p in a.pvals:
            for name in a.configs:
                for basis in a.bases:
                    if (name, basis, p) in done:
                        continue
                    circ = memory_circuit(code, CONFIGS[name], a.cycles, p, basis)
                    r = logical_error_rate(circ, shots_of[p], osd_order=a.osd_order,
                                           max_iter=a.max_iter, nproc=a.nproc, schedule=a.schedule, ms_scale=a.ms_scale,
                                           seed=int(p * 1e6) + hash(name + basis) % 1000)
                    lo, hi = wilson(r['fails'], r['shots'])
                    r.update(config=name, basis=basis, p=p, cycles=a.cycles,
                             ler_per_cycle=per_cycle(r['ler'], a.cycles),
                             ci95=[lo, hi])
                    data['ler'].append(r)
                    save(a.out, data)
                    print(f'  p={p:.4f} {name:5s} {basis}: fails={r["fails"]}/{r["shots"]} '
                          f'LER={r["ler"]:.4g} [{lo:.3g},{hi:.3g}] per-cycle={r["ler_per_cycle"]:.3g} '
                          f'BPconv={r["bp_converged_frac"]:.2f} ({r["seconds"]:.0f}s, '
                          f'{r["seconds"]/r["shots"]*a.nproc:.2f}s/shot/core)', flush=True)
    print('done', flush=True)


if __name__ == '__main__':
    main()
