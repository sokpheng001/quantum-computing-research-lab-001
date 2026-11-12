"""TASK2 task G: verification for [[144]] circuits whose 4-cycle bound beats Bravyi's S
under the same search.  (Bravyi reports d_circ <= 10 for S; our search stops at 11 for S,
so "> 10" alone is not informative -- a circuit is only interesting if it bounds strictly
higher than S with the same method.)  Re-searches those circuits AND S at 6 cycles with
fresh seeds (a longer circuit can only add fault paths).  Writes results/task_G.md and
results/task_G_over10.txt (specs still above S after verification, one per line).
usage: verify_bound.py --trials 2000 --nproc 12 [--dry-run]
"""
import argparse, csv, datetime, os
from sched_ids import named
ap = argparse.ArgumentParser(); ap.add_argument('--trials', type=int, default=2000); ap.add_argument('--nproc', type=int, default=12)
ap.add_argument('--dry-run', action='store_true'); a = ap.parse_args()
def read(cyc):
    rows = {}
    for r in csv.DictReader(open('results/exp_144_bounds.csv')):
        if int(r['cycles']) == cyc: rows.setdefault(r['sched'], {})[r['basis']] = int(r['bound'].split()[-1])
    return {sp: min(d.values()) for sp, d in rows.items() if len(d) == 2}
S = str(named()['S']); b4 = read(4); bS = b4.get(S)
over = sorted(sp for sp, v in b4.items() if bS is not None and v > bS and sp != S)
md = [f'\n## Task G — verification of [[144]] bounds above S ({datetime.date.today()})\n',
      '4-cycle bounds (min over bases): ' + ', '.join(f'{sp}: <= {v}' for sp, v in b4.items()),
      f'\nBravyi et al. report d_circ <= 10 for S; this search gives <= {bS} for S, so the criterion is "bounds strictly above S".',
      f'Circuits above S at 4 cycles: {over or "none"}.\n']
still = []
if over:
    specs = ','.join(over + [S])
    cmd = (f'../venv/bin/python bounds_pairs.py --n 144 --cycles 6 --trials {a.trials} --nproc {a.nproc} '
           f'--specs {specs} --out results/exp_144_bounds.csv --tag _6c')
    md.append(f'Re-search at 6 cycles, {a.trials} trials: `{cmd}`'); print(cmd, flush=True)
    if not a.dry_run:
        os.system(cmd); b6 = read(6)
        md += ['', '| spec | 4-cycle bound | 6-cycle bound |', '|---|---|---|']
        for sp in over + [S]: md.append(f'| {sp} | <= {b4[sp]} | <= {b6.get(sp)} |')
        still = [sp for sp in over if sp in b6 and S in b6 and b6[sp] > b6[S]]
        md.append(f'\nStill above S after the 6-cycle re-search: {still or "none"}')
else:
    md.append('Nothing to verify.')
if not a.dry_run:
    open('results/task_G_over10.txt', 'w').write('\n'.join(still)); open('results/task_G.md', 'w').write('\n'.join(md) + '\n')
print('\n'.join(md))
