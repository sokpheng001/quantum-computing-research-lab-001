"""Option-1 task C: "same code + same double check" equivalence checker.

``check_equivalence(inner)`` verifies, for a candidate cliffordea inner circuit
(MPP marker on the data, double check, trailing reset), with cliffordea's own
derivations (``verify.load_measurement`` -> ``find_data_indices``,
``find_stabilizer_generators``, ``find_logical_s_gate``) and stim:

  (i)   code: the data code is the d=3 colour code of d3a6 up to a relabelling
        of the data qubits (stabiliser supports AND the logical-S sublattice
        map onto d3a6's), and the full circuit's MPP framing is consistent.
  (ii)  check: the circuit (MPP marker removed) acts on the data as a
        projective measurement of X_L = X^(x)7 -- cliffordea's H_XY check in
        the inner frame (enum/circuits/main.py:42-45):
          * forward check: the detector containing the MPP record compares
            the MPP with records R1, and stim flow  X_L -> rec[R1]  holds;
          * time-reversed check: a detector without the MPP record contains
            records of R1 plus records R2 measured later, and  X_L -> rec[R2]
            holds (the unfold re-reads the same logical after the reset);
          * X_L and every generator of its commutant (X_q, Z_a Z_b) pass
            unchanged:  P -> P xor rec[...] ;  Z_L has no such flow.
  (iii) reverse: in canonical CX form (``absorb_hadamards``), the two-qubit
        gate layers of the unfold are exactly the fold's layers in reverse
        order, and U_unfold * U_fold = identity (stim tableaux). Gates on
        ``flag_qubits`` are excluded (flags are added gates, decision 4).
  (iv)  all detectors are deterministic (stim, noiseless circuit).

Fold / unfold: the TICKs strictly between the ancilla preparation layer and
the forward-check measurement TICK, and between that TICK and the final
measurement TICK (re-preparations of the measured qubits are absorbed by the
canonical form).
"""
import itertools
from collections import defaultdict
from dataclasses import dataclass, field

import stim

from cliffordea.enum.circuit_tools import split_by_ticks

from nnflags.verify import bundled_paths, load_measurement

_ANNOT = ("DETECTOR", "OBSERVABLE_INCLUDE")
_SKIP = ("QUBIT_COORDS", "SHIFT_COORDS")


# ---- layered representation with global measurement ids -----------------------

@dataclass
class Op:
    name: str
    targets: list          # qubit ints (MPP: stim targets)
    args: list = field(default_factory=list)
    ids: list = field(default_factory=list)   # global measurement ids
    tag: str = ""


def to_layers(circuit: stim.Circuit):
    """[[Op | ('det', name, args, ids) | ('coords', instr)]], one list per TICK,
    with every measurement split per target and given a global id."""
    layers, n = [], 0
    for layer in split_by_ticks(circuit):
        items = []
        for op in layer:
            if isinstance(op, stim.CircuitRepeatBlock):
                raise ValueError("Repeat blocks not supported.")
            if op.name in _ANNOT:
                items.append(("det", op.name, op.gate_args_copy(),
                              [n + t.value for t in op.targets_copy()]))
            elif op.name in _SKIP:
                items.append(("coords", op))
            elif op.name == "MPP":
                k = op.num_measurements
                items.append(Op("MPP", op.targets_copy(), op.gate_args_copy(),
                                list(range(n, n + k)), op.tag))
                n += k
            else:
                gd = stim.gate_data(op.name)
                ts = [t.value for t in op.targets_copy()]
                step = 2 if gd.is_two_qubit_gate else 1
                for i in range(0, len(ts), step):
                    ids = []
                    if gd.produces_measurements:
                        ids = [n]
                        n += 1
                    items.append(Op(op.name, ts[i:i + step], op.gate_args_copy(), ids, op.tag))
        layers.append(items)
    return layers


def from_layers(layers) -> stim.Circuit:
    """Inverse of ``to_layers`` (ops of the same name/args/tag are grouped per
    TICK; detector lookbacks are rebuilt from the global ids)."""
    out, n, pos = stim.Circuit(), 0, {}
    for i, items in enumerate(layers):
        if i:
            out.append("TICK")
        groups: dict = {}
        order = []
        for it in items:
            if isinstance(it, Op):
                key = (it.name, tuple(it.args), it.tag)
                if it.name == "MPP":
                    key = (it.name, tuple(it.args), it.tag, id(it))
                if key not in groups:
                    groups[key] = []
                    order.append(("op", key))
                groups[key].append(it)
            else:
                order.append(("x", it))
        for kind, x in order:
            if kind == "op":
                ops = groups[x]
                if x[0] == "MPP":
                    o = ops[0]
                    out.append(stim.CircuitInstruction("MPP", o.targets, o.args, tag=o.tag))
                    for k, gid in enumerate(o.ids):
                        pos[gid] = n + k
                    n += len(o.ids)
                    continue
                ts = [t for o in ops for t in o.targets]
                out.append(stim.CircuitInstruction(x[0], ts, list(x[1]), tag=x[2]))
                for o in ops:
                    for gid in o.ids:
                        pos[gid] = n
                        n += 1
            elif x[0] == "coords":
                out.append(x[1])
            else:  # detector / observable, emitted after this TICK's measurements
                pass
        for it in items:
            if not isinstance(it, Op) and it[0] == "det":
                out.append(it[1], [stim.target_rec(pos[g] - n) for g in it[3]], it[2])
    return out


# ---- canonical CX form: absorb Hadamard frames --------------------------------

_H = stim.Tableau.from_named_gate("H")
_1Q = {}
for _name in sorted(stim.gate_data()):
    _gd = stim.gate_data(_name)
    if _gd.is_unitary and _gd.is_single_qubit_gate:
        _1Q.setdefault(str(stim.Tableau.from_named_gate(_name)), _name)


def _conj_1q(name, h):
    if not h:
        return name
    t = _H.then(stim.Tableau.from_named_gate(name)).then(_H)
    return _1Q[str(t)]


def _conj_2q(name, a, b, ha, hb):
    """H^h G H^h for a two-qubit Clifford G on (a, b) -> (name, a', b')."""
    if not (ha or hb):
        return name, a, b
    c = stim.Circuit()
    for q, h in ((0, ha), (1, hb)):
        if h:
            c.append("H", [q])
    c.append(name, [0, 1])
    for q, h in ((0, ha), (1, hb)):
        if h:
            c.append("H", [q])
    t = stim.Tableau.from_circuit(c)
    for cand, x, y in (("CX", 0, 1), ("CX", 1, 0), ("CZ", 0, 1), ("XCX", 0, 1),
                       ("CY", 0, 1), ("CY", 1, 0), ("YCX", 0, 1), ("XCY", 0, 1),
                       ("YCY", 0, 1), ("XCZ", 0, 1), ("XCZ", 1, 0), ("YCZ", 0, 1),
                       ("YCZ", 1, 0), ("SWAP", 0, 1)):
        cc = stim.Circuit()
        cc.append(cand, [x, y])
        if stim.Tableau.from_circuit(cc) == t:
            return cand, (a, b)[x], (a, b)[y]
    raise ValueError(f"cannot conjugate {name}")


_MEAS = {("M", 0): "M", ("M", 1): "MX", ("MX", 0): "MX", ("MX", 1): "M"}
_RES = {("R", 0): "R", ("R", 1): "RX", ("RX", 0): "RX", ("RX", 1): "R"}


def _segments(layers, data):
    """Frame segments (qubit, start layer) that matter: a qubit's start or a
    reset, followed by at least one unitary gate before its next reset. (The
    frame of the other segments only fixes a reset basis; ``_apply_frames``
    then picks the basis that lets a measure-reset stay one MR/MRX.)"""
    events = defaultdict(list)  # qubit -> [(layer, kind)]
    for t, items in enumerate(layers):
        for it in items:
            if isinstance(it, Op) and it.name != "MPP":
                gd = stim.gate_data(it.name)
                kind = "reset" if gd.is_reset else ("gate" if gd.is_unitary and it.name != "I"
                                                    else "other")
                for q in it.targets:
                    events[q].append((t, kind))
    segs = []
    for q, ev in events.items():
        starts = [(-1, 0)] + [(t, i + 1) for i, (t, k) in enumerate(ev) if k == "reset"]
        for t, i in starts:
            if q in data and t == -1:
                continue
            nxt = ev[i:]
            stop = next((j for j, (_, k) in enumerate(nxt) if k == "reset"), len(nxt))
            if any(k == "gate" for _, k in nxt[:stop]):
                segs.append((q, t))
    return segs


def _apply_frames(layers, data, choice, drop_identity=True):
    """Rewrite with frame bits; returns (new layers, #non-CX 2q gates, data ok)."""
    h = defaultdict(int)
    new, bad, split = [], 0, 0
    for t, items in enumerate(layers):
        out = []
        for it in items:
            if not isinstance(it, Op):
                out.append(it)
                continue
            n = it.name
            if n == "MPP":
                if any(h[tq.value] for tq in it.targets if tq.is_qubit_target or tq.is_x_target
                       or tq.is_y_target or tq.is_z_target):
                    raise ValueError("MPP on a Hadamard-framed qubit")
                out.append(it)
                continue
            gd = stim.gate_data(n)
            if n == "H":
                h[it.targets[0]] ^= 1
            elif n == "I" and drop_identity:
                pass
            elif gd.is_two_qubit_gate:
                a, b = it.targets
                name, x, y = _conj_2q(n, a, b, h[a], h[b])
                bad += name != "CX"
                out.append(Op(name, [x, y], it.args, it.ids, ""))
            elif gd.is_reset or gd.produces_measurements:
                q = it.targets[0]
                if gd.produces_measurements:
                    base = {"M": "M", "MX": "MX", "MR": "M", "MRX": "MX"}[n]
                    mname = _MEAS[(base, h[q])]
                    if not gd.is_reset:
                        out.append(Op(mname, [q], it.args, it.ids))
                        continue
                rbase = {"R": "R", "RX": "RX", "MR": "R", "MRX": "RX"}[n]
                if (q, t) in choice:
                    h[q] = choice[(q, t)]
                elif gd.produces_measurements:  # free frame: keep MR / MRX in one op
                    h[q] = int(_RES[(rbase, 0)] != ("R" if mname == "M" else "RX"))
                else:
                    h[q] = 0
                rname = _RES[(rbase, h[q])]
                if gd.produces_measurements:
                    if (mname, rname) in (("M", "R"), ("MX", "RX")):
                        out.append(Op("MR" if rname == "R" else "MRX", [q], it.args, it.ids))
                    else:
                        out.append(Op(mname, [q], it.args, it.ids))
                        out.append(Op(rname, [q]))  # same TICK; rejected by the caller
                        split += 1
                else:
                    out.append(Op(rname, [q]))
            elif gd.is_unitary and gd.is_single_qubit_gate:
                out.append(Op(_conj_1q(n, h[it.targets[0]]), it.targets, it.args, it.ids, it.tag))
            else:
                raise ValueError(f"unsupported op {n}")
        new.append(out)
    data_ok = all(h[q] == 0 for q in data)
    return new, bad + 1000 * split, data_ok


def _merge_and_compact(layers):
    """Merge 'M q | R q' (next TICK holds only resets) into MR/MRX, and drop
    TICKs with no hardware op (their detectors move to the previous TICK)."""
    layers = [list(x) for x in layers]
    for t in range(len(layers) - 1):
        nxt = [it for it in layers[t + 1] if isinstance(it, Op)]
        if not nxt or any(o.name not in ("R", "RX") for o in nxt):
            continue
        meas = {o.targets[0]: o for o in layers[t] if isinstance(o, Op)
                and o.name in ("M", "MX", "MR", "MRX")}
        if all(o.targets[0] in meas and (meas[o.targets[0]].name, o.name) in
               (("M", "R"), ("MX", "RX"), ("MR", "R"), ("MRX", "RX")) for o in nxt):
            for o in nxt:  # 'MR q; TICK; R q' also collapses (the second reset is redundant)
                m = meas[o.targets[0]]
                m.name = "MR" if o.name == "R" else "MRX"
            layers[t + 1] = [it for it in layers[t + 1] if not isinstance(it, Op)]
    out = []
    for i, items in enumerate(layers):
        if i == 0 or any(isinstance(it, Op) for it in items) or i == len(layers) - 1:
            out.append(items)
        else:
            out[-1].extend(items)
    return out


def absorb_hadamards(circuit: stim.Circuit, data_qubits=None, merge=True):
    """Canonical CX form of a CZ + H (or any H-sandwiched) circuit.

    Pushes every H into a per-qubit frame bit (actual state = H^h |phi>), so
    CZ(a, b) with exactly one framed qubit becomes CX, R/M on a framed qubit
    become RX/MX, I gates (placeholders) are dropped, and H-only TICKs vanish.
    The frame after each preparation of a non-data qubit is chosen (exhaustive
    search, up to 2^14 choices) to minimise the number of two-qubit gates that
    are not CX; data qubits start and must end with frame 0. With ``merge``,
    'M q; TICK; R q' (or 'MR q; TICK; R q') with matching bases becomes one
    MR / MRX TICK (cliffordea d3a4 convention, RESULTS_step3.md C2).

    :return (circuit, info): info = {"non_cx": n, "choice": {...}}.
    """
    layers = to_layers(circuit)
    if data_qubits is None:
        mpp = [it for items in layers for it in items if isinstance(it, Op) and it.name == "MPP"]
        data_qubits = {t.value for t in mpp[0].targets if not t.is_combiner} if mpp else set()
    data = set(data_qubits)
    segs = _segments(layers, data)
    has_h = any(isinstance(it, Op) and it.name == "H" for items in layers for it in items)
    best = None
    space = itertools.product((0, 1), repeat=len(segs)) if has_h and len(segs) <= 14 else [
        (0,) * len(segs)]
    for bits in space:
        choice = dict(zip(segs, bits))
        new, bad, ok = _apply_frames(layers, data, choice)
        if not ok:
            continue
        key = (bad, sum(bits))
        if best is None or key < best[0]:
            best = (key, new, choice)
    if best is None:
        raise ValueError("no frame choice returns the data qubits to the standard frame")
    new = _merge_and_compact(best[1]) if merge else best[1]
    for items in new:  # no qubit twice in a TICK after conversion
        qs = [q for it in items if isinstance(it, Op) and it.name != "MPP" for q in it.targets]
        assert len(qs) == len(set(qs)), items
    return from_layers(new), {"non_cx": best[0][0],
                              "choice": {f"q{q}@{t}": b for (q, t), b in best[2].items()}}


# ---- checks -------------------------------------------------------------------

def _data_perm_to_reference(meas, ref):
    """Bijection data(candidate) -> data(ref) mapping stabiliser supports and
    the logical-S majority set, or None."""
    cand_sup = {frozenset(s) for s in meas._STABILIZER_GENERATOR_INDICES}
    ref_sup = {frozenset(s) for s in ref._STABILIZER_GENERATOR_INDICES}
    maj = lambda m: {t.value for op in m.LOGICAL_S if op.name == "S" for t in op.targets_copy()}
    cd, rd = list(meas.DATA_INDICES), list(ref.DATA_INDICES)
    if len(cd) != len(rd) or len(cand_sup) != len(ref_sup):
        return None
    cm, rm = maj(meas), maj(ref)
    for perm in itertools.permutations(rd):
        f = dict(zip(cd, perm))
        if ({frozenset(f[q] for q in s) for s in cand_sup} == ref_sup
                and {f[q] for q in cm} == rm):
            return f
    return None


def is_deterministic(circuit: stim.Circuit) -> bool:
    try:
        circuit.detector_error_model(allow_gauge_detectors=False)
        return True
    except ValueError:
        return False


def _strip_mpp(circuit):
    """Inner circuit without its MPP marker (detectors referring to the MPP
    record lose that record) and the MPP's global measurement ids."""
    layers = to_layers(circuit)
    mpp_ids = set()
    for items in layers:
        for it in list(items):
            if isinstance(it, Op) and it.name == "MPP":
                mpp_ids.update(it.ids)
                items.remove(it)
    for items in layers:
        for k, it in enumerate(items):
            if not isinstance(it, Op) and it[0] == "det":
                items[k] = (it[0], it[1], it[2], [g for g in it[3] if g not in mpp_ids],
                            [g for g in it[3] if g in mpp_ids])
    return layers, mpp_ids


def _detectors(layers):
    """Global ids of each DETECTOR (MPP ids kept, also after ``_strip_mpp``)."""
    return [it[3] + (it[4] if len(it) > 4 else []) for items in layers for it in items
            if not isinstance(it, Op) and it[0] == "det" and it[1] == "DETECTOR"]


def _meas_order(layers):
    """Global measurement ids in record order (MPP excluded) -> record index."""
    ids = [g for items in layers for it in items if isinstance(it, Op) for g in it.ids]
    return {g: i for i, g in enumerate(ids)}


def _flow(circuit, n_records, inp, out, recs):
    terms = " xor ".join(f"rec[{r - n_records}]" for r in sorted(recs))
    text = f"{inp} -> {out}" + (f" xor {terms}" if terms else "")
    return circuit.has_flow(stim.Flow(text)), text


def _pauli(nq, qubits, p):
    s = ["_"] * nq
    for q in qubits:
        s[q] = p
    return "".join(s)


def check_logical_action(inner: stim.Circuit, data):
    """Check (ii). Returns dict with the flows found."""
    layers, mpp_ids = _strip_mpp(inner)
    bare = from_layers(layers)
    nq = inner.num_qubits
    order = _meas_order(layers)
    nrec = len(order)
    xl = _pauli(nq, data, "X")
    dets = _detectors(layers)
    fwd = [d for d in dets if set(d) & mpp_ids]
    res = {"forward_detectors": [], "reverse_detectors": [], "commutant": {}, "ok": True}
    r1_all = set()
    for d in fwd:
        r1 = {order[g] for g in d if g not in mpp_ids}
        ok, text = _flow(bare, nrec, xl, "1", r1)
        res["forward_detectors"].append(dict(records=sorted(r1), flow=text, holds=ok))
        res["ok"] &= ok
        r1_all |= r1
    if not fwd:
        res["ok"] = False
        res["error"] = "no detector contains the MPP record"
        return res
    last_r1 = max(r1_all)
    for d in dets:
        if set(d) & mpp_ids:
            continue
        recs = {order[g] for g in d}
        r1 = recs & r1_all
        r2 = recs - r1_all
        if r1 and r2 and min(r2) > last_r1:
            ok, text = _flow(bare, nrec, xl, "1", r2)
            res["reverse_detectors"].append(dict(records=sorted(recs), r2=sorted(r2),
                                                 flow=text, holds=ok))
    res["time_reversed_check"] = any(x["holds"] for x in res["reverse_detectors"])
    res["ok"] &= res["time_reversed_check"]
    # Commutant of X_L passes unchanged; Z_L does not.
    gens = {f"X{q}": _pauli(nq, [q], "X") for q in data}
    ds = sorted(data)
    gens.update({f"Z{a}Z{b}": _pauli(nq, [a, b], "Z") for a, b in zip(ds, ds[1:])})
    gens["X_L"] = xl
    for k, p in gens.items():
        sol = bare.solve_flow_measurements([stim.Flow(f"{p} -> {p}")])[0]
        res["commutant"][k] = sol is not None
        res["ok"] &= sol is not None
    zl = _pauli(nq, data, "Z")
    res["Z_L_preserved"] = bare.solve_flow_measurements([stim.Flow(f"{zl} -> {zl}")])[0] is not None
    res["ok"] &= not res["Z_L_preserved"]
    return res


def fold_unfold(inner: stim.Circuit, data, flag_qubits=()):
    """Two-qubit layers (flags excluded) of fold and unfold in canonical CX form,
    and the forward-check TICK, for check (iii)."""
    cx, info = absorb_hadamards(inner, data)
    layers = to_layers(cx)
    _, mpp_ids = _strip_mpp(cx)
    fwd = [d for d in _detectors(layers) if set(d) & mpp_ids]
    fwd_ids = {g for d in fwd for g in d if g not in mpp_ids}
    tick_of = {g: t for t, items in enumerate(layers) for it in items if isinstance(it, Op)
               for g in it.ids}
    t_check = max(tick_of[g] for g in fwd_ids)
    meas_ticks = sorted({tick_of[g] for g in tick_of if g not in mpp_ids})
    t_final = meas_ticks[-1]
    flags = set(flag_qubits)

    def two_q(t0, t1):
        out = []
        for t in range(t0, t1):
            gates = sorted((it.name, *it.targets) for it in layers[t] if isinstance(it, Op)
                           and stim.gate_data(it.name).is_two_qubit_gate
                           and not (set(it.targets) & flags))
            if gates:
                out.append(tuple(gates))
        return out

    return two_q(0, t_check), two_q(t_check + 1, t_final), cx, info


def _tableau(nq, layers_):
    c = stim.Circuit(f"I {nq - 1}")
    for gates in layers_:
        for name, a, b in gates:
            c.append(name, [a, b])
    return stim.Tableau.from_circuit(c)


def check_equivalence(inner, full=None, flag_qubits=(), reference="d3a6") -> dict:
    """Run checks (i)-(iv) on ``inner`` with ``full`` = the full circuit given
    to verify() (cliffordea reads only its MPPs and S layers; default: the
    bundled reference full circuit). ``flag_qubits`` are excluded from (iii).
    :return: {"i_code", "ii_check", "iii_reverse", "iv_deterministic": {"ok", ...}, "ok"}."""
    inner = inner if isinstance(inner, stim.Circuit) else stim.Circuit.from_file(str(inner))
    ref_full, ref_inner = bundled_paths(reference)
    if full is None:
        full = ref_full
    out = {}
    meas = load_measurement(full, inner)
    ref = load_measurement(ref_full, ref_inner)
    data = meas.DATA_INDICES
    perm = _data_perm_to_reference(meas, ref)
    out["i_code"] = dict(ok=perm is not None, data=data, relabelling=perm,
                         stabilizers=sorted(map(sorted, meas._STABILIZER_GENERATOR_INDICES)),
                         logical_s=str(meas.LOGICAL_S).split("\n"))
    out["ii_check"] = check_logical_action(inner, data)
    try:
        fold, unfold, cx, info = fold_unfold(inner, data, flag_qubits)
    except ValueError as e:  # e.g. no forward-check detector to split fold / unfold
        out["iii_reverse"] = dict(ok=False, error=str(e))
    else:
        exact = unfold == fold[::-1]
        nq = inner.num_qubits
        identity = (_tableau(nq, fold + unfold) == stim.Tableau(nq))
        out["iii_reverse"] = dict(ok=exact and identity and len(fold) > 0,
                                  exact_layer_reverse=exact, tableau_identity=identity,
                                  fold=fold, unfold=unfold, canonical_non_cx=info["non_cx"])
    out["iv_deterministic"] = dict(ok=is_deterministic(inner))
    out["ok"] = all(out[k]["ok"] for k in ("i_code", "ii_check", "iii_reverse", "iv_deterministic"))
    return out
