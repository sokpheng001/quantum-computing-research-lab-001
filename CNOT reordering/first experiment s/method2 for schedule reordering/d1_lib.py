"""One-cycle circuit distance d1(A): the lightest set of faults, all inside ONE interior syndrome cycle of a
multi-cycle memory circuit run with schedule A, that trips no detector and flips a logical observable.

Construction: a memory circuit of 3 cycles in which only the middle cycle (t = 1) is noisy.  Its DEM then
contains exactly the one-cycle fault mechanisms (merged into columns as usual; weight = number of columns).
A fault in cycle 1 can only flip detectors of cycles 1 and 2 (a leftover data error is seen once and then
cancels in later detectors), so 3 cycles see everything an interior cycle of any longer circuit sees.
Exact minimum: integer program  min sum x  s.t.  H x = 0 (mod 2),  L x = z (mod 2),  sum z >= 1, x, z binary,
with each parity written as  row . x - 2 y = 0  (y integer).  Solved by HiGHS (scipy.optimize.milp).
"""
import time
import numpy as np
import scipy.sparse as sp
import stim
from scipy.optimize import milp, LinearConstraint, Bounds
from bb_code import BBCode, build_cycle, logical_ops
from dcirc import dem_matrices, dcirc_bound


def one_cycle_circuit(code, sched, basis, p=0.001, cycles=3, noisy=1):
    """bb_code.memory_circuit with noise only in cycle `noisy` (same detectors / observables)."""
    h = code.half
    dataq = list(map(int, code.L)) + list(map(int, code.R))
    c = stim.Circuit()
    c.append('R' if basis == 'Z' else 'RX', dataq); c.append('TICK')
    z_idx, x_idx = [], []; nmeas = 0
    for t in range(cycles):
        cyc, first = build_cycle(code, sched, p if t == noisy else 0.0)
        c += cyc
        if first == 'Z': z_idx.append(nmeas); x_idx.append(nmeas + h)
        else: x_idx.append(nmeas); z_idx.append(nmeas + h)
        nmeas += 2 * h
        rec = lambda a: stim.target_rec(a - nmeas)
        for i in range(h):
            if t == 0:
                c.append('DETECTOR', [rec((z_idx if basis == 'Z' else x_idx)[t] + i)], [i, 0 if basis == 'Z' else 1, t])
            else:
                c.append('DETECTOR', [rec(z_idx[t] + i), rec(z_idx[t - 1] + i)], [i, 0, t])
                c.append('DETECTOR', [rec(x_idx[t] + i), rec(x_idx[t - 1] + i)], [i, 1, t])
        c.append('TICK')
    c.append('M' if basis == 'Z' else 'MX', dataq)
    nd = len(dataq); nmeas += nd
    rec = lambda a: stim.target_rec(a - nmeas)
    H = code.hz() if basis == 'Z' else code.hx()
    last = (z_idx if basis == 'Z' else x_idx)[-1]
    for i in range(h):
        c.append('DETECTOR', [rec(nmeas - nd + j) for j in np.flatnonzero(H[i])] + [rec(last + i)], [i, 0 if basis == 'Z' else 1, cycles])
    for k, Lk in enumerate(logical_ops(code, basis)):
        c.append('OBSERVABLE_INCLUDE', [rec(nmeas - nd + j) for j in np.flatnonzero(Lk)], k)
    return c


def matrices(code, sched, basis):
    c = one_cycle_circuit(code, sched, basis)
    H, L, _ = dem_matrices(c)
    H = sp.csr_matrix(H); L = sp.csr_matrix(L)
    keep = np.flatnonzero(np.asarray(H.sum(axis=1)).ravel() > 0)       # drop detectors no fault touches
    return H[keep], L, c


def d1_ilp(H, L, upper=None, time_limit=600):
    """Exact min weight of x with H x = 0, L x != 0 (mod 2).  Returns (weight, x, status)."""
    D, E = H.shape; K = L.shape[0]
    # variables: x (E binary), z (K binary), y (D + K integer slacks)
    A = sp.bmat([[H, None, -2 * sp.identity(D), None],
                 [L, -sp.identity(K), None, -2 * sp.identity(K)]]).tocsr()
    nv = E + K + D + K
    cons = [LinearConstraint(A, 0, 0),
            LinearConstraint(sp.hstack([sp.csr_matrix((1, E)), sp.csr_matrix(np.ones((1, K))), sp.csr_matrix((1, D + K))]), 1, np.inf)]
    if upper is not None:
        cons.append(LinearConstraint(sp.hstack([sp.csr_matrix(np.ones((1, E))), sp.csr_matrix((1, K + D + K))]), 0, upper))
    hi_y = np.concatenate([np.asarray(abs(H).sum(axis=1)).ravel() // 2, np.asarray(abs(L).sum(axis=1)).ravel() // 2])
    lb = np.zeros(nv); ub = np.concatenate([np.ones(E + K), hi_y])
    cost = np.concatenate([np.ones(E), np.zeros(K + D + K)])
    r = milp(cost, constraints=cons, integrality=np.ones(nv), bounds=Bounds(lb, ub),
             options=dict(time_limit=time_limit, disp=False))
    if r.x is None: return None, None, r.message
    x = np.round(r.x[:E]).astype(np.uint8)
    assert not ((H @ x) % 2).any() and ((L @ x) % 2).any()
    return int(x.sum()), x, ('optimal' if r.status == 0 else r.message)


def d1_heuristic(H, L, trials=200, seed=0):
    r = dcirc_bound(H, L, trials=trials, osd_order=20, max_iter=10, seed=seed, ms_scale=0.625)
    return r['min_weight']


def d1_cpsat(H, L, workers=12, time_limit=600, hint=None, upper=None):
    """Exact min weight of x with H x = 0, L x != 0 (mod 2) by OR-Tools CP-SAT (native XOR constraints).
    Returns (weight, x, status) with status 'optimal' only when CP-SAT proves optimality."""
    from ortools.sat.python import cp_model
    H = sp.csr_matrix(H); L = sp.csr_matrix(L); D, E = H.shape; K = L.shape[0]
    m = cp_model.CpModel(); x = [m.NewBoolVar(f'x{j}') for j in range(E)]
    one = m.NewConstant(1)
    for i in range(D):
        cols = H.indices[H.indptr[i]:H.indptr[i + 1]]
        if len(cols): m.AddBoolXOr([x[j] for j in cols] + [one])            # parity 0
    z = [m.NewBoolVar(f'z{k}') for k in range(K)]
    for k in range(K):
        cols = L.indices[L.indptr[k]:L.indptr[k + 1]]
        m.AddBoolXOr([x[j] for j in cols] + [z[k].Not()])                  # z_k = parity of L_k x
    m.AddBoolOr(z)
    if upper is not None: m.Add(sum(x) <= upper)
    m.Minimize(sum(x))
    if hint is not None:
        for j in range(E): m.AddHint(x[j], int(hint[j]))
    s = cp_model.CpSolver(); s.parameters.num_search_workers = workers; s.parameters.max_time_in_seconds = time_limit
    st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): return None, None, s.StatusName(st)
    xv = np.array([s.Value(v) for v in x], dtype=np.uint8)
    assert not ((H @ xv) % 2).any() and ((L @ xv) % 2).any()
    return int(xv.sum()), xv, ('optimal' if st == cp_model.OPTIMAL else f'feasible (bound {s.BestObjectiveBound():.0f})')
