"""Figures for the [[72]] L/R scheduling study.
  figures/dcirc_by_lr_switches.png  d_circ (stim search) of all valid depth-7 schedules vs L/R block switches
  figures/ler_72_lr.png             LER per cycle, Z and X memory, log-log, Wilson 95% error bars"""
import csv, json, collections, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from dcirc import wilson, per_cycle
os.makedirs('figures', exist_ok=True)
rows = list(csv.DictReader(open('results/distance_72.csv')))
by = collections.defaultdict(collections.Counter)
for r in rows: by[int(r['switches_x']) + int(r['switches_z'])][min(int(r['dZ']), int(r['dX']))] += 1
sws = sorted(by); ds = sorted({d for c in by.values() for d in c})
fig, ax = plt.subplots(figsize=(7, 4)); w = 0.8 / len(ds)
for i, d in enumerate(ds):
    vals = [by[s][d] for s in sws]
    ax.bar([k + (i - (len(ds) - 1) / 2) * w for k in range(len(sws))], vals, w, label=f'd_circ <= {d}', color=plt.cm.RdYlGn((d - 2) / 4))
    for k, v in enumerate(vals):
        if v: ax.text(k + (i - (len(ds) - 1) / 2) * w, v, str(v), ha='center', va='bottom', fontsize=7)
ax.set_xticks(range(len(sws))); ax.set_xticklabels([f'{s} switches\n({sum(by[s].values())} schedules)' for s in sws])
ax.set_ylabel('valid depth-7 schedules'); ax.legend(); ax.grid(alpha=0.3, axis='y')
ax.set_title('[[72,12,6]]: circuit-level distance vs L/R block switches\n(strategies A/B/C would have 2 switches in total; none is valid)', fontsize=10)
fig.tight_layout(); fig.savefig('figures/dcirc_by_lr_switches.png', dpi=150); print('figure: figures/dcirc_by_lr_switches.png')
if os.path.exists('results/ler_72.csv'):
    agg = collections.defaultdict(lambda: [0, 0])
    for r in csv.DictReader(open('results/ler_72.csv')):
        k = (r['name'], r['basis'], int(r['cycles']), float(r['p'])); agg[k][0] += int(r['shots']); agg[k][1] += int(r['fails'])
    names = sorted({k[0] for k in agg}, key=lambda n: ['S', 'LR_d6', 'LR_d3'].index(n) if n in ('S', 'LR_d6', 'LR_d3') else 9)
    lab = {'S': 'S (Bravyi)', 'LR_d6': 'most L/R-like, d_circ = 6', 'LR_d3': 'fewest-switch schedule with d_circ = 3 (L/R alternating)'}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, b in zip(axes, 'ZX'):
        for i, n in enumerate(names):
            pts = sorted((k[3], v, k[2]) for k, v in agg.items() if k[0] == n and k[1] == b and v[1] > 0)
            if not pts: continue
            x = [p for p, _, _ in pts]; y = [per_cycle(f / s, c) for p, (s, f), c in pts]
            lo = [per_cycle(wilson(f, s)[0], c) for p, (s, f), c in pts]; hi = [per_cycle(wilson(f, s)[1], c) for p, (s, f), c in pts]
            ax.errorbar(x, y, yerr=[np.array(y) - lo, np.array(hi) - y], marker='os^'[i % 3], capsize=3, label=lab.get(n, n))
        ax.set_xscale('log'); ax.set_yscale('log'); ax.set_title(f'{b} memory'); ax.set_xlabel('physical error rate p'); ax.grid(True, which='both', alpha=0.3)
    axes[0].set_ylabel('logical error rate per cycle (k = 12)'); axes[0].legend(fontsize=8)
    fig.suptitle('[[72,12,6]] BB code, 6 cycles, BP-OSD: L/R-structured schedules vs Bravyi'); fig.tight_layout()
    fig.savefig('figures/ler_72_lr.png', dpi=150); print('figure: figures/ler_72_lr.png')
