"""Test 6, step 4: is the circuit Google RAN the circuit we used as our baseline?

Compares the released stim circuits (Zenodo, as run on Willow) with the circuits we built from the
paper's Crumble links (nnflags/data/google_circuits/rosenfeld2512_G*.stim):
    fig2/cultivation [X]          vs  G4  (our baseline; its double check = TICKs 31-56)
    fig3/with_idle_rounds         vs  G5  (kickback tomography)
    fig4/cultivation_N=2 [X]      vs  G6  (grafting; source of the "G4 G6-style" rule)
The Z-basis files are the second tomography setting (different basis change, so not expected to equal
the Crumble circuit, which is the X setting); they are reported for completeness.

Comparison, time step by time step (order inside a TICK does not matter; trailing empty / idle-only
TICKs reported separately):
  * gates  : multiset of (gate, qubit or qubit pair) per TICK, tags ignored, and with tags
  * detectors : each detector as the set of absolute measurement indices it combines (coordinate
    labels ignored); the logical observable likewise
Also: the released cirq circuit (real rotations) vs its own stim file: same CZ pairs, same
measurement order, real T / T^dagger (Z**+-0.25) on exactly the qubits stim marks.

Writes results/step4_circuits.json.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t6_common as C  # noqa: E402

OURS = C.ROOT / "nnflags" / "data" / "google_circuits"
PAIRS = [("fig2/cultivation", "X", "G4"), ("fig2/cultivation", "Z", "G4"),
         ("fig3/with_idle_rounds", "X", "G5"), ("fig4/cultivation_N=2", "X", "G6"),
         ("fig4/cultivation_N=2", "Z", "G6")]
SKIP = ("QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "SHIFT_COORDS")


def ticks(c, tags: bool):
    T = [collections.Counter()]
    for i in c.flattened():
        if i.name == "TICK":
            T.append(collections.Counter())
            continue
        if i.name in SKIP:
            continue
        ts = [t.value for t in i.targets_copy()]
        tg = i.tag if tags else ""
        if i.name in ("CZ", "CX"):
            for a, b in zip(ts[::2], ts[1::2]):
                T[-1][(i.name, tg, tuple(sorted((a, b))))] += 1
        else:
            for a in ts:
                T[-1][(i.name, tg, a)] += 1
    return T


def trailing_idle(T):
    """Drop trailing TICKs that hold only identities (idle/echo placeholders) or nothing."""
    n = 0
    while T and all(k[0] == "I" for k in T[-1]):
        T = T[:-1]
        n += 1
    return T, n


def detector_sets(c):
    dets, obs, m = [], collections.defaultdict(set), 0
    for i in c.flattened():
        if i.name in ("M", "MR", "MX", "MY", "MRX", "MPP"):
            m += sum(1 for t in i.targets_copy() if not t.is_combiner)
        elif i.name == "DETECTOR":
            dets.append(frozenset(m + t.value for t in i.targets_copy()))
        elif i.name == "OBSERVABLE_INCLUDE":
            obs[int(i.gate_args_copy()[0])] ^= {m + t.value for t in i.targets_copy()}
    return dets, {k: frozenset(v) for k, v in obs.items()}


def compare(rel, ours) -> dict:
    out = {}
    for tags in (False, True):
        A, na = trailing_idle(ticks(rel, tags))
        B, nb = trailing_idle(ticks(ours, tags))
        diff = [i for i in range(max(len(A), len(B)))
                if (A[i] if i < len(A) else None) != (B[i] if i < len(B) else None)]
        key = "with_tags" if tags else "gates"
        out[key] = dict(ticks=(len(A), len(B)), trailing_idle_ticks_dropped=(na, nb),
                        differing_ticks=diff[:20], n_differing_ticks=len(diff), identical=not diff)
        if diff and not tags:
            i = diff[0]
            a = A[i] if i < len(A) else collections.Counter()
            b = B[i] if i < len(B) else collections.Counter()
            out[key]["first_difference"] = dict(tick=i, released_only=str(dict(a - b)), ours_only=str(dict(b - a)))
    dr, orl = detector_sets(rel)
    do, oo = detector_sets(ours)
    out["detectors"] = dict(n=(len(dr), len(do)), same_set=set(dr) == set(do), same_order=dr == do,
                            observables_same=orl == oo, n_observables=(len(orl), len(oo)))
    out["num_measurements"] = (rel.num_measurements, ours.num_measurements)
    return out


def cirq_vs_stim(exp, basis) -> dict:
    import cirq
    cj, st = C.circuit_files(exp, basis)
    c = C.load_cirq(cj)
    s = C.load_stim(st)
    coord = {}
    for inst in s:
        if inst.name == "QUBIT_COORDS":
            r_, c_ = inst.gate_args_copy()[:2]
            coord[inst.targets_copy()[0].value] = (int(r_), int(c_))
    cz_cirq = sorted(tuple(sorted((x.row, x.col) for x in op.qubits)) for m in c for op in m
                     if isinstance(op.gate, cirq.CZPowGate))
    cz_stim = []
    for inst in s.flattened():
        if inst.name == "CZ":
            t = [x.value for x in inst.targets_copy()]
            cz_stim += [tuple(sorted((coord[x], coord[y]))) for x, y in zip(t[::2], t[1::2])]
    meas_cirq = [(x.row, x.col) for m in c for op in m if cirq.is_measurement(op) for x in op.qubits]
    meas_stim = [coord[x.value] for inst in s.flattened() if inst.name in ("M", "MR", "MX")
                 for x in inst.targets_copy()]
    tq = [(float(op.gate.exponent), (op.qubits[0].row, op.qubits[0].col)) for m in c for op in m
          if isinstance(op.gate, cirq.ZPowGate) and not cirq.is_parameterized(op)
          and float(op.gate.exponent) in (0.25, -0.25)]
    inj = [(str(op.gate.exponent), (op.qubits[0].row, op.qubits[0].col)) for m in c for op in m
           if cirq.is_parameterized(op)]
    return dict(qubits=len(c.all_qubits()), cz_same=cz_cirq == sorted(cz_stim), n_cz=(len(cz_cirq), len(cz_stim)),
                measurement_order_same=meas_cirq == meas_stim, n_measurements=len(meas_cirq),
                real_T=sum(1 for e, _ in tq if e == 0.25), real_T_dagger=sum(1 for e, _ in tq if e == -0.25),
                real_T_qubits=sorted({q for _, q in tq}), injection_rotation=inj)


def main():
    out = {}
    for exp, b, g in PAIRS:
        _, st = C.circuit_files(exp, b)
        r = compare(C.load_stim(st), C.load_stim(OURS / f"rosenfeld2512_{g}.stim"))
        r["cirq_vs_stim"] = cirq_vs_stim(exp, b)
        out[f"{exp} [{b}] vs {g}"] = r
        C.log(f"step 4: {exp} [{b}] vs {g}: gates identical={r['gates']['identical']} "
              f"(differing ticks {r['gates']['n_differing_ticks']}), with tags={r['with_tags']['identical']}, "
              f"detectors same={r['detectors']['same_set']}, observable same={r['detectors']['observables_same']}, "
              f"cirq vs stim: CZ {r['cirq_vs_stim']['cz_same']}, meas order {r['cirq_vs_stim']['measurement_order_same']}, "
              f"T {r['cirq_vs_stim']['real_T']} / T-dagger {r['cirq_vs_stim']['real_T_dagger']}")
    C.save_json(C.RES / "step4_circuits.json", out)
    C.log("step 4 done")


if __name__ == "__main__":
    main()
