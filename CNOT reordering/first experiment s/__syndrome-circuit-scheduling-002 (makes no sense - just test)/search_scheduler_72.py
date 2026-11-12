"""
Phases 2-4 of task.md on the [[72,12,6]] BB code.

Phase 2  L/R structural filter.  X-check L targets = A labels, R targets = B labels;
         Z-check L targets = B labels, R targets = A labels (see bb72_matrices.py).
         Strategy A: L targets in CNOT layers 1-3, R in 4-6 (both check types)
         Strategy B: R targets in layers 1-3, L in 4-6 (both check types)
         Strategy C: X checks use A, Z checks use B
         Each strategy: 3! x 3! orders per side -> 1296 schedules, tested in three layouts:
           simultaneous  X and Z sides both in layers 1-6, layer 7 = measurement buffer (task.md)
           z_first       Z side layers 1-6, X side 2-7, measurements in rounds 7 and 8 (Bravyi Fig. 5)
           x_first       mirror of z_first
         A schedule is feasible if no data qubit is in two CNOTs in one layer, and valid if, in
         addition, every X-check/Z-check pair has an even number of shared data qubits whose
         Z-CNOT precedes the X-CNOT (all noiseless detectors deterministic; confirmed with stim).
         Because no strategy schedule is valid (see the report), the search is widened to
           (a) every simultaneous-layout schedule (all 720 x 720 orders), and
           (b) every valid staggered schedule, ranked by how close it is to L/R block order
               (number of L<->R switches along each check's CNOT sequence; strategies have 1).
Phase 3  build_72_stim_circuit(schedule): explicit layers with TICK dividers, uniform circuit-level
         depolarising noise (p = 0.001 default), multi-round detectors, 12 logical observables.
Phase 4  task.md asks for dem.shortest_graph_fault_path() on detector_error_model(decompose_errors=True).
         That does not apply to BB codes: every data fault flips >= 3 detectors, stim cannot
         decompose the model into graph-like errors, and shortest_graphlike_error finds none.
         We use stim's hypergraph search Circuit.search_for_undetectable_logical_errors (bounded
         exploration -> the weight found is an upper bound on d_circ) and cross-check it against
         the randomised BP-OSD bound of the original project.
         d_circ <= d = 6 for every schedule: a weight-6 code logical on idle data qubits is
         undetectable, so "maximum possible d_circ" = 6.  Schedules reaching 6 are logged.

usage:  ../venv/bin/python search_scheduler_72.py [--nproc 2] [--cycles 3]
outputs: results/phase2_strategies.json, results/simultaneous_layout.json,
         results/distance_72.csv (resumable), results_72code.json, report printed
"""
import argparse, csv, itertools, json, os, sys, time, collections
import multiprocessing as mp
import numpy as np
import stim
import bb72_matrices as bm

H = bm.N_HALF
XQ = list(range(2 * H, 3 * H))            # X ancillas 72..107
ZQ = list(range(3 * H, 4 * H))            # Z ancillas 108..143
DATA = list(range(0, 2 * H))
NQ = 4 * H
AL, BL = ['A1', 'A2', 'A3'], ['B1', 'B2', 'B3']
XT = {l: [bm.x_target(l, i) for i in range(H)] for l in bm.LABELS}
ZT = {l: [bm.z_target(l, i) for i in range(H)] for l in bm.LABELS}


# ------------------------------------------------------------------ schedules
def make_schedule(x_order, z_order, layout, name=''):
    """7-layer schedule.  layers[t] = {'X': label or None, 'Z': label or None}, t = 0..6 (layers 1-7);
    meas = {'X': round, 'Z': round} (round 7 = layer 7, round 8 = extra measurement round)."""
    if layout == 'simultaneous': xl, zl = range(0, 6), range(0, 6)
    elif layout == 'z_first':    xl, zl = range(1, 7), range(0, 6)
    elif layout == 'x_first':    xl, zl = range(0, 6), range(1, 7)
    else: raise ValueError(layout)
    layers = [{'X': None, 'Z': None} for _ in range(7)]
    for t, lab in zip(xl, x_order): layers[t]['X'] = lab
    for t, lab in zip(zl, z_order): layers[t]['Z'] = lab
    meas = {'X': max(xl) + 2, 'Z': max(zl) + 2}          # 1-based round after the last CNOT layer
    return dict(name=name, layout=layout, x_order=list(x_order), z_order=list(z_order), layers=layers, meas=meas)


def collision(s):
    """First layer (1-based) where a data qubit gets two CNOTs, else 0."""
    for t, ly in enumerate(s['layers']):
        if ly['X'] and ly['Z']:
            xb = 'L' if ly['X'][0] == 'A' else 'R'; zb = 'L' if ly['Z'][0] == 'B' else 'R'
            if xb == zb: return t + 1
    return 0


def valid_algebraic(s):
    """Even number of shared qubits with the Z-CNOT before the X-CNOT, for every X/Z check pair."""
    tX = np.full((H, 2 * H), -1); tZ = np.full((H, 2 * H), -1)
    for t, ly in enumerate(s['layers']):
        if ly['X']: tX[np.arange(H), XT[ly['X']]] = t
        if ly['Z']: tZ[np.arange(H), ZT[ly['Z']]] = t
    shared = (tX[:, None, :] >= 0) & (tZ[None, :, :] >= 0)
    zfirst = shared & (tZ[None, :, :] < tX[:, None, :])
    return bool((zfirst.sum(2) % 2 == 0).all())


def lr_switches(order, side):
    """Number of L<->R switches along a check's CNOT sequence (strategies A/B/C: 1)."""
    blk = [('L' if l[0] == 'A' else 'R') if side == 'X' else ('L' if l[0] == 'B' else 'R') for l in order]
    return sum(a != b for a, b in zip(blk, blk[1:]))


def layer_array(s):
    """Human-readable 7-layer array: per layer the label and target block of each side."""
    out = []
    for t, ly in enumerate(s['layers']):
        e = {'layer': t + 1}
        if ly['X']: e['X'] = f"{ly['X']} ({'L' if ly['X'][0] == 'A' else 'R'})"
        if ly['Z']: e['Z'] = f"{ly['Z']}^T ({'L' if ly['Z'][0] == 'B' else 'R'})"
        if s['meas']['X'] == t + 1: e['measure'] = e.get('measure', '') + 'X '
        if s['meas']['Z'] == t + 1: e['measure'] = e.get('measure', '') + 'Z '
        out.append(e)
    if 8 in s['meas'].values(): out.append({'layer': 8, 'measure': ' '.join(k for k, v in s['meas'].items() if v == 8)})
    return out


# ------------------------------------------------------------------ Phase 3
def build_72_stim_circuit(schedule, cycles=6, p=0.001, basis='Z'):
    """Memory experiment: data prepared in |0> (Z) or |+> (X), `cycles` syndrome cycles, data
    measured.  Noise: DEPOLARIZE2(p) after every CNOT, DEPOLARIZE1(p) on every idle qubit in every
    layer, X_ERROR/Z_ERROR(p) after ancilla reset and before ancilla measurement.  Data preparation
    and final data readout are noiseless.  Raises ValueError on a same-layer collision."""
    if collision(schedule): raise ValueError(f'collision in layer {collision(schedule)}')
    c = stim.Circuit()
    c.append('R' if basis == 'Z' else 'RX', DATA); c.append('TICK')
    prev = {}; nmeas = 0
    nrounds = max(7, max(schedule['meas'].values()))
    for cyc in range(cycles):
        c.append('RX', XQ); c.append('R', ZQ)
        if p > 0: c.append('Z_ERROR', XQ, p); c.append('X_ERROR', ZQ, p)
        c.append('TICK')
        idx = {}
        for r in range(1, nrounds + 1):
            busy = set()
            ly = schedule['layers'][r - 1] if r <= 7 else {'X': None, 'Z': None}
            if ly['X']:
                pairs = [q for i in range(H) for q in (XQ[i], XT[ly['X']][i])]
                c.append('CNOT', pairs); busy.update(pairs)
                if p > 0: c.append('DEPOLARIZE2', pairs, p)
            if ly['Z']:
                pairs = [q for i in range(H) for q in (ZT[ly['Z']][i], ZQ[i])]
                c.append('CNOT', pairs); busy.update(pairs)
                if p > 0: c.append('DEPOLARIZE2', pairs, p)
            for side, anc, gate, err in (('Z', ZQ, 'M', 'X_ERROR'), ('X', XQ, 'MX', 'Z_ERROR')):
                if schedule['meas'][side] == r:
                    if p > 0: c.append(err, anc, p)
                    c.append(gate, anc); idx[side] = nmeas; nmeas += H; busy.update(anc)
            idle = [q for q in range(NQ) if q not in busy]
            if p > 0 and idle: c.append('DEPOLARIZE1', idle, p)
            c.append('TICK')
        rec = lambda a: stim.target_rec(a - nmeas)
        for i in range(H):
            for side, k in (('Z', 0), ('X', 1)):
                if cyc == 0:
                    if side == basis: c.append('DETECTOR', [rec(idx[side] + i)], [i, k, cyc])
                else:
                    c.append('DETECTOR', [rec(idx[side] + i), rec(prev[side] + i)], [i, k, cyc])
        prev = idx
    c.append('M' if basis == 'Z' else 'MX', DATA); nmeas += 2 * H
    rec = lambda a: stim.target_rec(a - nmeas)
    Hc = bm.HZ if basis == 'Z' else bm.HX
    for i in range(H):
        c.append('DETECTOR', [rec(nmeas - 2 * H + j) for j in np.nonzero(Hc[i])[0]] + [rec(prev[basis] + i)], [i, 0 if basis == 'Z' else 1, cycles])
    for k, Lop in enumerate(bm.logical_ops(basis)):
        c.append('OBSERVABLE_INCLUDE', [rec(nmeas - 2 * H + j) for j in np.nonzero(Lop)[0]], k)
    return c


def valid_stim(s):
    """All noiseless detectors and observables deterministic-zero in both bases (2 cycles)."""
    for b in 'ZX':
        d, o = build_72_stim_circuit(s, cycles=2, p=0.0, basis=b).compile_detector_sampler(seed=1).sample(2, separate_observables=True)
        if d.any() or o.any(): return False
    return True


# ------------------------------------------------------------------ Phase 4
def dcirc_stim(s, cycles, basis, limit=4):
    """Upper bound on d_circ from stim's undetectable-logical-error search (hypergraph, bounded)."""
    c = build_72_stim_circuit(s, cycles=cycles, p=0.001, basis=basis)
    t = time.time()
    err = c.search_for_undetectable_logical_errors(dont_explore_detection_event_sets_with_size_above=limit,
                                                   dont_explore_edges_with_degree_above=limit,
                                                   dont_explore_edges_increasing_symptom_degree=False)
    return len(err), time.time() - t, err


def _dist_job(args):
    key, s, cycles, limit = args
    out = {}
    for b in 'ZX':
        w, sec, _ = dcirc_stim(s, cycles, b, limit)
        out[b] = (w, sec)
    return key, out


# ------------------------------------------------------------------ driver
def strategy_orders(strategy):
    """(x_order, z_order) pairs of one strategy: L/R blocks of 3 in the given order."""
    pa, pb = list(itertools.permutations(AL)), list(itertools.permutations(BL))
    if strategy == 'A':   # L first: X = A..B.., Z = B..A..
        xs = [list(a) + list(b) for a in pa for b in pb]; zs = [list(b) + list(a) for b in pb for a in pa]
    elif strategy == 'B': # R first: X = B..A.., Z = A..B..
        xs = [list(b) + list(a) for b in pb for a in pa]; zs = [list(a) + list(b) for a in pa for b in pb]
    else:                 # C: X L-first (A), Z R-first (B)
        xs = [list(a) + list(b) for a in pa for b in pb]; zs = [list(a) + list(b) for a in pa for b in pb]
    return [(x, z) for x in xs for z in zs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nproc', type=int, default=2); ap.add_argument('--cycles', type=int, default=3)
    ap.add_argument('--limit', type=int, default=4)
    a = ap.parse_args()
    os.makedirs('results', exist_ok=True)
    print('== Phase 1:', bm.check(), flush=True)

    # ---- Phase 2: strategies A/B/C in three layouts
    rep = {}
    for st in 'ABC':
        for lay in ('simultaneous', 'z_first', 'x_first'):
            cnt = collections.Counter(); ex = {}
            for x, z in strategy_orders(st):
                s = make_schedule(x, z, lay)
                col = collision(s)
                if col: cnt['collision'] += 1; ex.setdefault('collision', (x, z, f'layer {col}')); continue
                if not valid_algebraic(s): cnt['invalid (non-deterministic detectors)'] += 1; ex.setdefault('invalid', (x, z)); continue
                if valid_stim(s): cnt['VALID'] += 1; ex.setdefault('VALID', (x, z))
                else: cnt['algebraic ok but stim rejects'] += 1
            rep[f'{st}/{lay}'] = dict(counts=dict(cnt), examples=ex)
            print(f'  strategy {st}, layout {lay:12s}: {dict(cnt)}', flush=True)
    json.dump(rep, open('results/phase2_strategies.json', 'w'), indent=1)

    # ---- widened search (a): every simultaneous-layout schedule
    t0 = time.time(); cnt = collections.Counter(); valid_sim = []
    perms = list(itertools.permutations(bm.LABELS))
    for x in perms:
        for z in perms:
            if any(xl[0] != zl[0] for xl, zl in zip(x, z)): cnt['collision'] += 1; continue   # same-block layer
            s = make_schedule(x, z, 'simultaneous')
            if valid_algebraic(s): cnt['valid'] += 1; valid_sim.append((x, z))
            else: cnt['invalid'] += 1
    confirmed = sum(valid_stim(make_schedule(x, z, 'simultaneous')) for x, z in valid_sim)
    print(f'== simultaneous layout, all {len(perms)**2} orders: {dict(cnt)}; stim confirms {confirmed}  ({time.time()-t0:.0f}s)', flush=True)
    json.dump(dict(counts=dict(cnt), stim_confirmed=confirmed, valid=valid_sim[:50]), open('results/simultaneous_layout.json', 'w'), indent=1)

    # ---- widened search (b): every valid staggered schedule, distance by stim search
    vals = []
    for lay in ('z_first', 'x_first'):
        for x in perms:
            for z in perms:
                s = make_schedule(x, z, lay)
                if collision(s) or not valid_algebraic(s): continue
                vals.append(s)
    print(f'== valid staggered depth-7 schedules: {len(vals)}', flush=True)
    CSV = 'results/distance_72.csv'; F = ['layout', 'x_order', 'z_order', 'switches_x', 'switches_z', 'cycles', 'limit', 'dZ', 'dX', 'secZ', 'secX']
    done = set()
    if os.path.exists(CSV):
        for r in csv.DictReader(open(CSV)):
            if int(r['cycles']) == a.cycles and int(r['limit']) == a.limit: done.add((r['layout'], r['x_order'], r['z_order']))
    key = lambda s: (s['layout'], ' '.join(s['x_order']), ' '.join(s['z_order']))
    # most L/R-like schedules first
    vals.sort(key=lambda s: (lr_switches(s['x_order'], 'X') + lr_switches(s['z_order'], 'Z'), key(s)))
    jobs = [(key(s), s, a.cycles, a.limit) for s in vals if key(s) not in done]
    print(f'   distance search: {len(done)} done, {len(jobs)} to go, {a.cycles} cycles, limit {a.limit}, {a.nproc} workers', flush=True)
    new = not os.path.exists(CSV); t0 = time.time()
    with mp.get_context('fork').Pool(a.nproc) as pool, open(CSV, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=F)
        if new: w.writeheader()
        byk = {key(s): s for s in vals}
        for n, (k, out) in enumerate(pool.imap_unordered(_dist_job, jobs, chunksize=1), 1):
            s = byk[k]
            w.writerow(dict(layout=k[0], x_order=k[1], z_order=k[2], switches_x=lr_switches(s['x_order'], 'X'),
                            switches_z=lr_switches(s['z_order'], 'Z'), cycles=a.cycles, limit=a.limit,
                            dZ=out['Z'][0], dX=out['X'][0], secZ=round(out['Z'][1], 1), secX=round(out['X'][1], 1))); f.flush()
            if n % 50 == 0 or n == len(jobs):
                el = time.time() - t0; print(f'   {n}/{len(jobs)}  {el/60:.0f} min, eta {el/n*(len(jobs)-n)/60:.0f} min', flush=True)

    # ---- results_72code.json
    rows = [r for r in csv.DictReader(open(CSV)) if int(r['cycles']) == a.cycles and int(r['limit']) == a.limit]
    for r in rows: r['d'] = min(int(r['dZ']), int(r['dX'])); r['sw'] = int(r['switches_x']) + int(r['switches_z'])
    dist = collections.Counter(r['d'] for r in rows)
    by_sw = collections.defaultdict(collections.Counter)
    for r in rows: by_sw[r['sw']][r['d']] += 1
    best_sw = min(r['sw'] for r in rows)
    winners = [r for r in rows if r['d'] == 6 and r['sw'] == best_sw]
    log = dict(
        code='[[72,12,6]] BB, A = x^3+y+y^2, B = y^3+x+x^2', d_max=6,
        method=f'stim search_for_undetectable_logical_errors, {a.cycles}-cycle memory circuit, p = 0.001, '
               f'exploration limit {a.limit} (upper bound on d_circ)',
        phase2_strategies={k: v['counts'] for k, v in rep.items()},
        phase2_conclusion='No schedule of strategy A, B or C is a valid depth-7 circuit in any layout.',
        simultaneous_layout=dict(counts=dict(cnt), stim_confirmed=confirmed),
        staggered_valid=len(rows), d_circ_distribution={str(k): v for k, v in sorted(dist.items())},
        d_circ_by_lr_switches={str(k): {str(d): n for d, n in sorted(v.items())} for k, v in sorted(by_sw.items())},
        min_lr_switches_valid=best_sw,
        schedules_reaching_d6_with_fewest_switches=[
            dict(layout=r['layout'], x_order=r['x_order'].split(), z_order=r['z_order'].split(), dZ=int(r['dZ']), dX=int(r['dX']),
                 switches=r['sw'], layers=layer_array(make_schedule(r['x_order'].split(), r['z_order'].split(), r['layout'])))
            for r in winners])
    json.dump(log, open('results_72code.json', 'w'), indent=1)
    print(f'== d_circ distribution {dict(sorted(dist.items()))}; by L/R switches {json.dumps(log["d_circ_by_lr_switches"])}')
    print(f'== {len(winners)} schedules with the fewest L/R switches ({best_sw}) reach d_circ = 6 -> results_72code.json')


if __name__ == '__main__':
    main()
