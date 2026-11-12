"""Exact one-cycle distance on Bravyi's (CSS-split) matrices: min |x| with Hdec x = 0 and Lrows x != 0 (mod 2),
solved by OR-Tools CP-SAT with native XOR constraints.  'optimal' = proven minimum."""
import numpy as np


def exact_min(M, workers=1, time_limit=300):
    from ortools.sat.python import cp_model
    Hd = M['Hdec'].tocsr(); Lr = M['Lrows'].tocsr(); E = Hd.shape[1]
    m = cp_model.CpModel(); x = [m.NewBoolVar('') for _ in range(E)]; one = m.NewConstant(1)
    for i in range(Hd.shape[0]):
        c = Hd.indices[Hd.indptr[i]:Hd.indptr[i + 1]]
        if len(c): m.AddBoolXOr([x[j] for j in c] + [one])
    z = [m.NewBoolVar('') for _ in range(Lr.shape[0])]
    for k in range(Lr.shape[0]):
        c = Lr.indices[Lr.indptr[k]:Lr.indptr[k + 1]]
        m.AddBoolXOr([x[j] for j in c] + [z[k].Not()])
    m.AddBoolOr(z); m.Minimize(sum(x))
    s = cp_model.CpSolver(); s.parameters.num_search_workers = workers; s.parameters.max_time_in_seconds = time_limit
    st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): return dict(value=None, status=s.StatusName(st), bound=None)
    xv = np.array([s.Value(v) for v in x], dtype=np.int64)
    assert not ((Hd @ xv) % 2).any() and ((Lr @ xv) % 2).any()
    return dict(value=int(xv.sum()), status='optimal' if st == cp_model.OPTIMAL else 'feasible',
                bound=int(round(s.BestObjectiveBound())), cols=tuple(np.flatnonzero(xv)), seconds=s.WallTime())
