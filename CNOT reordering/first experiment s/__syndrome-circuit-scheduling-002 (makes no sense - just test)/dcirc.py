"""
Circuit-level distance bounds and logical error rates for BB-code memory
circuits built by bb_code.memory_circuit, decoded with BP-OSD (ldpc >= 2).

dem_matrices(circuit)  -> H (D x E, csr uint8), L (K x E), priors (E,)
dcirc_bound(H, L, ...) -> Bravyi Eq. 12 style randomized upper bound on d_circ:
                          decode syndrome (0,...,0,1) for [H; random logical row]
                          with BP-OSD; any returned solution is a logical fault
                          path, its weight an upper bound.
logical_error_rate(circuit, shots, ...) -> Monte-Carlo LER with BP-OSD,
                          multiprocessing over shots.
"""
import os
import time
import numpy as np
import scipy.sparse as sp
import stim
from ldpc import BpOsdDecoder


# ---------------------------------------------------------------- DEM -> H, L
def dem_columns(circuit_or_dem):
    """Ordered dict (dets tuple, obs tuple) -> prob: one entry per merged DEM
    column, in the column order used by dem_matrices.  The key is independent
    of the CNOT schedule (detector i of cycle t always has the same index), so
    it identifies "the same fault" across schedules (Phase 3.2 / 4.2)."""
    dem = circuit_or_dem
    if isinstance(dem, stim.Circuit):
        dem = dem.detector_error_model(flatten_loops=True)
    cols = {}          # (dets tuple, obs tuple) -> prob
    for inst in dem.flattened():
        if inst.type != 'error':
            continue
        p = inst.args_copy()[0]
        dets, obs = [], []
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                dets.append(t.val)
            elif t.is_logical_observable_id():
                obs.append(t.val)
        # XOR-reduce repeated targets
        dets = tuple(sorted(d for d in set(dets) if dets.count(d) % 2))
        obs = tuple(sorted(o for o in set(obs) if obs.count(o) % 2))
        key = (dets, obs)
        if key in cols:
            q = cols[key]
            cols[key] = p + q - 2 * p * q
        else:
            cols[key] = p
    return cols


def dem_matrices(circuit_or_dem):
    """Parse a stim DEM into check matrix H, logical matrix L and priors.
    Identical (detector, observable) columns are merged (independent OR)."""
    dem = circuit_or_dem
    if isinstance(dem, stim.Circuit):
        dem = dem.detector_error_model(flatten_loops=True)
    D, K = dem.num_detectors, dem.num_observables
    cols = dem_columns(dem)
    E = len(cols)
    priors = np.empty(E)
    hr, hc, lr, lc = [], [], [], []
    for j, ((dets, obs), p) in enumerate(cols.items()):
        priors[j] = p
        hr += dets; hc += [j] * len(dets)
        lr += obs;  lc += [j] * len(obs)
    H = sp.csr_matrix((np.ones(len(hr), dtype=np.uint8), (hr, hc)), shape=(D, E))
    L = sp.csr_matrix((np.ones(len(lr), dtype=np.uint8), (lr, lc)), shape=(K, E))
    return H, L, priors


# ------------------------------------------------------------ distance bound
def dcirc_bound(H, L, trials=1000, osd_order=20, max_iter=100, seed=0,
                random_channel=True, verbose=False, stop_at=None,
                schedule='serial', ms_scale=1.0, keep_le=None):
    """Randomized upper bound on circuit-level distance (Bravyi et al. 2024,
    Eq. 12 method).  Each trial: pick a random nonzero combination of logical
    rows (plus a random combination of check rows, which does not change the
    solution set but perturbs BP/OSD), stack it under H, decode the syndrome
    (0,..,0,1).  BP-OSD always returns a vector consistent with the syndrome,
    i.e. an undetectable fault path that flips a logical -> its weight is an
    upper bound on d_circ.

    Returns dict(min_weight, hist{weight:count}, min_supports{frozenset},
                 trials, seconds)."""
    rng = np.random.default_rng(seed)
    H = sp.csr_matrix(H, dtype=np.uint8)
    L = sp.csr_matrix(L, dtype=np.uint8)
    D, E = H.shape
    K = L.shape[0]
    best = E
    hist = {}
    min_supports = set()
    supports = {}   # weight -> set of frozensets, for weights <= keep_le
    t0 = time.time()
    syndrome = np.zeros(D + 1, dtype=np.uint8)
    syndrome[-1] = 1
    for t in range(trials):
        rL = rng.integers(0, 2, K)
        if not rL.any():
            rL[rng.integers(K)] = 1
        row = (rL @ L.toarray().astype(np.int64)) % 2
        if rng.random() < 0.5:
            rH = rng.integers(0, 2, D)
            row = (row + rH @ H.toarray().astype(np.int64)) % 2
        Haug = sp.vstack([H, sp.csr_matrix(row.astype(np.uint8))]).tocsr()
        if random_channel:
            chan = rng.uniform(0.005, 0.1, E)
            dec = BpOsdDecoder(Haug, error_channel=list(chan), max_iter=max_iter,
                               bp_method='minimum_sum', ms_scaling_factor=ms_scale,
                               schedule=schedule, osd_method='OSD_CS', osd_order=osd_order)
        else:
            dec = BpOsdDecoder(Haug, error_rate=0.01, max_iter=max_iter,
                               bp_method='minimum_sum', ms_scaling_factor=ms_scale,
                               schedule=schedule, osd_method='OSD_CS', osd_order=osd_order)
        e = dec.decode(syndrome)
        # sanity: must satisfy the augmented syndrome
        assert ((Haug @ e) % 2 == syndrome).all(), 'OSD returned inconsistent solution'
        w = int(e.sum())
        hist[w] = hist.get(w, 0) + 1
        if keep_le is not None and w <= keep_le:
            supports.setdefault(w, set()).add(frozenset(np.flatnonzero(e)))
        if w < best:
            best = w
            min_supports = {frozenset(np.flatnonzero(e))}
        elif w == best:
            min_supports.add(frozenset(np.flatnonzero(e)))
        if verbose and (t + 1) % 100 == 0:
            print(f'  trial {t+1}/{trials}: min={best}, #distinct min paths={len(min_supports)}',
                  flush=True)
        if stop_at is not None and best <= stop_at:
            break
    return dict(min_weight=best, hist=dict(sorted(hist.items())),
                min_supports=min_supports, n_min_paths=len(min_supports),
                supports=supports, trials=t + 1, seconds=time.time() - t0)


# --------------------------------------------------------- logical error rate
_W = {}   # per-worker globals (fork start method)


def _init_worker(H, L, priors, max_iter, osd_order, ms_scale, bp_method, schedule):
    _W['dec'] = BpOsdDecoder(H, error_channel=list(priors), max_iter=max_iter,
                             bp_method=bp_method, ms_scaling_factor=ms_scale,
                             schedule=schedule,
                             osd_method='OSD_CS', osd_order=osd_order)
    _W['L'] = sp.csr_matrix(L, dtype=np.uint8)


def _decode_chunk(args):
    dets, obs = args
    dec, L = _W['dec'], _W['L']
    fails = 0
    conv = 0
    preds = np.zeros_like(obs)
    for i in range(dets.shape[0]):
        e = dec.decode(dets[i].astype(np.uint8))
        conv += int(dec.converge)
        pred = (L @ e) % 2
        preds[i] = pred
        if (pred != obs[i]).any():
            fails += 1
    return fails, conv, dets.shape[0], preds


def logical_error_rate(circuit, shots, osd_order=7, max_iter=100, ms_scale=1.0,
                       nproc=None, seed=0, chunk=50, bp_method='minimum_sum',
                       schedule='serial'):
    """NOTE: schedule='parallel' fails badly on these DEMs (0% BP convergence,
    ~5x the logical failures); keep 'serial'.  max_iter below ~100 also hurts."""
    """Sample `shots` from the noisy circuit, decode with BP-OSD in parallel.
    Returns dict(shots, fails, ler, ler_per_cycle(None unless cycles given),
                 bp_converged_frac, seconds)."""
    import multiprocessing as mp
    H, L, priors = dem_matrices(circuit)
    sampler = circuit.compile_detector_sampler(seed=seed)
    dets, obs = sampler.sample(shots, separate_observables=True)
    dets = dets.astype(np.uint8); obs = obs.astype(np.uint8)
    nproc = nproc or os.cpu_count()
    nproc = min(nproc, workers_that_fit(H, L, priors, max_iter, osd_order, ms_scale, bp_method, schedule, nproc))
    chunk = max(1, min(chunk, shots // nproc))
    chunks = [(dets[i:i + chunk], obs[i:i + chunk]) for i in range(0, shots, chunk)]
    t0 = time.time()
    ctx = mp.get_context('fork')
    with ctx.Pool(nproc, initializer=_init_worker,
                  initargs=(H, L, priors, max_iter, osd_order, ms_scale, bp_method, schedule)) as pool:
        res = pool.map(_decode_chunk, chunks)
    fails = sum(r[0] for r in res); conv = sum(r[1] for r in res)
    return dict(shots=shots, fails=fails, ler=fails / shots,
                bp_converged_frac=conv / shots, seconds=time.time() - t0,
                n_errors=H.shape[1], dets=dets, obs=obs,
                preds=np.concatenate([r[3] for r in res]))


def per_cycle(ler, cycles):
    """Convert a whole-experiment failure probability to a per-cycle rate."""
    return 1 - (1 - ler) ** (1 / cycles)


def wilson(f, n, z=1.96):
    """Wilson 95% CI for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    p = f / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def min_weight_count(H, L, w, trials=60, **kw):
    """Number of distinct undetectable logical fault sets of weight exactly w
    found by the randomised BP-OSD search in `trials` trials (a lower bound on
    the true count; comparable across circuits at a fixed trial budget).
    Returns (count, list of sorted index lists, full dcirc_bound result)."""
    r = dcirc_bound(H, L, trials=trials, keep_le=w, **kw)
    sets = r['supports'].get(w, set())
    return len(sets), [sorted(map(int, s)) for s in sets], r


def _rss_gb():
    for line in open('/proc/self/status'):
        if line.startswith('VmRSS'):
            return int(line.split()[1]) / 1e6
    return 0.0


def _avail_gb():
    for line in open('/proc/meminfo'):
        if line.startswith('MemAvailable'):
            return int(line.split()[1]) / 1e6
    return 0.0


def workers_that_fit(H, L, priors, max_iter, osd_order, ms_scale, bp_method, schedule,
                     requested, reserve_gb=8.0):
    """Build one decoder, measure its resident memory, and return how many
    workers fit in currently available RAM leaving `reserve_gb` untouched.
    Protects the machine (and the SSH / VPN daemons) from OOM kills."""
    import gc
    before = _rss_gb()
    dec = BpOsdDecoder(H, error_channel=list(priors), max_iter=max_iter, bp_method=bp_method,
                       ms_scaling_factor=ms_scale, schedule=schedule, osd_method='OSD_CS', osd_order=osd_order)
    per = max(_rss_gb() - before, 0.05)
    del dec; gc.collect()
    avail = _avail_gb()
    fit = int(max(1, (avail - reserve_gb) // (per * 1.15)))
    n = max(1, min(requested, fit))
    print(f'  [mem guard] decoder ~{per:.2f} GB, available {avail:.1f} GB, reserve {reserve_gb} GB '
          f'-> {n} workers (requested {requested})', flush=True)
    return n
