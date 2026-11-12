"""Test 3, step 0b: WHY no cs circuit fits G6's data layout with G6's code.

An ancilla on the square grid can only interact with the data qubits around its own
grid point. So every ancilla/flag of a circuit needs a grid point whose data
neighbours include the data it talks to. In code terms, every group of data qubits is
one of three kinds (7-qubit code = Fano plane, 7 "lines" of 3 qubits):

  * "logical"     - 3 qubits forming a line = a weight-3 logical operator
  * "stabiliser"  - 4 qubits forming a weight-4 stabiliser
  * "partial"     - 3 qubits inside a weight-4 stabiliser (not a line)

The script lists (1) what G6's layout offers: for every free grid point, the kind of
data group around it, and (2) what each cs circuit needs: for every non-data qubit,
the kind of data group it interacts with directly. A needed kind that the layout never
offers is an obstruction no placement can remove.

    .venv/bin/python "qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6/diagnose_g6_fit.py"
    -> results/g6_diagnosis.json
"""
import itertools
import json
import os
import sys
from collections import Counter
from pathlib import Path

import stim

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
os.chdir(ROOT)

from check_g6_fit import g6_layout, weight4_elements  # noqa: E402

from nnflags.continuing_data import data_qubits  # noqa: E402
from nnflags.willow import WILLOW, neighbours  # noqa: E402

RES = HERE / "results"


def kind(group, w4):
    """Kind of a set of data qubits in a code given by its weight-4 stabiliser sets."""
    g = frozenset(group)
    if len(g) == 4:
        return "stabiliser" if g in w4 else "other-4"
    if len(g) == 3:
        return "partial" if any(g < s for s in w4) else "logical"
    return f"{len(g)} data"


def g6_offer():
    g, co, data, code = g6_layout()
    pos = {co[q] for q in data}
    w4 = set(code["X"])
    offer = {}
    for p in sorted(WILLOW):
        if p in pos:
            continue
        nb = frozenset(n for n in neighbours(p) if n in pos)
        if len(nb) >= 2:
            subs = sorted({kind(s, w4) for k in range(3, len(nb) + 1) for s in itertools.combinations(nb, k)})
            offer[p] = dict(data=sorted(nb), kind=kind(nb, w4), contains=subs)
    return offer, w4


def needs(name, inner, full):
    d = data_qubits(inner)
    w4 = weight4_elements(full, "X")
    adj = {}
    for op in inner.flattened():
        if op.name in ("CX", "CZ"):
            t = [x.value for x in op.targets_copy()]
            for a, b in zip(t[::2], t[1::2]):
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)
    out = {}
    for q in sorted(adj):
        if q in d:
            continue
        dn = adj[q] & d
        out[q] = dict(data=sorted(dn), kind=kind(dn, w4), non_data_partners=sorted(adj[q] - d))
    return out


def requirement_check(offer, name="cs02", f="results/continuing/success02"):
    """For each of the 168 code-preserving maps of cs02's data onto G6's data positions:
    which non-data qubits find a free grid point adjacent to all of their data
    (requirements checked one by one, ignoring that two qubits cannot share a point)."""
    g, co, g6data, code = g6_layout()
    pos = sorted(co[q] for q in g6data)
    W4 = set(code["X"])
    inner, full = stim.Circuit.from_file(f + ".inner.stim"), stim.Circuit.from_file(f + ".full.stim")
    d = sorted(data_qubits(inner))
    w4 = weight4_elements(full, "X")
    need = needs(name, inner, full)
    free = [p for p in WILLOW if p not in set(pos)]
    fails, examples = Counter(), {}
    best = None
    for perm in itertools.permutations(pos):
        m = dict(zip(d, perm))
        if not all(frozenset(m[q] for q in s) in W4 for s in w4):
            continue
        f_here = [q for q, v in need.items()
                  if not any({m[x] for x in v["data"]} <= set(neighbours(p)) for p in free)]
        for q in f_here:
            fails[q] += 1
        key = tuple(f_here)
        examples.setdefault(key, {str(k): v for k, v in m.items()})
        if best is None or len(f_here) < len(best):
            best = f_here
    print(f"{name}, 168 code-preserving maps: maps where qubit q has NO grid point next to all its data: "
          + ", ".join(f"q{q} ({need[q]['data']}, {need[q]['kind']}): {n}" for q, n in sorted(fails.items())))
    print(f"  fewest failing qubits over all maps: {best}")
    for key, ex in sorted(examples.items(), key=lambda kv: len(kv[0]))[:3]:
        print(f"  failing {list(key)} e.g. data map {ex}")
    return dict(fail_counts={str(q): n for q, n in fails.items()}, fewest=best,
                examples={",".join(map(str, k)): v for k, v in examples.items()})


def main():
    RES.mkdir(exist_ok=True)
    offer, _ = g6_offer()
    print("What G6's layout offers (free grid points with >= 2 data neighbours):")
    for p, o in offer.items():
        print(f"  {p}: {len(o['data'])} data, kind {o['kind']}, 3-subsets: {o['contains']}")
    offered = Counter(k for o in offer.values() for k in o["contains"] + [o["kind"]])
    print(f"  kinds offered: {dict(offered)}")
    report = dict(g6_offer={str(p): o for p, o in offer.items()}, circuits={})
    for i in range(10):
        f = f"results/continuing/success{i:02d}"
        inner, full = stim.Circuit.from_file(f + ".inner.stim"), stim.Circuit.from_file(f + ".full.stim")
        n = needs(f"cs{i:02d}", inner, full)
        bad = {q: v for q, v in n.items() if v["kind"] in ("logical", "other-4")}
        report["circuits"][f"cs{i:02d}"] = dict(needs={str(q): v for q, v in n.items()},
                                                kinds_not_offered={str(q): v for q, v in bad.items()})
        print(f"cs{i:02d}: " + "; ".join(f"q{q} -> data {v['data']} ({v['kind']})" for q, v in n.items()))
        if bad:
            print(f"       NOT offered by G6's layout: " + ", ".join(f"q{q} needs a {v['kind']} group" for q, v in bad.items()))
    report["cs02_requirement_check"] = requirement_check(offer)
    (RES / "g6_diagnosis.json").write_text(json.dumps(report, indent=1, default=list))
    print(RES / "g6_diagnosis.json")


if __name__ == "__main__":
    main()
