"""
Phase 1 of task.md: check infrastructure of the [[72,12,6]] bivariate bicycle (BB) code.

Code (Bravyi et al. 2024): l = m = 6, A = x^3 + y + y^2, B = y^3 + x + x^2 over GF(2),
x = S_6 (x) I_6, y = I_6 (x) S_6 with S_6 the 6x6 cyclic shift.  Every term A1..A3,
B1..B3 is a 36x36 permutation matrix.

    H_X = [A | B]          (36 x 72)
    H_Z = [B^T | A^T]      (36 x 72)

Data-qubit partition (task.md Phase 1.3): Left block L = qubits 0..35 (columns of A in
H_X, of B^T in H_Z), Right block R = qubits 36..71 (columns of B in H_X, of A^T in H_Z).
Every weight-6 check therefore has exactly 3 targets in L and 3 in R.

Labels used by the schedules: 'A1','A2','A3','B1','B2','B3'.
  X-check i, label Ak -> L qubit  Ak[i]      label Bk -> R qubit 36 + Bk[i]
  Z-check i, label Bk -> L qubit  Bk^T[i]    label Ak -> R qubit 36 + Ak^T[i]
so for X checks the A labels are the L targets, for Z checks the B labels are.

Run as a script to print and verify everything:  ../venv/bin/python bb72_matrices.py
"""
import numpy as np

L_SIZE, M_SIZE = 6, 6
N_HALF = L_SIZE * M_SIZE          # 36
N = 2 * N_HALF                    # 72
LABELS = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3']
TERMS = {'A1': (3, 0), 'A2': (0, 1), 'A3': (0, 2),     # A = x^3 + y + y^2
         'B1': (0, 3), 'B2': (1, 0), 'B3': (2, 0)}     # B = y^3 + x + x^2
L_BLOCK = list(range(0, N_HALF))
R_BLOCK = list(range(N_HALF, N))


def shift(k):
    """k x k cyclic shift matrix S_k."""
    return np.roll(np.eye(k, dtype=np.uint8), 1, axis=1)


def monomial(a, b):
    """x^a y^b as a 36 x 36 permutation matrix, x = S_6 (x) I_6, y = I_6 (x) S_6."""
    x = np.kron(shift(L_SIZE), np.eye(M_SIZE, dtype=np.uint8))
    y = np.kron(np.eye(L_SIZE, dtype=np.uint8), shift(M_SIZE))
    return (np.linalg.matrix_power(x, a) @ np.linalg.matrix_power(y, b)) % 2


COMP = {lab: monomial(*TERMS[lab]).astype(np.uint8) for lab in LABELS}
A = (COMP['A1'] + COMP['A2'] + COMP['A3']) % 2
B = (COMP['B1'] + COMP['B2'] + COMP['B3']) % 2
HX = np.hstack([A, B]).astype(np.uint8)
HZ = np.hstack([B.T, A.T]).astype(np.uint8)


def perm(lab):
    """perm(lab)[i] = column of the single 1 in row i of the 36x36 component matrix."""
    return np.argmax(COMP[lab], axis=1)


def x_target(lab, i):
    """Data qubit touched by X-check i through component `lab`."""
    return int(perm(lab)[i]) if lab[0] == 'A' else N_HALF + int(perm(lab)[i])


def z_target(lab, i):
    """Data qubit touched by Z-check i through component `lab`^T."""
    col = int(np.argmax(COMP[lab][:, i]))          # row j with lab[j, i] = 1  <=>  lab^T[i, j] = 1
    return col if lab[0] == 'B' else N_HALF + col


def block(q):
    return 'L' if q < N_HALF else 'R'


def gf2_rank(M):
    M = M.copy() % 2; r = 0
    for c in range(M.shape[1]):
        piv = np.nonzero(M[r:, c])[0]
        if len(piv) == 0: continue
        p = r + piv[0]; M[[r, p]] = M[[p, r]]
        for i in np.nonzero(M[:, c])[0]:
            if i != r: M[i] ^= M[r]
        r += 1
        if r == M.shape[0]: break
    return r


def gf2_nullspace(M):
    """Basis of {v : M v = 0} over GF(2)."""
    M = M.copy() % 2; rows, cols = M.shape; piv = []; r = 0
    for c in range(cols):
        p = np.nonzero(M[r:, c])[0]
        if len(p) == 0: continue
        p = r + p[0]; M[[r, p]] = M[[p, r]]
        for i in np.nonzero(M[:, c])[0]:
            if i != r: M[i] ^= M[r]
        piv.append(c); r += 1
        if r == rows: break
    free = [c for c in range(cols) if c not in piv]
    basis = []
    for f in free:
        v = np.zeros(cols, dtype=np.uint8); v[f] = 1
        for i, c in enumerate(piv):
            v[c] = M[i, f]
        basis.append(v)
    return np.array(basis, dtype=np.uint8)


def logical_ops(basis='Z'):
    """k = 12 independent logical operators measured by a `basis` memory experiment:
    Z logicals (basis 'Z') commute with H_X and are not in the row space of H_Z."""
    Hc, Hs = (HX, HZ) if basis == 'Z' else (HZ, HX)
    ker = gf2_nullspace(Hc)
    out, cur = [], Hs.copy()
    for v in ker:
        test = np.vstack([cur, v])
        if gf2_rank(test) > gf2_rank(cur):
            out.append(v); cur = test
    return np.array(out, dtype=np.uint8)


def check():
    """Verify the infrastructure; returns a dict of facts."""
    facts = {}
    for lab in LABELS:
        P = COMP[lab]
        assert P.shape == (36, 36) and (P.sum(0) == 1).all() and (P.sum(1) == 1).all()
    assert (A @ B % 2 == B @ A % 2).all()
    facts['HX_HZ^T == 0'] = bool(((HX.astype(int) @ HZ.T.astype(int)) % 2 == 0).all())
    facts['row weight HX, HZ'] = (sorted(set(HX.sum(1))), sorted(set(HZ.sum(1))))
    facts['col weight HX, HZ'] = (sorted(set(HX.sum(0))), sorted(set(HZ.sum(0))))
    rk = gf2_rank(HX) + gf2_rank(HZ)
    facts['k = n - rank HX - rank HZ'] = N - rk
    # 3 L + 3 R targets per check, and labels map to the declared block
    for i in range(N_HALF):
        xs = [x_target(l, i) for l in LABELS]; zs = [z_target(l, i) for l in LABELS]
        assert sorted(xs) == list(np.nonzero(HX[i])[0]) and sorted(zs) == list(np.nonzero(HZ[i])[0])
        assert sum(block(q) == 'L' for q in xs) == 3 and sum(block(q) == 'L' for q in zs) == 3
        assert all(block(x_target(l, i)) == ('L' if l[0] == 'A' else 'R') for l in LABELS)
        assert all(block(z_target(l, i)) == ('L' if l[0] == 'B' else 'R') for l in LABELS)
    facts['every check: 3 targets in L, 3 in R'] = True
    facts['L targets: X-check via A labels, Z-check via B labels'] = True
    facts['logicals Z, X'] = (len(logical_ops('Z')), len(logical_ops('X')))
    return facts


if __name__ == '__main__':
    print('[[72,12,6]] BB code, l = m = 6, A = x^3 + y + y^2, B = y^3 + x + x^2')
    print('H_X shape', HX.shape, ' H_Z shape', HZ.shape, ' L block 0..35, R block 36..71')
    for k, v in check().items():
        print(f'  {k}: {v}')
    print('  X-check 0 targets:', {l: x_target(l, 0) for l in LABELS})
    print('  Z-check 0 targets:', {l: z_target(l, 0) for l in LABELS})
