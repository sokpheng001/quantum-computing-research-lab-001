"""Print everything we have for [[72]] and [[144]] (bounds + LER) and draw
figures/exp_144_ler.png.  Usage: ../venv/bin/python status.py"""
import csv, os, json, collections
from ler_table import aggregate, stats
from sched_ids import named
ids = named(); name = {str(ids['S']): 'S', str(ids['Sinv']): 'S^-1', f"{ids['S']}+{ids['Sinv']}": 'alt S/S^-1'}
print('=== d_circ upper bounds (results/bounds_exp1.csv) ===')
if os.path.exists('results/bounds_exp1.csv'):
    for r in csv.DictReader(open('results/bounds_exp1.csv')):
        print(f"  [[{r['n']}]] {name.get(r['sched'], r['sched']):11s} {r['basis']}  cycles={r['cycles']}  trials={r['trials']:>5}  d_circ {r['bound']}  min-weight paths found={r['n_min_paths']}")
print('\n=== logical error rate (results/ler.csv) ===')
agg = aggregate(); rows = collections.defaultdict(dict)
for (n, basis, cyc, p, sched), (s, f) in agg.items():
    rows[(n, cyc, p)][(name.get(sched, sched), basis)] = (s, f)
for n in (72, 144):
    keys = sorted(k for k in rows if k[0] == n)
    if not keys: print(f'  [[{n}]]: no data yet'); continue
    cyc = keys[0][1]
    print(f"  [[{n}]], {cyc} cycles.  Cells: fails/shots  (per-cycle p_L)")
    print(f"  {'p':>6} | {'S  Z':>22} | {'S  X':>22} | {'S^-1 Z':>22} | {'S^-1 X':>22} | {'alt Z':>22} | {'alt X':>22}")
    for (_, cyc, p) in keys:
        cells = []
        for nm in ('S', 'S^-1', 'alt S/S^-1'):
            for b in 'ZX':
                s, f = rows[(n, cyc, p)].get((nm, b), (0, 0))
                cells.append(f'{f}/{s} ({stats(s, f, cyc)["pc"]:.1e})' if s else '-')
        print(f'  {p:>6} | ' + ' | '.join(f'{c:>22}' for c in cells))
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    for n, cyc, out in ((72, 6, 'figures/exp_72_ler.png'), (144, 12, 'figures/exp_144_ler.png')):
        keys = sorted(k for k in rows if k[0] == n)
        if not keys: continue
        fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
        sty = {'S': ('C0', 'o'), 'S^-1': ('C1', 's'), 'alt S/S^-1': ('C2', '^')}
        for ax, b in zip(axes, 'ZX'):
            for nm, (c, m) in sty.items():
                xs, ys, lo, hi = [], [], [], []
                for (_, _, p) in keys:
                    s, f = rows[(n, cyc, p)].get((nm, b), (0, 0))
                    if s and f:
                        st = stats(s, f, cyc); xs.append(p); ys.append(st['pc']); lo.append(st['pc'] - st['pc_lo']); hi.append(st['pc_hi'] - st['pc'])
                if xs: ax.errorbar(xs, ys, yerr=[lo, hi], color=c, marker=m, capsize=3, label=nm)
            ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlabel('physical error rate p'); ax.set_title(f'{b} memory'); ax.grid(True, which='both', alpha=0.3)
        axes[0].set_ylabel('logical error rate per cycle (k=12)'); axes[0].legend()
        fig.suptitle(f'[[{n},12,{6 if n==72 else 12}]] BB code, {cyc} cycles, BP-OSD'); fig.tight_layout(); fig.savefig(out, dpi=150)
        print('figure:', out)
except ImportError:
    pass
