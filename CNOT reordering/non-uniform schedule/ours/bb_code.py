# COPY of quantum001/first experiment/syndrome-circuit-scheduling-001/bb_code.py (our stim builder), unchanged.
"""
Bivariate bicycle (BB) code syndrome-extraction circuits in Stim.

Code: H_X = [A | B],  H_Z = [B^T | A^T],  A = A1+A2+A3, B = B1+B2+B3,
each Ai/Bi a permutation (monomial x^a y^b on an l x m torus).

Qubit registers: q(L) data, q(R) data, q(X) ancillas, q(Z) ancillas (n/2 each).

A schedule is a pair (x_order, z_order): each a list of 6 labels from
{'A1','A2','A3','B1','B2','B3'}.  In CNOT round t (t = 1..7):
  Z ancillas use z_order[t-1]  for t = 1..6   (Z side starts at round 1)
  X ancillas use x_order[t-2]  for t = 2..7   (X side starts at round 2)
X ancilla i -> L qubit  via A_k (row i), -> R qubit via B_k.
Z ancilla i <- R qubit  via A_k^T (col i), <- L qubit via B_k^T.
Round 7 also measures Z, round 8 measures X.  This is Bravyi Fig. 5.
"""
import numpy as np
import stim
from itertools import product

LABELS = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3']

# ---- code definitions: polynomial terms as (x-power, y-power) ----
CODES = {
    # [[72,12,6]]  l=6, m=6, A = x^3 + y + y^2,   B = y^3 + x + x^2
    72:  dict(l=6,  m=6,  A=[(3, 0), (0, 1), (0, 2)], B=[(0, 3), (1, 0), (2, 0)]),
    # [[90,8,10]]  l=15, m=3, A = x^9 + y + y^2,   B = 1 + x^2 + x^7
    90:  dict(l=15, m=3,  A=[(9, 0), (0, 1), (0, 2)], B=[(0, 0), (2, 0), (7, 0)]),
    # [[108,8,10]] l=9, m=6, A = x^3 + y + y^2,    B = y^3 + x + x^2
    108: dict(l=9,  m=6,  A=[(3, 0), (0, 1), (0, 2)], B=[(0, 3), (1, 0), (2, 0)]),
    # [[144,12,12]] l=12, m=6, A = x^3 + y + y^2,  B = y^3 + x + x^2   (gross code)
    144: dict(l=12, m=6,  A=[(3, 0), (0, 1), (0, 2)], B=[(0, 3), (1, 0), (2, 0)]),
}


def monomial_perm(l, m, a, b):
    """Permutation p with p[i] = index of x^a y^b * (group element i).
    Group element i = (ix, iy) with i = ix*m + iy."""
    p = np.empty(l * m, dtype=int)
    for ix in range(l):
        for iy in range(m):
            p[ix * m + iy] = ((ix + a) % l) * m + ((iy + b) % m)
    return p


class BBCode:
    def __init__(self, n):
        c = CODES[n]
        self.n = n
        self.l, self.m = c['l'], c['m']
        self.half = self.l * self.m
        assert 2 * self.half == n
        # term k of A: ancilla i connects to L qubit perm[i]
        self.perm = {}
        for k, (a, b) in enumerate(c['A']):
            self.perm[f'A{k+1}'] = monomial_perm(self.l, self.m, a, b)
        for k, (a, b) in enumerate(c['B']):
            self.perm[f'B{k+1}'] = monomial_perm(self.l, self.m, a, b)
        # register layout
        h = self.half
        self.L = np.arange(0, h)
        self.R = np.arange(h, 2 * h)
        self.X = np.arange(2 * h, 3 * h)
        self.Z = np.arange(3 * h, 4 * h)
        self.nq = 4 * h

    # parity-check matrices (for distance / decoding later)
    def hx(self):
        h = self.half
        H = np.zeros((h, 2 * h), dtype=np.uint8)
        for lab in ['A1', 'A2', 'A3']:
            H[np.arange(h), self.perm[lab]] ^= 1
        for lab in ['B1', 'B2', 'B3']:
            H[np.arange(h), h + self.perm[lab]] ^= 1
        return H

    def hz(self):
        h = self.half
        H = np.zeros((h, 2 * h), dtype=np.uint8)
        # H_Z = [B^T | A^T]: Z-ancilla i touches L qubit j where B[j,i]=1
        for lab in ['B1', 'B2', 'B3']:
            inv = np.argsort(self.perm[lab])
            H[np.arange(h), inv] ^= 1
        for lab in ['A1', 'A2', 'A3']:
            inv = np.argsort(self.perm[lab])
            H[np.arange(h), h + inv] ^= 1
        return H

    # ---- one CNOT layer ----
    def x_layer(self, label):
        """CNOTs X-ancilla (control) -> data (target) for matrix `label`."""
        p = self.perm[label]
        data = self.L if label[0] == 'A' else self.R
        pairs = []
        for i in range(self.half):
            pairs += [int(self.X[i]), int(data[p[i]])]
        return pairs

    def z_layer(self, label):
        """CNOTs data (control) -> Z-ancilla (target) for matrix `label`^T."""
        p = self.perm[label]
        data = self.R if label[0] == 'A' else self.L
        inv = np.argsort(p)  # Z-ancilla i <- data qubit inv[i]
        pairs = []
        for i in range(self.half):
            pairs += [int(data[inv[i]]), int(self.Z[i])]
        return pairs


BRAVYI_X = ['A2', 'B2', 'B1', 'B3', 'A1', 'A3']   # X side rounds 2..7
BRAVYI_Z = ['A1', 'A3', 'B1', 'B2', 'B3', 'A2']   # Z side rounds 1..6
BRAVYI = (BRAVYI_X, BRAVYI_Z, True)   # Z side starts first


def reverse_schedule(sched):
    """Time-reverse: CNOT order reversed on both sides and the side that
    finished last now starts first."""
    x, z, z_first = sched
    return (x[::-1], z[::-1], not z_first)


def build_cycle(code, sched, p):
    """Append one syndrome cycle (Bravyi Fig. 5 layout, 7 CNOT rounds + 1
    measurement round).  Returns (circuit, first_measured) where
    first_measured is 'Z' or 'X' (that side is measured in round 7, the
    other in round 8)."""
    x_order, z_order, z_first = sched
    c = stim.Circuit()
    allq = list(range(code.nq))
    Xq, Zq = list(map(int, code.X)), list(map(int, code.Z))

    def noise1(qs):
        if p > 0 and qs:
            c.append('DEPOLARIZE1', qs, p)

    c.append('RX', Xq)
    c.append('R', Zq)
    if p > 0:
        c.append('X_ERROR', Zq, p)
        c.append('Z_ERROR', Xq, p)
    c.append('TICK')

    # side starting at round 1 occupies rounds 1..6, the other 2..7
    early = ('Z', z_order, code.z_layer) if z_first else ('X', x_order, code.x_layer)
    late  = ('X', x_order, code.x_layer) if z_first else ('Z', z_order, code.z_layer)
    early_q = Zq if z_first else Xq
    late_q  = Xq if z_first else Zq
    early_meas = ('M', 'X_ERROR') if z_first else ('MX', 'Z_ERROR')
    late_meas  = ('MX', 'Z_ERROR') if z_first else ('M', 'X_ERROR')

    for t in range(1, 8):
        busy = set()
        if 1 <= t <= 6:
            pairs = early[2](early[1][t - 1])
            c.append('CNOT', pairs); busy.update(pairs)
            if p > 0: c.append('DEPOLARIZE2', pairs, p)
        if 2 <= t <= 7:
            pairs = late[2](late[1][t - 2])
            c.append('CNOT', pairs); busy.update(pairs)
            if p > 0: c.append('DEPOLARIZE2', pairs, p)
        if len(busy) != (len(pairs) if (t == 1 or t == 7) else 2 * len(pairs)):
            raise ValueError(f'schedule {sched} reuses a qubit in round {t}: not depth 7')
        idle = [q for q in allq if q not in busy]
        if t == 7:
            if p > 0: c.append(early_meas[1], early_q, p)
            c.append(early_meas[0], early_q)
            idle = [q for q in idle if q not in early_q]
        noise1(idle)
        c.append('TICK')

    if p > 0: c.append(late_meas[1], late_q, p)
    c.append(late_meas[0], late_q)
    noise1([q for q in allq if q not in late_q])
    c.append('TICK')
    return c, early[0]


def memory_circuit(code, schedules, cycles, p, basis='Z'):
    """Memory experiment: prepare data in |0> (Z) or |+> (X), run `cycles`
    syndrome cycles, measure data.  Cycle t uses schedules[t % len(schedules)]
    (so a list of two schedules alternates)."""
    h = code.half
    dataq = list(map(int, code.L)) + list(map(int, code.R))
    c = stim.Circuit()
    c.append('R' if basis == 'Z' else 'RX', dataq)
    c.append('TICK')

    # absolute measurement index of Z-check i / X-check i in each cycle
    z_idx, x_idx = [], []
    nmeas = 0
    for t in range(cycles):
        cyc, first = build_cycle(code, schedules[t % len(schedules)], p)
        c += cyc
        if first == 'Z':
            z_idx.append(nmeas); x_idx.append(nmeas + h)
        else:
            x_idx.append(nmeas); z_idx.append(nmeas + h)
        nmeas += 2 * h
        rec = lambda a: stim.target_rec(a - nmeas)
        for i in range(h):
            if t == 0:
                if basis == 'Z':
                    c.append('DETECTOR', [rec(z_idx[t] + i)], [i, 0, t])
                else:
                    c.append('DETECTOR', [rec(x_idx[t] + i)], [i, 1, t])
            else:
                c.append('DETECTOR', [rec(z_idx[t] + i), rec(z_idx[t-1] + i)], [i, 0, t])
                c.append('DETECTOR', [rec(x_idx[t] + i), rec(x_idx[t-1] + i)], [i, 1, t])
        c.append('TICK')

    c.append('M' if basis == 'Z' else 'MX', dataq)
    nd = len(dataq)
    nmeas += nd
    rec = lambda a: stim.target_rec(a - nmeas)
    H = code.hz() if basis == 'Z' else code.hx()
    last = (z_idx if basis == 'Z' else x_idx)[-1]
    for i in range(h):
        targets = [rec(nmeas - nd + j) for j in np.flatnonzero(H[i])]
        c.append('DETECTOR', targets + [rec(last + i)], [i, 0 if basis == 'Z' else 1, cycles])
    for k, L in enumerate(logical_ops(code, basis)):
        c.append('OBSERVABLE_INCLUDE', [rec(nmeas - nd + j) for j in np.flatnonzero(L)], k)
    return c


def gf2_nullspace(M):
    """Basis of {v : M v = 0} over GF(2). M: (r, n) uint8 -> rows of basis (n,)."""
    M = M.copy() % 2
    r, n = M.shape
    pivots = []
    row = 0
    for col in range(n):
        piv = None
        for i in range(row, r):
            if M[i, col]:
                piv = i
                break
        if piv is None:
            continue
        M[[row, piv]] = M[[piv, row]]
        for i in range(r):
            if i != row and M[i, col]:
                M[i] ^= M[row]
        pivots.append(col)
        row += 1
        if row == r:
            break
    free = [c for c in range(n) if c not in pivots]
    basis = []
    for f in free:
        v = np.zeros(n, dtype=np.uint8)
        v[f] = 1
        for i, pc in enumerate(pivots):
            if M[i, f]:
                v[pc] = 1
        basis.append(v)
    return np.array(basis, dtype=np.uint8) if basis else np.zeros((0, n), dtype=np.uint8)


def gf2_rank(M):
    M = M.copy() % 2
    r, n = M.shape
    rank = 0
    for col in range(n):
        piv = None
        for i in range(rank, r):
            if M[i, col]:
                piv = i
                break
        if piv is None:
            continue
        M[[rank, piv]] = M[[piv, rank]]
        for i in range(r):
            if i != rank and M[i, col]:
                M[i] ^= M[rank]
        rank += 1
        if rank == r:
            break
    return rank


def logical_ops(code, basis='Z'):
    """k independent logical Z (or X) operators: in ker(H_X) (resp. ker(H_Z)),
    independent modulo the Z (resp. X) stabilisers."""
    H_other = code.hx() if basis == 'Z' else code.hz()
    H_same = code.hz() if basis == 'Z' else code.hx()
    ker = gf2_nullspace(H_other)
    chosen = []
    base_rank = gf2_rank(H_same)
    cur = H_same
    for v in ker:
        test = np.vstack([cur, v[None, :]])
        if gf2_rank(test) > gf2_rank(cur):
            chosen.append(v)
            cur = test
    return chosen


if __name__ == '__main__':
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 72
    code = BBCode(n)
    Hx, Hz = code.hx(), code.hz()
    print(f'[[{n}]]: Hx {Hx.shape}, Hz {Hz.shape}, Hx Hz^T == 0: {not ((Hx @ Hz.T) % 2).any()}')
    k = n - gf2_rank(Hx) - gf2_rank(Hz)
    print(f'k = {k}')
    tests = {
        'bravyi': [BRAVYI],
        'reversed': [reverse_schedule(BRAVYI)],
        'alternating': [BRAVYI, reverse_schedule(BRAVYI)],
    }
    for name, scheds in tests.items():
        for basis in 'ZX':
            circ = memory_circuit(code, scheds, cycles=4, p=0.0, basis=basis)
            samp = circ.compile_detector_sampler().sample(50)
            print(f'{name:12s} basis {basis}: detectors={circ.num_detectors}, '
                  f'obs={circ.num_observables}, any nonzero detector: {samp.any()}')