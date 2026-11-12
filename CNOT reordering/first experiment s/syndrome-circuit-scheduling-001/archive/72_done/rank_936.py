"""TASK2 task B (Phase 3.2-3.3): rank the 936 Z-first depth-7 schedules of [[72]] from
results/bounds_936.csv + results/faultsets/, find symmetry classes, report Bravyi's rank.

Ranking key: min(dZ, dX) descending, then number of NONTRIVIAL min-weight fault sets
(Z + X) ascending, then total min-weight sets ascending.  (TASKS.md says max(dZ,dX);
the circuit distance of a memory is the smaller of the two, so min is used.)

Symmetry classes: two code automorphisms act on schedule labels and keep the Z-first
set invariant (verified below by membership):
  T1  x<->y on the torus: A_i <-> B_i in both orders (registers L<->R swap).
  T2  inversion x->x^-1, y->y^-1 composed with L<->R, X<->Z (Hadamard) and time
      reversal: (x_order, z_order) -> (reversed z_order, reversed x_order).
Schedules in one orbit of <T1, T2> have the same LER up to the Z<->X swap.
Outputs: results/ranking_936.csv, figures/hist_dcirc_936.png, results/ranking_936.md
"""
import csv, json, os, datetime, collections
import numpy as np
from sched_ids import table, named
from faultsets import load_sets, core_keys, n_nontrivial

N, CYC = 72, 4
rows = {}
for r in csv.DictReader(open('results/bounds_936.csv')):
    if int(r['n']) == N and int(r['cycles']) == CYC and int(r['sched']) < 936:
        rows[(int(r['sched']), r['basis'])] = r
ids = sorted({s for s, _ in rows if (s, 'Z') in rows and (s, 'X') in rows})
print(f'{len(ids)} schedules with both bases')
CORE = {b: core_keys(N, b, ids) for b in 'ZX'}
print('core keys:', {b: len(CORE[b]) for b in 'ZX'})
rec = {}
for s in ids:
    d = {}
    for b in 'ZX':
        r = rows[(s, b)]; sets = load_sets(N, b, s) or []
        d['d' + b] = int(r['bound'].split()[-1]); d['n' + b] = int(r['n_min_paths']); d['nt' + b] = n_nontrivial(sets, CORE[b])
    d['dmin'] = min(d['dZ'], d['dX']); d['nt'] = d['ntZ'] + d['ntX']; d['nmin'] = d['nZ'] + d['nX']
    rec[s] = d
order = sorted(ids, key=lambda s: (-rec[s]['dmin'], rec[s]['nt'], rec[s]['nmin'], s))
rank = {s: i + 1 for i, s in enumerate(order)}

# ---- symmetry classes
T = table(); key2id = {(tuple(x), tuple(z), zf): i for i, (x, z, zf) in T.items()}
swap = lambda lab: ('B' if lab[0] == 'A' else 'A') + lab[1]
def T1(s): x, z, zf = T[s]; return key2id.get((tuple(map(swap, x)), tuple(map(swap, z)), zf))
def T2(s): x, z, zf = T[s]; return key2id.get((tuple(z[::-1]), tuple(x[::-1]), zf))
parent = {s: s for s in range(936)}
def find(s):
    while parent[s] != s: parent[s] = parent[parent[s]]; s = parent[s]
    return s
ok = {'T1': 0, 'T2': 0}
for s in range(936):
    for nm, f in (('T1', T1), ('T2', T2)):
        t = f(s)
        if t is not None and t < 936:
            ok[nm] += 1; parent[find(s)] = find(t)
classes = collections.defaultdict(list)
for s in range(936): classes[find(s)].append(s)
cls_id = {}; 
for k, (root, mem) in enumerate(sorted(classes.items(), key=lambda kv: min(rank.get(m, 9999) for m in kv[1]))):
    for m in mem: cls_id[m] = k + 1
# consistency: within a class, bounds agree (T2 swaps Z<->X, so compare the sorted pair)
agree = tot = 0
for mem in classes.values():
    vals = {tuple(sorted((rec[m]['dZ'], rec[m]['dX']))) for m in mem if m in rec}
    if len(vals) >= 1: tot += 1; agree += (len(vals) == 1)

# ---- outputs
os.makedirs('figures', exist_ok=True)
with open('results/ranking_936.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['rank', 'id', 'class', 'dZ', 'dX', 'nZ', 'nX', 'ntZ', 'ntX', 'x', 'z'])
    for s in order:
        d = rec[s]; x, z, _ = T[s]
        w.writerow([rank[s], s, cls_id[s], d['dZ'], d['dX'], d['nZ'], d['nX'], d['ntZ'], d['ntX'], ' '.join(x), ' '.join(z)])
S = named()['S']
def line(s):
    d = rec[s]; x, z, _ = T[s]
    return f"| {rank[s]} | {s} | {cls_id[s]} | <= {d['dZ']} | <= {d['dX']} | {d['nZ']} / {d['nX']} | {d['ntZ']} / {d['ntX']} | {' '.join(x)} / {' '.join(z)} |"
hdr = ['| rank | id | class | dZ | dX | min-weight sets Z / X | nontrivial Z / X | X order / Z order |', '|---|---|---|---|---|---|---|---|']
med = order[len(order) // 2]
md = [f'\n## Task B — ranking of the {len(ids)} Z-first depth-7 schedules, [[72]], {CYC} cycles, 100 trials ({datetime.date.today()})\n',
      f'Key: min(dZ,dX) desc, then nontrivial min-weight sets (Z+X) asc, then all min-weight sets asc. '
      f'Core (schedule-independent) keys: Z {len(CORE["Z"])}, X {len(CORE["X"])}; a set is nontrivial if it uses a non-core fault.\n',
      f'Bound values: {dict(collections.Counter(rec[s]["dmin"] for s in ids))}. '
      f'Nontrivial sets per schedule: min {min(rec[s]["nt"] for s in ids)}, median {int(np.median([rec[s]["nt"] for s in ids]))}, max {max(rec[s]["nt"] for s in ids)}.\n',
      f'Symmetry: T1 maps {ok["T1"]}/936 and T2 maps {ok["T2"]}/936 schedules into the Z-first set; '
      f'**{len(classes)} classes** (sizes {dict(collections.Counter(len(m) for m in classes.values()))}); '
      f'bounds agree within {agree}/{tot} classes.\n',
      (f'**Bravyi S (id {S}): rank {rank[S]} of {len(ids)}, class {cls_id[S]}** (class members {classes[find(S)]}).\n' if S in rank else f'Bravyi S (id {S}) not in the data yet.\n'),
      '\nTop 5:', *hdr, *[line(s) for s in order[:5]],
      '\nMedian:', *hdr, line(med),
      '\nBottom 5:', *hdr, *[line(s) for s in order[-5:]],
      '\nBravyi:', *hdr, (line(S) if S in rank else '(missing)'), '\nFigure: figures/hist_dcirc_936.png; table: results/ranking_936.csv']
open('results/ranking_936.md', 'w').write('\n'.join(md) + '\n'); print('\n'.join(md))
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    ax[0].hist([rec[s]['dmin'] for s in ids], bins=np.arange(2.5, 7.5, 1), color='C0'); ax[0].set_xlabel('min(dZ, dX) upper bound'); ax[0].set_title('d_circ bound, 936 schedules')
    ax[1].hist([rec[s]['nt'] for s in ids], bins=30, color='C1'); (ax[1].axvline(rec[S]['nt'], color='k', ls='--', label=f'Bravyi S ({rec[S]["nt"]})'), ax[1].legend()) if S in rec else None; ax[1].set_xlabel('nontrivial min-weight sets (Z+X)')
    ax[2].hist([rec[s]['nmin'] for s in ids], bins=30, color='C2'); (ax[2].axvline(rec[S]['nmin'], color='k', ls='--') if S in rec else None); ax[2].set_xlabel('all min-weight sets found (Z+X)')
    for a in ax: a.set_ylabel('schedules'); a.grid(alpha=0.3)
    fig.suptitle(f'[[72,12,6]], {CYC} cycles, 100 randomised BP-OSD trials per schedule and basis'); fig.tight_layout(); fig.savefig('figures/hist_dcirc_936.png', dpi=150)
except ImportError: pass
