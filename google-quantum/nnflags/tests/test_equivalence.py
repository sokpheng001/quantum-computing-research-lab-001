"""Option-1 task C: the "same code + same double check" checker."""
import pytest
import stim

from nnflags import equivalence as Q
from nnflags import g4
from nnflags.verify import bundled_paths


def bundled(name):
    f, i = bundled_paths(name)
    return stim.Circuit.from_file(str(f)), stim.Circuit.from_file(str(i))


def oks(r):
    return {k: r[k]["ok"] for k in ("i_code", "ii_check", "iii_reverse", "iv_deterministic")}


@pytest.mark.parametrize("name,flags", [("d3a6", ()), ("d3a4", ()), ("d3a6f2", (4, 9))])
def test_bundled_pass(name, flags):
    full, inner = bundled(name)
    r = Q.check_equivalence(inner, full, flag_qubits=flags)
    assert r["ok"], oks(r)
    assert r["i_code"]["relabelling"] is not None


@pytest.mark.parametrize("variant", ["native", "cx"])
def test_extracted_g4_passes(variant):
    inner = g4.inner_native() if variant == "native" else g4.inner_cx()[0]
    r = Q.check_equivalence(inner, g4.full_for(inner))
    assert r["ok"], oks(r)
    assert r["i_code"]["relabelling"] == {0: 0, 2: 7, 3: 3, 5: 11, 8: 10, 10: 5, 11: 8}


def test_layer_roundtrip_and_absorb_identity_on_cx():
    full, inner = bundled("d3a6")
    assert Q.from_layers(Q.to_layers(inner)) == inner
    cx, info = Q.absorb_hadamards(inner)
    assert info["non_cx"] == 0 and Q.is_deterministic(cx)


def _edit(inner, old, new, count=1):
    text = str(inner)
    assert text.count(old) >= count, old
    return stim.Circuit(text.replace(old, new, count))


def test_broken_code_fails():
    # Full circuit whose MPPs describe a different code (a stabiliser support changed).
    full, inner = bundled("d3a6")
    bad_full = _edit(full, "MPP X8*X0*X3*X5\n", "MPP X8*X0*X3*X7\n")
    r = Q.check_equivalence(inner, bad_full)
    assert not r["i_code"]["ok"] and not r["ok"]


def test_broken_sublattice_fails():
    # Logical S on the wrong sublattice (swap S and S_DAG targets of the 2nd pair).
    full, inner = bundled("d3a6")
    bad_full = _edit(full, "S 5 11 7 0\nS_DAG 3 8 10", "S 3 8 10\nS_DAG 5 11 7 0")
    r = Q.check_equivalence(inner, bad_full)
    assert not r["i_code"]["ok"]


def test_broken_check_fails():
    # Drop CX 1 0 from both fold and unfold: the parity no longer contains data 0.
    full, inner = bundled("d3a6")
    bad = _edit(inner, "CX 1 0 9 8", "CX 9 8", count=2)
    r = Q.check_equivalence(bad, full)
    assert not r["ii_check"]["ok"] and not r["ok"]


def test_broken_reverse_fails():
    # Unfold layers 2 and 3 swapped (CX 5 3 9 10 <-> CX 3 1 5 6 9 12 after the MRX).
    full, inner = bundled("d3a6")
    text = str(inner)
    head, tail = text.split("MRX 5")
    tail = tail.replace("CX 5 3 9 10\nTICK\nCX 3 1 5 6 9 12", "CX 3 1 5 6 9 12\nTICK\nCX 5 3 9 10", 1)
    bad = stim.Circuit(head + "MRX 5" + tail)
    r = Q.check_equivalence(bad, full)
    assert not r["iii_reverse"]["ok"] and not r["ok"]


def test_reverse_checker_rejects_relayered_unfold_with_same_unitary():
    # d3a6: 9's commuting CXs 9->12 and 9->10 reordered in the unfold only. The
    # unfold unitary is still the inverse, but not the exact layer reverse.
    full, inner = bundled("d3a6")
    text = str(inner)
    head, tail = text.split("MRX 5")
    tail = tail.replace("CX 5 3 9 10\nTICK\nCX 3 1 5 6 9 12", "CX 5 3 9 12\nTICK\nCX 3 1 5 6 9 10", 1)
    bad = stim.Circuit(head + "MRX 5" + tail)
    r = Q.check_equivalence(bad, full)
    assert r["iii_reverse"]["tableau_identity"] and not r["iii_reverse"]["exact_layer_reverse"]
    assert not r["ok"]


def test_nondeterministic_detector_fails():
    full, inner = bundled("d3a6")
    bad = _edit(inner, "DETECTOR(0, 1, 1) rec[-1]", "DETECTOR(0, 1, 1) rec[-1]\nDETECTOR rec[-8]")
    r = Q.check_equivalence(bad, full)
    assert not r["iv_deterministic"]["ok"] and not r["ok"]


def test_missing_forward_detector_fails():
    full, inner = bundled("d3a6")
    bad = _edit(inner, "DETECTOR(0, 0, 0) rec[-1] rec[-2]", "DETECTOR(0, 0, 0) rec[-1]")
    r = Q.check_equivalence(bad, full)
    assert not r["ok"]


def test_g4_cz_form_with_broken_unfold_fails():
    inner = g4.inner_native()
    text = str(inner)
    head, tail = text.split("MR 9 6")
    tail = tail.replace("CZ 4 5 8 9 6 7", "CZ 4 5 8 9", 1)  # drop CZ 6 7 in the unfold
    r = Q.check_equivalence(stim.Circuit(head + "MR 9 6" + tail), g4.full_for(inner))
    assert not r["ok"]
