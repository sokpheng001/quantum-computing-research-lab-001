"""RESULTS_method3.md (summary tables on top) + figures F4 (and F3 if B3 ran LER).  Run from ours/."""
import json, os, csv, collections, datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RES = os.environ.get('M3_RES', '../results_method3'); FIG = os.environ.get('M3_FIG', '../figures_method3')
MD = os.environ.get('M3_MD', '../RESULTS_method3.md')
CODES = [72, 90, 108]; NAME = {72: '[[72,12,6]]', 90: '[[90,8,10]]', 108: '[[108,8,10]]'}
BRAVYI = {72: 6, 90: 8, 108: 8}; D = {72: 6, 90: 10, 108: 10}
INK, MUTED, GRID, C1, C2 = '#0b0b0b', '#52514e', '#e4e3df', '#2a78d6', '#eb6834'
def J(n, f):
    p = os.path.join(RES, str(n), f); return json.load(open(p)) if os.path.exists(p) else None
def wilson(f, n, z=1.96):
    if n == 0: return 0, 1
    p = f / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)
def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %I:%M %p KST')

# ---------------------------------------------------------------- F4
def f4():
    codes = [n for n in CODES if J(n, 'screen.json')]
    if not codes: return
    plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': MUTED})
    fig, axs = plt.subplots(1, len(codes), figsize=(3.8 * len(codes), 3.0), squeeze=False)
    for ax, n in zip(axs[0], codes):
        s = J(n, 'screen.json'); b = J(n, 'b0.json'); h = {int(k): v for k, v in s['hist'].items()}
        xs = np.arange(min(h), max(max(h), D[n]) + 1)
        ax.bar(xs, [h.get(x, 0) for x in xs], width=0.8, color=C1, edgecolor='white', linewidth=1, zorder=2)
        top_ = max(h.values()) * 1.12
        ax.vlines(BRAVYI[n], 0, top_, color=INK, lw=1.2, zorder=3, label=f"Bravyi's value {BRAVYI[n]} (= d1 of his schedule S here: {b['d1S']})")
        if D[n] != BRAVYI[n]: ax.vlines(D[n], 0, top_, color=MUTED, lw=1, ls='--', zorder=3, label=f'code distance d = {D[n]}')
        else: ax.plot([], [], color=MUTED, lw=1, ls='--', label=f'code distance d = {D[n]} (same line)')
        for x in xs:
            if h.get(x): ax.text(x, h[x] + max(h.values()) * 0.02, f'{h[x]}', ha='center', va='bottom', fontsize=7, color=INK,
                                 bbox=dict(facecolor='white', edgecolor='none', pad=1), zorder=4)
        ax.set_ylim(0, max(h.values()) * 1.45); ax.set_xticks(xs)
        ax.set_xlabel('one-cycle distance d1 (upper bound)'); ax.set_ylabel('number of schedules')
        ax.set_title(f'{NAME[n]}: {sum(h.values())} schedules', loc='left', fontsize=9)
        ax.grid(axis='y', color=GRID, lw=0.6, zorder=0); ax.legend(fontsize=7, frameon=False, loc='upper left', borderaxespad=0.2)
    fig.text(0.01, -0.03, 'd1 = min over X- and Z-type faults, Bravyi setup (1 noisy + 2 noiseless cycles), \n>= 200 trials per fault type and schedule; '
             'schedules above d1(S) re-run up to 9000.', fontsize=7, color=MUTED)
    fig.tight_layout(); os.makedirs(FIG, exist_ok=True)
    for e in ('png', 'pdf'): fig.savefig(os.path.join(FIG, f'F4_d1_hist.{e}'), dpi=200, bbox_inches='tight')
    plt.close(fig); print('written F4')

# ---------------------------------------------------------------- F6 / F7 (extra stage)
SERIES = [('#2a78d6', 'o', '-'), ('#eb6834', 's', '-'), ('#1baf7a', '^', '--'), ('#eda100', 'D', '--')]   # palette slots 1-4

def _extra_circuits(n):
    e = J(n, 'extra_dcirc.json') or J(n, 'ler.json')
    f = os.path.join(RES, str(n), 'ler.csv')
    if e: circs = list(e['circuits'])
    elif os.path.exists(f):                          # stage still running: circuits in the order they appear
        circs = list(dict.fromkeys(r['circuit'] for r in csv.DictReader(open(f))))
    else: return None, None
    if not circs: return None, None
    b = J(n, 'b0.json'); S, Si = str(b['S']), f"{b['S']}+{b['Sinv']}"
    def nm(k):
        if k == S: return 'S (Bravyi)'
        if k == Si: return 'alt[S, S$^{-1}$]'
        return f'A* = #{k}' if '+' not in k else 'alt[A*, A*$^{-1}$] = #' + k.replace('+', ' + #')
    return circs, nm

def f6():
    from scipy.stats import beta
    codes = [n for n in CODES if os.path.exists(os.path.join(RES, str(n), 'ler.csv')) and _extra_circuits(n)[0]]
    if not codes: return
    fig, axs = plt.subplots(len(codes), 2, figsize=(9, 3.4 * len(codes)), squeeze=False)
    pc = lambda q: 1 - (1 - q) ** (1 / 6)
    for row, n in zip(axs, codes):
        rows = list(csv.DictReader(open(os.path.join(RES, str(n), 'ler.csv')))); circs, nm = _extra_circuits(n)
        for ax, basis in zip(row, 'ZX'):
            drawn = False
            for si, ((col, mk, ls), k) in enumerate(zip(SERIES, circs)):
                agg = collections.defaultdict(lambda: [0, 0])
                for r in rows:
                    if r['circuit'] == k and r['basis'] == basis: agg[float(r['p'])][0] += int(r['fails']); agg[float(r['p'])][1] += int(r['shots'])
                ps = sorted(p for p in agg if agg[p][1])
                if not ps: continue
                y = [pc(agg[p][0] / agg[p][1]) for p in ps]
                lo = [pc(beta.ppf(0.025, agg[p][0], agg[p][1] - agg[p][0] + 1)) if agg[p][0] else 0 for p in ps]
                hi = [pc(beta.ppf(0.975, agg[p][0] + 1, agg[p][1] - agg[p][0])) for p in ps]
                lab = nm(k)
                ok = [i for i in range(len(ps)) if agg[ps[i]][0] > 0]
                if len(ok) >= 2:
                    sl = np.polyfit(np.log([ps[i] for i in ok]), np.log([y[i] for i in ok]), 1)[0]; lab += f', slope {sl:.1f}'
                running = [agg[p][0] < 50 for p in ps]
                if any(running): lab += ' (running)'
                xs = [p * (1 + 0.012 * (si - 1.5)) for p in ps]                  # small dodge so error bars do not overlap
                ax.errorbar(xs, [100 * v for v in y], yerr=[[100 * (y[i] - lo[i]) for i in range(len(ps))], [100 * (hi[i] - y[i]) for i in range(len(ps))]],
                            color=col, ls=ls, lw=2, capsize=3, label=lab, marker='none')
                for x_, y_, rn in zip(xs, y, running):
                    ax.plot([x_], [100 * y_], marker=mk, ms=7, color=col if not rn else 'white', mec=col if rn else 'white', mew=1.5, zorder=4)
                drawn = True
            if not drawn:
                ax.text(0.5, 0.5, 'pending', transform=ax.transAxes, ha='center', va='center', color=MUTED, fontsize=10)
                ax.set_yticks([])
            ax.set_xscale('log')
            if drawn: ax.set_yscale('log')
            ax.set_xlim(0.0036, 0.0056); ax.set_xticks([0.004, 0.005]); ax.set_xticklabels(['0.4%', '0.5%']); ax.minorticks_off()
            if drawn:
                ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(base=10, subs=(1, 2, 3, 5)))
                ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:g}%'))
            ax.set_xlabel('physical error rate p'); ax.set_ylabel('logical error rate per cycle')
            ax.set_title(f'{NAME[n]}, {basis} basis, 6 cycles', loc='left', fontsize=9)
            ax.grid(color=GRID, lw=0.6, which='both')
            if drawn: ax.legend(fontsize=7, frameon=False, loc='upper left')
    fig.text(0.01, -0.02, 'Method 3 extra stage: stim circuit, full circuit-level depolarising noise, BP-OSD (min-sum 0.625, OSD-CS 7); '
             '95% Clopper-Pearson ranges; >= 50 failures per point (hollow marker = still running).', fontsize=7, color=MUTED)
    fig.tight_layout(); os.makedirs(FIG, exist_ok=True)
    for e in ('png', 'pdf'): fig.savefig(os.path.join(FIG, f'F6_ler.{e}'), dpi=200, bbox_inches='tight')
    plt.close(fig); print('written F6')

def f7():
    codes = [n for n in CODES if J(n, 'extra_dcirc.json')]
    if not codes: return
    fig, axs = plt.subplots(1, len(codes), figsize=(4.6 * len(codes), 3.2), squeeze=False)
    for ax, n in zip(axs[0], codes):
        e = J(n, 'extra_dcirc.json'); circs, nm = _extra_circuits(n)
        for i, k in enumerate(circs):
            mm = e['circuits'][k]['mins']
            for j, (key, col, mk) in enumerate((('X4', SERIES[0][0], 'o'), ('X6', SERIES[0][0], 's'), ('Z4', SERIES[1][0], 'o'), ('Z6', SERIES[1][0], 's'))):
                ax.scatter(i + (j - 1.5) * 0.12, mm[key], color=col, marker=mk, s=40, edgecolor='white', linewidth=0.8, zorder=3,
                           label={'X4': 'X faults, 4 cycles', 'X6': 'X faults, 6 cycles', 'Z4': 'Z faults, 4 cycles', 'Z6': 'Z faults, 6 cycles'}[key] if i == 0 else None)
        ax.axhline(BRAVYI[n], color=INK, lw=1.2, zorder=1, label=f"Bravyi's value {BRAVYI[n]}")
        ax.axhline(D[n], color=MUTED, lw=1, ls='--', zorder=1, label=f'code distance d = {D[n]}')
        ax.set_xticks(range(len(circs))); ax.set_xticklabels([nm(k) for k in circs], rotation=20, ha='right', fontsize=7)
        allv = [v for k in circs for v in e['circuits'][k]['mins'].values()]
        ax.set_ylim(min(min(allv), BRAVYI[n]) - 1, max(max(allv), D[n]) + 0.6)
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True)); ax.set_ylabel('circuit-level distance (upper bound)')
        ax.set_title(f'{NAME[n]}: 5 seeds x 1000 trials', loc='left', fontsize=9); ax.grid(axis='y', color=GRID, lw=0.6, zorder=0)
        ax.legend(fontsize=6.5, frameon=False, loc='upper left', bbox_to_anchor=(1.0, 1.0))
    fig.text(0.01, -0.06, 'Bravyi setup: 4 or 6 noisy cycles + 2 noiseless; values are upper bounds; minimum paths re-simulated exactly.', fontsize=7, color=MUTED)
    fig.tight_layout(); os.makedirs(FIG, exist_ok=True)
    for e in ('png', 'pdf'): fig.savefig(os.path.join(FIG, f'F7_dcirc.{e}'), dpi=200, bbox_inches='tight')
    plt.close(fig); print('written F7')


# ---------------------------------------------------------------- report
def report():
    L = ['# RESULTS_method3.md — one-cycle distance ranking (Method 3)', '',
         f'Task: docs/task.md. Rebuilt by ours/report_m3.py; last update {now()}. Server runs Track B only; Track A runs on the Mac mini.',
         'All distances are upper bounds from Bravyi\'s randomised BP-OSD search unless stated otherwise.', '',
         '## Summary', '', '### Table 1 — Track A (Mac mini)', '',
         '| Bravyi bound reproduced? | Section 6 setup | Weight-10 sets hidden in alt[S,S^-1] | in alt[S,S_mirror] | Verdict for [[144]] |',
         '|---|---|---|---|---|', '| not run on this server (Track A is the Mac mini\'s) | | | | |', '',
         '### Table 2 — Track B', '',
         '| Code | d1(S) | Bravyi value | max d1 over all schedules | # schedules above d1(S) | best alt[A,A^-1] | Beats S? |',
         '|---|---|---|---|---|---|---|']
    sent = []
    for n in CODES:
        b, s, b3 = J(n, 'b0.json'), J(n, 'screen.json'), J(n, 'b3.json')
        if not b: L.append(f'| {NAME[n]} | pending | <= {BRAVYI[n]} | | | | |'); continue
        d1s = f'upper bound {b["d1S"]} ({"PASS" if b["PASS"] else "FAIL"})'
        if not s: L.append(f'| {NAME[n]} | {d1s} | <= {BRAVYI[n]} | pending | | | |'); continue
        best, beat = '—', 'no'
        if b3 and b3.get('circuits'):
            alts = {k: v for k, v in b3['circuits'].items() if '+' in k}
            if alts:
                k = max(alts, key=lambda k: alts[k]['min']); best = f'alt[#{k.replace("+", ", #")}]: upper bound {alts[k]["min"]}'
                beat = 'yes' if b3['beats'] else 'no'
        elif not s['above_S']: best = 'none needed'
        L.append(f'| {NAME[n]} | {d1s} | <= {BRAVYI[n]} | upper bound {s["max"]} ({s["n_at_max"]} schedules) | {s["n_above_S"]} | {best} | {beat if s["above_S"] or b3 else "no"} |')
        if not s['above_S']:
            sent.append(f'- {NAME[n]}: no depth-7 schedule has a one-cycle distance above {b["d1S"]} (Bravyi setup, 1 noisy cycle, X and Z faults, '
                        f'>= 200 trials per fault type and schedule, up to 9000 for any schedule above {b["d1S"]}), so no alternation can beat Bravyi\'s schedule.')
        elif b3 and b3.get('circuits'):
            for k, v in b3['circuits'].items():
                if '+' in k:
                    A = int(k.split('+')[0])
                    sent.append(f'- {NAME[n]}: schedule #{A} has d1 upper bound {s["max"] if A in s["at_max"] else ">" + str(b["d1S"])}; alt[#{A}, #{k.split("+")[1]}] '
                                f'has upper bound {v["min"]} versus {b3["circuits"][str(b["S"])]["min"]} for S (4 and 6 cycles, X and Z faults, 5 seeds x 1000 trials).')
        else:
            sent.append(f'- {NAME[n]}: {s["n_above_S"]} schedules have d1 above {b["d1S"]}; B3 pending.')
    L += ['', '### Table 3 — circuit-level distance and logical error rate (extra stage, user request; not in task.md)', '',
          'Circuits: S, alt[S, S^-1], A* (top-ranked schedule: at the maximum d1, the one whose search needed the most trials to reach it) and '
          'alt[A*, A*^-1]. Distance: Bravyi setup, 4 and 6 noisy cycles + 2 noiseless, X and Z faults, 5 seeds x 1000 trials (upper bounds). '
          'LER: stim circuit, full circuit-level depolarising noise, BP-OSD (min-sum 0.625, OSD-CS 7), 6 cycles; per-cycle rate with 95% range.', '',
          '| Code | Circuit | d_circ upper bound (X 4c / X 6c / Z 4c / Z 6c) | LER/cycle Z, p=0.5% | X, p=0.5% | Z, p=0.4% | X, p=0.4% |', '|---|---|---|---|---|---|---|']
    any3 = False
    for n in CODES:
        e = J(n, 'extra_dcirc.json')
        if not e:
            cc, _ = _extra_circuits(n)
            if cc: e = dict(circuits={k: {} for k in cc})
        if not e: continue
        any3 = True; lrows = list(csv.DictReader(open(os.path.join(RES, str(n), 'ler.csv')))) if os.path.exists(os.path.join(RES, str(n), 'ler.csv')) else []
        names = {str(J(n, 'b0.json')['S']): 'S', f"{J(n, 'b0.json')['S']}+{J(n, 'b0.json')['Sinv']}": 'alt[S, S^-1]'}
        for k, v in e['circuits'].items():
            nm = names.get(k, f'A* = #{k}' if '+' not in k else f'alt[A*, A*^-1] = #{k.replace("+", " + #")}')
            cells = []
            for p, bs in ((0.005, 'Z'), (0.005, 'X'), (0.004, 'Z'), (0.004, 'X')):
                f_ = sum(int(r['fails']) for r in lrows if r['circuit'] == k and r['basis'] == bs and float(r['p']) == p)
                s_ = sum(int(r['shots']) for r in lrows if r['circuit'] == k and r['basis'] == bs and float(r['p']) == p)
                if not s_: cells.append('pending'); continue
                pc = lambda q: 1 - (1 - q) ** (1 / 6)
                lo, hi = wilson(f_, s_); cells.append(f'{100*pc(f_/s_):.2f}% ({100*pc(lo):.2f}–{100*pc(hi):.2f}%), {f_}/{s_}')
            mm = v.get('mins', {})
            dc = f'{v["min"]} ({mm.get("X4")} / {mm.get("X6")} / {mm.get("Z4")} / {mm.get("Z6")})' if v.get('min') is not None else 'pending'
            L.append(f'| {NAME[n]} | {nm} | {dc} | ' + ' | '.join(cells) + ' |')
    if not any3: L.append('| pending (starts after the [[108]] screen) | | | | | | |')
    L += ['', '### Per code', ''] + (sent or ['- pending']) + ['']
    for n in CODES:
        b, s, b3 = J(n, 'b0.json'), J(n, 'screen.json'), J(n, 'b3.json')
        if not b: continue
        L += [f'## {NAME[n]}', '', f'### B0 — regression: {"PASS" if b["PASS"] else "FAIL"}', '',
              f'Schedules: {b["schedules"]} valid (S = #{b["S"]}, S^-1 = #{b["Sinv"]}). Bravyi mapping sX = [idle,1,4,3,5,0,2], '
              f'sZ = [3,5,0,1,2,4,idle] equals S: {b["map_ok"]}. d1(S): X-type faults upper bound {b["d1S_X"][0]} ({b["d1S_X"][1]} trials), '
              f'Z-type upper bound {b["d1S_Z"][0]} ({b["d1S_Z"][1]} trials); min {b["d1S"]} vs Bravyi {BRAVYI[n]}.']
        if s:
            L += ['', f'### d1 of all schedules', '',
                  f'Histogram of d1 (min over X/Z faults; after re-runs): {s["hist"]}.  At the fixed 200-trial budget: {s["hist_base200"]}.',
                  f'Maximum: upper bound {s["max"]}, reached by {s["n_at_max"]} schedules (ids: {s["at_max"][:40]}{" ..." if s["n_at_max"] > 40 else ""}).',
                  f'Schedules with d1 above d1(S) after up to 9000 trials per fault type: {s["n_above_S"]} {s["above_S"][:40]}.',
                  f'Table: results_method3/{n}/d1_{n}.csv (id, d1_Z, d1_X, trials, ...).']
        if b3 and b3.get('circuits'):
            L += ['', '### B3 — alt[A, A^-1] for schedules above d1(S)', '', '| circuit | noiseless ok | X 4c | X 6c | Z 4c | Z 6c | min | min paths exactly re-simulated |', '|---|---|---|---|---|---|---|---|']
            for k, v in b3['circuits'].items():
                mm = v.get('mins', {})
                L.append(f'| {k} | {v["noiseless_ok"]} | {mm.get("X4")} | {mm.get("X6")} | {mm.get("Z4")} | {mm.get("Z6")} | {v.get("min")} | {v.get("exact")} |')
            L.append(f'Beats S: {b3["beats"] or "none"} (5 seeds x 1000 trials per cycle count and fault type; Bravyi settings).')
        L.append('')
    L += ['Figures: figures_method3/F4_d1_hist.png; F6_ler.png (error rates) and F7_dcirc.png (distances) from the extra stage; F3 only if B3 finds a winner.', '']
    open(MD, 'w').write('\n'.join(L)); print('written', MD)

if __name__ == '__main__':
    f4(); f6(); f7(); report()
