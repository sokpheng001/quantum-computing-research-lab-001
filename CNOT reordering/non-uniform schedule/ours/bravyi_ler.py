"""Logical error rate with Bravyi's decoder procedure (port of bravyi_ref/decoder_run.py, Apache 2.0, Bravyi et al.).

Changes relative to the reference (bravyi_ref/ is never edited):
  1. Works for any schedule, including per-ancilla (class) tables, through bravyi_d1.decoding_matrices.
  2. Sampling is vectorised: every noisy location of the num_cycles noisy cycles gets an error with
     probability p and a uniformly random type, exactly the reference distribution (CNOT: 15 two-qubit Paulis,
     IDLE: X/Y/Z, PrepX/MeasX: Z, PrepZ/MeasZ: X).  Each error is split into its X part and Z part; the syndrome
     history of each part is the XOR of the corresponding single-fault columns (linear propagation, the same
     columns the reference builds), followed by the 2 noiseless cycles already included in those columns.
  3. Both decoders always run: X-part failure (logical Z operators, = Z-basis memory) and Z-part failure
     (= X-basis memory) are reported separately; 'any' = either failed (the reference's single number).
Decoder (unchanged): ldpc bposd_decoder, bp_method 'ms', ms_scaling_factor 0, max_iter 10000, osd_cs order 7,
channel_probs = the merged priors of each column.
"""
import numpy as np
import multiprocessing as mp
from bravyi_d1 import _setup, decoding_matrices

# reference CNOT error list (decoder_run.py, error_type 0..14): Pauli on (control, target)
CNOT_PAULIS = [('X', 'I'), ('Y', 'I'), ('Z', 'I'), ('I', 'X'), ('I', 'Y'), ('I', 'Z'), ('X', 'X'), ('Y', 'Y'), ('Z', 'Z'),
               ('X', 'Y'), ('Y', 'X'), ('Y', 'Z'), ('Z', 'Y'), ('X', 'Z'), ('Z', 'X')]
HAS_X = {'I': 0, 'X': 1, 'Y': 1, 'Z': 0}; HAS_Z = {'I': 0, 'X': 0, 'Y': 1, 'Z': 1}


def _key(info):
    return (info[0], tuple(info[1]), info[2], info[3], tuple(info[4]) if len(info) > 4 else None)


class LerModel:
    def __init__(self, code, tX, tZ, p, cycles):
        self.M = {k: decoding_matrices(code, tX, tZ, k, p=p, num_cycles=cycles) for k in 'XZ'}
        self.p = p
        # effect matrix per kind: row = single fault (mechanism), columns = [syndrome history | logical]
        self.E, self.idx = {}, {}
        for k, M in self.M.items():
            H = M['H'].toarray().astype(np.uint8); col_of = {}
            for j, fl in enumerate(M['faults']):
                for f in fl: col_of[f] = j
            nf = len(M['fault_info'])
            E = np.zeros((nf + 1, H.shape[0]), dtype=np.uint8)          # last row = "no fault" (all zero)
            for f in range(nf):
                if f in col_of: E[f] = H[:, col_of[f]]
            self.E[k] = E; self.idx[k] = {_key(M['fault_info'][f]): f for f in range(nf)}
        full, _, _, _ = _setup(code, tX, tZ, 'X', p, cycles, [(tX, tZ)])
        noisy = sum(1 for _ in range(len(full)))  # placeholder, recomputed below
        # physical locations of the noisy cycles: (type, table of (x_mech, z_mech) per error type)
        nx, nz = len(self.E['X']) - 1, len(self.E['Z']) - 1
        gx = lambda key: self.idx['X'].get(key, nx); gz = lambda key: self.idx['Z'].get(key, nz)
        locs = []
        cyc_len = len(full) // (cycles + 2) if False else None
        fx = [self.M['X']['fault_info'][f] for f in range(nx)]
        cycles_of = {}
        for info in fx + [self.M['Z']['fault_info'][f] for f in range(nz)]:
            cycles_of[(info[0], tuple(info[1]), info[2], info[3])] = True
        for (op, qs, t, c) in cycles_of:
            if op == 'CNOT':
                a, b = qs; tab = []
                for pa, pb in CNOT_PAULIS:
                    xq = tuple(q for q, P in ((a, pa), (b, pb)) if HAS_X[P]); zq = tuple(q for q, P in ((a, pa), (b, pb)) if HAS_Z[P])
                    tab.append((gx((op, qs, t, c, xq)) if xq else nx, gz((op, qs, t, c, zq)) if zq else nz))
                locs.append(tab)
            elif op == 'IDLE':
                locs.append([(gx((op, qs, t, c, None)), nz), (gx((op, qs, t, c, None)), gz((op, qs, t, c, None))), (nx, gz((op, qs, t, c, None)))])
            elif op in ('PrepZ', 'MeasZ'):
                locs.append([(gx((op, qs, t, c, None)), nz)])
            elif op in ('PrepX', 'MeasX'):
                locs.append([(nx, gz((op, qs, t, c, None)))])
        self.locs = locs
        self.tabx = [np.array([e[0] for e in tab]) for tab in locs]; self.tabz = [np.array([e[1] for e in tab]) for tab in locs]

    def sample(self, shots, rng):
        """-> per kind: (syndrome history shots x D, true logical shots x K)."""
        L = len(self.locs); hit = rng.random((shots, L)) < self.p
        out = {}
        acc = {'X': np.zeros((shots, self.E['X'].shape[1]), dtype=np.uint8), 'Z': np.zeros((shots, self.E['Z'].shape[1]), dtype=np.uint8)}
        for j in range(L):
            rows = np.flatnonzero(hit[:, j])
            if not len(rows): continue
            ty = rng.integers(0, len(self.locs[j]), len(rows))
            acc['X'][rows] ^= self.E['X'][self.tabx[j][ty]]
            acc['Z'][rows] ^= self.E['Z'][self.tabz[j][ty]]
        for k in 'XZ':
            D = self.M[k]['D']; out[k] = (acc[k][:, :D], acc[k][:, D:])
        return out


_W = {}
def _init(Mx, Mz):
    from ldpc import bposd_decoder
    for k, M in (('X', Mx), ('Z', Mz)):
        _W[k] = (bposd_decoder(M['Hdec'].toarray().astype(np.uint8), channel_probs=list(M['probs']), max_iter=10000, bp_method='ms',
                               ms_scaling_factor=0, osd_method='osd_cs', osd_order=7), M['Lrows'].toarray().astype(np.int64))

def _decode(args):
    k, syn, logical = args; dec, Lr = _W[k]; fails = np.zeros(len(syn), dtype=bool)
    for i in range(len(syn)):
        dec.decode(syn[i].astype(int)); e = np.asarray(dec.osdw_decoding, dtype=np.int64)
        fails[i] = not np.array_equal((Lr @ e) % 2, logical[i])
    return k, fails

def run(model, shots, seed, nproc):
    """-> dict(shots, fail_X, fail_Z, fail_any) for one batch."""
    rng = np.random.default_rng(seed); s = model.sample(shots, rng)
    jobs = [(k, s[k][0][i:i + 20], s[k][1][i:i + 20]) for k in 'XZ' for i in range(0, shots, 20)]
    res = {'X': [], 'Z': []}
    with mp.get_context('fork').Pool(nproc, initializer=_init, initargs=(model.M['X'], model.M['Z'])) as pool:
        for k, f in pool.map(_decode, jobs): res[k].append(f)
    fx = np.concatenate(res['X']); fz = np.concatenate(res['Z'])
    return dict(shots=shots, fail_X=int(fx.sum()), fail_Z=int(fz.sum()), fail_any=int((fx | fz).sum()))
