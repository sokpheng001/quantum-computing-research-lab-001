"""Figure for the [[144]] multi-seed d_circ search: lowest weight found vs trials, per seed,
for S, S^-1 and alt S/S^-1, Z and X basis (two panels like the LER figures), plus the final
per-seed values.  usage: fig_bounds.py [--out figures/exp_144_bounds.png]"""
import csv, collections, argparse
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
ap = argparse.ArgumentParser(); ap.add_argument('--out', default='figures/exp_144_bounds.png'); a = ap.parse_args()
rows = sorted(csv.DictReader(open('results/strong_144.csv')), key=lambda r: int(r['chunk']))
sty = {'212': ('S (Bravyi)', 'C0', 'o'), '1307': ('S^-1', 'C1', 's'), '212+1307': ('alt S/S^-1', 'C2', '^')}
curves = collections.defaultdict(list)
for r in rows:
    k = (r['circuit'], r['basis'], int(r['seed'])); prev = curves[k][-1] if curves[k] else (0, 99)
    curves[k].append((prev[0] + int(r['trials']), min(prev[1], int(r['min_weight']))))
fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), gridspec_kw={'width_ratios': [2, 2, 1.3]})
for ax, b in zip(axes[:2], 'ZX'):
    for c, (lab, col, m) in sty.items():
        first = True
        for (cc, bb, s), pts in sorted(curves.items()):
            if cc != c or bb != b: continue
            x = [0] + [p[0] for p in pts]; y = [pts[0][1]] + [p[1] for p in pts]
            ax.step(x, [v + (list(sty).index(c) - 1) * 0.06 for v in y], where='post', color=col, alpha=0.75, lw=1.4, label=lab if first else None)
            first = False
    ax.axhline(10, color='k', ls='--', lw=1, label='Bravyi et al.: d_circ <= 10 for S')
    ax.set_title(f'{b} memory'); ax.set_xlabel('trials per seed'); ax.grid(alpha=0.3); ax.set_yticks(range(9, 14))
axes[0].set_ylabel('lowest fault-path weight found (upper bound on d_circ)'); axes[0].legend(fontsize=8)
ax = axes[2]; xs = []
for i, (c, (lab, col, m)) in enumerate(sty.items()):
    for j, b in enumerate('ZX'):
        fin = [pts[-1][1] for (cc, bb, s), pts in curves.items() if cc == c and bb == b]
        if not fin: continue
        x = i * 2.6 + j
        ax.scatter([x + (k - 2) * 0.12 for k in range(len(fin))], fin, color=col, marker=m, s=30)
        xs.append((x, f"{lab.split(' ')[0]}\n{b}"))
ax.axhline(10, color='k', ls='--', lw=1); ax.set_xticks([x for x, _ in xs]); ax.set_xticklabels([l for _, l in xs], fontsize=8)
ax.set_yticks(range(9, 14)); ax.set_title('final value per seed'); ax.grid(alpha=0.3, axis='y')
fig.suptitle('[[144,12,12]] circuit-level distance search, 4 cycles, 5 seeds per circuit and basis (lines offset slightly for visibility)')
fig.tight_layout(); fig.savefig(a.out, dpi=150); print('figure:', a.out)
