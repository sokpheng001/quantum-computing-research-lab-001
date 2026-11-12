"""Verification STEP 3: exact check of the single schedule's min-weight fault sets inside the
alternating circuit.

For every saved fault set of the single-schedule circuit (DEM columns keyed by
(detectors, observables)), stim's error explanation lists the physical fault locations of
each column: tick, instruction offset, gate, Pauli product, flipped measurement.  A set is
mappable if every column has at least one location in a cycle where the alternating circuit
runs the same schedule (alt cycle t uses schedules[t % 2], so cycles 0, 2, ...) AND the
instruction at that offset is identical in both circuits (checked).  For mappable sets the
detector/observable flips of the same physical faults in the alternating circuit are taken
from the alternating circuit's own error explanation, i.e. computed exactly.  When a column
has several physical representatives, every combination is checked: the set counts as
"undetected and logical in alt" if ANY choice flips no detector and at least one observable.

usage: step3_exact.py --single 212 --alt 212+1307 --basis Z --weight 10
                      [--sets results/strong_sets_144.jsonl | --sets results/faultsets/144_Z_744.json]
"""
import argparse, json, collections, datetime
from bb_code import BBCode, memory_circuit
from sched_ids import table

ap = argparse.ArgumentParser()
ap.add_argument('--single', default='212'); ap.add_argument('--alt', default='212+1307'); ap.add_argument('--basis', required=True)
ap.add_argument('--weight', type=int, default=10); ap.add_argument('--cycles', type=int, default=4)
ap.add_argument('--sets', default='results/strong_sets_144.jsonl'); ap.add_argument('--n', type=int, default=144)
ap.add_argument('--cap', type=int, default=2_000_000)
a = ap.parse_args()
code = BBCode(a.n); T = table()
alt_ids = [int(i) for i in a.alt.split('+')]; single = int(a.single)
cS = memory_circuit(code, [T[single]], a.cycles, 0.001, a.basis)
cA = memory_circuit(code, [T[i] for i in alt_ids], a.cycles, 0.001, a.basis)
D = cS.num_detectors; assert D == cA.num_detectors and cS.num_ticks == cA.num_ticks
TPC = (cS.num_ticks - 1) // a.cycles                     # ticks per cycle (1 prep tick)
same_cycles = {t for t in range(a.cycles) if alt_ids[t % len(alt_ids)] == single}

def cycle_of(tick): return (tick - 1) // TPC
def lkey(loc):
    m = loc.flipped_measurement
    return (loc.tick_offset, loc.stack_frames[-1].instruction_offset, loc.instruction_targets.gate,
            tuple(sorted(str(p.gate_target) for p in loc.flipped_pauli_product)), m.record_index if m is not None else None)
def symkey(terms):
    dets = tuple(sorted(t.dem_target.val for t in terms if t.dem_target.is_relative_detector_id()))
    obs = tuple(sorted(t.dem_target.val for t in terms if t.dem_target.is_logical_observable_id()))
    return dets, obs
def explain(c):
    col2locs, loc2sym = collections.defaultdict(list), {}
    for e in c.explain_detector_error_model_errors(reduce_to_one_representative_error=False):
        k = symkey(e.dem_error_terms)
        for loc in e.circuit_error_locations:
            col2locs[k].append(loc); loc2sym[lkey(loc)] = k
    return col2locs, loc2sym
colS, _ = explain(cS); _, symA = explain(cA)
def bits(k): return sum(1 << d for d in k[0]) | sum(1 << (D + o) for o in k[1])
DMASK = (1 << D) - 1

# ---- load sets
if a.sets.endswith('.jsonl'):
    raw = [json.loads(l) for l in open(a.sets)]
    raw = [r['set'] for r in raw if r['circuit'] == a.single and r['basis'] == a.basis and r['weight'] == a.weight]
else:
    d = json.load(open(a.sets)); raw = [s for s in d['sets'] if len(s) == a.weight]
sets = sorted({tuple(sorted((tuple(x[0]), tuple(x[1])) for x in s)) for s in raw})
print(f'{a.single} vs alt {a.alt}, basis {a.basis}, {a.cycles} cycles: {len(sets)} distinct weight-{a.weight} sets; '
      f'alt runs {a.single} in cycles {sorted(same_cycles)}', flush=True)

res = collections.Counter(); details = []
for s in sets:
    # sanity: in the single-schedule circuit the set is undetected and logical
    tot = 0
    for col in s: tot ^= bits(col)
    if tot & DMASK or not tot >> D:
        res['BAD: not an undetected logical in the single circuit'] += 1; continue
    opts = []
    for col in s:
        locs = [l for l in colS.get(col, []) if cycle_of(l.tick_offset) in same_cycles]
        o = set()
        for l in locs:
            off = l.stack_frames[-1].instruction_offset
            if cS[off] != cA[off]: continue                      # instruction must be identical in alt
            k = symA.get(lkey(l))
            if k is not None: o.add(bits(k))
        opts.append(o)
    cyc = sorted({cycle_of(l.tick_offset) for col in s for l in colS.get(col, [])})
    if any(not o for o in opts):
        res['not mappable (uses cycles where alt runs the other schedule)'] += 1
        details.append(dict(set=s, status='not mappable', cycles=cyc)); continue
    reach = {0}; capped = False
    for o in opts:
        reach = {r ^ x for r in reach for x in o}
        if len(reach) > a.cap: capped = True; break
    if capped:
        res['mappable, too many representative choices (unresolved)'] += 1; continue
    und = [r for r in reach if not r & DMASK]
    logical = any(r >> D for r in und)
    st = ('mappable: UNDETECTED and LOGICAL in alt' if logical else
          'mappable: undetected but no logical flip in alt' if und else 'mappable: now DETECTED in alt (every choice)')
    res[st] += 1
    details.append(dict(set=s, status=st, cycles=cyc, n_choices=len(reach)))
print('\n'.join(f'  {v:5d}  {k}' for k, v in sorted(res.items(), key=lambda kv: kv[0])))
out = f'results/step3_{a.n}_{a.basis}_{a.single}_w{a.weight}.json'
json.dump(dict(date=str(datetime.date.today()), args=vars(a), counts=dict(res),
               details=[dict(d, set=[[list(x[0]), list(x[1])] for x in d['set']]) for d in details]), open(out, 'w'))
print('written', out)
