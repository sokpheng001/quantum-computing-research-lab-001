"""One-cycle distance d1 with Bravyi's reference setup, for ANY depth-7 schedule and any BB code.

Derived from bravyi_ref/decoder_setup.py and bravyi_ref/circuit_distance.py (Apache 2.0, S. Bravyi et al.).
Changes relative to the reference (bravyi_ref/ itself is never edited):
  1. Schedule is an argument (sX, sZ lists in Bravyi's neighbour numbering), and X-first schedules are
     supported: the side that starts in round 0 is measured at the start of round 6 and re-prepared at
     the end of round 7; the other side is prepared in round 0 and measured in round 7.  For Z-first
     schedules this is exactly the reference cycle (checked against the reference by check_vs_ref.py).
  2. Fault propagation is vectorised (all single faults pushed through the circuit at once as rows of a
     bit matrix) instead of one Python simulation per fault.  Same columns, same merging, same priors.
  3. Distance search (circuit_distance.py logic, same decoder call): the random target row is a random
     combination of ALL rows of [Hdec; logical rows] exactly as in the reference, but a trial whose
     combination has no logical part is redrawn (its syndrome (0,..,0,1) has no solution, and the
     reference would then record the weight of an invalid OSD output); every OSD output is checked to
     satisfy the augmented syndrome before its weight is used.  The reference's per-trial np.random
     calls are replaced by a seeded numpy Generator.
  4. Returns the minimum-weight fault sets with their physical locations (gate, qubits, round, cycle).
  5. (non-uniform folder, 2026-10-18) _setup passes the next cycle's per-ancilla tables to code.cycle when
     the schedule is a per-ancilla table (classsched.NBRef); uniform schedules are unchanged.  The search
     (d1_search) is unchanged.
Model (unchanged): X-type and Z-type faults are treated separately (CSS split).  Faults on PrepX/PrepZ,
MeasX/MeasZ, IDLE data qubits (rate 2p/3) and CNOTs (control, target, both: 4p/15 each).  num_cycles
noisy cycles followed by 2 noiseless cycles; d1 = num_cycles = 1.
"""
import numpy as np
from scipy.sparse import csr_matrix
from bposd.css import css_code

X_LAB = {'A1': 0, 'A2': 1, 'A3': 2, 'B1': 3, 'B2': 4, 'B3': 5}      # X-check neighbour index
Z_LAB = {'B1': 0, 'B2': 1, 'B3': 2, 'A1': 3, 'A2': 4, 'A3': 5}      # Z-check neighbour index (B^T left, A^T right)
CODES = {72: (6, 6, (3, 1, 2), (3, 1, 2)), 90: (15, 3, (9, 1, 2), (0, 2, 7)),
         108: (9, 6, (3, 1, 2), (3, 1, 2)), 144: (12, 6, (3, 1, 2), (3, 1, 2))}


def to_bravyi(sched):
    """our (x_order, z_order, z_first) -> Bravyi (sX, sZ) lists of length 7."""
    xo, zo, zf = sched
    xs = [X_LAB[a] for a in xo]; zs = [Z_LAB[a] for a in zo]
    return (['idle'] + xs, zs + ['idle']) if zf else (xs + ['idle'], ['idle'] + zs)


class BBRef:
    def __init__(self, n):
        ell, m, (a1, a2, a3), (b1, b2, b3) = CODES[n]
        self.n, self.ell, self.m = n, ell, m
        n2 = ell * m; self.n2 = n2
        Il, Im = np.identity(ell, dtype=int), np.identity(m, dtype=int)
        x = {i: np.kron(np.roll(Il, i, axis=1), Im) for i in range(ell)}
        y = {i: np.kron(Il, np.roll(Im, i, axis=1)) for i in range(m)}
        A1, A2, A3, B1, B2, B3 = x[a1], y[a2], y[a3], y[b1], x[b2], x[b3]
        A, B = (A1 + A2 + A3) % 2, (B1 + B2 + B3) % 2
        self.hx = np.hstack((A, B)); self.hz = np.hstack((B.T, A.T))
        q = css_code(self.hx, self.hz); self.lx, self.lz, self.k = q.lx.toarray() if hasattr(q.lx, 'toarray') else q.lx, \
            q.lz.toarray() if hasattr(q.lz, 'toarray') else q.lz, q.K
        # linear order exactly as the reference: Xchecks, data_left, data_right, Zchecks
        self.X = np.arange(n2); self.DL = n2 + np.arange(n2); self.DR = 2 * n2 + np.arange(n2); self.Z = 3 * n2 + np.arange(n2)
        self.data = np.concatenate([self.DL, self.DR]); self.nq = 4 * n2
        nz = lambda M: np.array([np.nonzero(M[i, :])[0][0] for i in range(n2)])
        nzT = lambda M: np.array([np.nonzero(M[:, i])[0][0] for i in range(n2)])
        # nbs[(Xcheck i, d)] / nbs[(Zcheck i, d)] -> qubit index
        self.nbX = [self.DL[nz(A1)], self.DL[nz(A2)], self.DL[nz(A3)], self.DR[nz(B1)], self.DR[nz(B2)], self.DR[nz(B3)]]
        self.nbZ = [self.DL[nzT(B1)], self.DL[nzT(B2)], self.DL[nzT(B3)], self.DR[nzT(A1)], self.DR[nzT(A2)], self.DR[nzT(A3)]]

    def name(self, q):
        n2 = self.n2; r, i = divmod(int(q), n2)
        return ['Xcheck', 'data_left', 'data_right', 'Zcheck'][r] + f'[{i}]'

    def cycle(self, sX, sZ, next_early=None):
        """List of (op, a, b, round).  Z-first (sZ[0] != 'idle') reproduces the reference cycle exactly.
        next_early: starting side ('X'/'Z') of the NEXT cycle's schedule; its ancillas are prepared at the end
        of round 7 (default: this cycle's own starting side, as in the reference)."""
        zf = sZ[0] != 'idle'
        E, Lt = ('Z', 'X') if zf else ('X', 'Z')                 # early / late side
        s = {'X': sX, 'Z': sZ}; anc = {'X': self.X, 'Z': self.Z}
        def cnots(side, t):
            d = s[side][t]; out = []
            if d == 'idle': return out
            if side == 'X':
                for i in range(self.n2): out.append(('CNOT', int(self.X[i]), int(self.nbX[d][i]), t))
            else:
                for i in range(self.n2): out.append(('CNOT', int(self.nbZ[d][i]), int(self.Z[i]), t))
            return out
        C = []
        # round 0: prep late side, CNOT early side, idle data not touched
        for q in anc[Lt]: C.append(('Prep' + Lt, int(q), None, 0))
        g = cnots(E, 0); C += g
        touched = {c[1] if E == 'Z' else c[2] for c in g}
        C += [('IDLE', int(q), None, 0) for q in self.data if int(q) not in touched]
        # rounds 1-5: late side then early side (reference order: X first, then Z)
        for t in range(1, 6):
            for side in ('X', 'Z'):
                C += cnots(side, t)
        # round 6: measure early side, CNOT late side, idle data not touched
        for q in anc[E]: C.append(('Meas' + E, int(q), None, 6))
        g = cnots(Lt, 6); C += g
        touched = {c[2] if Lt == 'X' else c[1] for c in g}
        C += [('IDLE', int(q), None, 6) for q in self.data if int(q) not in touched]
        # round 7: idle data, measure late side, prep early side
        C += [('IDLE', int(q), None, 7) for q in self.data]
        for q in anc[Lt]: C.append(('Meas' + Lt, int(q), None, 7))
        ne = next_early or E
        for q in anc[ne]: C.append(('Prep' + ne, int(q), None, 7))
        return C

    def check_cycle(self, sX, sZ):
        """Reference test: interleaved circuit == sequential (all X checks, then all Z checks), and no qubit
        used twice in a round."""
        C = self.cycle(sX, sZ)
        U = np.identity(self.nq, dtype=np.uint8)
        for op, a, b, t in C:
            if op == 'CNOT': U[b] ^= U[a]
        V = np.identity(self.nq, dtype=np.uint8)
        for t in range(7):
            if sX[t] != 'idle':
                for i in range(self.n2): V[self.nbX[sX[t]][i]] ^= V[self.X[i]]
        for t in range(7):
            if sZ[t] != 'idle':
                for i in range(self.n2): V[self.Z[i]] ^= V[self.nbZ[sZ[t]][i]]
        used = {}
        for op, a, b, t in C:
            if op == 'CNOT':
                for q in (a, b):
                    if (q, t) in used: return False
                    used[(q, t)] = 1
        return np.array_equal(U, V)


def _setup(code, sX, sZ, kind, p, num_cycles, schedules):
    sch = schedules or [(sX, sZ)]
    # per-ancilla tables (classsched.NBRef): pass the next cycle's tables; uniform: its starting side
    early = lambda s: (s[0], s[1]) if isinstance(s[0][0], list) else ('Z' if s[1][0] != 'idle' else 'X')
    total = num_cycles + 2
    cycles = [code.cycle(*sch[t % len(sch)], next_early=early(sch[(t + 1) % len(sch)])) for t in range(total)]
    full = [g for c in cycles for g in c]
    noisy_len = sum(len(c) for c in cycles[:num_cycles])
    starts = np.cumsum([0] + [len(c) for c in cycles])
    meas_op, prep_op = ('MeasZ', 'PrepZ') if kind == 'X' else ('MeasX', 'PrepX')
    faults = []          # (position, qubits tuple, prob, info) -- same order and rates as the reference
    for pos in range(noisy_len):
        op, a, b, t = full[pos]; c = int(np.searchsorted(starts, pos, side='right') - 1)
        if op == meas_op: faults.append((pos, (a,), p, (op, (a,), t, c)))             # before the measurement
        if op == prep_op: faults.append((pos + 1, (a,), p, (op, (a,), t, c)))         # after the preparation
        if op == 'IDLE': faults.append((pos + 1, (a,), p * 2 / 3, (op, (a,), t, c)))
        if op == 'CNOT':
            for qs in ((a,), (b,), (a, b)): faults.append((pos + 1, qs, p * 4 / 15, (op, (a, b), t, c, qs)))
    return full, faults, meas_op, prep_op


def _simulate(code, full, faults, rows_faults, kind, meas_op, prep_op):
    """rows_faults: list (one per output row) of fault-index lists inserted together.  Returns
    (sparsified syndrome history R x D, logical flips R x K)."""
    Rn = len(rows_faults); state = np.zeros((Rn, code.nq), dtype=np.uint8); by_pos = {}
    for r, fl in enumerate(rows_faults):
        for f in fl:
            pos, qs = faults[f][0], faults[f][1]; by_pos.setdefault(pos, []).append((r, qs))
    synd = []; meas_rows = {}
    for pos, (op, a, b, t) in enumerate(full):
        for r, qs in by_pos.get(pos, ()):
            for q in qs: state[r, q] ^= 1
        if op == 'CNOT':
            if kind == 'X': state[:, b] ^= state[:, a]          # X errors: control -> target
            else: state[:, a] ^= state[:, b]                     # Z errors: target -> control
        elif op == prep_op: state[:, a] = 0
        elif op == meas_op:
            meas_rows.setdefault(a, []).append(len(synd)); synd.append(state[:, a].copy())
    S = np.array(synd, dtype=np.uint8).T; Sc = S.copy()
    for q, rows in meas_rows.items():                           # syndrome sparsification (differences)
        for r in range(1, len(rows)): S[:, rows[r]] ^= Sc[:, rows[r - 1]]
    Lmat = code.lz if kind == 'X' else code.lx
    logical = (state[:, code.data].astype(np.int64) @ np.asarray(Lmat).T.astype(np.int64)) % 2
    return S, logical.astype(np.uint8)


def decoding_matrices(code, sX, sZ, kind, p=0.003, num_cycles=1, schedules=None):
    """kind 'X' (X-type faults, Z-check syndromes, lz final) or 'Z'.  Returns dict(H=[Hdec; logical rows]
    (csr), Hdec, Lrows, probs, faults=[fault indices per column], fault_info=[(op, qubits, round, cycle)]).
    schedules: optional list of (sX, sZ) used cyclically (cycle t uses schedules[t % len]) for the
    num_cycles noisy cycles and the 2 noiseless cycles that follow (alternating circuits)."""
    full, faults, meas_op, prep_op = _setup(code, sX, sZ, kind, p, num_cycles, schedules)
    S, logical = _simulate(code, full, faults, [[f] for f in range(len(faults))], kind, meas_op, prep_op)
    aug = np.hstack([S, logical])
    cols = {}
    for f in range(len(faults)):
        cols.setdefault(tuple(np.flatnonzero(aug[f])), []).append(f)
    cols = {k: v for k, v in cols.items() if len(k)}             # (reference keeps an empty column too, never chosen)
    D = S.shape[1]; K = logical.shape[1]
    keys = list(cols); rows, cidx = [], []
    for j, kk in enumerate(keys):
        rows += list(kk); cidx += [j] * len(kk)
    H = csr_matrix((np.ones(len(rows), dtype=np.uint8), (rows, cidx)), shape=(D + K, len(keys)))
    probs = [sum(faults[f][2] for f in cols[kk]) for kk in keys]
    return dict(H=H, Hdec=H[:D], Lrows=H[D:], D=D, K=K, keys=keys, probs=probs,
                faults=[cols[kk] for kk in keys], fault_info=[faults[f][3] for f in range(len(faults))])


def joint_effect(code, n, schedules, kind, num_cycles, fault_ids, p=0.003):
    """Insert the given physical faults TOGETHER and propagate them: (syndrome history, logical flips)."""
    full, faults, meas_op, prep_op = _setup(code, None, None, kind, p, num_cycles, schedules)
    S, logical = _simulate(code, full, faults, [list(fault_ids)], kind, meas_op, prep_op)
    return S[0], logical[0]


def d1_search(M, trials, seed=0, keep_extra=0, bp_method='ms', max_iter=10000, osd_order=20, ms_scaling_factor=0):
    """circuit_distance.py search on matrices M.  Returns dict(min, hist, sets{weight: set of column tuples},
    invalid, redrawn)."""
    from ldpc import bposd_decoder
    rng = np.random.default_rng(seed)
    Hfull = M['H'].toarray().astype(np.int64); Hdec = M['Hdec'].toarray().astype(np.uint8); D = M['D']
    best = None; hist = {}; sets = {}; invalid = 0; redrawn = 0
    for _ in range(trials):
        while True:
            rv = rng.integers(0, 2, Hfull.shape[0])
            if rv[D:].any(): break
            redrawn += 1
        row = (rv @ Hfull) % 2
        H1 = np.vstack([Hdec, row.astype(np.uint8)[None, :]])
        syn = np.zeros(H1.shape[0], dtype=int); syn[-1] = 1
        dec = bposd_decoder(H1, error_rate=0.01, max_iter=max_iter, bp_method=bp_method,
                            ms_scaling_factor=ms_scaling_factor, osd_method='osd_cs', osd_order=osd_order)
        dec.decode(syn)
        e = np.asarray(dec.osdw_decoding, dtype=np.int64)
        if not np.array_equal((H1.astype(np.int64) @ e) % 2, syn) or not ((M['Lrows'].toarray() @ e) % 2).any():
            invalid += 1; continue
        w = int(e.sum()); hist[w] = hist.get(w, 0) + 1
        if best is None or w < best: best = w
        if w <= best + keep_extra: sets.setdefault(w, set()).add(tuple(np.flatnonzero(e)))
    if best is not None: sets = {w: s for w, s in sets.items() if w <= best + keep_extra}
    return dict(min=best, hist=dict(sorted(hist.items())), sets=sets, invalid=invalid, redrawn=redrawn)


def describe_set(M, cols, code):
    """Physical location of one representative fault per column: (gate, qubits, round, cycle[, faulted qubits])."""
    out = []
    for j in cols:
        info = M['fault_info'][M['faults'][j][0]]
        op, qs, t, c = info[:4]
        d = dict(gate=op, qubits=[code.name(q) for q in qs], round=t, cycle=c)
        if len(info) > 4: d['faulted'] = [code.name(q) for q in info[4]]
        d['n_equivalent'] = len(M['faults'][j])
        out.append(d)
    return out
