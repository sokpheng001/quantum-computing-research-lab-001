"""Redraw figures/hist_dcirc_below6.png from results/ranking_936.csv (no other output):
d_circ bound distribution of the 936 Z-first depth-7 schedules on [[72]], and the
per-basis split of the schedules below 6."""
import csv, collections
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
R = list(csv.DictReader(open('results/ranking_936.csv')))
for r in R:
    r['dZ'], r['dX'] = int(r['dZ']), int(r['dX']); r['d'] = min(r['dZ'], r['dX'])
low = [r for r in R if r['d'] < 6]
byb = {b: collections.Counter(r['d' + b] for r in R if r['d' + b] < 6) for b in 'ZX'}
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
vals = [3, 4, 5, 6]; cnt = [sum(1 for r in R if r['d'] == v) for v in vals]
ax[0].bar([str(v) for v in vals], cnt, color=['C3', 'C1', 'C1', 'C0'])
for i, c in enumerate(cnt): ax[0].text(i, c, str(c), ha='center', va='bottom')
ax[0].set_xlabel('min(dZ, dX) upper bound'); ax[0].set_ylabel('schedules'); ax[0].set_title('all 936 Z-first depth-7 schedules')
x = [3, 4, 5]
ax[1].bar([v - 0.2 for v in x], [byb['Z'][v] for v in x], 0.4, label='Z basis')
ax[1].bar([v + 0.2 for v in x], [byb['X'][v] for v in x], 0.4, label='X basis')
ax[1].set_xticks(x); ax[1].set_xlabel('bound in that basis'); ax[1].set_title(f'the {len(low)} schedules with d_circ < 6, per basis'); ax[1].legend()
for a in ax: a.grid(alpha=0.3, axis='y')
fig.suptitle('[[72,12,6]], 4-cycle memory circuit, 100 randomised BP-OSD trials per schedule and basis'); fig.tight_layout()
fig.savefig('figures/hist_dcirc_below6.png', dpi=150); print('figure: figures/hist_dcirc_below6.png')
