"""Option-1 task D: search building blocks."""
import stim

from nnflags import constraints as C
from nnflags import equivalence as Q
from nnflags import search_option1 as S
from nnflags.verify import verify
from nnflags.willow import readout_line

# G4's X-parity tree without its copy ancilla and its 6/7 gadget (prototype in RESULTS_option1.md):
# root (9,9) <- (8,9), (9,8), (9,10), (10,9); (8,9) <- (8,10), (8,8); (8,10) <- (7,10);
# (8,8) <- (7,8), (8,7). (8,10) is on the root's line 18, so use it only in role tests.
PARENT = {(9, 9): None, (8, 9): (9, 9), (9, 8): (9, 9), (9, 10): (9, 9), (10, 9): (9, 9),
          (8, 8): (8, 9), (7, 8): (8, 8), (8, 7): (8, 8), (7, 9): (8, 9), (6, 9): (7, 9)}
ROLES = {p: "D" for p in PARENT} | {(9, 9): "A", (8, 8): "A", (7, 9): "A"}


def base():
    return S.Base(PARENT, ROLES, ((9, 9),))


def test_labelling_classes():
    assert len(S.code_automorphisms()) == 24
    assert len(S.labelling_classes()) == 210


def test_canonical_order_is_isomorphism_invariant():
    b = base()
    mirrored = {(r, 18 - c) if p is not None else None for r, c in []}  # noqa: F841 (placeholder)
    # transpose the tree around the root: (r, c) -> (c, r) keeps it a grid tree
    t = lambda p: None if p is None else (p[1], p[0])
    b2 = S.Base({t(k): t(v) for k, v in PARENT.items()}, {t(k): v for k, v in ROLES.items()},
                ((9, 9),))
    assert b.abstract_key() == b2.abstract_key()
    c1 = S.to_circuit(S.build(b)).without_noise()
    c2 = S.to_circuit(S.build(b2)).without_noise()
    strip = lambda c: stim.Circuit("\n".join(l for l in str(c).splitlines() if "QUBIT_COORDS" not in l))
    assert strip(c1) == strip(c2)


def test_built_base_is_a_valid_double_check():
    b = base()
    lay = S.build(b)
    inner = S.to_circuit(lay)
    full = S.full_circuit(inner, lay, S.labelling_classes()[0])
    r = Q.check_equivalence(inner, full)
    assert r["ok"], {k: r[k]["ok"] for k in ("i_code", "ii_check", "iii_reverse", "iv_deterministic")}
    assert C.check_circuit(inner, lay["emb"]) == []          # root line 18 is clear
    assert lay["depth"] == S.depth_of(PARENT, ((9, 9),))
    v = verify(full, inner, max_fault_count=2)
    assert v["T"][1]["malignant"] == 0


def test_flag_is_deterministic_and_checked():
    b = base()
    lay = S.build(b)
    inner = S.to_circuit(lay)
    lab = S.labelling_classes()[0]
    full = S.full_circuit(inner, lay, lab)
    hooks, nmal = S.hooks_of(inner, full, lay)
    assert hooks and nmal > 0
    q = next(iter(hooks))
    opts = S.flag_options(lay, q, hooks[q], set(lay["emb"].values()))
    assert opts
    flag = opts[0][0]
    lay2 = S.build(b, (flag,))
    c2 = S.to_circuit(lay2)
    assert Q.is_deterministic(c2)
    r = Q.check_equivalence(c2, S.full_circuit(c2, lay2, lab), flag_qubits=tuple(lay2["flags"]))
    assert r["ok"]


def test_grow_forests_respects_depth_and_lines():
    trees = list(S.grow_forests(((9, 9),), 3, 6))
    assert trees and all(S.depth_of(t, ((9, 9),)) <= 3 for t in trees)
    assert all(readout_line(p) != 18 for t in trees for p in t if p != (9, 9))
