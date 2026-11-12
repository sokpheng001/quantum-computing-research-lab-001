"""One-off: import results/exp1_72.json (Experiment 1, 2026-10-12) into the
CSV files required by TASKS.md.  Seeds of those runs are unknown (-1)."""
import json, csv, os
from sched_ids import named
d = json.load(open('results/exp1_72.json')); ids = named()
lab = {'S': str(ids['S']), 'Sinv': str(ids['Sinv']), 'alt': f"{ids['S']}+{ids['Sinv']}"}
rows = [r for r in csv.DictReader(open('results/ler.csv'))] if os.path.exists('results/ler.csv') else []
if any(r['source'] == 'exp1_72.json' for r in rows):
    print('already imported'); raise SystemExit
import sys; sys.path.insert(0, "."); from run_ler import append
for r in d['ler']:
    append(dict(n=72, basis=r['basis'], cycles=r['cycles'], p=r['p'], shots=r['shots'], seed=-1, sched=lab[r['config']],
                fails=r['fails'], bp_conv=round(r['bp_converged_frac'], 3), seconds=round(r['seconds'], 1), source='exp1_72.json'))
new = not os.path.exists('results/bounds_exp1.csv')
with open('results/bounds_exp1.csv', 'a', newline='') as f:
    w = csv.writer(f)
    if new: w.writerow(['n', 'basis', 'cycles', 'p', 'trials', 'seed', 'sched', 'bound', 'n_min_paths', 'hist'])
    for key, g in d['bounds'].items():
        cfg, basis = key.split('/')
        w.writerow([72, basis, d['args']['cycles'], d['args']['bound_p'], g['trials'], '0-11', lab[cfg], f"<= {g['min_weight']}", g['n_min_paths_found'], json.dumps(g['hist'])])
print('imported', len(d['ler']), 'LER rows and', len(d['bounds']), 'bound rows')
