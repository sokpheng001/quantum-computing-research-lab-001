"""Shared helpers for saved min-weight fault sets (results/faultsets/<n>_<basis>_<spec>.json).

A fault key is (detector ids, observable ids) of a merged DEM column; it is the same
object in every schedule's circuit (detector i of cycle t has a fixed index), so sets
of different schedules can be intersected.  "Core" keys are those that occur in the
min-weight sets of more than half of all single schedules: these are the
schedule-independent paths (e.g. a weight-d code logical applied in one idle slot)
that give the trivial bound d_circ <= d.  A min-weight set is *nontrivial* if it
contains at least one non-core key; nontrivial sets are what a schedule adds."""
import json, os, collections

def load_sets(n, basis, spec):
    f = f'results/faultsets/{n}_{basis}_{spec}.json'
    if not os.path.exists(f):
        return None
    return [frozenset((tuple(d), tuple(o)) for d, o in st) for st in json.load(open(f))['sets']]

def core_keys(n, basis, ids, frac=0.5):
    """Keys present in the min-weight sets of more than `frac` of the schedules `ids`."""
    cnt = collections.Counter(); m = 0
    for s in ids:
        sets = load_sets(n, basis, s)
        if sets is None: continue
        m += 1
        cnt.update(set().union(*sets) if sets else set())
    return {k for k, c in cnt.items() if c > frac * m}

def specific_keys(sets, core):
    """Union of the keys of the nontrivial sets, minus the core."""
    out = set()
    for st in sets:
        if not st <= core:
            out |= (st - core)
    return out

def n_nontrivial(sets, core):
    return sum(1 for st in sets if not st <= core)
