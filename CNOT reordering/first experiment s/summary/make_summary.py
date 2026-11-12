"""
Summary figures across all codes tested in folders 001-004. Re-run any time; it reads the
latest results, so the figures fill in as the running jobs finish.

  cd /home/ubuntu/quantum001-PKNU-Lab/summary && ../venv/bin/python make_summary.py

figures/method_pipeline.png   how the logical error rate and the circuit-level distance are obtained
figures/summary_dcirc.png     lowest fault-path weight found (upper bound on d_circ), S / S^-1 / alt, every code
figures/summary_ler.png       logical error rate per cycle vs p, S / S^-1 / alt, every code, Z and X
figures/decoder_compare.png   [[72]]: BP-OSD (OSD-CS order 7) vs BP-OSD-0 for the same circuits
"""
import csv, os, collections, math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

ROOT = '/home/ubuntu/quantum001'
F = {d: f'{ROOT}/syndrome-circuit-scheduling-{d}/results' for d in ('001', '002', '004')}
F['003'] = f'{ROOT}/_syndrome-circuit-scheduling-003/results'   # closed folder (prefix _ = not running)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figures'); os.makedirs(OUT, exist_ok=True)

# ---- style (reference palette, light mode): colour = circuit, marker + line style = secondary encoding
SURF, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
CIRC = [('212', 'S (Bravyi)', '#2a78d6', 'o', '-'), ('1307', 'S⁻¹ (time reverse)', '#eb6834', 's', '--'),
        ('212+1307', 'alternating S / S⁻¹', '#1baf7a', '^', ':')]
CODES = [(72, '[[72,12,6]]', 6, 6), (90, '[[90,8,10]]', 10, 8), (144, '[[144,12,12]]', 12, 10)]   # n, name, d, Bravyi d_circ(S)
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'text.color': INK,
                     'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'axes.edgecolor': INK2,
                     'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.8, 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False, 'lines.linewidth': 2, 'lines.markersize': 8})


def rows(path):
    return list(csv.DictReader(open(path))) if os.path.exists(path) else []


def wilson(f, n, z=1.96):
    if n == 0: return 0.0, 1.0
    p = f / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def per_cycle(x, cyc): return 1 - (1 - x) ** (1 / cyc)


# ------------------------------------------------------------------ 1. method diagram
def method():
    fig, ax = plt.subplots(figsize=(12, 7.2)); ax.set_xlim(0, 12); ax.set_ylim(0, 7.2); ax.axis('off'); ax.grid(False)
    def box(x, y, w, h, title, body, edge=INK2, fill='#f3f2ee'):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.12', fc=fill, ec=edge, lw=1.4))
        ax.text(x + w / 2, y + h - 0.22, title, ha='center', va='top', fontsize=10.5, weight='bold', color=INK)
        ax.text(x + w / 2, y + h - 0.55, body, ha='center', va='top', fontsize=8.6, color=INK2, linespacing=1.35)
    def arrow(x1, y1, x2, y2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle='-|>', color=INK2, lw=1.4))
    box(0.3, 5.75, 3.4, 1.25, '1. BB code', 'H_X = [A | B],  H_Z = [Bᵀ | Aᵀ]\n[[72,12,6]], [[90,8,10]], [[144,12,12]]')
    box(4.3, 5.75, 3.4, 1.25, '2. Syndrome circuit (stim)', 'depth-7 CNOT schedule: S, S⁻¹ or alternating\nuniform depolarising noise at rate p')
    box(8.3, 5.75, 3.4, 1.25, '3. Detector error model', 'H: detectors × faults,  L: logicals × faults\nprior probability of every fault')
    arrow(3.7, 6.37, 4.3, 6.37); arrow(7.7, 6.37, 8.3, 6.37)
    blue, green = '#2a78d6', '#1baf7a'
    ax.text(3.0, 5.25, 'LOGICAL ERROR RATE', ha='center', fontsize=11, weight='bold', color=blue)
    ax.text(9.0, 5.25, 'CIRCUIT-LEVEL DISTANCE', ha='center', fontsize=11, weight='bold', color=green)
    arrow(10.0, 5.75, 9.0, 5.45); arrow(10.0, 5.75, 3.0, 5.45)
    L = [('4a. Sample noisy shots', 'stim samples detector flips and the true\nlogical flips for many runs of the circuit'),
         ('5a. Decode every shot', 'BP-OSD: serial min-sum BP (100 iterations),\nthen OSD order 7 (001, 002, 004) or OSD-0 (003)'),
         ('6a. Count failures', 'failure = predicted logical flip ≠ true flip\nat least 30–50 failures per point'),
         ('7a. Logical error rate per cycle', 'p_L = 1 − (1 − failures/shots)^(1/cycles)\nwith 95% Wilson error bars')]
    R = [('4b. Ask for an undetected logical', 'add a random logical row to H and ask for\nsyndrome (0,…,0,1): no detector, logical flipped'),
         ('5b. Solve with BP-OSD', 'OSD order 20, random fault priors,\nthousands of trials × 5 independent seeds'),
         ('6b. Fault path found', 'every answer is a real set of faults that\nflips a logical silently; its size = weight'),
         ('7b. Distance bound', 'd_circ ≤ smallest weight found\n(cross-checked with stim\'s exact-style search)')]
    for i, ((t1, b1), (t2, b2)) in enumerate(zip(L, R)):
        y = 4.0 - i * 1.25
        box(0.9, y, 4.2, 1.05, t1, b1, edge=blue, fill='#eef4fc'); box(6.9, y, 4.2, 1.05, t2, b2, edge=green, fill='#ecf8f3')
        if i: arrow(3.0, y + 1.25, 3.0, y + 1.05); arrow(9.0, y + 1.25, 9.0, y + 1.05)
    fig.suptitle('How the two quantities are measured (same circuit and noise model for both)', fontsize=12, weight='bold', color=INK, y=0.995)
    fig.tight_layout(); fig.savefig(f'{OUT}/method_pipeline.png', dpi=160); plt.close(fig)


# ------------------------------------------------------------------ 2. distance summary
def dcirc_data():
    """(n, circuit) -> dict(Z=min, X=min, trials=max trials per basis, source)."""
    out = {}
    def put(n, c, b, w, tr, src):
        e = out.setdefault((n, c), dict(Z=None, X=None, trials=0, src=set()))
        e[b] = w if e[b] is None else min(e[b], w); e['trials'] = max(e['trials'], tr); e['src'].add(src)
    for r in rows(f"{F['001']}/bounds_exp1.csv"):           # first searches ([[72]] 6 cycles, [[144]] 4 cycles)
        put(int(r['n']), r['sched'], r['basis'], int(r['bound'].split()[-1]), int(r['trials']), 'single search')
    for n, path in ((144, f"{F['001']}/strong_144.csv"), (90, f"{F['004']}/strong_90.csv")):
        tr = collections.Counter()
        for r in rows(path): tr[(r['circuit'], r['basis'])] += int(r['trials'])
        for r in rows(path): put(n, r['circuit'], r['basis'], int(r['min_weight']), tr[(r['circuit'], r['basis'])], '5-seed search')
    return out


def dcirc_fig():
    D = dcirc_data()
    fig, ax = plt.subplots(figsize=(10, 6.0))
    ticks = []; note = []
    for k, (n, name, d, dref) in enumerate(CODES):
        ax.hlines(d, k - 0.36, k + 0.36, color=INK2, lw=1.4, ls=(0, (4, 3)), zorder=1)
        ax.hlines(dref, k - 0.36, k + 0.36, color=INK, lw=1.4, zorder=1)
        detail = []
        for j, (cid, lab, col, mk, _) in enumerate(CIRC):
            e = D.get((n, cid)); x = k + (j - 1) * 0.22
            if not e or e['Z'] is None or e['X'] is None:
                detail.append(f"{lab.split(' ')[0]} –"); continue
            v = min(e['Z'], e['X'])
            if cid == '212' and dref < v:
                # our search did not reach the lighter path Bravyi et al. found: show the best KNOWN bound
                ax.plot([x], [v], marker=mk, color=col, ms=12, ls='none', mfc=SURF, mec=col, mew=2, zorder=3)
                ax.annotate('', xy=(x, dref + 0.18), xytext=(x, v - 0.22), arrowprops=dict(arrowstyle='-|>', color=col, lw=1.6), zorder=3)
                ax.plot([x], [dref], marker=mk, color=col, ms=12, ls='none', mec=SURF, mew=2, zorder=4)
                ax.text(x - 0.06, v + 0.32, f'our search {v}', ha='center', va='bottom', fontsize=8, color=INK2, zorder=4)
                ax.text(x - 0.06, dref - 0.3, f'{dref}', ha='center', va='top', fontsize=10, weight='bold', color=INK, zorder=4)
                note.append(f'{name}: our search found {v} for S; Bravyi et al. already found {dref}, so the known bound for S is {dref}.')
            else:
                ax.plot([x], [v], marker=mk, color=col, ms=12, ls='none', mec=SURF, mew=2, zorder=3)
                ax.text(x, v + 0.32, f'{v}', ha='center', va='bottom', fontsize=10, weight='bold', color=INK, zorder=4)
            detail.append(f"{lab.split(' ')[0]} {e['Z']}/{e['X']}")
        ticks.append(f'{name}\nZ/X:  ' + ' · '.join(detail))
    ax.set_xticks(range(len(CODES))); ax.set_xticklabels(ticks, fontsize=9.5)
    ax.set_xlim(-0.55, len(CODES) - 0.45); ax.set_ylim(3.5, 13.5); ax.set_yticks(range(4, 14))
    ax.set_ylabel('lowest fault-path weight found\n(upper bound on circuit-level distance)')
    h = [Line2D([], [], marker=m, color=c, ls='none', ms=9, label=l) for _, l, c, m, _ in CIRC]
    h += [Line2D([], [], color=INK2, lw=1.4, ls=(0, (4, 3)), label='code distance d'),
          Line2D([], [], color=INK, lw=1.4, label='Bravyi et al. value for S')]
    tr = {n: max((D[(n, c)]['trials'] for c, *_ in CIRC if (n, c) in D), default=0) for n, *_ in CODES}
    h.insert(3, Line2D([], [], marker='o', color=CIRC[0][2], mfc=SURF, ls='none', ms=9, label='our search only (a lighter path is known)'))
    fig.text(0.01, 0.01, 'Every value is an UPPER bound: a fault path of that weight exists. A higher value can mean the search missed a '
             'lighter path,\nso differences are only meaningful once the lighter paths are checked exactly. ' + ' '.join(note),
             fontsize=7.5, color=INK2, va='bottom')
    ax.legend(handles=h, loc='upper left', frameon=False, fontsize=9)
    ax.set_title('Circuit-level distance (minimum over Z and X); higher is better, values are upper bounds\n'
                 f'search trials per circuit and basis, all seeds together: [[72]] {tr[72]:,}, [[90]] {tr[90]:,}, [[144]] {tr[144]:,}',
                 fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0.07, 1, 1)); fig.savefig(f'{OUT}/summary_dcirc.png', dpi=160); plt.close(fig)


# ------------------------------------------------------------------ 3. logical error rate summary
def ler_agg(folder):
    agg = collections.defaultdict(lambda: [0, 0])
    for r in rows(f'{F[folder]}/ler.csv'):
        k = (int(r['n']), r['basis'], int(r['cycles']), float(r['p']), r['sched']); agg[k][0] += int(r['shots']); agg[k][1] += int(r['fails'])
    return agg


def series(agg, n, b, cyc, sched):
    pts = sorted((k[3], v) for k, v in agg.items() if k[0] == n and k[1] == b and k[2] == cyc and k[4] == sched and v[1] > 0)
    x = [p for p, _ in pts]; y = [per_cycle(f / s, cyc) for _, (s, f) in pts]
    lo = [per_cycle(wilson(f, s)[0], cyc) for _, (s, f) in pts]; hi = [per_cycle(wilson(f, s)[1], cyc) for _, (s, f) in pts]
    return x, y, [a - b for a, b in zip(y, lo)], [b - a for a, b in zip(y, hi)]


def ler_fig():
    agg = ler_agg('001'); agg4 = ler_agg('004')
    for k, v in agg4.items(): agg[k] = v
    fig, axes = plt.subplots(len(CODES), 2, figsize=(10.5, 11), squeeze=False)
    for i, (n, name, d, _) in enumerate(CODES):
        cycs = sorted({k[2] for k in agg if k[0] == n}) or [6]
        cyc = 6 if 6 in cycs else cycs[0]
        for jb, b in enumerate('ZX'):
            ax = axes[i][jb]; any_pts = False
            for cid, lab, col, mk, ls in CIRC:
                x, y, el, eh = series(agg, n, b, cyc, cid)
                if x:
                    ax.errorbar(x, y, yerr=[el, eh], color=col, marker=mk, ls=ls, capsize=3, mec=SURF, mew=1.5, label=lab); any_pts = True
            ax.set_xscale('log'); ax.set_yscale('log'); ax.set_title(f'{name}, {b} memory, {cyc} cycles', fontsize=10, color=INK)
            ax.set_xlabel('physical error rate p'); ax.grid(True, which='both', color=GRID, lw=0.6)
            if not any_pts:
                ax.text(0.5, 0.5, 'running – no data yet', transform=ax.transAxes, ha='center', va='center', color=INK2, fontsize=10)
                ax.set_xticks([]); ax.set_yticks([])
            if jb == 0: ax.set_ylabel('logical error rate per cycle')
    axes[0][0].legend(fontsize=8, frameon=False, loc='upper left')
    fig.suptitle('Logical error rate of S, S⁻¹ and alternating S / S⁻¹ on every code  (BP-OSD, OSD order 7; 95% error bars)',
                 fontsize=11, weight='bold', color=INK)
    fig.tight_layout(); fig.savefig(f'{OUT}/summary_ler.png', dpi=160); plt.close(fig)


# ------------------------------------------------------------------ 4. decoder comparison ([[72]])
def decoder_fig():
    A = {'BP-OSD (OSD order 7)': (ler_agg('001'), 'filled'), 'BP-OSD-0': (ler_agg('003'), 'hollow')}
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
    for ax, b in zip(axes, 'ZX'):
        for cid, lab, col, mk, ls in CIRC:
            for dec, (agg, style) in A.items():
                x, y, el, eh = series(agg, 72, b, 6, cid)
                if x:
                    ax.errorbar(x, y, yerr=[el, eh], color=col, marker=mk, ls='-' if style == 'filled' else '--', capsize=3,
                                mfc=col if style == 'filled' else SURF, mec=col, mew=1.6, alpha=1 if style == 'filled' else 0.95)
        ax.set_xscale('log'); ax.set_yscale('log'); ax.set_title(f'[[72,12,6]], {b} memory, 6 cycles', fontsize=10)
        ax.set_xlabel('physical error rate p'); ax.grid(True, which='both', color=GRID, lw=0.6)
    axes[0].set_ylabel('logical error rate per cycle')
    h = [Line2D([], [], color=c, marker=m, ls='none', ms=8, label=l) for _, l, c, m, _ in CIRC]
    h += [Line2D([], [], color=INK2, marker='o', ls='-', label='BP-OSD, OSD order 7 (filled, solid)'),
          Line2D([], [], color=INK2, marker='o', mfc=SURF, ls='--', label='BP-OSD-0 (hollow, dashed)')]
    axes[1].legend(handles=h, fontsize=8, frameon=False, loc='upper left')
    fig.suptitle('Effect of the decoder: same circuits decoded with BP-OSD order 7 (folder 001) and BP-OSD-0 (folder 003)',
                 fontsize=11, weight='bold', color=INK)
    fig.tight_layout(); fig.savefig(f'{OUT}/decoder_compare.png', dpi=160); plt.close(fig)


if __name__ == '__main__':
    method(); dcirc_fig(); ler_fig(); decoder_fig()
    print('figures written to', OUT)
