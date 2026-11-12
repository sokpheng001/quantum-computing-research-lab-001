"""Task 1 of the continuing-data search round: what Google's G6 (Rosenfeld et al.,
arXiv:2512.13908, Fig. 4 grafting N = 2 with cultivation, as run on Willow) does
about readout lines when the data continue, and the continuing-data strict rule
on G6, G4 and success03.

    .venv/bin/python -m nnflags.g6_continuing        -> results/continuing_g6.json

G6 TICK map (0-based ``split_by_ticks``, see the dump in the report):
   0-24   injection + encoding (as G4)     25  M 9 3 11 19     26  R
   27-30  T layer on data (I[T_gate] at 29)
   31-39  fold          40  M 19 11 (mid check)  41  R 19 11
   42-50  unfold        51-54 T^dagger           55  M 9 3 19 11
   56     R 11 9 12 3 19  (end of cultivation)
   57-    grafting into the surface code (first op on a qubit outside the
          cultivation patch); 90 / 124 surface-code measurements.
Cultivation data = targets of I[T_gate] (TICK 29).
"""
import json
from pathlib import Path

import stim

from nnflags import constraints as C
from nnflags import equivalence as Q
from nnflags import g4
from nnflags.continuing_data import data_qubits as mpp_data
from nnflags.verify import verify
from nnflags.willow import readout_line

G6_FILE = Path(__file__).with_name("data") / "google_circuits" / "rosenfeld2512_G6.stim"


def load_g6():
    g = stim.Circuit.from_file(str(G6_FILE))
    emb = {q: tuple(int(x) for x in p) for q, p in C.native_coords(g).items()}
    return g, emb


def tagged_targets(circuit, tag):
    return sorted({t.value for inst in circuit.flattened() if inst.tag == tag
                   for t in inst.targets_copy()})


def layer_ops(circuit):
    return [[(n, list(qs)) for n, qs, _ in C._hardware_ops(layer)]
            for layer in C.split_by_ticks(circuit)]


def sub_circuit(circuit, t0, t1):
    """TICKs t0 .. t1 - 1 of ``circuit`` (QUBIT_COORDS kept; detectors dropped)."""
    out = stim.Circuit()
    for q, p in circuit.get_final_qubit_coordinates().items():
        out.append("QUBIT_COORDS", [q], p)
    for k, layer in enumerate(C.split_by_ticks(circuit)[t0:t1]):
        if k:
            out.append("TICK")
        for inst in layer:
            if inst.name not in ("DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS", "SHIFT_COORDS"):
                out.append(inst)
    return out


def g4_without_q7():
    """G4's extracted double check (CX form) with qubit 7's final M and its
    detector removed: the double check as G6 runs it (G6 never measures its q12,
    the counterpart of G4's q7, which sits on a data readout line)."""
    inner, _ = g4.inner_cx("cliffordea")
    layers = Q.to_layers(inner)
    drop = set()
    for items in layers:
        for it in list(items):
            if isinstance(it, Q.Op) and it.name == "M" and it.targets == [7]:
                drop.update(it.ids)
                items.remove(it)
    for items in layers:
        for it in list(items):
            if not isinstance(it, Q.Op) and it[0] == "det" and set(it[3]) & drop:
                items.remove(it)
    return Q.from_layers(layers)


def lines_of(qs, emb):
    return sorted({readout_line(emb[q]) for q in qs})


def run(out=Path("results")):
    g, emb = load_g6()
    ops = layer_ops(g)
    data = tagged_targets(g, "T_gate")
    # cultivation patch = qubits used up to the T layer; grafting starts at the first
    # TICK that touches a qubit outside it
    patch = sorted({q for t in range(0, 31) for _, qs in ops[t] for q in qs})
    graft_start = next(t for t, layer in enumerate(ops) if any(q not in patch for _, qs in layer for q in qs))
    meas = {t: sorted(q for n, qs in layer if stim.gate_data(n).produces_measurements for q in qs)
            for t, layer in enumerate(ops)}
    meas = {t: m for t, m in meas.items() if m}
    cult_meas = {t: m for t, m in meas.items() if t < graft_start}
    dc_anc = sorted({q for t in range(31, 51) for _, qs in ops[t] for q in qs} - set(data))
    dc_measured = sorted({q for t in range(31, graft_start) for q in meas.get(t, [])})
    rec = dict(file=str(G6_FILE), qubits=g.num_qubits, ticks=g.num_ticks,
               cultivation_data=data, data_positions={q: emb[q] for q in data},
               data_lines=lines_of(data, emb), cultivation_patch=patch,
               grafting_starts_at_tick=graft_start,
               double_check_ancillas=dc_anc, ancilla_positions={q: emb[q] for q in dc_anc},
               ancilla_lines={q: readout_line(emb[q]) for q in dc_anc},
               cultivation_measurements={t: [(q, emb[q], readout_line(emb[q])) for q in m]
                                         for t, m in cult_meas.items()},
               double_check_measured=dc_measured,
               double_check_never_measured=sorted(set(dc_anc) - set(dc_measured)),
               resets_at_end_of_cultivation=[qs for n, qs in ops[graft_start - 1] if n == "R"])
    # strict rule (current live rule) on the whole G6, data = cultivation data and none
    for label, dq in (("data_cultivation", data), ("data_none", ())):
        for fl in ("auto", "check"):
            v = C.check_circuit(g, emb, data_qubits=tuple(dq), final_layer=fl)
            rec[f"strict_whole_G6_{label}_final_{fl}"] = dict(n=len(v), summary=C.summarize(v))
    # continuing-data rule restricted to the cultivation stage (TICKs 0 .. graft_start-1)
    cult = sub_circuit(g, 0, graft_start)
    v = C.continuing_data_violations(cult, emb, data)
    rec["continuing_data_cultivation_stage"] = dict(n=len(v), violations=[str(x) for x in v])
    v = C.check_circuit(cult, emb, data_qubits=tuple(data), data_continue=True)
    rec["strict_plus_continuing_cultivation_stage"] = dict(n=len(v), summary=C.summarize(v))
    # What if q12 (on data line 13) had been measured with the others at TICK 55?
    what_if = [x for x in C.continuing_data_violations(cult, emb, data)]
    rec["what_if_q12_measured"] = [dict(data=d, at=emb[d]) for d in data
                                   if readout_line(emb[d]) == readout_line(emb[12])]
    # surface-code stage: which qubits are measured at the first surface-code round
    t_sc = next(t for t in sorted(meas) if t > graft_start)
    sc_qubits = sorted({q for t in range(graft_start, len(ops)) for _, qs in ops[t] for q in qs})
    sc_meas = meas[t_sc]
    sc_data = sorted(set(sc_qubits) - set(sc_meas))
    rec["surface_code"] = dict(
        first_round_measure_tick=t_sc, measure_qubits=sc_meas, data_qubits=sc_data,
        measure_line_parities=sorted({readout_line(emb[q]) % 2 for q in sc_meas}),
        data_line_parities=sorted({readout_line(emb[q]) % 2 for q in sc_data}),
        measure_lines=lines_of(sc_meas, emb), data_lines=lines_of(sc_data, emb),
        lines_disjoint=not (set(lines_of(sc_meas, emb)) & set(lines_of(sc_data, emb))),
        cultivation_data_become=dict(measure=[q for q in data if q in sc_meas],
                                     data=[q for q in data if q in sc_data]),
        cultivation_ancillas_become=dict(measure=[q for q in dc_anc if q in sc_meas],
                                         data=[q for q in dc_anc if q in sc_data]))
    # G4 <-> G6 layout map (one lattice symmetry + translation)
    g4c = g4.load_g4()
    e4 = {q: tuple(int(x) for x in p) for q, p in C.native_coords(g4c).items()}
    rec["g4_data_lines"] = lines_of(g4.DATA, e4)
    rec["g4_ancilla_lines"] = {q: readout_line(e4[q]) for q in g4.ANC}
    # cliffordea: G4 vs G4 with q7 unmeasured (= G6's double check)
    rows = {}
    for name, inner in (("G4-CX", g4.inner_cx("cliffordea")[0]), ("G4-CX, q7 unmeasured (G6 style)", g4_without_q7())):
        e = {q: tuple(int(x) for x in p) for q, p in C.native_coords(inner).items()}
        full = g4.full_for(inner)
        r2, r3 = verify(full, inner, max_fault_count=2), verify(full, inner, max_fault_count=3)
        eq = Q.check_equivalence(inner, full)
        rows[name] = dict(
            continuing=len(C.continuing_data_violations(inner, e)),
            strict=len(C.check_circuit(inner, e)), equivalence_ok=eq["ok"],
            malignant_T=[r3["T"][k]["malignant"] for k in range(4)],
            malignant_S_le2=sum(r2["S"][k]["malignant"] for k in range(3)),
            ler_T_mfc2=r2["error_rate_per_kept_shot"]["T"], ler_T_mfc3=r3["error_rate_per_kept_shot"]["T"])
        rows[name]["one_in_mfc3"] = round(1 / rows[name]["ler_T_mfc3"])
    rec["cliffordea"] = rows
    (out / "continuing_g6.json").write_text(json.dumps(rec, indent=1, default=str))
    return rec


if __name__ == "__main__":
    r = run()
    for k, v in r.items():
        if k not in ("cultivation_patch",):
            print(k, ":", v)
