"""Option-1 task B: fault distance of Google's as-run double check (G4).

G4 = rosenfeld2512_G4.stim, the complete Fig. 2 cultivation circuit of
Rosenfeld et al., arXiv:2512.13908, at Willow coordinates (CZ + H gate set,
Z-basis measurement, no MPP; non-Clifford gates appear as tagged identities).

TICK map of G4 (0-based, ``split_by_ticks``):
   0-3    injection on qubit 5 (H_YZ[conjugate] S[injection] H_YZ[conjugate])
   4-25   encoding into the d=3 colour code; TICK 25: M 4 1 6 9 (checks)
   26     R 4 1 9 6
   27-30  transversal T on data 3 0 8 5 11 2 10: I[conjugate] I[echo]
          I[T_gate] I[conjugate]
   31-39  FOLD (H / CZ layers)
   40     M 9 6 (mid-check measurement)          41  R 9 6
   42-50  UNFOLD (time reverse of 31-39, except that the H on ancillas 1, 4
          that starts the fold is applied at TICK 55 instead)
   51-54  transversal T^dagger: I[conjugate] I[echo] I[T_dagger_gate] I[conjugate]
   55     H on all qubits but 7                    56  M on all 12 qubits

Data (T-gate targets) = 0 2 3 5 8 10 11; ancillas = 1 4 6 7 9. The double
check = TICKs 31-50 plus the ancilla part of the readout (TICKs 55-56).
Rosenfeld et al. (Sec. I): T := exp(-i pi sigma_y / 8) and the measured
operator is H = T^dag X T; "[conjugate]" is the H_YZ basis change that turns
the Z rotation into this Y rotation (same tag around S[injection], TICKs 0-2).

Extraction into cliffordea's inner-circuit conventions (enum/circuits/main.py:42-54):
  * TICK 0: QUBIT_COORDS (G4's), noiseless ``MPP X^(x)7`` marker on the data.
  * TICK 1: ``R 4 1 9 6`` (G4 TICK 26) + ``R 7``: G4 never resets qubit 7 (it
    is in |0> from the start of the experiment; checked by simulation).
  * G4 TICKs 31-50 verbatim, except: identity placeholders I[...] dropped
    (cliffordea's noise model gives an I gate and an idle qubit the same
    DEPOLARIZE1(p), enum/noise/_noise.py:278-317; checked numerically), and
    ``M 9 6`` -> ``MR 9 6`` (cliffordea: a measured ancilla that is used
    again must be MR, main.py:46-50; the following ``R 9 6`` is kept, so the
    TICK structure is G4's).
  * Ancilla readout: ``H 4 1 9 6`` then ``M 4 1 9 6 7`` (G4 TICKs 55-56
    restricted to the ancillas; it commutes with the T^dagger on the data,
    so it is moved before it, as in cliffordea's own inner circuits).
  * Detectors: G4's, restricted to these measurements. The forward-check
    detector "M 9" becomes "M 9 xor MPP" (G4's stand-in state is |+_L>, so
    there it is deterministic alone; in the inner frame the reference is
    the MPP marker).
  * Trailing ``R`` of all ancillas (main.py:51-53).
  -> variant "native" (CZ + H, G4's TICKs).
  "cx" = ``equivalence.absorb_hadamards(native)``: every H pushed into a
  per-qubit frame, CZ -> CX, R/M -> RX/MX where framed, H-only TICKs gone,
  'M; TICK; R' merged into MR/MRX (the conversion cliffordea's d3a4 uses for
  the same experiment).

T-gate convention. cliffordea pushes the data effect through T on the
logical-S "majority" sublattice and T^dag on the rest (Z rotations,
accept/logical_analyzers.py:178-189); G4 applies T_y^dag = exp(+i pi Y/8)
uniformly. With W = H_NYZ on the majority, H_YZ on the minority (per qubit
W T_y^dag W^dag = T_z on majority, T_z^dag on minority), the G4 protocol is
cliffordea's protocol for the inner circuit W^dag . DC . W. frame="as_run"
inserts W^dag after the MPP marker (TICK 0) and W in the trailing reset TICK;
both TICKs are noiseless in uniformly_depolarize (enum/noise/main.py:39-40),
so nothing about the noise changes. frame="cliffordea" omits W (= G4's double
check run inside cliffordea's standard T_z convention, like d3a6/d3a4).

Usage: python -m nnflags.g4 [--out results] [--max3]
"""
import argparse
import itertools
import json
import time
from pathlib import Path

import stim

from cliffordea.enum.circuit_tools import split_by_ticks
from cliffordea.enum.circuits._base import find_stabilizer_generators

from nnflags import constraints as C
from nnflags import equivalence as Q
from nnflags.verify import bundled_paths, load_measurement, verify

G4_FILE = Path(__file__).with_name("data") / "google_circuits" / "rosenfeld2512_G4.stim"
DATA = (0, 2, 3, 5, 8, 10, 11)
ANC = (1, 4, 6, 7, 9)
FOLD_TICKS = range(31, 40)
MID_TICK, RESET_TICK = 40, 41
UNFOLD_TICKS = range(42, 51)
DC_TICKS = range(31, 51)
PLAQUETTES = ((0, 3, 10, 11), (2, 3, 8, 10), (5, 8, 10, 11))  # checked in faithfulness()
MAJORITY = (0, 2, 5, 10)   # centre 10 + corners (S targets of logical S)
MINORITY = (3, 8, 11)      # edge qubits


def load_g4() -> stim.Circuit:
    return stim.Circuit.from_file(str(G4_FILE))


def _ops(layer, keep_i=False):
    """Hardware ops of a G4 TICK (no annotations), I placeholders dropped
    unless ``keep_i``."""
    out = []
    for op in layer:
        if op.name in ("DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS"):
            continue
        if op.name == "I" and not keep_i:
            continue
        out.append(op)
    return out


def _frame_gates(inverse: bool):
    # W = H_NYZ (majority), H_YZ (minority); both self-inverse.
    return [stim.CircuitInstruction("H_NYZ", list(MAJORITY)),
            stim.CircuitInstruction("H_YZ", list(MINORITY))]


def inner_native(frame="cliffordea", keep_i=False) -> stim.Circuit:
    """G4's double check as a cliffordea inner circuit (see module docstring)."""
    g = load_g4()
    L = split_by_ticks(g)
    coords = g.get_final_qubit_coordinates()
    c = stim.Circuit()
    for q in sorted(coords):
        c.append("QUBIT_COORDS", [q], coords[q])
    c.append("MPP", [x for q in (3, 0, 8, 5, 11, 2, 10)
                     for x in (stim.target_x(q), stim.target_combiner())][:-1])
    if frame == "as_run":
        for op in _frame_gates(inverse=True):
            c.append(op)
    c.append("TICK")
    c.append("R", [4, 1, 9, 6, 7])
    for t in DC_TICKS:
        c.append("TICK")
        for op in _ops(L[t], keep_i):
            if t == MID_TICK and op.name == "M":
                assert [x.value for x in op.targets_copy()] == [9, 6]
                c.append("MR", [9, 6])
                # rec[-2] = MR 9, rec[-1] = MR 6, MPP = 2 + 0 measurements earlier
                c.append("DETECTOR", [stim.target_rec(-2), stim.target_rec(-3)], [9, 9, 1])
                c.append("DETECTOR", [stim.target_rec(-1)], [8, 10, 1])
            else:
                c.append(op)
    c.append("TICK")
    c.append("H", [4, 1, 9, 6])
    c.append("TICK")
    c.append("M", [4, 1, 9, 6, 7])
    # G4 TICK-56 detectors restricted to the ancillas (record offsets rebuilt):
    # rec[-5..-1] = M 4 1 9 6 7; mid MR 9 = rec[-7].
    c.append("DETECTOR", [stim.target_rec(-5)], [8, 8, 2])
    c.append("DETECTOR", [stim.target_rec(-4)], [7, 9, 2])
    c.append("DETECTOR", [stim.target_rec(-3), stim.target_rec(-7)], [9, 9, 2])
    c.append("DETECTOR", [stim.target_rec(-2)], [8, 10, 2])
    c.append("DETECTOR", [stim.target_rec(-1)], [8, 11, 2])
    c.append("TICK")
    c.append("R", list(ANC))
    if frame == "as_run":
        for op in _frame_gates(inverse=False):
            c.append(op)
    return c


def inner_cx(frame="cliffordea") -> tuple[stim.Circuit, dict]:
    """Canonical CX form of ``inner_native`` (frames re-inserted afterwards so
    that the H-frame absorption never touches the analysis frame W)."""
    cx, info = Q.absorb_hadamards(inner_native("cliffordea"), DATA)
    if frame == "as_run":
        layers = Q.to_layers(cx)
        layers[0] += [Q.Op(op.name, [t.value for t in op.targets_copy()])
                      for op in _frame_gates(True)]
        layers[-1] += [Q.Op(op.name, [t.value for t in op.targets_copy()])
                       for op in _frame_gates(False)]
        cx = Q.from_layers(layers)
    return cx, info


def full_for(inner: stim.Circuit, plaquettes=None, majority=None, minority=None,
             data=None) -> stim.Circuit:
    """Full circuit in the layout of cliffordea's bundled full.stim files:
    MPP Y_L, MPP X / Z plaquettes, logical S^dag layer (S minority, S_DAG
    majority), the inner body (its MPP marker becomes the initial MPP Y_L,
    which the forward-check detector now references), logical S layer
    (S majority, S_DAG minority) right after the last unitary TICK, then
    final MPP checks with detectors and the Y_L observable. Final-check
    detectors = final MPP xor initial MPP xor the body records solving the
    stim flow P -> P. cliffordea reads only the MPPs (stabilisers) and the
    S/S_DAG instructions (logical S = the 3rd and 4th, _base.py:43-71).
    Defaults: G4's plaquettes and sublattices."""
    plaquettes = PLAQUETTES if plaquettes is None else plaquettes
    majority = MAJORITY if majority is None else majority
    minority = MINORITY if minority is None else minority
    data = sorted(DATA if data is None else data)
    layers = Q.to_layers(inner)
    head0 = [it for it in layers[0] if not isinstance(it, Q.Op) and it[0] == "coords"]
    marker = next(it for it in layers[0] if isinstance(it, Q.Op) and it.name == "MPP")
    rest0 = [it for it in layers[0] if it is not marker and it not in head0]
    nid = iter(range(10 ** 6, 10 ** 7))
    pt = lambda qs, f: [x for q in qs for x in (f(q), stim.target_combiner())][:-1]
    marker.targets = pt(data, stim.target_y)  # same global id: detectors follow it
    init = {("Y", tuple(data)): marker.ids[0]}
    out = [head0, [marker]]
    for b, f in (("X", stim.target_x), ("Z", stim.target_z)):
        for p in plaquettes:
            i = next(nid)
            init[(b, tuple(p))] = i
            out.append([Q.Op("MPP", pt(p, f), [], [i])])
    out.append([Q.Op("S", [q]) for q in minority] + [Q.Op("S_DAG", [q]) for q in majority])
    body = [rest0] + layers[1:]
    # (frame gates W in the trailing TICK count: the logical S must follow W)
    unitary = lambda it: (isinstance(it, Q.Op) and it.name != "MPP"
                          and stim.gate_data(it.name).is_unitary)
    last_u = max(t for t, items in enumerate(body) if any(unitary(it) for it in items))
    for t, items in enumerate(body):
        out.append(items)
        if t == last_u:
            out.append([Q.Op("S", [q]) for q in majority] + [Q.Op("S_DAG", [q]) for q in minority])
    # body measurement ids in record order, for flow solving
    body_ids = [g for items in body for it in items if isinstance(it, Q.Op) for g in it.ids]
    body_c = Q.from_layers([[it for it in items if isinstance(it, Q.Op) and it.name != "MPP"]
                            for items in out])
    nq = inner.num_qubits
    finals = [("X", tuple(p)) for p in plaquettes] + [("Z", tuple(p)) for p in plaquettes] + [
        ("Y", tuple(data))]
    for b, p in finals:
        ps = "".join(b if q in p else "_" for q in range(nq))
        sol = body_c.solve_flow_measurements([stim.Flow(f"{ps} -> {ps}")])[0]
        assert sol is not None, (b, p)
        i = next(nid)
        f = {"X": stim.target_x, "Z": stim.target_z, "Y": stim.target_y}[b]
        ids = [init[(b, p)]] + [body_ids[r] for r in sol] + [i]
        det = (("det", "OBSERVABLE_INCLUDE", [0], ids) if b == "Y"
               else ("det", "DETECTOR", [float(len(out)), 0, 9], ids))
        out.append([Q.Op("MPP", pt(p, f), [], [i]), det])
    return Q.from_layers(out)


# ---- faithfulness -------------------------------------------------------------

def g4_segment(keep_i=True) -> stim.Circuit:
    """The corresponding part of G4 itself: TICKs 26-56 with the data part of
    the final readout (H on data at 55, M on data at 56: the experiment's
    destructive data readout) removed, plus R 7 at TICK 26 (qubit 7 is in
    |0> there, see ``faithfulness``). Identity placeholders are kept."""
    L = split_by_ticks(load_g4())
    c = stim.Circuit()
    for t in range(26, 57):
        if t > 26:
            c.append("TICK")
        for op in _ops(L[t], keep_i):
            ts = [x.value for x in op.targets_copy()]
            if t in (55, 56):
                ts = [q for q in ts if q in ANC]
            if ts:
                c.append(op.name, ts, op.gate_args_copy())
        if t == 26:
            c.append("R", [7])
    return c


def _flows_signature(circ, nq):
    """Data-action flows of a (MPP-free) circuit: X_L measured, commutant of X_L
    preserved, Z_L not preserved."""
    xl = "".join("X" if q in DATA else "_" for q in range(nq))
    zl = "".join("Z" if q in DATA else "_" for q in range(nq))
    out = {"X_L -> rec": circ.solve_flow_measurements([stim.Flow(f"{xl} -> 1")])[0]}
    for q in DATA:
        p = "".join("X" if k == q else "_" for k in range(nq))
        out[f"X{q} -> X{q}"] = circ.solve_flow_measurements([stim.Flow(f"{p} -> {p}")])[0]
    for p in PLAQUETTES:
        for b in "XZ":
            s = "".join(b if k in p else "_" for k in range(nq))
            out[f"{b}{p} -> same"] = circ.solve_flow_measurements([stim.Flow(f"{s} -> {s}")])[0]
    ds = sorted(DATA)
    for a, b in zip(ds, ds[1:]):
        s = "".join("Z" if k in (a, b) else "_" for k in range(nq))
        out[f"Z{a}Z{b} -> same"] = circ.solve_flow_measurements([stim.Flow(f"{s} -> {s}")])[0]
    out["Z_L -> Z_L"] = circ.solve_flow_measurements([stim.Flow(f"{zl} -> {zl}")])[0]
    return out


def faithfulness() -> dict:
    """Tableau / stabiliser evidence that the extracted circuits are G4's double check."""
    g = load_g4()
    L = split_by_ticks(g)
    rec = {}
    # (1) state at the start of the double check (Clifford stand-in, T -> I)
    sim = stim.TableauSimulator()
    pre = stim.Circuit()
    for t in range(31):
        for op in _ops(L[t], keep_i=True):
            pre.append(op)
    sim.do(pre)
    exp = lambda s: sim.peek_observable_expectation(stim.PauliString(s))
    nq = g.num_qubits
    P = lambda b, qs: "".join(b if q in qs else "_" for q in range(nq))
    rec["state_at_tick31"] = {
        **{f"X{p}": exp(P("X", p)) for p in PLAQUETTES},
        **{f"Z{p}": exp(P("Z", p)) for p in PLAQUETTES},
        "X_L": exp(P("X", DATA)), "Z_L": exp(P("Z", DATA)),
        **{f"Z{q}": exp(P("Z", [q])) for q in ANC}}
    # (2) the code: cliffordea's derivations on the extracted full circuit, and
    #     a relabelling onto d3a6 (stabilisers + logical-S sublattice).
    native = inner_native()
    full = full_for(native)
    meas = load_measurement(full, native)
    ref = load_measurement(*bundled_paths("d3a6"))
    perm = Q._data_perm_to_reference(meas, ref)
    rec["code"] = dict(data_indices=meas.DATA_INDICES,
                       stabilizers=sorted(map(sorted, find_stabilizer_generators(full))),
                       logical_s=str(meas.LOGICAL_S).split("\n"),
                       relabelling_to_d3a6=perm, same_code_as_d3a6=perm is not None,
                       stabilizers_match_simulated_state=all(
                           v == 1 for k, v in rec["state_at_tick31"].items()
                           if k[0] in "XZ" and k[1] == "("))
    # (3) the fold measures X_L on qubit 9 and Z_7 on qubit 6 (Heisenberg)
    fold = stim.Circuit(f"I {nq - 1}")
    for t in FOLD_TICKS:
        for op in _ops(L[t]):
            fold.append(op)
    U = stim.Tableau.from_circuit(fold).inverse()
    for q in (9, 6):
        z = stim.PauliString(nq)
        z[q] = "Z"
        rec[f"mid_M{q}_measures"] = str(U(z))
    unfold = stim.Circuit(f"I {nq - 1}")
    for t in UNFOLD_TICKS:
        for op in _ops(L[t]):
            unfold.append(op)
    Uf, Uu = stim.Tableau.from_circuit(fold), stim.Tableau.from_circuit(unfold)
    hs = stim.Circuit(f"I {nq - 1}\nH 1 4 6 9")
    rec["unfold_is_fold_inverse_up_to_H_1_4_6_9"] = (
        Uf.then(Uu).then(stim.Tableau.from_circuit(hs)) == stim.Tableau(nq))
    # (4) same data action: flows of G4's own segment vs the extracted circuits
    seg = g4_segment()
    strip = lambda c: Q.from_layers(Q._strip_mpp(c)[0])
    cx, cx_info = inner_cx()
    sig = {"G4 segment (TICKs 26-56)": _flows_signature(seg, nq),
           "extracted native": _flows_signature(strip(native), nq),
           "extracted CX": _flows_signature(strip(cx), nq)}
    norm = {k: {f: (v is not None) for f, v in s.items()} for k, s in sig.items()}
    rec["flows_exist"] = norm
    rec["flows_identical_existence"] = len({json.dumps(v, sort_keys=True) for v in norm.values()}) == 1
    rec["flows_records"] = {k: {f: v for f, v in s.items()} for k, s in sig.items()}
    # (5) the native extraction is G4's TICKs 31-50 op for op (I dropped, M->MR)
    ext = split_by_ticks(native)
    same = []
    for k, t in enumerate(DC_TICKS):
        a = [(op.name if op.name != "MR" else "M", [x.value for x in op.targets_copy()])
             for op in _ops(ext[2 + k]) if op.name not in ("DETECTOR",)]
        b = [(op.name, [x.value for x in op.targets_copy()]) for op in _ops(L[t])]
        same.append(a == b)
    rec["native_ticks_equal_g4_31_50"] = all(same)
    # (6) determinism and the equivalence checker
    rec["deterministic"] = {"native": Q.is_deterministic(native), "cx": Q.is_deterministic(cx),
                            "full_native": Q.is_deterministic(full),
                            "full_cx": Q.is_deterministic(full_for(cx)),
                            "native_as_run": Q.is_deterministic(inner_native("as_run")),
                            "full_native_as_run": Q.is_deterministic(full_for(inner_native("as_run")))}
    rec["cx_conversion"] = cx_info
    for name, c in (("native", native), ("cx", cx)):
        r = Q.check_equivalence(c, full_for(c))
        rec[f"equivalence_{name}"] = {k: (v["ok"] if isinstance(v, dict) else v)
                                      for k, v in r.items()}
    return rec


def _verify_row(name, inner, mfc):
    r = verify(full_for(inner), inner, max_fault_count=mfc)
    rate = r["error_rate_per_kept_shot"]["T"]
    return dict(variant=name, max_fault_count=mfc,
                T={k: v for k, v in r["T"].items()}, S={k: v for k, v in r["S"].items()},
                rate_T=rate, one_in_T=(1 / rate if rate > 0 else None),
                fault_count=r["fault_count"], signature_count=r["signature_count"],
                malignant_T=r["malignant_configurations"]["T"],
                summary=r["summary"].to_string(), runtime_s=r["runtime_s"],
                ticks=inner.num_ticks, n_2q=len(C.two_qubit_gates(inner)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results")
    parser.add_argument("--max3", action="store_true", help="also max_fault_count=3")
    args = parser.parse_args()
    out = Path(args.out)
    (out / "g4").mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    rec = {"faithfulness": faithfulness()}
    print(json.dumps({k: v for k, v in rec["faithfulness"].items() if k != "flows_records"},
                     indent=1, default=str)[:6000], flush=True)
    variants = {
        "G4-CX (cliffordea T_z convention)": inner_cx("cliffordea")[0],
        "G4-native CZ+H (cliffordea T_z convention)": inner_native("cliffordea"),
        "G4-CX (as-run T_y frame)": inner_cx("as_run")[0],
        "G4-native CZ+H (as-run T_y frame)": inner_native("as_run"),
        "G4-native CZ+H, I placeholders kept (cliffordea T_z convention)":
            inner_native("cliffordea", keep_i=True),
    }
    files = {}
    for name, c in variants.items():
        slug = (name.split(" (")[0].replace(" ", "_").replace("+", "").replace(",", "")
                + ("_asrun" if "as-run" in name else ""))
        p = out / "g4" / f"{slug}.inner.stim"
        p.write_text(str(c))
        (out / "g4" / f"{slug}.full.stim").write_text(str(full_for(c)))
        files[name] = str(p)
    rec["files"] = files
    rows = []
    refs = {n: tuple(map(stim.Circuit.from_file, map(str, bundled_paths(n))))
            for n in ("d3a6", "d3a4")}
    for mfc in ([2, 3] if args.max3 else [2]):
        for n, (f, i) in refs.items():
            r = verify(f, i, max_fault_count=mfc)
            rate = r["error_rate_per_kept_shot"]["T"]
            rows.append(dict(variant=n, max_fault_count=mfc, T=r["T"], S=r["S"], rate_T=rate,
                             one_in_T=1 / rate if rate else None, fault_count=r["fault_count"],
                             malignant_T=r["malignant_configurations"]["T"],
                             runtime_s=r["runtime_s"], ticks=i.num_ticks,
                             n_2q=len(C.two_qubit_gates(i)), summary=r["summary"].to_string()))
            print(n, mfc, r["T"], r["S"], f"1 in {1 / rate:,.0f}" if rate else 0,
                  f"{r['runtime_s']:.1f} s", flush=True)
        for name, c in variants.items():
            row = _verify_row(name, c, mfc)
            rows.append(row)
            print(name, mfc, row["T"], row["S"],
                  f"1 in {row['one_in_T']:,.0f}" if row["one_in_T"] else 0,
                  f"{row['runtime_s']:.1f} s", flush=True)
            (out / "g4_result.json").write_text(json.dumps({**rec, "rows": rows}, indent=1,
                                                           default=str))
    # malignant configurations of the primary variant, as physical events
    from nnflags.verify import load_measurement as _lm
    from cliffordea import enum
    prim = variants["G4-CX (cliffordea T_z convention)"]
    m = _lm(full_for(prim), prim)
    comb = enum.FaultCombinator(enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=1e-3))
    events = {}
    for row in rows:
        if row["variant"].startswith("G4-CX (cliffordea") and row["max_fault_count"] == 2:
            for k, cfg in row["malignant_T"]:
                events[str(cfg)] = [sorted(map(str, comb.index_to_events[i]))[:6] for i in cfg]
    rec["primary_malignant_T_events"] = events
    rec["runtime_s"] = time.perf_counter() - t0
    (out / "g4_result.json").write_text(json.dumps({**rec, "rows": rows}, indent=1, default=str))


if __name__ == "__main__":
    main()
