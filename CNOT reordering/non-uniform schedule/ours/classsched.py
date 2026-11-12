"""Non-uniform (class) depth-7 schedules for BB codes (TASKS_nonuniform.md, Method 4).

A class schedule: ancillas (X and Z, both indexed by the group element i = ix*m + iy of G = Z_l x Z_m) are
split into k classes by a homomorphism f: G -> Z_k, f(ix, iy) = (a*ix + b*iy) mod k, written (a, b) = (image
of x, image of y).  Class c uses the uniform schedule orders[c] (an id from the 1,872 list): X-ancilla i
follows that schedule's X order, Z-ancilla i its Z order, each with its own starting round.

Per-ancilla tables: tabX[i], tabZ[i] = 7-slot lists in Bravyi's neighbour numbering ('idle' or 0..5), the
same format as bravyi_ref's sX / sZ.  NBRef.cycle accepts these tables and generalises the reference
cycle ancilla by ancilla: an ancilla whose first CNOT is in round 0 ("early") is measured at the start of
round 6 and re-prepared at the end of round 7 (for the next cycle), a "late" ancilla is prepared in round 0
and measured in round 7; data qubits not in any CNOT in rounds 0-6 idle, all data qubits idle in round 7.
For uniform tables this is exactly bravyi_d1.BBRef.cycle (checked by tests in this file), so the fault
model, the decoding matrices and the distance search (bravyi_d1.decoding_matrices / d1_search, unchanged)
apply as they are.
"""
import itertools
import numpy as np
import stim
from bravyi_d1 import BBRef, to_bravyi, CODES


def homomorphisms(n, k):
    """All surjective (a, b) with a in Z_k, b in Z_k, well defined on Z_l x Z_m, up to multiplication by
    units of Z_k (so each class partition appears once)."""
    l, m = CODES[n][0], CODES[n][1]
    units = [u for u in range(1, k) if np.gcd(u, k) == 1]
    out, seen = [], set()
    for a in range(k):
        for b in range(k):
            if (a * l) % k or (b * m) % k: continue                       # not well defined
            if np.gcd(np.gcd(a, b), k) != 1: continue                     # not surjective
            key = min(((u * a) % k, (u * b) % k) for u in units)
            if key in seen: continue
            seen.add(key); out.append(key)
    return out


def class_of(n, hom, k):
    l, m = CODES[n][0], CODES[n][1]; a, b = hom
    return np.array([(a * ix + b * iy) % k for ix in range(l) for iy in range(m)])


def tables(n, hom, k, scheds):
    """scheds[c] = (x_order, z_order, z_first) of class c -> (tabX, tabZ) per ancilla."""
    cls = class_of(n, hom, k); br = [to_bravyi(s) for s in scheds]
    return [list(br[c][0]) for c in cls], [list(br[c][1]) for c in cls]


def uniform_tables(n, sched):
    sX, sZ = to_bravyi(sched); n2 = CODES[n][0] * CODES[n][1]
    return [list(sX)] * n2, [list(sZ)] * n2


class NBRef(BBRef):
    """BBRef whose cycle() also accepts per-ancilla tables (lists of 7-slot lists)."""

    def cycle(self, sX, sZ, next_early=None):
        per = isinstance(sX[0], list)
        if not per:
            return BBRef.cycle(self, sX, sZ, next_early)
        n2 = self.n2
        tab = {'X': sX, 'Z': sZ}; anc = {'X': self.X, 'Z': self.Z}
        early = {s: [tab[s][i][0] != 'idle' for i in range(n2)] for s in 'XZ'}
        if next_early is None: nxt = early
        else:
            nX, nZ = next_early
            nxt = {'X': [nX[i][0] != 'idle' for i in range(n2)], 'Z': [nZ[i][0] != 'idle' for i in range(n2)]}
        def cnots(side, t):
            out = []
            for i in range(n2):
                d = tab[side][i][t]
                if d == 'idle': continue
                if side == 'X': out.append(('CNOT', int(self.X[i]), int(self.nbX[d][i]), t))
                else: out.append(('CNOT', int(self.nbZ[d][i]), int(self.Z[i]), t))
            return out
        def idles(g, t):
            touched = {c[2] for c in g if c[1] in set(map(int, self.X))} | {c[1] for c in g if c[2] in set(map(int, self.Z))}
            return [('IDLE', int(q), None, t) for q in self.data if int(q) not in touched]
        C = []
        # round 0: prepare the late ancillas, CNOTs of every ancilla with a round-0 slot
        for s in 'XZ':
            for i in range(n2):
                if not early[s][i]: C.append(('Prep' + s, int(anc[s][i]), None, 0))
        g = cnots('X', 0) + cnots('Z', 0); C += g; C += idles(g, 0)
        for t in range(1, 6):
            g = cnots('X', t) + cnots('Z', t); C += g; C += idles(g, t)
        # round 6: measure the early ancillas (finished in round 5), CNOTs of round-6 slots
        for s in ('Z', 'X'):
            for i in range(n2):
                if early[s][i]: C.append(('Meas' + s, int(anc[s][i]), None, 6))
        g = cnots('X', 6) + cnots('Z', 6); C += g; C += idles(g, 6)
        # round 7: data idle, measure the late ancillas, prepare the ancillas that are early next cycle
        C += [('IDLE', int(q), None, 7) for q in self.data]
        for s in ('X', 'Z'):
            for i in range(n2):
                if not early[s][i]: C.append(('Meas' + s, int(anc[s][i]), None, 7))
        for s in ('X', 'Z'):
            for i in range(n2):
                if nxt[s][i]: C.append(('Prep' + s, int(anc[s][i]), None, 7))
        return C

    def check_cycle(self, sX, sZ):
        """Depth-7 validity: (i) no qubit in two CNOTs of one round (across classes), (ii) each ancilla has 6
        CNOTs in 6 consecutive rounds starting at 0 or 1 (Bravyi's stagger), (iii) interleaved circuit =
        sequential circuit (all X checks, then all Z checks) -> it measures the stabilisers."""
        if not isinstance(sX[0], list): return BBRef.check_cycle(self, sX, sZ)
        for tab in (sX, sZ):
            for row in tab:
                busy = [t for t in range(7) if row[t] != 'idle']
                if len(busy) != 6 or busy not in (list(range(0, 6)), list(range(1, 7))): return False
                if sorted(row[t] for t in busy) != list(range(6)): return False
        C = self.cycle(sX, sZ); used = set()
        for op, a, b, t in C:
            if op == 'CNOT':
                for q in (a, b):
                    if (q, t) in used: return False
                    used.add((q, t))
        U = np.identity(self.nq, dtype=np.uint8)
        for op, a, b, t in C:
            if op == 'CNOT': U[b] ^= U[a]
        V = np.identity(self.nq, dtype=np.uint8)
        for i in range(self.n2):
            for t in range(7):
                d = sX[i][t]
                if d != 'idle': V[self.nbX[d][i]] ^= V[self.X[i]]
        for i in range(self.n2):
            for t in range(7):
                d = sZ[i][t]
                if d != 'idle': V[self.Z[i]] ^= V[self.nbZ[d][i]]
        return np.array_equal(U, V)


# ------------------------------------------------------------------ stim circuits from the op list
def stim_memory(code, schedules, cycles, p, basis):
    """Memory experiment built from NBRef.cycle op lists (cycle t uses schedules[t % len], each (tabX, tabZ) or
    uniform (sX, sZ)).  Noise (uniform circuit-level depolarising, Bravyi's model): DEPOLARIZE2(p) after
    every CNOT, DEPOLARIZE1(p) on idle data, X/Z_ERROR(p) after preparation and before measurement.
    Data preparation and final data readout are noiseless.  Detectors: ancilla outcome XOR its previous
    outcome; in cycle 0 only the checks of the memory basis; final detectors from the data readout."""
    c = stim.Circuit(); data = list(map(int, code.data))
    c.append('R' if basis == 'Z' else 'RX', data)
    # ancillas that start in round 0 of cycle 0 are normally prepared at the end of the previous cycle:
    # prepare them here (noiseless, like the data)
    s0X, s0Z = schedules[0]
    for side, tab, anc in (('X', s0X, code.X), ('Z', s0Z, code.Z)):
        rows = tab if isinstance(tab[0], list) else [tab] * code.n2
        qs = [int(anc[i]) for i in range(code.n2) if rows[i][0] != 'idle']
        if qs: c.append('RX' if side == 'X' else 'R', qs)
    c.append('TICK')
    nmeas = 0; last = {}                       # ancilla -> absolute index of its latest measurement
    for t in range(cycles):
        sX, sZ = schedules[t % len(schedules)]; nX, nZ = schedules[(t + 1) % len(schedules)]
        ops = code.cycle(sX, sZ, next_early=(nX, nZ) if isinstance(sX[0], list) else
                         ('Z' if nZ[0] != 'idle' else 'X'))
        rnd = None; prev = {}
        for op, a, b, r in ops:
            if r != rnd:
                if rnd is not None: c.append('TICK')
                rnd = r
            if op == 'CNOT':
                c.append('CNOT', [a, b])
                if p > 0: c.append('DEPOLARIZE2', [a, b], p)
            elif op == 'IDLE':
                if p > 0: c.append('DEPOLARIZE1', [a], p)
            elif op in ('PrepX', 'PrepZ'):
                c.append('RX' if op == 'PrepX' else 'R', [a])
                if p > 0: c.append('Z_ERROR' if op == 'PrepX' else 'X_ERROR', [a], p)
            else:
                if p > 0: c.append('Z_ERROR' if op == 'MeasX' else 'X_ERROR', [a], p)
                c.append('MX' if op == 'MeasX' else 'M', [a])
                prev[a] = last.get(a); last[a] = nmeas; nmeas += 1
        c.append('TICK')
        rec = lambda idx: stim.target_rec(idx - nmeas)
        for typ, anc in (('Z', code.Z), ('X', code.X)):
            for i, q in enumerate(map(int, anc)):
                if t == 0:
                    if typ == basis: c.append('DETECTOR', [rec(last[q])], [i, 0 if typ == 'Z' else 1, t])
                else:
                    c.append('DETECTOR', [rec(last[q]), rec(prev[q])], [i, 0 if typ == 'Z' else 1, t])
    c.append('M' if basis == 'Z' else 'MX', data)
    nd = len(data); nmeas += nd
    rec = lambda idx: stim.target_rec(idx - nmeas)
    H = code.hz if basis == 'Z' else code.hx
    anc = code.Z if basis == 'Z' else code.X
    for i in range(code.n2):
        c.append('DETECTOR', [rec(nmeas - nd + j) for j in np.flatnonzero(H[i])] + [rec(last[int(anc[i])])],
                 [i, 0 if basis == 'Z' else 1, cycles])
    Lm = np.asarray(code.lz if basis == 'Z' else code.lx)
    for k_, row in enumerate(Lm):
        c.append('OBSERVABLE_INCLUDE', [rec(nmeas - nd + j) for j in np.flatnonzero(row)], k_)
    return c


def noiseless_ok(code, schedules, cycles_list=(2, 6)):
    for cy in cycles_list:
        for basis in 'ZX':
            circ = stim_memory(code, schedules, cy, 0.0, basis)
            if circ.compile_detector_sampler().sample(4).any(): return False
    return True


# ------------------------------------------------------------------ translations (exact screen, B4)
def shift_maps(code):
    """For each torus shift g = (dx, dy): array mapping qubit index -> translated qubit index (every
    register shifts the same way; a symmetry of every uniform-schedule circuit)."""
    l, m, n2 = code.ell, code.m, code.n2
    out = []
    for dx in range(l):
        for dy in range(m):
            perm = np.array([((ix + dx) % l) * m + (iy + dy) % m for ix in range(l) for iy in range(m)])
            mp = np.concatenate([r * n2 + perm for r in range(4)])
            out.append(((dx, dy), mp))
    return out
