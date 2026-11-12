from cliffordea import enum

from nnflags import constraints as C
from nnflags.willow import WILLOW, edges, load_spec_file, neighbours, readout_line


def d3a6():
    return enum.circuits.DoubleCheck(distance=3, ancilla_count=6).INNER_CIRCUIT


def d3a6f2():
    return enum.circuits.DoubleCheck(distance=3, ancilla_count=6, flag_count=2).INNER_CIRCUIT


def test_willow_matches_google_spec():
    qubits, pairs = load_spec_file()
    assert len(WILLOW) == 105 and qubits == set(WILLOW)
    assert pairs == edges() and len(pairs) == 182
    assert max(len(neighbours(q)) for q in WILLOW) == 4
    assert readout_line((6, 5)) == 11


def test_d3a6_passes_neighbour_and_degree_on_every_willow_embedding():
    embs = C.grid_embeddings(d3a6())
    assert len(embs) == 350
    for _, _, emb in embs:
        kinds = C.summarize(C.check_circuit(d3a6(), emb, ignore_readout=True))
        assert kinds == {}, kinds


def test_d3a6f2_native_failures_match_plan():
    c = d3a6f2()
    v = C.check_circuit(c, C.native_coords(c), grid=None, ignore_readout=True)
    nn = {tuple(sorted(x.detail["pair"])) for x in v if x.kind == "non_neighbour"}
    assert nn == {(3, 4), (4, 6), (6, 9), (9, 11)}            # 4 diagonal flag gates
    assert sum(x.kind == "non_neighbour" for x in v) == 8     # each used in fold + unfold
    deg = {x.detail["qubit"]: x.detail["partner_count"] for x in v if x.kind == "degree"}
    assert deg == {6: 6, 11: 5}
    assert not any(x.kind == "reuse_in_tick" for x in v)


def test_d3a6f2_cannot_be_nearest_neighbour_on_willow():
    c = d3a6f2()
    _, _, emb6 = next(e for e in C.grid_embeddings(d3a6()) if e[:2] == ("id", (4, 4)))
    coords6 = {xy: q for q, xy in C.native_coords(d3a6()).items()}
    partial = {q: emb6[coords6[xy]] for q, xy in C.native_coords(c).items() if xy in coords6}
    emb, v = C.extend_embedding(c, partial, ignore_readout=True)
    kinds = C.summarize(v)
    assert kinds["degree"] == 2 and kinds["non_neighbour"] > 0


def test_readout_rule_and_toggle():
    c = d3a6()
    emb = C.native_coords(c)
    v = C.readout_violations(c, emb)
    assert [(x.detail["measured"], x.detail["victim"]) for x in v] == [(5, 8)]
    assert not any(x.kind == "readout" for x in C.check_circuit(c, emb, grid=None, ignore_readout=True))
    assert not any(x.kind == "readout" for x in C.check_circuit(c, emb, grid=None, readout="ignore"))


def test_reuse_in_tick_detected():
    import stim
    c = stim.Circuit("MPP X0*X1\nTICK\nCX 0 1 1 2\nTICK\nM 2")
    emb = {0: (6, 4), 1: (6, 5), 2: (6, 6)}
    v = C.check_circuit(c, emb, ignore_readout=True)
    assert [x.detail["qubit"] for x in v if x.kind == "reuse_in_tick"] == [1]
