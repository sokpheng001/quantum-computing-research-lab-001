"""Phase 2 PASS check: every (S, S^-1, alt) x (Z, X) x p point has >= 30
failures.  Writes figures/exp1_ler_vs_p.png and appends a Phase 2 section to
RESULTS.md.  Exit code 1 if the PASS condition fails."""
import sys, datetime
from ler_table import aggregate, stats
from sched_ids import named
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
ids = named(); cfg = {'S': str(ids['S']), 'S^-1': str(ids['Sinv']), 'alt S/S^-1': f"{ids['S']}+{ids['Sinv']}"}
PV = [0.002, 0.004, 0.006, 0.008]; CYC = 6
agg = aggregate(); ok = True; lines = []
lines.append(f'\n## Phase 2 — Experiment 1 on [[72,12,6]] (k = 12), {CYC} cycles, BP-OSD  ({datetime.date.today()})\n')
lines.append('| p | basis | S fails/shots | S p_L/cycle | S^-1 fails/shots | S^-1 p_L/cycle | alt fails/shots | alt p_L/cycle |')
lines.append('|---|---|---|---|---|---|---|---|')
fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
sty = {'S': ('C0', 'o'), 'S^-1': ('C1', 's'), 'alt S/S^-1': ('C2', '^')}
for ax, basis in zip(axes, 'ZX'):
    for name, lab in cfg.items():
        xs, ys, lo, hi = [], [], [], []
        for p in PV:
            s, f = agg.get((72, basis, CYC, p, lab), (0, 0))
            st = stats(s, f, CYC)
            if s: xs.append(p); ys.append(max(st['pc'], 1e-6)); lo.append(max(st['pc'] - st['pc_lo'], 0)); hi.append(st['pc_hi'] - st['pc'])
            if f < 30: ok = False
        c, m = sty[name]
        ax.errorbar(xs, ys, yerr=[lo, hi], color=c, marker=m, capsize=3, label=name)
    ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlabel('physical error rate p'); ax.set_title(f'{basis} memory'); ax.grid(True, which='both', alpha=0.3)
axes[0].set_ylabel('logical error rate per cycle p_L (k=12)'); axes[0].legend()
fig.suptitle('[[72,12,6]]: Bravyi schedule S vs time-reverse vs alternating'); fig.tight_layout(); fig.savefig('figures/exp1_ler_vs_p.png', dpi=150)
for p in PV:
    for basis in 'ZX':
        cells = []
        for name, lab in cfg.items():
            s, f = agg.get((72, basis, CYC, p, lab), (0, 0)); st = stats(s, f, CYC)
            cells.append(f'{f}/{s}'); cells.append(f"{st['pc']:.2e} [{st['pc_lo']:.1e},{st['pc_hi']:.1e}]")
        lines.append(f'| {p} | {basis} | ' + ' | '.join(cells) + ' |')
lines.append(f'\nFigure: figures/exp1_ler_vs_p.png. PASS condition (>= 30 failures per point): **{"PASS" if ok else "FAIL"}**.')
lines.append('Interpretation to be written by hand below this line after inspection.')
open('RESULTS.md', 'a').write('\n'.join(lines) + '\n')
print('\n'.join(lines)); sys.exit(0 if ok else 1)
