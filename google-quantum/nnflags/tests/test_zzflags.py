"""ZZ-flag round: generalised flag generator (zzflags.py) and the saved successes."""
import csv
import itertools
import random
from pathlib import Path

import pytest
import stim

from nnflags import constraints as C
from nnflags import equivalence as Q
from nnflags import zzflags as Z
from nnflags.verify import verify

ROOT = Path(__file__).resolve().parents[2]
ZZ = ROOT / "results" / "zz"


@pytest.fixture(scope="module")
def g4():
    d = Z.design_g4()
    pa = Z.ProbeAnalysis(d)
    pairs, events, _, _ = Z.malignant_pairs(d)
    return d, pa, pairs, events


def test_g4_baseline_pairs(g4):
    d, pa, pairs, events = g4
    assert len(pairs) == 7                       # RESULTS_g4.md: 7 malignant 2-fault T configurations
    assert d.mid_measured == [6, 9] and d.final == 11


def test_syndrome_predicts_stim_determinism(g4):
    """A probe set is a deterministic flag iff the xor of its syndromes is 0 (stim decides)."""
    d, pa, _, _ = g4
    rng = random.Random(1)
    by_q = {}
    for p in pa.probes:
        by_q.setdefault((p.q, p.basis), []).append(p)
    checked = {True: 0, False: 0}
    for _ in range(300):
        q1, q2 = rng.sample(d.qubits, 2)
        if d.colour[q1] != d.colour[q2]:
            continue
        basis = rng.choice("ZX")
        ps = rng.sample(by_q[(q1, basis)], 2) + rng.sample(by_q[(q2, basis)], rng.choice((0, 1, 2)))
        if len({p.slot for p in ps}) != len(ps):
            continue
        syn = 0
        for p in ps:
            syn ^= pa.syndrome[p]
        try:
            c, _ = Z.build_flagged(d, [Z.Flag(tuple(ps))])
            det = True
        except ValueError as e:
            assert "not deterministic" in str(e)
            det = False
        assert det == (syn == 0), [str(p) for p in ps]
        checked[det] += 1
    assert checked[True] > 10 and checked[False] > 10


def two_control_flag(d, pa, a=0, b=10):
    """A deterministic Z flag on controls a, b whose per-control parts are not
    deterministic on their own (a genuine two-control flag)."""
    pz = lambda q: [p for p in pa.probes if p.q == q and p.basis == "Z"]
    for pa_ in itertools.combinations(pz(a), 2):
        if pa.syndrome[pa_[0]] ^ pa.syndrome[pa_[1]] == 0:
            continue
        for pb in itertools.combinations(pz(b), 2):
            ps = pa_ + pb
            syn = 0
            for p in ps:
                syn ^= pa.syndrome[p]
            if syn == 0 and len({p.slot for p in ps}) == 4:
                return Z.Flag(tuple(sorted(ps, key=lambda p: p.slot)))
    raise AssertionError("no two-control flag")


def test_same_control_and_two_control_flags_deterministic(g4):
    d, pa, _, _ = g4
    same = Z.Flag((Z.Probe(4, 8.5, "Z"), Z.Probe(4, 9.5, "Z")))
    two = two_control_flag(d, pa)
    for fl in (same, two):
        c, fq = Z.build_flagged(d, [fl])
        assert Q.is_deterministic(c)
        assert fq == [d.nq]
    bad = Z.Flag((Z.Probe(4, 2.5, "Z"), Z.Probe(4, 9.5, "Z")))   # spans CX 5 -> 4 (4 is a target)
    with pytest.raises(ValueError, match="not deterministic"):
        Z.build_flagged(d, [bad])


def test_prefilter_exact_for_base_faults(g4):
    """The Z flag on q4 (TICKs 8.5, 9.5) is predicted to separate exactly one malignant
    pair; verify() drops from 7 to 6 (no new malignant pair from the flag's own faults)."""
    d, pa, pairs, events = g4
    cov = Z.Coverage(pa, pairs, events)
    fl = Z.Flag((Z.Probe(4, 8.5, "Z"), Z.Probe(4, 9.5, "Z")))
    cols = [pa.probes.index(p) for p in fl.probes]
    # x = both probes: a pair is separated iff every equation (mask, rhs) holds
    x_sep = sum(all(bin(m & 0b11).count("1") % 2 == r for m, r in cov.system(cols, [i]))
                for i in range(len(pairs)))
    assert x_sep == 1
    c, _ = Z.build_flagged(d, [fl])
    assert verify(d.full(c), c, max_fault_count=2)["T"][2]["malignant"] == 6


def test_degree_and_equivalence_with_flags_excluded(g4):
    d, pa, _, _ = g4
    two = two_control_flag(d, pa)
    c, fq = Z.build_flagged(d, [two])
    r = Q.check_equivalence(c, d.full(c), flag_qubits=tuple(fq))
    assert r["ok"]
    specs, _ = Z.flag_specs(c, fq)
    assert specs[0][0] == (0, 10)
    emb, tried, _ = Z.find_valid_embedding(d, specs, c)
    assert emb is not None
    assert C.check_circuit(c, emb) == []
    assert max(map(len, C.partners(c).values())) <= 4
    # the flag sits next to both controls on the grid
    for q in (0, 10):
        assert abs(emb[q][0] - emb[fq[0]][0]) + abs(emb[q][1] - emb[fq[0]][1]) == 1


def test_embeddings_respect_bipartite_parity(g4):
    d, _, _, _ = g4
    # 4 and 0 are tree neighbours: no grid point is adjacent to both
    assert next(Z.embeddings(d, [((0, 4), False)]), None) is None


def _successes():
    rows = list(csv.DictReader((ROOT / "results" / "zz_candidates.csv").open())) \
        if (ROOT / "results" / "zz_candidates.csv").exists() else []
    return [r for r in rows if r.get("success") == "True" and r.get("stim_file")]


@pytest.mark.parametrize("row", _successes(), ids=lambda r: Path(r["stim_file"]).stem)
def test_saved_success_reverifies(row):
    inner = stim.Circuit.from_file(str(ROOT / row["stim_file"]))
    full = stim.Circuit.from_file(str(ROOT / row["full_stim_file"]))
    emb = {q: tuple(int(x) for x in c) for q, c in inner.get_final_qubit_coordinates().items()}
    data = set(C.find_data_indices(inner))
    flags = [q for q in emb if q >= inner.num_qubits - int(row["n_flags"])]
    assert C.check_circuit(inner, emb) == []                       # strict, gate rule, auto final
    assert max(map(len, C.partners(inner).values())) <= 4
    assert Q.check_equivalence(inner, full, flag_qubits=tuple(flags))["ok"]
    assert Q.is_deterministic(inner) and Q.is_deterministic(full)
    r = verify(full, inner, max_fault_count=2)
    assert r["T"][1]["malignant"] == 0 and r["T"][2]["malignant"] == 0
    assert r["S"][1]["malignant"] + r["S"][2]["malignant"] == int(row["malignant_S_2"])
    assert not data & set(flags)


def test_measurement_flip_events_have_no_pauli():
    """Two-root bases have measurement-result flips (MX, MRX) in malignant pairs; they
    carry no Pauli on the qubits, so they flip no probe (regression, Z-only pass)."""
    t = stim.target_x(0)
    assert Z.event_pauli((3, "MX", (stim.GateTarget(2),)), 5) == stim.PauliString(5)
    assert Z.event_pauli((3, "MRX", (stim.GateTarget(2),)), 5) == stim.PauliString(5)
    assert Z.event_pauli((3, "X_ERROR", (stim.GateTarget(2),)), 5) == stim.PauliString("__X__")
    assert Z.event_pauli((3, "E", (t, stim.target_z(4))), 5) == stim.PauliString("X___Z")
