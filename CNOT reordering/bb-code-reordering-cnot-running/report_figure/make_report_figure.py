"""One summary figure of the BB-code CNOT-reordering study (syndrome-extraction level).
(a) one-cycle circuit-level distance of all 1872 valid depth-7 orders, relative to Bravyi's schedule S
    (uniform work, Bravyi's randomised BP-OSD search; results_method3/<n>/d1_<n>.csv)
(b) best circuit-level distance per code: S, best reordered single schedule, alternating S/S^-1
    ([[144]] alternating: exact check of S's 17 weight-10 paths, 001 RESULTS.md, 2026-10-25)
Run: /home/ubuntu/quantum001-PKNU-Lab/venv/bin/python make_report_figure.py"""
import csv, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

U = '../bb-code-reordering-cnot-running/results_method3'
def d1_counts(n, dS):
    c = collections.Counter()
    for r in csv.DictReader(open(f'{U}/{n}/d1_{n}.csv')):
        c[min(int(r['d1_Z']), int(r['d1_X'])) - dS] += 1
    return c
c72, c90 = d1_counts(72, 6), d1_counts(90, 8)

plt.rcParams.update({'font.family': 'STIXGeneral', 'mathtext.fontset': 'stix', 'font.size': 11,
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.linewidth': 0.8})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0), gridspec_kw={'width_ratios': [1.15, 1]})

# (a) distance relative to S
deltas = [-3, -2, -1, 0, 1]
w = 0.38
for i, (lab, c, col) in enumerate((('[[72,12,6]]', c72, '#2a78d6'), ('[[90,8,10]]', c90, '#eb6834'))):
    vals = [c.get(d, 0) for d in deltas]
    x = [k + (i - 0.5) * w for k in range(len(deltas))]
    ax1.bar(x, vals, w, color=col, label=lab, edgecolor='white', linewidth=0.6)
    for xx, v in zip(x, vals):
        ax1.text(xx, v + 25, str(v), ha='center', va='bottom', fontsize=8.5)
ax1.set_xticks(range(len(deltas)))
ax1.set_xticklabels(['−3', '−2', '−1', '0', '+1 or more'])
ax1.set_xlabel("$d_1 - d_1(S)$:  one-cycle circuit-level distance relative to Bravyi's $S$")
ax1.set_ylabel('number of depth-7 schedules')
ax1.set_ylim(0, 1950)
ax1.legend(frameon=False, loc='upper left')
ax1.set_title('(a) All 1872 valid depth-7 CNOT orders', loc='left', fontsize=11)

# (b) best distance per code
codes = ['[[72,12,6]]', '[[90,8,10]]', '[[144,12,12]]']
d = [6, 10, 12]
S = [6, 8, 10]
best = [6, 8, None]          # [[144]]: full scan of single orders not run
alt = [6, 8, 10]
series = [('Bravyi schedule $S$', S, '#2a78d6'), ('best reordered single schedule', best, '#eb6834'),
          ('alternating $S$ / $S^{-1}$', alt, '#1baf7a')]
w = 0.24
for i, (lab, vals, col) in enumerate(series):
    for k, v in enumerate(vals):
        xx = k + (i - 1) * w
        if v is None:
            ax2.text(xx, 0.25, 'not\nscanned', ha='center', va='bottom', fontsize=8, color='#52514e', linespacing=1.1)
            continue
        ax2.bar(xx, v, w, color=col, edgecolor='white', linewidth=0.6, label=lab if k == 0 else None)
        ax2.text(xx, v + 0.15, str(v), ha='center', va='bottom', fontsize=8.5)
for k, dd in enumerate(d):
    ax2.hlines(dd, k - 0.42, k + 0.42, color='black', linestyle=(0, (4, 3)), linewidth=1.0,
               label='code distance $d$' if k == 0 else None)
ax2.set_xticks(range(3)); ax2.set_xticklabels(codes)
ax2.set_ylabel(r'circuit-level distance $d_{\mathrm{circ}}$ (upper bound)')
ax2.set_ylim(0, 14.5); ax2.set_yticks(range(0, 15, 2))
ax2.legend(frameon=False, loc='upper left', fontsize=9)
ax2.set_title('(b) Best circuit-level distance reached', loc='left', fontsize=11)

fig.tight_layout()
fig.savefig('fig_bb_cnot_reordering.png', dpi=300)
fig.savefig('fig_bb_cnot_reordering.pdf')
print('72:', dict(sorted(c72.items())), ' 90:', dict(sorted(c90.items())))
