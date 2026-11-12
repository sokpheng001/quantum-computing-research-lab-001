"""LER-vs-p figure for arbitrary schedule specs.
usage: fig_ler.py --n 72 --cycles 6 --scheds "212:S (Bravyi),5:best,900:worst" --out figures/x.png --title "..."
Also prints a markdown table (fails/shots and per-cycle rate with Wilson CI) to stdout."""
import argparse
from ler_table import aggregate, stats
ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, required=True); ap.add_argument('--cycles', type=int, required=True)
ap.add_argument('--scheds', required=True); ap.add_argument('--out', required=True); ap.add_argument('--title', default='')
a = ap.parse_args()
names = [tuple(s.split(':', 1)) for s in a.scheds.split(',')]
agg = aggregate(); ps = sorted({k[3] for k in agg if k[0] == a.n and k[2] == a.cycles})
print(f'| p | ' + ' | '.join(f'{nm} Z | {nm} X' for _, nm in names) + ' |'); print('|---|' + '---|' * 2 * len(names))
for p in ps:
    cells = []
    for sp, nm in names:
        for b in 'ZX':
            s, f = agg.get((a.n, b, a.cycles, p, sp), (0, 0))
            cells.append(f'{f}/{s} ({stats(s, f, a.cycles)["pc"]:.1e})' if s else '-')
    print(f'| {p} | ' + ' | '.join(cells) + ' |')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, b in zip(axes, 'ZX'):
    for i, (sp, nm) in enumerate(names):
        xs, ys, lo, hi = [], [], [], []
        for p in ps:
            s, f = agg.get((a.n, b, a.cycles, p, sp), (0, 0))
            if s and f:
                st = stats(s, f, a.cycles); xs.append(p); ys.append(st['pc']); lo.append(st['pc'] - st['pc_lo']); hi.append(st['pc_hi'] - st['pc'])
        if xs: ax.errorbar(xs, ys, yerr=[lo, hi], color=f'C{i}', marker='os^vD*'[i % 6], capsize=3, label=nm)
    ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlabel('physical error rate p'); ax.set_title(f'{b} memory'); ax.grid(True, which='both', alpha=0.3)
axes[0].set_ylabel('logical error rate per cycle (k=12)'); axes[0].legend(fontsize=8)
fig.suptitle(a.title or f'[[{a.n}]] BB code, {a.cycles} cycles, BP-OSD'); fig.tight_layout(); fig.savefig(a.out, dpi=150); print('figure:', a.out)
