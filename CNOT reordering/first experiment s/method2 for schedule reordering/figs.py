"""Figures F1-F3 of docs/task.md -> figures_partner/*.png + *.pdf.  Draws whatever stages are finished."""
import json, os, csv, collections
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RES = os.environ.get('PARTNER_RES', 'results_partner'); OUT = os.environ.get('PARTNER_FIG', 'figures_partner')
CODES = [72, 90, 108]; D = {72: 6, 90: 10, 108: 10}; BRAVYI = {72: 6, 90: 8, 108: 8}
Z_COL, X_COL, INK, MUTED, GRID = '#2a78d6', '#eb6834', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False})

def J(n, f):
    p = os.path.join(RES, str(n), f)
    return json.load(open(p)) if os.path.exists(p) else None

def label(spec, ids):
    inv = {str(v): k for k, v in ids.items()}
    nm = {'S': 'S', 'Sinv': 'S$^{-1}$', 'Smirror': 'S$_{mirror}$'}
    p = spec.split('+')
    if len(p) == 1: return nm.get(inv.get(p[0]), '#' + p[0])
    return 'alt[S, ' + (nm[inv[p[1]]] if p[1] in inv else "S'#" + p[1]) + ']'

def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    for ext in ('png', 'pdf'): fig.savefig(os.path.join(OUT, f'{name}.{ext}'), dpi=200, bbox_inches='tight')
    plt.close(fig); print('written', os.path.join(OUT, name + '.png'))

def f1():
    codes = [n for n in CODES if J(n, 'stage4.json')]
    if not codes: return
    fig, axs = plt.subplots(len(codes), 1, figsize=(9, 2.9 * len(codes)), squeeze=False)
    for ax, n in zip(axs[:, 0], codes):
        s4 = J(n, 'stage4.json'); ids = J(n, 'named_ids.json'); specs = s4['specs']
        per = collections.defaultdict(lambda: 10**9)                   # (spec, basis, seed) -> min over cycles
        for k, v in s4['table'].items():
            c, b, cy, sd = k.split('|'); per[(c, b, int(sd))] = min(per[(c, b, int(sd))], v)
        rng = np.random.default_rng(0)
        for i, s in enumerate(specs):
            for b, col, mk, dx in (('Z', Z_COL, 'o', -0.12), ('X', X_COL, '^', 0.12)):
                ys = [per[(s, b, sd)] for sd in range(1, 6) if (s, b, sd) in per]
                xs = i + dx + rng.uniform(-0.05, 0.05, len(ys))
                ax.scatter(xs, ys, s=30, marker=mk, color=col, edgecolor='white', linewidth=0.8, zorder=3,
                           label=f'{b} basis (one point per seed)' if i == 0 else None)
            ok, bad = s4['verified'][s]
            if ok and not bad:
                ax.scatter([i], [s4['mins'][s] - 0.45], marker='*', s=60, color=INK, zorder=4,
                           label='minimum-weight path verified exactly' if i == 0 else None)
        ax.axhline(D[n], ls='--', lw=1, color=MUTED, zorder=1, label=f'code distance d = {D[n]}')
        ax.axhline(BRAVYI[n], ls='-', lw=1.2, color=INK, zorder=1, label=f"Bravyi d$_{{circ}}$(S) $\\leq$ {BRAVYI[n]}")
        ax.set_xticks(range(len(specs))); ax.set_xticklabels([label(s, ids) for s in specs], rotation=30, ha='right')
        lo = min(min(per.values()), BRAVYI[n]) - 1; hi = max(max(per.values()), D[n]) + 1
        ax.set_ylim(lo, hi); ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
        n_k = {72: '[[72,12,6]]', 90: '[[90,8,10]]', 108: '[[108,8,10]]'}[n]
        ax.set_title(f'{n_k}: minimum fault-path weight found ({s4["trials_per_seed"]} trials/seed, 5 seeds, min over 4 and 6 cycles)',
                     loc='left', fontsize=9, color=INK)
        ax.set_ylabel('weight (upper bound)')
        ax.legend(fontsize=7, frameon=False, loc='upper left', bbox_to_anchor=(1.0, 1.0))
    fig.text(0.01, -0.01, 'Values are upper bounds on the circuit-level distance.', fontsize=8, color=MUTED)
    fig.tight_layout(); save(fig, 'F1_bounds')

def f2():
    codes = [n for n in CODES if J(n, 'stage3.json')]
    if not codes: return
    fig, axs = plt.subplots(1, len(codes), figsize=(3.6 * len(codes), 2.8), squeeze=False)
    for ax, n in zip(axs[0], codes):
        s3 = J(n, 'stage3.json'); h = {int(k): v for k, v in s3['hist'].items()}; F = s3['families']
        xs = np.arange(0, F + 1)
        ax.bar(xs, [h.get(x, 0) for x in xs], width=0.8, color=Z_COL, edgecolor='white', linewidth=1)
        ymax = max(h.values())
        marks = [('score_Sinv', 'S$^{-1}$'), ('score_Smirror', 'S$_{mirror}$')]
        if s3['score_Sinv'] == s3['score_Smirror']: marks = [('score_Sinv', 'S$^{-1}$ and S$_{mirror}$')]
        for j, (key_, nm) in enumerate(marks):
            x = s3[key_]
            ax.annotate(f'{nm}: {x}', xy=(x, h.get(x, 0)), xytext=(x, ymax * (1.12 + 0.1 * j)), ha='right' if x > F / 2 else 'left',
                        fontsize=7, color=INK, arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.8))
        ax.set_ylim(0, ymax * 1.35); ax.set_xlim(-0.8, F + 0.8)
        ax.set_xlabel(f'score = S families still undetected + logical (of {F})'); ax.set_ylabel('number of partners S\'')
        ax.set_title({72: '[[72,12,6]]', 90: '[[90,8,10]]', 108: '[[108,8,10]]'}[n] + f': {s3["partners"]} partners', loc='left', fontsize=9)
        ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
    fig.tight_layout(); save(fig, 'F2_screen')

def f3():
    from scipy.stats import beta
    runs = [(n, J(n, 'stage5.json')) for n in CODES]; runs = [(n, r) for n, r in runs if r and r.get('ran')]
    if not runs: return
    fig, axs = plt.subplots(len(runs), 2, figsize=(8, 3.2 * len(runs)), squeeze=False)
    for row, (n, r) in zip(axs, runs):
        rows = list(csv.DictReader(open(os.path.join(RES, str(n), 'ler.csv'))))
        for ax, b in zip(row, 'ZX'):
            for spec, col, mk, nm in ((r['S'], Z_COL, 'o', 'S'), (r['winner'], X_COL, '^', f'alt #{r["winner"]}')):
                agg = collections.defaultdict(lambda: [0, 0])
                for x in rows:
                    if x['circuit'] == spec and x['basis'] == b:
                        agg[float(x['p'])][0] += int(x['fails']); agg[float(x['p'])][1] += int(x['shots'])
                ps = sorted(agg); pc = lambda q: 1 - (1 - q) ** (1 / 6)
                y, lo, hi = [], [], []
                for p in ps:
                    f, s = agg[p]; y.append(pc(f / s) if f else pc(beta.ppf(0.95, 1, s)))
                    lo.append(pc(beta.ppf(0.025, f, s - f + 1)) if f else 0); hi.append(pc(beta.ppf(0.975, f + 1, s - f)))
                ok = [i for i in range(len(ps)) if agg[ps[i]][0] > 0]
                sl = ''
                if len(ok) >= 2:
                    X = np.log([ps[i] for i in ok]); Y = np.log([y[i] for i in ok])
                    cf, cov = np.polyfit(X, Y, 1, cov=True) if len(ok) > 2 else (np.polyfit(X, Y, 1), np.zeros((2, 2)))
                    sl = f', slope {cf[0]:.1f} ± {np.sqrt(cov[0, 0]):.1f}'
                ax.errorbar([ps[i] for i in ok], [y[i] for i in ok], yerr=[[y[i] - lo[i] for i in ok], [hi[i] - y[i] for i in ok]],
                            fmt=mk + '-', color=col, ms=6, lw=2, capsize=2, label=nm + sl)
                z = [i for i in range(len(ps)) if agg[ps[i]][0] == 0]
                if z: ax.errorbar([ps[i] for i in z], [y[i] for i in z], yerr=[[y[i] * 0.4 for i in z], [0] * len(z)], uplims=True, fmt=mk, color=col, ms=6)
            ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlabel('physical error rate p'); ax.set_ylabel('logical error rate per cycle')
            ax.set_title(f'[[{n}]] {b} basis, 6 cycles', loc='left', fontsize=9); ax.legend(fontsize=7, frameon=False)
            ax.grid(color=GRID, lw=0.6, which='both')
    fig.tight_layout(); save(fig, 'F3_ler')

if __name__ == '__main__':
    f1(); f2(); f3()
