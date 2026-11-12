"""
Batch logical-error-rate runner.  Appends one CSV row per batch to
results/ler.csv and keeps sampling until `target_fails` failures have been
accumulated for this (n, basis, cycles, p, sched) or `max_shots` is reached
(earlier rows for the same key count).

usage: python run_ler.py --sched S|Sinv|alt|<id>|<id+id> --basis Z --p 0.003
         [--n 72] [--cycles 6] [--target-fails 50] [--max-shots 20000] [--batch 2000]
"""
import argparse, csv, os, time, zlib
import numpy as np
from bb_code import BBCode, memory_circuit
from dcirc import logical_error_rate
from sched_ids import resolve

CSV = 'results/ler.csv'
SAMPLES = 'results/samples'
FIELDS = ['n', 'basis', 'cycles', 'p', 'shots', 'seed', 'sched', 'fails', 'bp_conv', 'seconds', 'source']


def load(key):
    shots = fails = 0
    if os.path.exists(CSV):
        for r in csv.DictReader(open(CSV)):
            if (int(r['n']), r['basis'], int(r['cycles']), float(r['p']), r['sched']) == key:
                shots += int(r['shots']); fails += int(r['fails'])
    return shots, fails


def append(row):
    new = not os.path.exists(CSV)
    with open(CSV, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sched', required=True); ap.add_argument('--basis', required=True)
    ap.add_argument('--p', type=float, required=True)
    ap.add_argument('--n', type=int, default=72); ap.add_argument('--cycles', type=int, default=6)
    ap.add_argument('--target-fails', type=int, default=50); ap.add_argument('--max-shots', type=int, default=20000)
    ap.add_argument('--batch', type=int, default=2000); ap.add_argument('--nproc', type=int, default=os.cpu_count())
    ap.add_argument('--csv', default=CSV); ap.add_argument('--no-samples', action='store_true')
    a = ap.parse_args()
    globals()['CSV'] = a.csv
    label, scheds = resolve(a.sched)
    key = (a.n, a.basis, a.cycles, a.p, label)
    shots, fails = load(key)
    print(f'[{label} {a.basis} p={a.p}] start: {fails}/{shots} failures', flush=True)
    code = BBCode(a.n)
    circ = memory_circuit(code, scheds, a.cycles, a.p, a.basis)
    base = zlib.crc32(f'{a.n}{a.basis}{a.cycles}{a.p}{label}'.encode()) % 100000
    while fails < a.target_fails and shots < a.max_shots:
        nb = min(a.batch, a.max_shots - shots)
        seed = base + shots
        r = logical_error_rate(circ, nb, nproc=a.nproc, seed=seed)
        if not a.no_samples:   # raw samples: detector bits (packed), observables, decoder predictions
            os.makedirs(SAMPLES, exist_ok=True)
            np.savez_compressed(f'{SAMPLES}/{a.n}_{a.basis}_{a.cycles}_{a.p}_{label}_{seed}.npz',
                                dets=np.packbits(r['dets'], axis=1), n_dets=r['dets'].shape[1], obs=r['obs'], preds=r['preds'], seed=seed)
        append(dict(n=a.n, basis=a.basis, cycles=a.cycles, p=a.p, shots=nb, seed=seed, sched=label,
                    fails=r['fails'], bp_conv=round(r['bp_converged_frac'], 3), seconds=round(r['seconds'], 1), source='run_ler'))
        shots += nb; fails += r['fails']
        print(f'  batch {nb} shots seed {seed}: {r["fails"]} fails ({r["seconds"]:.0f}s) -> total {fails}/{shots} '
              f'LER={fails/shots:.3g}', flush=True)
    print(f'[{label} {a.basis} p={a.p}] end: {fails}/{shots}  LER={fails/max(shots,1):.3g}'
          + ('' if fails >= a.target_fails else f'  (target {a.target_fails} NOT reached, max shots)'), flush=True)


if __name__ == '__main__':
    main()
