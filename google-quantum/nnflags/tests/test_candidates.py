"""Step 3 candidate generator (nnflags/candidates.py)."""
import itertools

import stim

from nnflags import candidates as K
from nnflags import constraints as C
from nnflags.willow import neighbours

BASE = K.d3a6()
EMBS = C.grid_embeddings(BASE)
PRIMARY = next(e for s, o, e in EMBS if (s, o) == K.PRIMARY)


def strip_coords(c):
    return stim.Circuit("\n".join(l for l in str(c).splitlines() if not l.startswith("QUBIT_COORDS")))


def detector_sources(c):
    """Each DETECTOR as the sorted (qubit, k-th measurement of that qubit) it reads."""
    seen, meas, out = {}, [], []
    for op in c.flattened():
        if op.name == "DETECTOR":
            out.append(sorted(meas[len(meas) + t.value] for t in op.targets_copy()))
        elif op.num_measurements:
            for g in op.target_groups():
                key = tuple(t.value for t in g)
                seen[key] = seen.get(key, 0) + 1
                meas.append((key, seen[key]))
    return out


def test_build_without_flags_is_d3a6():
    c, e = K.build(BASE, PRIMARY)
    assert strip_coords(c) == strip_coords(BASE)
    assert e == PRIMARY


def test_slot_pairs_keep_z_of_control():
    pairs = K.slot_pairs(BASE, 3)
    assert (5, 7) in pairs and (2.5, 3.5) in pairs     # in place / across CX 3->1 (control)
    assert (3.5, 4.5) not in pairs                     # across CX 5->3: 3 is a target
    assert all(t1 != int(t1) and t2 != int(t2) for t1, t2 in K.slot_pairs(BASE, 5))  # 5 never idle
    assert (5.5, 6) in K.slot_pairs(BASE, 9) and (4.5, 5.5) not in K.slot_pairs(BASE, 9)


def test_hook_qubits_5_and_9_have_no_free_neighbour_anywhere():
    for _, _, emb in EMBS:
        used = set(emb.values())
        for q in (5, 9):
            assert all(n in used for n in neighbours(emb[q]))
            assert len(neighbours(emb[q])) == 4
    flags = list(K.single_flags(BASE, PRIMARY))
    assert {f.q for f in flags[:46]} == {3}            # hook qubits first; only 3 can host
    assert not any(f.q in (5, 9) for f in flags)


def test_single_flag_circuit():
    f = K.Flag(3, (5, 6), 2.5, 3.5, "next")
    c, e = K.build(BASE, PRIMARY, (f,))
    assert e[13] == (5, 6) and K.is_deterministic(c)
    assert c.num_detectors == BASE.num_detectors + 1
    layers = C.split_by_ticks(c)
    assert len(layers) == len(C.split_by_ticks(BASE)) + 2          # two new TICKs
    assert K.added_ticks((f,)) == 2
    cx = [t for t, n, a, b in C.two_qubit_gates(c) if (a, b) == (3, 13)]
    assert cx == [3, 5]                                            # inserted after TICK 2 and 3
    assert any(op.name == "R" and op.targets_copy()[0].value == 13 for op in layers[2])
    assert any(op.name == "M" for op in layers[6])                 # "next": right after t2
    assert C.summarize(C.check_circuit(c, e, readout="ignore")) == {}
    # Every original detector still reads the same measurements.
    new = detector_sources(c)
    assert [((13,), 1)] in new
    new.remove([((13,), 1)])
    assert new == detector_sources(BASE)


def test_flag_measured_in_final_layer_and_in_place_slots():
    f = K.Flag(3, (5, 6), 5, 7, "final")
    c, e = K.build(BASE, PRIMARY, (f,))
    assert K.added_ticks((f,)) == 0 and len(C.split_by_ticks(c)) == len(C.split_by_ticks(BASE))
    assert K.is_deterministic(c)
    final = C.split_by_ticks(c)[11]
    assert any(op.name == "M" and op.targets_copy()[0].value == 13 for op in final)


def test_crossing_a_target_is_not_deterministic():
    bad = K.Flag(3, (5, 6), 3.5, 4.5, "final")                     # CX 5->3 in between
    assert not K.is_deterministic(K.build(BASE, PRIMARY, (bad,))[0])


def test_two_flags_same_control_same_slot_is_reuse():
    f1 = K.Flag(0, (3, 4), 3, 5, "final")
    f2 = K.Flag(0, (4, 3), 3, 6, "final")
    c, e = K.build(BASE, PRIMARY, (f1, f2))
    kinds = C.summarize(C.check_circuit(c, e, readout="ignore"))
    assert kinds == {"reuse_in_tick": 1}


def test_degree_violation_when_control_gets_a_fifth_partner():
    # Qubit 3 has partners {1, 2, 5}; two flags on 3 give it 5 partners. Only
    # one free neighbour exists in the primary placement, so place the second
    # flag off-grid on purpose to test the degree check alone.
    f1 = K.Flag(3, (5, 6), 5, 7, "final")
    f2 = K.Flag(3, (5, 6), 5.5, 6, "final")
    c, e = K.build(BASE, PRIMARY, (f1, f2))
    e[14] = (4, 6)
    kinds = C.summarize(C.check_circuit(c, e, readout="ignore"))
    assert kinds["degree"] == 1


def test_b_layer_permutations_and_fold_variants():
    assert K.layer_permutations(BASE) == [(0, 1, 2, 3)]
    folds = K.fold_variants(BASE)
    assert len(folds) == 6
    for fold in folds[1:]:
        c, e = K.build(BASE, PRIMARY, (), fold)
        assert K.is_deterministic(c)
        assert C.summarize(C.check_circuit(c, e, readout="ignore")) == {}
        layers = C.split_by_ticks(c)
        for t, u in zip(K.FOLD, K.UNFOLD):                         # time reverse
            assert str(layers[t]) == str(layers[u])


def test_count_flag_sets_matches_brute_force():
    singles = list(K.single_flags(BASE, PRIMARY))[:120]
    for k in (2, 3):
        brute = sum(len({f.at for f in combo}) == k for combo in itertools.combinations(singles, k))
        assert K.count_flag_sets(singles, k) == brute


def test_strict_readout_never_passes_but_ignore_does():
    singles = list(K.single_flags(BASE, PRIMARY))
    for f in singles[::97]:
        c, e = K.build(BASE, PRIMARY, (f,))
        r = K.evaluate(c, e)
        assert r["hw_ok"] and r["readout_strict"] >= 1


def test_verify_accepts_a_flagged_candidate():
    from nnflags.verify import bundled_paths, verify
    c, _ = K.build(BASE, PRIMARY, (K.Flag(3, (5, 6), 5, 7, "final"),))
    r = verify(bundled_paths("d3a6")[0], c, max_fault_count=2)
    assert set(r["T"]) == {0, 1, 2} and r["T"][0] == {"benign": 1, "malignant": 0}
    assert r["data_indices"] == (0, 3, 5, 7, 8, 10, 11)
