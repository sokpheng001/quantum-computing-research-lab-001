"""Table for the [[144]] multi-seed d_circ search: circuit x basis x seed -> lowest weight found."""
import csv, collections, os, json
N = int(os.environ.get('BB_N', '144')); REF = int(os.environ.get('BB_REF', '10'))
rows = list(csv.DictReader(open(f'results/strong_{N}.csv')))
best = collections.defaultdict(lambda: [10**9, 0])
for r in rows:
    k = (r['circuit'], r['basis'], int(r['seed'])); best[k][0] = min(best[k][0], int(r['min_weight'])); best[k][1] += int(r['trials'])
name = {'212': 'S', '1307': 'S^-1', '212+1307': 'alt S/S^-1'}
circs = [c for c in ('212', '1307', '212+1307') if any(k[0] == c for k in best)]
seeds = sorted({k[2] for k in best})
nsets = collections.Counter()
for l in open(f'results/strong_sets_{N}.jsonl'):
    d = json.loads(l); nsets[(d['circuit'], d['basis'], d['weight'])] += 0
print('| circuit | basis | ' + ' | '.join(f'seed {s}' for s in seeds) + ' | min over seeds | trials per seed |')
print('|---|---|' + '---|' * (len(seeds) + 2))
mn = {}
for c in circs:
    for b in 'ZX':
        v = [best[(c, b, s)] if (c, b, s) in best else [None, 0] for s in seeds]
        m = min(x[0] for x in v if x[0] is not None); mn[(c, b)] = m
        print(f'| {name[c]} | {b} | ' + ' | '.join(f'<= {x[0]}' if x[0] is not None else '-' for x in v) + f' | <= {m} | {min(x[1] for x in v)} |')
print()
for c in circs: print(f'{name[c]}: d_circ <= {min(mn[(c, b)] for b in "ZX")} (min over bases)')
if all(c in circs for c in ('212', '1307', '212+1307')):
    for b in 'ZX':
        alt, lo = mn[('212+1307', b)], min(mn[('212', b)], mn[('1307', b)])
        print(f'{b}: bound(alt) = {alt} vs min(bound(S), bound(S^-1)) = {lo} -> Shaw-Terhal Prop. 3 consistent: {alt >= lo}')
