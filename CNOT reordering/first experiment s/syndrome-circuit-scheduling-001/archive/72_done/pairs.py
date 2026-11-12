"""TASK2 task D (Phase 4.1-4.2).
  pairs.py select    -> results/pair_candidates.csv + results/pair_specs.txt
       top-K schedules from results/ranking_936.csv; pairwise overlap of their
       schedule-specific min-weight fault keys (both bases, core keys removed);
       5 disjoint (or least-overlapping) pairs with the lowest rank sum, plus
       (best, best^-1).
  pairs.py finalist  -> results/pair_finalist.txt + markdown table
       after bounds_pairs.py ran on the candidates: finalist = pair with the
       highest min(dZ,dX) alternating bound, then fewest nontrivial min-weight
       sets, compared with the best single schedule.
"""
import sys, csv, json, os, itertools, datetime
from sched_ids import table, named
from faultsets import load_sets, core_keys, specific_keys, n_nontrivial

N, CYC, K = 72, 4, 20
rk = list(csv.DictReader(open('results/ranking_936.csv')))
rank = {int(r['id']): int(r['rank']) for r in rk}
ids_all = sorted(rank)
CORE = {b: core_keys(N, b, ids_all) for b in 'ZX'}
rev = {json.loads(l)['id']: json.loads(l)['reverse_id'] for l in open('results/schedules.jsonl')}

if sys.argv[1] == 'select':
    top = [int(r['id']) for r in rk[:K]]
    F = {(s, b): specific_keys(load_sets(N, b, s) or [], CORE[b]) for s in top for b in 'ZX'}
    cand = []
    for a, b2 in itertools.combinations(top, 2):
        ov = len(F[(a, 'Z')] & F[(b2, 'Z')]) + len(F[(a, 'X')] & F[(b2, 'X')])
        cand.append((ov, rank[a] + rank[b2], a, b2))
    cand.sort()
    chosen = cand[:5]
    best = top[0]
    with open('results/pair_candidates.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['pair', 'spec', 'id1', 'id2', 'rank1', 'rank2', 'overlap', 'specific_keys_1', 'specific_keys_2'])
        for i, (ov, rs, a, b2) in enumerate(chosen):
            w.writerow([f'P{i+1}', f'{a}+{b2}', a, b2, rank[a], rank[b2], ov, len(F[(a,'Z')]) + len(F[(a,'X')]), len(F[(b2,'Z')]) + len(F[(b2,'X')])])
        w.writerow(['PA', f'{best}+{rev[best]}', best, rev[best], rank[best], 'reverse', '-', len(F[(best,'Z')]) + len(F[(best,'X')]), '-'])
    specs = [f'{a}+{b2}' for _, _, a, b2 in chosen] + [f'{best}+{rev[best]}', str(best)]
    open('results/pair_specs.txt', 'w').write(','.join(specs))
    print(f'top {K}: {top}\n{sum(1 for c in cand if c[0] == 0)} of {len(cand)} pairs are disjoint')
    for i, (ov, rs, a, b2) in enumerate(chosen): print(f'  P{i+1}: {a}+{b2}  ranks {rank[a]},{rank[b2]}  overlap {ov}')
    print(f'  PA: {best}+{rev[best]} (best with its time reverse)\nspecs: {",".join(specs)}')

elif sys.argv[1] == 'finalist':
    rows = {}
    for r in csv.DictReader(open('results/pair_bounds.csv')):
        if int(r['n']) == N and int(r['cycles']) == CYC: rows[(r['sched'], r['basis'])] = r
    specs = open('results/pair_specs.txt').read().strip().split(',')
    tab = []
    for sp in specs:
        if (sp, 'Z') not in rows or (sp, 'X') not in rows: continue
        d = {b: int(rows[(sp, b)]['bound'].split()[-1]) for b in 'ZX'}
        nt = {b: n_nontrivial(load_sets(N, b, sp + '_pb') or [], CORE[b]) for b in 'ZX'}
        nm = {b: int(rows[(sp, b)]['n_min_paths']) for b in 'ZX'}
        tab.append((-min(d.values()), nt['Z'] + nt['X'], nm['Z'] + nm['X'], sp, d, nt, nm))
    tab.sort()
    pairs_only = [t for t in tab if '+' in t[3]]
    fin = pairs_only[0][3]
    open('results/pair_finalist.txt', 'w').write(fin)
    md = [f'\n## Task D — candidate pairs, alternating d_circ bounds on [[72]], {CYC} cycles, 600 trials ({datetime.date.today()})\n',
          '| spec | dZ | dX | min-weight sets Z / X | nontrivial Z / X |', '|---|---|---|---|---|']
    for _, _, _, sp, d, nt, nm in tab:
        md.append(f"| {sp}{' (best single)' if '+' not in sp else ''} | <= {d['Z']} | <= {d['X']} | {nm['Z']} / {nm['X']} | {nt['Z']} / {nt['X']} |")
    md.append(f'\n**Finalist pair: {fin}** (highest min bound, then fewest nontrivial min-weight sets). Candidates: results/pair_candidates.csv')
    open('results/pairs.md', 'w').write('\n'.join(md) + '\n'); print('\n'.join(md))
