"""Continuing-data strict rule (constraints.continuing_data_violations) and the
continuing-data search machinery (search_continuing.py)."""
from pathlib import Path

import pytest
import stim

from nnflags import constraints as C
from nnflags import continuing_data as CD
from nnflags import g4
from nnflags import g6_continuing as G6
from nnflags import search_continuing as SC
from nnflags import search_option1 as S
from nnflags.willow import readout_line

ROOT = Path(__file__).resolve().parents[2]


def own(c):
    return {q: (int(a), int(b)) for q, (a, b) in C.native_coords(c).items()}


def test_success03_has_7():
    c = stim.Circuit.from_file(str(ROOT / "results/zz/success03.inner.stim"))
    v = CD.strict_conflicts(c)
    assert len(v) == 7
    assert {x.kind for x in v} == {"readout_continuing"}
    # same pairs as the final-layer-only count of RESULTS_continuing_data.md
    assert {(x.detail["measured"], x.detail["victim"]) for x in v} == {
        (c_["measured"], c_["data"]) for c_ in CD.continuing_data_conflicts(c)}


@pytest.mark.parametrize("name", ["G4-CX", "G4-native_CZH"])
def test_g4_has_2(name):
    c = stim.Circuit.from_file(str(ROOT / f"results/g4/{name}.inner.stim"))
    v = CD.strict_conflicts(c)
    assert len(v) == 2
    assert {x.detail["measured"] for x in v} == {7}
    assert {x.detail["line"] for x in v} == {19}


def test_hand_made_clean_example_has_0():
    # data on odd lines, measured ancilla root on line 0 / ancilla on line 2
    c = stim.Circuit("""
        QUBIT_COORDS(0, 0) 0
        QUBIT_COORDS(0, 1) 1
        QUBIT_COORDS(1, 0) 2
        QUBIT_COORDS(1, 1) 3
        QUBIT_COORDS(1, 2) 4
        MPP X1*X2*X4
        TICK
        RX 0 3
        TICK
        CX 3 4
        TICK
        CX 0 1 3 2
        TICK
        MRX 0
        TICK
        MX 3
        TICK
        R 0 3
    """)
    assert [readout_line(p) for p in own(c).values()] == [0, 1, 1, 2, 3]
    assert CD.strict_conflicts(c) == []
    assert C.check_circuit(c, own(c), grid=None, data_continue=True) == []


def test_g4_with_q7_unmeasured_is_clean_and_g6_cultivation_is_clean():
    c = G6.g4_without_q7()
    assert CD.strict_conflicts(c) == []
    assert C.check_circuit(c, own(c), data_continue=True) == []
    g, emb = G6.load_g6()
    data = G6.tagged_targets(g, "T_gate")
    assert data == [2, 4, 8, 10, 18, 20, 28]
    cult = G6.sub_circuit(g, 0, 57)
    assert C.continuing_data_violations(cult, emb, data) == []
    # G6's q12 (line 13, a data line) is never measured in the cultivation stage
    measured = {t.value for inst in cult.flattened() if stim.gate_data(inst.name).produces_measurements
                for t in inst.targets_copy()}
    assert 12 not in measured and readout_line(emb[12]) == readout_line(emb[20]) == 13


def test_measuring_a_data_qubit_and_simultaneity():
    c = stim.Circuit("""
        QUBIT_COORDS(0, 0) 0
        QUBIT_COORDS(0, 1) 1
        QUBIT_COORDS(1, 0) 2
        MPP X1
        TICK
        RX 0
        TICK
        CX 0 1
        TICK
        M 1
        MX 0 2
    """)
    v = C.continuing_data_violations(c, own(c))
    kinds = sorted(x.kind for x in v)
    # data 1 measured; ancilla 2 on line 1 hits data 1 even though measured simultaneously
    assert kinds == ["data_measured", "readout_continuing"]
    # default check_circuit is unchanged
    assert not any(x.kind in ("data_measured", "readout_continuing")
                   for x in C.check_circuit(c, own(c), grid=None))


def test_enumerated_bases_respect_line_disjointness():
    groups, _, _ = SC.enumerate_space([1, 2], 4, 9, 1, log=lambda *a: None, workers=2)
    assert groups
    n = 0
    for key, insts in groups.items():
        for parent, roles, roots in insts[:5]:
            lay = SC.build_u(parent, roles, roots)
            inner = S.to_circuit(lay)
            emb = lay["emb"]
            assert C.continuing_data_violations(inner, emb) == []
            assert C.check_circuit(inner, emb, grid=None, data_continue=True) == []
            u = lay["unmeasured"]
            assert all(roles[lay["nodes"][q]] == "U" for q in u)
            n += 1
    assert n > 50


def test_placer_embeddings_pass_full_check():
    groups, _, _ = SC.enumerate_space([1], 4, 10, 0, log=lambda *a: None, workers=2)
    key = max(groups, key=lambda k: len(groups[k]))
    lay = SC.build_u(*groups[key][0])
    inner = S.to_circuit(lay)
    pl = SC.Placer(groups[key])
    embs = list(pl.place([], want=20))
    assert embs
    for e in embs:
        assert SC.full_check(inner, e) == []


@pytest.mark.parametrize("path", sorted(str(p)[:-len(".inner.stim")] for p in
                                        (ROOT / "results/continuing").glob("success*.inner.stim")))
def test_saved_continuing_success_reverifies(path):
    from nnflags import continuing_evidence as CE
    from nnflags import equivalence as Q
    from nnflags import zzflags as Z
    from nnflags.verify import verify
    inner = stim.Circuit.from_file(path + ".inner.stim")
    full = stim.Circuit.from_file(path + ".full.stim")
    assert C.check_circuit(inner, own(inner), data_continue=True) == []
    d = Z.Design("s", inner, (CE.plaquettes_from_full(full), (), (), ()), {})
    flags = CE.flag_qubits(inner, d)
    assert len(flags) == 2
    assert Q.check_equivalence(inner, full, flag_qubits=tuple(flags))["ok"]
    r = verify(full, inner, max_fault_count=2)
    assert all(r["T"][k]["malignant"] == 0 for k in range(3))
