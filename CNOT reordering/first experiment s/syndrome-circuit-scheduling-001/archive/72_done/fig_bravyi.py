"""Phase 1.2: compare our S-only [[72]] curve with Bravyi et al. 2024.
Bravyi counts a trial as failed if ANY logical Pauli error occurs (X or Z type),
so we combine our two memory bases: P = 1 - (1-P_Z)(1-P_X), then per-cycle.
Reference: Table 1 (p_L(0.001) = 7e-5, p0 = 0.0048) and the fit
p_L = p^3 exp(11.09 + 365.6 p - 16088 p^2) (Table 6, d_circ = 6)."""
import datetime, numpy as np
from ler_table import aggregate, stats
from dcirc import per_cycle
from sched_ids import named
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = str(named()['S']); CYC = 6; agg = aggregate()
fit = lambda p: p**3 * np.exp(11.09 + 365.6 * p - 16088 * p**2)
pv = sorted({k[3] for k in agg if k[4] == S and k[1] in 'ZX' and k[2] == CYC})
lines = [f'\n## Phase 1.2 — reproduction of Bravyi 2024 Fig. 2A, [[72,12,6]], S only, {CYC} cycles ({datetime.date.today()})\n',
         '| p | Z fails/shots | X fails/shots | our p_L/cycle (both types) | Bravyi fit | ratio ours/Bravyi |', '|---|---|---|---|---|---|']
xs, ys, lo, hi = [], [], [], []
for p in pv:
    sz, fz = agg.get((72, 'Z', CYC, p, S), (0, 0)); sx, fx = agg.get((72, 'X', CYC, p, S), (0, 0))
    if not sz or not sx: continue
    stz, stx = stats(sz, fz, CYC), stats(sx, fx, CYC)
    P = 1 - (1 - stz['ler']) * (1 - stx['ler']); Plo = 1 - (1 - stz['lo']) * (1 - stx['lo']); Phi = 1 - (1 - stz['hi']) * (1 - stx['hi'])
    pc, pclo, pchi = per_cycle(P, CYC), per_cycle(Plo, CYC), per_cycle(Phi, CYC)
    ratio = pc / fit(p) if pc > 0 else float('nan')
    lines.append(f'| {p} | {fz}/{sz} | {fx}/{sx} | {pc:.2e} [{pclo:.1e},{pchi:.1e}] | {fit(p):.2e} | {ratio:.2f} |')
    xs.append(p); ys.append(max(pc, 1e-7)); lo.append(max(pc - pclo, 0)); hi.append(pchi - pc)
pp = np.logspace(-3, np.log10(0.01), 100)
plt.figure(figsize=(5.5, 4.2))
plt.plot(pp, fit(pp), 'k-', label='Bravyi 2024 fit (Table 6)')
plt.plot([0.001], [7e-5], 'k*', ms=10, label='Bravyi Table 1: p_L(0.001)=7e-5')
plt.errorbar(xs, ys, yerr=[lo, hi], fmt='o', color='C0', capsize=3, label='this work, S, both bases combined')
plt.plot(pp, 12 * pp, 'k--', alpha=0.4, label='break-even p_L = 12 p')
plt.xscale('log'); plt.yscale('log'); plt.xlabel('physical error rate p'); plt.ylabel('logical error rate per cycle p_L')
plt.title('[[72,12,6]], schedule S, 6 cycles'); plt.grid(True, which='both', alpha=0.3); plt.legend(fontsize=7); plt.tight_layout()
plt.savefig('figures/bravyi_reproduction.png', dpi=150)
lines.append('\nFigure: figures/bravyi_reproduction.png. PASS condition: within a factor ~3 of Bravyi at the same p.')
open('RESULTS.md', 'a').write('\n'.join(lines) + '\n'); print('\n'.join(lines))
