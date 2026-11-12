"""Shared library for the path-targeted partner search (docs/task.md).

Schedules  : enumerate(code) -> list of (x_order, z_order, z_first) in the same order as folder 001
             (Z-first block, then X-first, itertools.permutations order), so ids match 001 on [[72]].
Circuits   : spec '212' = single schedule, '212+947' = alternating (cycle t uses ids[t % 2]).
Locations  : a physical fault location is (cycle, rel, paulis): `rel` = instruction offset inside
             the cycle block (every cycle of every schedule has the same instruction layout, only the
             targets differ), paulis = ((qubit, 'X'|'Y'|'Z'), ...).  The same location can be placed
             into any circuit where the instruction at (cycle, rel) is the same noise channel acting on
             the same qubits (same CNOT pair for DEPOLARIZE2).
Exact check: detector / observable flips of a location in a circuit are computed by stim's
             FlipSimulator (noiseless run, the Pauli injected at that point).  Flips are linear, so a
             fault set's effect is the XOR of its locations' effects.  DEM columns with several
             physical representatives: every combination is explored (reach set, capped).
Families   : fault sets equal up to a torus translation x^i y^j (detector check index shifted).
"""
import collections, itertools, json, os
import numpy as np
import stim
from bb_code import BBCode, memory_circuit, LABELS, BRAVYI, reverse_schedule

TICKS_PER_CYCLE = 10
NOISE = {'DEPOLARIZE1', 'DEPOLARIZE2', 'X_ERROR', 'Z_ERROR', 'Y_ERROR', 'PAULI_CHANNEL_1', 'PAULI_CHANNEL_2'}
S_MIRROR = (['B2', 'A2', 'A1', 'A3', 'B1', 'B3'], ['B1', 'B3', 'A1', 'A2', 'A3', 'B2'], True)
P_STRUCT = 0.001          # any p > 0: only used to make the noise locations exist


# ------------------------------------------------------------------ schedules
def _incidence(code):
    xq = {}
    for lab in LABELS:
        pr = code.x_layer(lab); xq[lab] = {pr[2 * i]: pr[2 * i + 1] for i in range(code.half)}
    zinc = {}
    for lab in LABELS:
        pr = code.z_layer(lab)
        for i in range(code.half):
            zinc.setdefault(pr[2 * i], []).append((pr[2 * i + 1], lab))
    return xq, zinc


def _alg_valid(xo, zo, zf, xq, zinc, a):
    xr = {lab: i + (2 if zf else 1) for i, lab in enumerate(xo)}
    zr = {lab: i + (1 if zf else 2) for i, lab in enumerate(zo)}
    fl = {}
    for lab in LABELS:
        d = xq[lab][a]; tx = xr[lab]
        for b, lz in zinc[d]:
            if zr[lz] == tx: return False
            if zr[lz] < tx: fl[b] = fl.get(b, 0) ^ 1
    return not any(fl.values())


def noiseless_ok(code, scheds, cycles):
    """True if the memory circuit builds (no same-round collision) and every detector is 0, both bases."""
    for basis in 'ZX':
        try:
            c = memory_circuit(code, scheds, cycles, 0.0, basis)
        except ValueError:
            return False
        if c.compile_detector_sampler().sample(4).any():
            return False
    return True


def enumerate_schedules(code):
    xq, zinc = _incidence(code); a0 = int(code.X[0])
    perms = list(itertools.permutations(LABELS)); out = []
    for zf in (True, False):
        for xo in perms:
            for zo in perms:
                if _alg_valid(xo, zo, zf, xq, zinc, a0):
                    out.append((list(xo), list(zo), zf))
    return out


def load_table(n):
    T = {}
    for line in open(os.path.join(os.environ.get('PARTNER_RES', 'results_partner'), str(n), 'schedules.jsonl')):
        r = json.loads(line); T[r['id']] = (r['x'], r['z'], r['z_first'])
    return T


def named(n):
    return json.load(open(os.path.join(os.environ.get('PARTNER_RES', 'results_partner'), str(n), 'named_ids.json')))


def scheds_of(spec, T):
    return [T[int(i)] for i in str(spec).split('+')]


# ---------------------------------------------------------------- circuits
_CIRC = {}


def circuit(n, spec, cycles, basis, T, p=P_STRUCT):
    k = (n, spec, cycles, basis, p)
    if k not in _CIRC:
        c = memory_circuit(BBCode(n), scheds_of(spec, T), cycles, p, basis)
        assert c.num_ticks == 1 + TICKS_PER_CYCLE * cycles, c.num_ticks
        _CIRC[k] = c
    return _CIRC[k]


def cycle_starts(c):
    """starts[t] = flat instruction offset where cycle t's block begins (after its first tick)."""
    starts, ticks = [], 0
    for i, ins in enumerate(c):
        if ins.name == 'TICK':
            ticks += 1
            if (ticks - 1) % TICKS_PER_CYCLE == 0:
                starts.append(i + 1)
    return starts[:-1] if len(starts) * TICKS_PER_CYCLE + 1 > c.num_ticks else starts


def _cyc_rel(starts, off):
    t = max(i for i, s in enumerate(starts) if s <= off)
    return t, off - starts[t]


def location_of(loc, starts):
    off = loc.stack_frames[-1].instruction_offset
    t, rel = _cyc_rel(starts, off)
    paulis = []
    for g in loc.flipped_pauli_product:
        q = g.gate_target.qubit_value
        P = 'X' if g.gate_target.is_x_target else 'Y' if g.gate_target.is_y_target else 'Z'
        paulis.append((q, P))
    assert paulis, 'location without a Pauli'
    return (t, rel, tuple(sorted(paulis)))


def column_dem_line(col):
    dets, obs = col
    return 'error(0.1) ' + ' '.join([f'D{d}' for d in dets] + [f'L{o}' for o in obs])


def explain_columns(c, cols):
    """col (dets, obs) -> sorted list of physical locations (cycle, rel, paulis) in circuit c."""
    cols = list(set(cols)); out = {k: set() for k in cols}
    if not cols: return {}
    starts = cycle_starts(c)
    dem = stim.DetectorErrorModel('\n'.join(column_dem_line(k) for k in cols))
    for e in c.explain_detector_error_model_errors(dem_filter=dem, reduce_to_one_representative_error=False):
        dets = tuple(sorted(t.dem_target.val for t in e.dem_error_terms if t.dem_target.is_relative_detector_id()))
        obs = tuple(sorted(t.dem_target.val for t in e.dem_error_terms if t.dem_target.is_logical_observable_id()))
        if (dets, obs) in out:
            for loc in e.circuit_error_locations:
                out[(dets, obs)].add(location_of(loc, starts))
    return {k: sorted(v) for k, v in out.items()}


def describe(loc, code):
    """(type, qubits, round, cycle) of a location; round 0 = reset, 1..7 CNOT rounds, 8 = last measurement."""
    t, rel, paulis = loc
    reg = lambda q: 'LRXZ'[q // code.half] + str(q % code.half)
    return dict(paulis=''.join(P for _, P in paulis), qubits=[reg(q) for q, _ in paulis], cycle=t, rel=rel)


_PL = {}


def forget(c):
    _PL.pop(id(c), None)


def placeable(c, loc, shift=0):
    """Absolute offset of location `loc` shifted by `shift` cycles in circuit c, or None if circuit c
    has no identical fault location there (same noise gate on the same qubit / CNOT pair)."""
    key = id(c)
    if key not in _PL:
        _PL[key] = (c, cycle_starts(c), {})
    c_, starts, info = _PL[key]
    t, rel, paulis = loc; t += shift
    if not 0 <= t < len(starts): return None
    off = starts[t] + rel
    if t + 1 < len(starts) and off >= starts[t + 1]: return None
    if off not in info:
        ins = c[off]; tg = [x.value for x in ins.targets_copy()]
        if ins.name == 'DEPOLARIZE2':
            info[off] = (ins.name, {frozenset(tg[i:i + 2]) for i in range(0, len(tg), 2)})
        else:
            info[off] = (ins.name, set(tg))
    name, tset = info[off]
    if name not in NOISE: return None
    qs = [q for q, _ in paulis]
    if name == 'DEPOLARIZE2':
        if len(qs) == 2 and frozenset(qs) in tset: return off
        if len(qs) == 1 and any(qs[0] in pr for pr in tset): return off
        return None
    return off if (len(qs) == 1 and qs[0] in tset) else None


def flips(c, faults):
    """faults: list of (abs_offset, paulis).  Returns list of ints: detector bits | observable bits << D."""
    B = len(faults)
    if B == 0: return []
    by_off = collections.defaultdict(list)
    for s, (off, paulis) in enumerate(faults):
        by_off[off].append((s, paulis))
    sim = stim.FlipSimulator(batch_size=B, num_qubits=c.num_qubits, disable_stabilizer_randomization=True)
    for i, ins in enumerate(c):
        if ins.name in NOISE:
            if i in by_off:
                for P in 'XYZ':
                    m = np.zeros((c.num_qubits, B), dtype=bool); hit = False
                    for s, paulis in by_off[i]:
                        for q, pp in paulis:
                            if pp == P: m[q, s] = True; hit = True
                    if hit: sim.broadcast_pauli_errors(pauli=P, mask=m)
            continue
        sim.do(ins)
    D, K = c.num_detectors, c.num_observables
    det = sim.get_detector_flips(); obs = sim.get_observable_flips()
    out = []
    for s in range(B):
        bits = np.concatenate([det[:, s], obs[:, s]])
        out.append(int.from_bytes(np.packbits(bits, bitorder='little').tobytes(), 'little'))
    return out


def _bitint(col, D):
    v = 0
    for d in col[0]: v |= 1 << d
    for o in col[1]: v |= 1 << (D + o)
    return v


# ---------------------------------------------------------------- families
def det_shift_maps(n, c):
    """List over torus shifts g of an array mapping detector index -> index of the translated detector."""
    code = BBCode(n); l, m = code.l, code.m
    co = c.get_detector_coordinates()
    idx = {tuple(int(round(x)) for x in v): k for k, v in co.items()}
    maps = []
    for a in range(l):
        for b in range(m):
            mp = np.empty(len(co), dtype=np.int64)
            for k, v in co.items():
                i, typ, t = (int(round(x)) for x in v)
                ix, iy = divmod(i, m); j = ((ix + a) % l) * m + (iy + b) % m
                mp[k] = idx[(j, typ, t)]
            maps.append(mp)
    return maps


def canonical(fs, maps):
    """Canonical form of a fault set (iterable of (dets, obs)) under torus translations (detectors only)."""
    best = None
    for mp in maps:
        f = tuple(sorted(tuple(sorted(int(mp[d]) for d in dets)) for dets, _ in fs))
        if best is None or f < best: best = f
    return best


def cycle_span(fs, locs):
    """Smallest number of consecutive cycles that contain one physical representative of every column."""
    cyc = [sorted({l[0] for l in locs[col]}) for col in fs]
    allc = sorted(set().union(*map(set, cyc)))
    for s in range(1, len(allc) + 2):
        for w in range(min(allc), max(allc) + 1):
            if all(any(w <= x < w + s for x in cs) for cs in cyc): return s
    return None


# -------------------------------------------------------------- exact test
ORDER = {'broken': 0, 'detected': 1, 'trivial': 2, 'unresolved': 3, 'survives': 4}


def candidates(fs, locs, src, dst, sh, ok_cycles=None):
    """per column: list of (offset in dst, paulis, offset in src) of shifted representatives that are
    fault locations of both circuits; None if some column has none (cannot be placed)."""
    per_col = []
    for col in fs:
        cand = []
        for l in locs[col]:
            if ok_cycles is not None and (l[0] + sh) not in ok_cycles: continue
            o_s, o_d = placeable(src, l, sh), placeable(dst, l, sh)
            if o_s is not None and o_d is not None: cand.append((o_d, l[2], o_s))
        if not cand: return None
        per_col.append(cand)
    return per_col


def status_from(opts, D, K, cap=200_000):
    """opts: per column, set of (src_bits | dst_bits << W).  Status of the best representative choice."""
    W = D + K; DM = (1 << D) - 1; mask = (1 << W) - 1
    reach = {0}
    for o in opts:
        reach = {r ^ x for r in reach for x in o}
        if len(reach) > cap: return 'unresolved'
    ok_src = [r >> W for r in reach if not (r & mask) & DM and (r & mask) >> D]
    if not ok_src: return None                                   # not an S logical here (boundary)
    if any(not (d & DM) and d >> D for d in ok_src): return 'survives'
    if any(not (d & DM) for d in ok_src): return 'trivial'
    return 'detected'


def transfer(fs, locs, src, dst, shifts=(0,), dst_ok_cycles=None, cap=200_000):
    """Exact test of path `fs` (columns of circuit `src`, physical reps `locs`) inside circuit `dst`:
    over every time shift and every choice of representatives that is an undetected logical in src,
    is some choice an undetected logical in dst?  Returns (status, shift):
      'survives'  undetected and logical in dst          'detected'  every choice trips a detector in dst
      'trivial'   undetected but no logical flip in dst   'broken'    cannot be placed (by construction)
      'unresolved' too many choices (counted as surviving)"""
    D, K = src.num_detectors, src.num_observables; W = D + K
    best = 'broken', None
    for sh in shifts:
        pc = candidates(fs, locs, src, dst, sh, dst_ok_cycles)
        if pc is None: continue
        flat = [x for cand in pc for x in cand]
        fs_ = flips(src, [(o, p) for _, p, o in flat]); fd_ = flips(dst, [(o, p) for o, p, _ in flat])
        opts, k = [], 0
        for cand in pc:
            opts.append({fs_[k + j] | (fd_[k + j] << W) for j in range(len(cand))}); k += len(cand)
        st = status_from(opts, D, K, cap)
        if st is None: continue
        if ORDER[st] > ORDER[best[0]]: best = st, sh
        if st == 'survives': break
    return best
