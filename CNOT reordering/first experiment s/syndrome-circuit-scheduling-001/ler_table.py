"""Aggregate results/ler.csv -> dict[(n,basis,cycles,p,sched)] = (shots, fails)."""
import csv, os
from dcirc import wilson, per_cycle
def aggregate(path='results/ler.csv'):
    agg = {}
    if not os.path.exists(path): return agg
    for r in csv.DictReader(open(path)):
        k = (int(r['n']), r['basis'], int(r['cycles']), float(r['p']), r['sched'])
        s, f = agg.get(k, (0, 0)); agg[k] = (s + int(r['shots']), f + int(r['fails']))
    return agg
def stats(shots, fails, cycles):
    ler = fails / shots if shots else 0.0
    lo, hi = wilson(fails, shots)
    return dict(shots=shots, fails=fails, ler=ler, lo=lo, hi=hi, pc=per_cycle(ler, cycles), pc_lo=per_cycle(lo, cycles), pc_hi=per_cycle(hi, cycles))
