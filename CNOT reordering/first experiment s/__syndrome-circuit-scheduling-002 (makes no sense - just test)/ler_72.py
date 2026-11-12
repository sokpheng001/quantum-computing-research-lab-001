"""Logical error rate of chosen [[72]] schedules (6 cycles), fixed decoder of the project:
ldpc BpOsdDecoder, serial min-sum, scaling 1.0, 100 iterations, OSD-CS order 7, DEM priors
(dcirc.logical_error_rate of ../syndrome-circuit-scheduling-001, memory-guarded).
Appends one row per batch to results/ler_72.csv (resumable); raw samples -> results/samples/.
usage: ler_72.py --name LR6 --layout z_first --x "A1 ..." --z "..." --basis Z --p 0.004 [--target 50 --max-shots 6000 --batch 1000 --nproc 2]"""
import argparse, csv, os, sys, zlib
import numpy as np
from dcirc import logical_error_rate
from search_scheduler_72 import make_schedule, build_72_stim_circuit
CSV = 'results/ler_72.csv'; F = ['name', 'layout', 'x_order', 'z_order', 'basis', 'cycles', 'p', 'shots', 'seed', 'fails', 'bp_conv', 'seconds']
ap = argparse.ArgumentParser()
for k in ('name', 'layout', 'x', 'z', 'basis'): ap.add_argument('--' + k, required=True)
ap.add_argument('--p', type=float, required=True); ap.add_argument('--cycles', type=int, default=6)
ap.add_argument('--target', type=int, default=50); ap.add_argument('--max-shots', type=int, default=6000)
ap.add_argument('--batch', type=int, default=1000); ap.add_argument('--nproc', type=int, default=2)
a = ap.parse_args()
shots = fails = 0
if os.path.exists(CSV):
    for r in csv.DictReader(open(CSV)):
        if (r['name'], r['basis'], int(r['cycles']), float(r['p'])) == (a.name, a.basis, a.cycles, a.p):
            shots += int(r['shots']); fails += int(r['fails'])
print(f'[{a.name} {a.basis} p={a.p}] start {fails}/{shots}', flush=True)
circ = build_72_stim_circuit(make_schedule(a.x.split(), a.z.split(), a.layout), a.cycles, a.p, a.basis)
base = zlib.crc32(f'{a.name}{a.basis}{a.cycles}{a.p}'.encode()) % 100000
os.makedirs('results/samples', exist_ok=True)
while fails < a.target and shots < a.max_shots:
    nb = min(a.batch, a.max_shots - shots); seed = base + shots
    r = logical_error_rate(circ, nb, nproc=a.nproc, seed=seed)
    np.savez_compressed(f'results/samples/{a.name}_{a.basis}_{a.cycles}_{a.p}_{seed}.npz', dets=np.packbits(r['dets'], axis=1),
                        n_dets=r['dets'].shape[1], obs=r['obs'], preds=r['preds'], seed=seed)
    new = not os.path.exists(CSV)
    with open(CSV, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=F)
        if new: w.writeheader()
        w.writerow(dict(name=a.name, layout=a.layout, x_order=a.x, z_order=a.z, basis=a.basis, cycles=a.cycles, p=a.p, shots=nb,
                        seed=seed, fails=r['fails'], bp_conv=round(r['bp_converged_frac'], 3), seconds=round(r['seconds'], 1)))
    shots += nb; fails += r['fails']
    print(f'  batch {nb} seed {seed}: {r["fails"]} fails ({r["seconds"]:.0f}s) -> {fails}/{shots}', flush=True)
print(f'[{a.name} {a.basis} p={a.p}] end {fails}/{shots}', flush=True)
