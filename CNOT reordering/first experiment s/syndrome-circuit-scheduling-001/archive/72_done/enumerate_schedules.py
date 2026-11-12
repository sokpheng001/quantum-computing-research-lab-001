"""
Enumerate all valid depth-7 syndrome schedules (x_order, z_order, z_first)
for a BB code and compare with Bravyi's count of 936.

Validity criterion (fast, algebraic): the interleaved circuit equals the
sequential 'all X-check CNOTs then all Z-check CNOTs' circuit.  CNOT(a->q)
[X-ancilla a] and CNOT(q->b) [Z-ancilla b] on a shared data qubit q commute
up to CNOT(a->b).  For every X-check a and Z-check b the number of shared
data qubits whose Z-CNOT happens BEFORE the X-CNOT must be even, so the
stray CNOT(a->b) factors cancel.  In addition no data qubit may take part in
an X-side and a Z-side CNOT in the same round (collision -> not depth 7).  The code is translation invariant, so
checking a = 0 against all b suffices.

Ground truth: all-zero noiseless detectors in both memory bases (stim); the
script cross-checks the algebraic test against stim on a random sample.

usage: python enumerate_schedules.py [--n 72] [--verify 300] [--out results/schedules_72.json]
"""
import argparse, json, itertools, time, os
import numpy as np
from bb_code import BBCode, LABELS, BRAVYI, reverse_schedule, memory_circuit


def build_incidence(code):
    """xq[label][a] = data qubit of X-check a via label;
       zinc[d] = list of (b, label) Z-checks touching data qubit d."""
    xq = {}
    for lab in LABELS:
        pairs = code.x_layer(lab)
        xq[lab] = {pairs[2 * i]: pairs[2 * i + 1] for i in range(code.half)}
    zinc = {}
    for lab in LABELS:
        pairs = code.z_layer(lab)
        for i in range(code.half):
            d, b = pairs[2 * i], pairs[2 * i + 1]
            zinc.setdefault(d, []).append((b, lab))
    return xq, zinc


def is_valid(x_order, z_order, z_first, xq, zinc, a):
    xr = {lab: i + (2 if z_first else 1) for i, lab in enumerate(x_order)}
    zr = {lab: i + (1 if z_first else 2) for i, lab in enumerate(z_order)}
    flipped = {}
    for lab in LABELS:
        d = xq[lab][a]
        tx = xr[lab]
        for b, lz in zinc[d]:
            if zr[lz] == tx:      # same data qubit in two CNOTs in one round
                return False      # -> not a depth-7 circuit
            if zr[lz] < tx:
                flipped[b] = flipped.get(b, 0) ^ 1
    return not any(flipped.values())


def stim_valid(code, sched, cycles=3):
    for basis in 'ZX':
        c = memory_circuit(code, [sched], cycles, 0.0, basis)
        if c.compile_detector_sampler().sample(8).any():
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=72)
    ap.add_argument('--verify', type=int, default=300)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    code = BBCode(a.n)
    xq, zinc = build_incidence(code)
    a0 = int(code.X[0])
    perms = list(itertools.permutations(LABELS))
    t0 = time.time()
    valid = []
    for z_first in (True, False):
        for xo in perms:
            for zo in perms:
                if is_valid(xo, zo, z_first, xq, zinc, a0):
                    valid.append((list(xo), list(zo), z_first))
    nz = sum(1 for v in valid if v[2]); nx = len(valid) - nz
    print(f'[[{a.n}]]: {len(valid)} valid schedules of {2*len(perms)**2} '
          f'(Z-first: {nz}, X-first: {nx})  [{time.time()-t0:.0f}s]')
    S = (list(BRAVYI[0]), list(BRAVYI[1]), BRAVYI[2])
    Sinv = reverse_schedule(BRAVYI); Sinv = (list(Sinv[0]), list(Sinv[1]), Sinv[2])
    print('Bravyi S in set:', S in valid, '  S^-1 in set:', Sinv in valid)

    # cross-check vs stim on a random sample of valid + invalid candidates
    rng = np.random.default_rng(0)
    vset = {(tuple(x), tuple(z), f) for x, z, f in valid}
    agree = 0; checked = 0; mism = []
    for i in range(a.verify):
        if i % 2 == 0 and valid:
            x, z, f = valid[rng.integers(len(valid))]
        else:
            while True:
                x = list(perms[rng.integers(len(perms))]); z = list(perms[rng.integers(len(perms))]); f = bool(rng.integers(2))
                if (tuple(x), tuple(z), f) not in vset:
                    break
        alg = (tuple(x), tuple(z), f) in vset
        st = stim_valid(code, (x, z, f))
        checked += 1
        if alg == st:
            agree += 1
        else:
            mism.append((x, z, f, alg, st))
    print(f'stim cross-check: {agree}/{checked} agree' + ('' if not mism else f'  MISMATCHES: {mism[:3]}'))

    out = a.out or f'results/schedules_{a.n}.json'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w') as f:
        json.dump(dict(n=a.n, count=len(valid), schedules=valid), f)
    print('saved', out)


if __name__ == '__main__':
    main()
