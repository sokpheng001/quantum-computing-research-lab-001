"""Tests for classsched.py.  Run: ../../../venv/bin/python test_classsched.py"""
import sys, warnings; warnings.filterwarnings('ignore')
import numpy as np
from bravyi_d1 import BBRef, to_bravyi, decoding_matrices
from classsched import NBRef, uniform_tables, tables, homomorphisms, noiseless_ok, stim_memory
from bb_code import BRAVYI, reverse_schedule
S = BRAVYI; Sinv = reverse_schedule(BRAVYI)
for n in (72, 90, 108):
    code = NBRef(n)
    for nm, sch in (('S', S), ('S^-1', Sinv)):
        u = to_bravyi(sch); t = uniform_tables(n, sch)
        same_cycle = BBRef.cycle(code, *u) == code.cycle(*t)
        same_m = all(set(decoding_matrices(code, *u, k)['keys']) == set(decoding_matrices(code, *t, k)['keys']) for k in 'XZ')
        print(f'[[{n}]] {nm}: per-ancilla table == uniform cycle: {same_cycle}; matrices identical: {same_m}; '
              f'valid: {code.check_cycle(*t)}; noiseless detectors zero (2, 6 cycles, Z/X): {noiseless_ok(code, [t])}')
    # alternation S / S^-1 as tables
    print(f'[[{n}]] alt[S,S^-1] tables noiseless: {noiseless_ok(code, [uniform_tables(n, S), uniform_tables(n, Sinv)])}')
    print(f'[[{n}]] Z_2 homs: {homomorphisms(n, 2)}  Z_3 homs: {homomorphisms(n, 3)}')
# a class schedule mixing S and S^-1 (different starting sides) must be rejected or at least checked
code = NBRef(72)
t = tables(72, (1, 0), 2, [S, Sinv])
print('[[72]] class (x->1) S / S^-1 valid:', code.check_cycle(*t), ' noiseless:', noiseless_ok(code, [t]) if code.check_cycle(*t) else '-')
# stim op-list builder vs bb_code builder: same detector/observable counts for S
from bb_code import BBCode, memory_circuit
c1 = stim_memory(code, [uniform_tables(72, S)], 6, 0.001, 'Z'); c2 = memory_circuit(BBCode(72), [S], 6, 0.001, 'Z')
print('stim op-list vs bb_code (S, 6 cycles, Z): detectors', c1.num_detectors, c2.num_detectors, ' observables', c1.num_observables, c2.num_observables)
