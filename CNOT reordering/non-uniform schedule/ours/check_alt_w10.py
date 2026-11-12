"""Exact check (2026-10-25): do S's weight-10 one-cycle fault sets on [[144]] survive in the alternating
circuit S, S^-1, S, ... ?

Sets: the regression run of nu.py (tag 'reg', spec u212, Bravyi setup, 100,000 trials per fault type), read
with nu.s_sets: every set is a list of DEM columns, every column the list of ALL physical faults (op, qubits,
round, cycle, faulted qubits) that give that column in S's circuit.
For a target circuit (schedule list used cyclically, num_cycles noisy + 2 noiseless, same builder
bravyi_d1._setup/_simulate as the search) the same physical faults are placed in cycle `cyc` and pushed
through the target circuit together.  A column whose representatives do not exist in the target circuit
(different round structure) is unmappable.  Every choice of representative per column is covered by an
XOR-reachability set of (syndrome history, logical flips) vectors.  Verdict per set:
  UNDETECTED+LOGICAL  some choice leaves no syndrome and flips a logical (path survives: d <= 10)
  detected            every choice leaves a syndrome
Run from ours/:  ../../../venv/bin/python check_alt_w10.py
"""
import json, datetime, collections
import numpy as np
from bravyi_d1 import to_bravyi, _setup, _simulate
from classsched import NBRef
from nu import s_sets, fkey, sched_table

N, S_ID, W = 144, 212, 10
T, REV = sched_table(N)
SINV = REV[S_ID]
S, Si = to_bravyi(T[S_ID]), to_bravyi(T[SINV])
code = NBRef(N)

CASES = [  # (label, schedules, num_cycles, cycle the faults are placed in)
    ('control: S only, cycle 0', [S], 1, 0),
    ('alt S,S^-1: cycle 0 (Bravyi setup)', [S, Si], 1, 0),
    ('alt S,S^-1: cycle 2 of 3 (mid-circuit S cycle)', [S, Si], 3, 2),
    ('alt S^-1,S: cycle 1 of 2 (S after an S^-1 cycle)', [Si, S], 2, 1),
]

def run(kind, label, schedules, ncyc, cyc, sets):
    full, faults, meas_op, prep_op = _setup(code, None, None, kind, 0.003, ncyc, schedules)
    index = {fkey(f[3]): i for i, f in enumerate(faults)}
    shift = lambda k: (k[0], k[1], k[2], cyc, k[4])
    need = sorted({index[shift(k)] for st in sets for col in st for k in col if shift(k) in index})
    Sm, Lm = _simulate(code, full, faults, [[f] for f in need], kind, meas_op, prep_op)
    eff = {f: (int(''.join(map(str, Sm[r]))[::-1] or '0', 2) if Sm.shape[1] else 0,
               int(''.join(map(str, Lm[r])) or '0', 2)) for r, f in enumerate(need)}
    res = collections.Counter()
    for st in sets:
        opts = []
        for col in st:
            o = {eff[index[shift(k)]] for k in col if shift(k) in index}
            opts.append(o)
        if any(not o for o in opts):
            res['unmappable'] += 1; continue
        reach = {(0, 0)}
        for o in opts:
            reach = {(a ^ x, b ^ y) for a, b in reach for x, y in o}
            if len(reach) > 2_000_000: break
        und = [b for a, b in reach if a == 0]
        res['UNDETECTED+LOGICAL' if any(b for b in und) else
            'undetected, no logical' if und else 'detected'] += 1
    return dict(res)

out = dict(date=str(datetime.datetime.now()), code=N, S=S_ID, Sinv=SINV, weight=W, results={})
for kind in ('X', 'Z'):
    sets = s_sets(N, kind, S_ID, W)
    print(f'[[{N}]] {kind}-type faults: {len(sets)} distinct weight-{W} sets of S (#{S_ID}); S^-1 = #{SINV}', flush=True)
    for label, sch, nc, cyc in CASES:
        r = run(kind, label, sch, nc, cyc, sets)
        out['results'][f'{kind} | {label}'] = r
        print(f'   {label:55s} {r}', flush=True)
json.dump(out, open('../results_nonuniform/144/check_alt_w10.json', 'w'), indent=1)
print('written ../results_nonuniform/144/check_alt_w10.json')
