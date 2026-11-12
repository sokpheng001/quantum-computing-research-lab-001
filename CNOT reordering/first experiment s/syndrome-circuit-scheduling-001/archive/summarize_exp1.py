"""Table + plot for Experiment 1 (results/exp1_72.json)."""
import json, sys
import numpy as np
path = sys.argv[1] if len(sys.argv) > 1 else 'results/exp1_72.json'
d = json.load(open(path))
cyc = d['args']['cycles']
print(f"[[{d['args']['n']}]] code, k = 12 logical qubits, {cyc} cycles, failure = any of the 12 logicals wrong")
print('\nStage A: d_circ upper bounds')
for key, g in d['bounds'].items():
    print(f"  {key:8s} d_circ <= {g['min_weight']}   distinct min-weight paths found: {g['n_min_paths_found']}  (trials {g['trials']})")
print('\nStage B: logical error rate')
print(f"{'p':>7} {'config':>6} {'basis':>5} {'fails/shots':>12} {'LER':>9} {'95% CI':>19} {'per cycle':>10} {'BP conv':>8}")
rows = sorted(d['ler'], key=lambda r: (r['p'], r['basis'], ['S', 'Sinv', 'alt'].index(r['config'])))
for r in rows:
    lo, hi = r['ci95']
    print(f"{r['p']:7.4f} {r['config']:>6} {r['basis']:>5} {str(r['fails'])+'/'+str(r['shots']):>12} "
          f"{r['ler']:9.4f} [{lo:8.4f},{hi:8.4f}] {r['ler_per_cycle']:10.4f} {r['bp_converged_frac']:8.2f}")
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    style = {'S': ('C0', 'o'), 'Sinv': ('C1', 's'), 'alt': ('C2', '^')}
    for ax, basis in zip(axes, 'ZX'):
        for cfg in ['S', 'Sinv', 'alt']:
            rr = sorted([r for r in rows if r['basis'] == basis and r['config'] == cfg], key=lambda r: r['p'])
            if not rr: continue
            p = [r['p'] for r in rr]; y = [max(r['ler'], 1e-5) for r in rr]
            lo = [max(r['ler'] - r['ci95'][0], 0) for r in rr]; hi = [r['ci95'][1] - r['ler'] for r in rr]
            c, m = style[cfg]
            ax.errorbar(p, y, yerr=[lo, hi], color=c, marker=m, capsize=3, label={'S': 'S (Bravyi)', 'Sinv': 'S$^{-1}$', 'alt': 'alternating'}[cfg])
        ax.set_yscale('log'); ax.set_xlabel('physical error rate p'); ax.set_title(f'{basis} memory')
        ax.grid(True, which='both', alpha=0.3)
    axes[0].set_ylabel(f'logical failure prob. ({cyc} cycles, k=12)'); axes[0].legend()
    fig.suptitle(f"[[{d['args']['n']},12,6]] BB code: schedule S vs time-reverse vs alternating (BP-OSD)")
    fig.tight_layout(); out = 'figures/exp1_72.png'; fig.savefig(out, dpi=150); print('\nplot saved', out)
except ImportError:
    print('matplotlib not available; no plot')
