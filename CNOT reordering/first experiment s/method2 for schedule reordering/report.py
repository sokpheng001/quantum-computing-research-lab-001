"""Write RESULTS_partner.md: the three summary tables at the top, then per-code details.
Rebuilt from results_partner/<n>/stage*.json after every stage (finished stages only)."""
import json, os, csv, collections, datetime
import numpy as np

RES = os.environ.get('PARTNER_RES', 'results_partner'); OUT = os.environ.get('PARTNER_MD', 'RESULTS_partner.md')
CODES = [72, 90, 108]; NAME = {72: '[[72,12,6]]', 90: '[[90,8,10]]', 108: '[[108,8,10]]'}; BRAVYI = {72: 6, 90: 8, 108: 8}

def J(n, f):
    p = os.path.join(RES, str(n), f)
    return json.load(open(p)) if os.path.exists(p) else None

def lab(spec, ids):
    inv = {str(v): k for k, v in ids.items()}; nm = {'S': 'S', 'Sinv': 'S^-1', 'Smirror': 'S_mirror'}
    p = spec.split('+')
    if len(p) == 1: return nm.get(inv.get(p[0]), f'#{p[0]}')
    return f'alt [S, {nm[inv[p[1]]]}]' if p[1] in inv else f"alt [S, S'#{p[1]}]"

def settings(s):
    return f'{s["trials_per_seed"]} trials/seed, 5 seeds, Z+X, 4+6 cycles'

def wilson(f, n, z=1.96):
    if n == 0: return 0, 1
    p = f / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)

def pct(x): return f'{100 * x:.2f}%'

L = [f'# RESULTS_partner.md — path-targeted partner search (Method 2)', '',
     f'Task: docs/task.md. Rebuilt by report.py; last update {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %I:%M %p")} KST. '
     'All distances are upper bounds from the randomised BP-OSD search unless marked as exactly verified.', '',
     '## Summary', '', '### Table A — regression and verdict', '',
     '| Code | Bravyi d_circ(S) | Our S | Stage 0 | Best alt circuit | Its bound | Beats S? |', '|---|---|---|---|---|---|---|']
sent = []
for n in CODES:
    s0, s4, ids = J(n, 'stage0.json'), J(n, 'stage4.json'), J(n, 'named_ids.json')
    if not s0: L.append(f'| {NAME[n]} | <= {BRAVYI[n]} | pending | pending | | | |'); continue
    our = f'<= {s0["min"]} ({settings(s0)})'; st = 'PASS' if s0['PASS'] else f'FAIL ({s0["min"]} vs {BRAVYI[n]})'
    if s4:
        alts = {s: v for s, v in s4['mins'].items() if '+' in s}
        best = max(alts, key=lambda s: (alts[s], -s4['specs'].index(s)))
        beat = 'yes' if alts[best] > s4['mins'][s4['specs'][0]] else 'no'
        L.append(f'| {NAME[n]} | <= {BRAVYI[n]} | {our} | {st} | {lab(best, ids)} | upper bound {alts[best]} | {beat} |')
        S = s4['mins'][s4['specs'][0]]
        if beat == 'no':
            sent.append(f'- {NAME[n]}: no partner of S raises the distance above {S} (best alternating circuit {lab(best, ids)}: '
                        f'upper bound {alts[best]} vs {S} for S; {settings(s4)}).')
        else:
            x = s4['cross'].get(best, {})
            sent.append(f'- {NAME[n]}: {lab(best, ids)} has upper bound {alts[best]} vs {S} for S ({settings(s4)}); '
                        f"exact check of S's weight-{S} paths in it: {x.get('S_to_alt')}.")
    else:
        L.append(f'| {NAME[n]} | <= {BRAVYI[n]} | {our} | {st} | pending | | |')
L += ['', '### Table B — partner screen', '',
      '| Code | S min-weight families | Partners tested | Partners catching all families | Best survivor\'s bound |', '|---|---|---|---|---|']
for n in CODES:
    s2, s3, s4, ids = J(n, 'stage2.json'), J(n, 'stage3.json'), J(n, 'stage4.json'), J(n, 'named_ids.json')
    if not s3: L.append(f'| {NAME[n]} | {sum(len(v) for v in s2["min"]["groups"].values()) if s2 else "pending"} | pending | | |'); continue
    w = s2['min']['weight']; bs = '—'
    if s4:
        sv = [f'{s4["specs"][0]}+{p}' for p in s3['survivors']]
        sv = [s for s in sv if s in s4['mins']]
        if sv:
            b = max(sv, key=lambda s: s4['mins'][s]); bs = f'upper bound {s4["mins"][b]} ({lab(b, ids)})'
    L.append(f'| {NAME[n]} | {s3["families"]} (weight {w}) | {s3["partners"]} | {s3["n_zero"]} | {bs} |')
L += ['', '### Table C — logical error rate (only if Stage 5 ran)', '']
c_rows = []
for n in CODES:
    s5 = J(n, 'stage5.json')
    if not (s5 and s5.get('ran')): continue
    rows = list(csv.DictReader(open(os.path.join(RES, str(n), 'ler.csv'))))
    for spec in (s5['S'], s5['winner']):
        for p in sorted({float(r['p']) for r in rows}, reverse=True):
            cell = {}
            for b in 'ZX':
                f = sum(int(r['fails']) for r in rows if r['circuit'] == spec and r['basis'] == b and float(r['p']) == p)
                s = sum(int(r['shots']) for r in rows if r['circuit'] == spec and r['basis'] == b and float(r['p']) == p)
                if s: lo, hi = wilson(f, s); cell[b] = f'{f}/{s} = {pct(f/s)} ({pct(lo)}–{pct(hi)})'
            c_rows.append(f'| {NAME[n]} | {lab(spec, J(n, "named_ids.json"))} | {p} | {cell.get("Z", "—")} | {cell.get("X", "—")} | see F3 |')
if c_rows: L += ['| Code | Circuit | p | Z basis (95% CI) | X basis (95% CI) | Slope |', '|---|---|---|---|---|---|'] + c_rows
else: L.append('Stage 5 did not run (it runs only for a [[90]] or [[108]] circuit that beats S).')
L += ['', '### Verdict per code', ''] + (sent or ['- pending']) + ['']

# -------- details
for n in CODES:
    s0, s1, s2, s3, s4, ids = (J(n, f) for f in ('stage0.json', 'stage1.json', 'stage2.json', 'stage3.json', 'stage4.json', 'named_ids.json'))
    if not s0: continue
    L += [f'## {NAME[n]}', '', f'### Stage 0 — setup and regression: {"PASS" if s0["PASS"] else "FAIL"}', '',
          f'n = {s0["n"]}, k = {s0["k"]}, H_X H_Z^T = 0: {s0["commute"]}. S noiseless detectors all zero (both bases) at 2 and 6 cycles: '
          f'{all(s0["noiseless"].values())}. S bound: minimum {s0["min"]} (Bravyi {s0["target"]}), {settings(s0)}.', '',
          '| basis | cycles | seed 1 | seed 2 | seed 3 | seed 4 | seed 5 |', '|---|---|---|---|---|---|---|']
    for b in 'ZX':
        for cy in (4, 6):
            L.append(f'| {b} | {cy} | ' + ' | '.join(str(s0['table'].get(f'{s0["S"]}|{b}|{cy}|{sd}', '')) for sd in range(1, 6)) + ' |')
    if s1:
        L += ['', '### Stage 1 — valid schedules', '',
              f'{s1["count"]} valid depth-7 schedules (Z-first {s1["z_first"]}, X-first {s1["x_first"]}): no same-round collision and all-zero '
              f'noiseless detectors in both bases (stim, every schedule). ids: S = {s1["ids"]["S"]}, S^-1 = {s1["ids"]["Sinv"]}, '
              f'S_mirror = {s1["ids"]["Smirror"]}; time-reverse ids: {s1["reverse_ids"]}. File: results_partner/{n}/schedules.jsonl.']
    if s2:
        w = s2['min']['weight']; L += ['', f'### Stage 2 — S\'s weakest paths (weight {w})', '',
              '| basis | cycles | distinct sets | families | cycle spans of families |', '|---|---|---|---|---|']
        for g, fl in s2['min']['groups'].items():
            b, cy = g.split('|')
            L.append(f'| {b} | {cy} | {sum(f["members"] for f in fl)} | {len(fl)} | {dict(collections.Counter(f["span"] for f in fl))} |')
        L += ['', 'One representative per family (first DEM column\'s physical location shown for each fault: Pauli, qubits, cycle):', '']
        for g, fl in s2['min']['groups'].items():
            for i, f in enumerate(fl):
                ph = '; '.join(f'{x["paulis"]}@{",".join(x["qubits"])} c{x["cycle"]}' for x in f['physical'])
                L.append(f'- {g} family {i} ({f["members"]} sets, span {f["span"]} cycle(s)): {ph}')
    if s3:
        L += ['', '### Stage 3 — exact screen of all partners', '',
              f'{s3["partners"]} partners S\' (both starting sides, S itself excluded). Each S family representative placed so that all its '
              f'faults fall in S cycles of alt [S, S\'] (every time shift tried); detector and observable flips computed exactly by stim '
              f'FlipSimulator in the alt circuit. Score = families still undetected AND logical.', '',
              f'- Score histogram: {s3["hist"]}', f'- Partners with score 0: {s3["n_zero"]} {s3["zero"][:30]}',
              f'- S^-1 ({ids["Sinv"]}): score {s3["score_Sinv"]}; S_mirror ({ids["Smirror"]}): score {s3["score_Smirror"]}',
              f'- Status counts over all (partner, family) pairs: {s3["status_counts"]}',
              f'- Sanity, alt [S, S] = S: {dict(collections.Counter(x[3] for x in s3["sanity_SS"]["min"]))}',
              f'- Stage 4 survivors: {s3["survivors"]}']
    if s4:
        L += ['', '### Stage 4 — distance search on the survivors', '', f'Settings: {settings(s4)}; S rerun in the same batch.', '',
              '| circuit | ids | Z 4c | Z 6c | X 4c | X 6c | min | min path exactly verified | alt sets in S / S sets in alt (exact) |', '|---|---|---|---|---|---|---|---|---|']
        for s in s4['specs']:
            cell = lambda b, cy: min(s4['table'][f'{s}|{b}|{cy}|{sd}'] for sd in range(1, 6))
            ok, bad = s4['verified'][s]; x = s4['cross'].get(s)
            L.append(f'| {lab(s, ids)} | {s} | {cell("Z",4)} | {cell("Z",6)} | {cell("X",4)} | {cell("X",6)} | {s4["mins"][s]} | '
                     f'{"yes" if ok and not bad else f"{ok} ok, {bad} not"} | {f"{x[chr(97)+"lt_to_S"]} / {x["S_to_alt"]}" if x else ""} |')
        L += ['', f'Circuits that beat S: {s4["beats"] or "none"}.']
    ctl = J(n, 'control.json')
    if ctl:
        L += ['', f'### Control check: {"PASS" if ctl["PASS"] else "FAIL"}', '',
              f'S gives 6: {ctl["S_gives_6"]}. Every alternating circuit <= 6: {ctl["every_alt_le_6"]} {ctl["alt_values"]}. '
              f'Agrees with earlier [[72]] runs (S, S^-1, alt [S, S^-1] all 6): {ctl["agrees_with_001"]} {ctl["values_001_check"]}. '
              f'Partners that caught all of S\'s weight-6 families in Stage 3: {ctl["partners_catching_all_families"]}.']
    L.append('')
L += ['Figures: figures_partner/F1_bounds.png, F2_screen.png (F3_ler.png only if Stage 5 ran).', '']
open(OUT, 'w').write('\n'.join(L)); print('written', OUT)
