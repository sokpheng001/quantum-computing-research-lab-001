"""Hardware-constraint checks for a Stim circuit under an embedding onto Willow.

check_circuit(circuit, embedding) reports
  * unmapped / non-injective / off-grid qubits,
  * two-qubit gates that are not edges of G (non-neighbour),
  * qubits with more than ``max_degree`` distinct two-qubit partners,
  * readout-line conflicts (strict rule, see ``liveness`` / ``readout_violations``),
  * qubits used twice in one TICK.

Conventions (decisions, see RESULTS_steps0-2.md):
  * MPP is the noiseless boundary marker of cliffordea's inner circuits (it
    defines the data qubits), not a hardware operation, so it is ignored by
    the gate checks. Annotations and noise channels are ignored too.
  * Data qubits = cliffordea's ``find_data_indices`` (the MPP targets).
  * "Final layer" = the last TICK that contains a (non-MPP) measurement.
    Measurements in earlier TICKs are mid-circuit (``final_layer="check"``
    checks the final layer too).
  * Readout rule (user's answer, 2026-10-31; replaces the data-only rule of
    Steps 0-2): measuring any qubit dephases its whole r + c line, so every
    other qubit on that line that is live at that TICK is a violation,
    whatever its role. Live intervals: see ``liveness``.
  * Defaults since the Option-1 round (2026-11-01, user decisions 2 and 3):
    ``live_rule="gate"`` (a qubit idling in |0> is not live until its first
    H-like or two-qubit gate) and ``final_layer="auto"`` (final layer exempt
    only if ``final_layer_status`` holds). The Step-3 behaviour is
    ``live_rule="prep", final_layer="exempt"``.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

import stim

from cliffordea.enum.circuit_tools import split_by_ticks
from cliffordea.enum.circuits._base import find_data_indices

from nnflags.willow import WILLOW, Qubit, is_edge, readout_line

Embedding = dict[int, Qubit]


@dataclass(frozen=True)
class Violation:
    kind: Literal["unmapped", "not_injective", "off_grid", "non_neighbour",
                  "degree", "readout", "reuse_in_tick", "readout_continuing",
                  "data_measured"]
    detail: dict = field(hash=False, compare=False)

    def __str__(self):
        return f"{self.kind}: " + ", ".join(f"{k}={v}" for k, v in self.detail.items())


def _hardware_ops(layer: stim.Circuit):
    """Yield (name, qubit targets) of the hardware operations in one TICK."""
    for op in layer:
        if isinstance(op, stim.CircuitRepeatBlock):
            raise ValueError("Repeat blocks not supported.")
        if op.name == "MPP":
            continue
        gd = stim.gate_data(op.name)
        if gd.is_noisy_gate and not gd.produces_measurements or op.name.startswith("HERALDED"):
            continue
        if not (gd.is_unitary or gd.is_reset or gd.produces_measurements):
            continue  # annotations such as QUBIT_COORDS, DETECTOR
        qubits = [t.value for t in op.targets_copy() if t.is_qubit_target]
        if qubits:
            yield op.name, qubits, gd


def two_qubit_gates(circuit: stim.Circuit) -> list[tuple[int, str, int, int]]:
    """All two-qubit gate instances as (tick, name, q1, q2)."""
    out = []
    for tick, layer in enumerate(split_by_ticks(circuit)):
        for name, qubits, gd in _hardware_ops(layer):
            if gd.is_two_qubit_gate:
                out += [(tick, name, a, b) for a, b in zip(qubits[::2], qubits[1::2])]
    return out


def partners(circuit: stim.Circuit) -> dict[int, set[int]]:
    """Distinct two-qubit-gate partners of each qubit."""
    p: defaultdict[int, set[int]] = defaultdict(set)
    for _, _, a, b in two_qubit_gates(circuit):
        p[a].add(b)
        p[b].add(a)
    return dict(p)


def native_coords(circuit: stim.Circuit) -> Embedding:
    """QUBIT_COORDS of the circuit as (row, col) (may be half-integer)."""
    return {q: tuple(c) for q, c in circuit.get_final_qubit_coordinates().items()}


LIVE_RULES = ("gate", "prep", "prep_zdormant")
DEFAULT_LIVE_RULE = "gate"
FINAL_LAYER_MODES = ("auto", "exempt", "check")
DEFAULT_FINAL_LAYER = "auto"


def _resolve_live_rule(live_rule, z_reset_idle):
    """Map the Step-3 ``z_reset_idle`` keyword onto ``live_rule`` (old callers
    that pass ``z_reset_idle`` explicitly keep their old meaning)."""
    if live_rule is not None:
        if live_rule not in LIVE_RULES:
            raise ValueError(f"live_rule must be one of {LIVE_RULES}, not {live_rule!r}")
        return live_rule
    if z_reset_idle is None:
        return DEFAULT_LIVE_RULE
    return {"live": "prep", "not_live": "prep_zdormant"}[z_reset_idle]


def keeps_z_basis(name: str) -> bool:
    """Whether a single-qubit unitary maps Z to +-Z (I, Paulis, S, S_DAG, ...):
    it leaves a qubit idling in |0> (or |1>) in a Z eigenstate, which readout
    dephasing cannot disturb."""
    z = stim.Tableau.from_named_gate(name).z_output(0)
    return str(z)[1:] == "Z"


def liveness(circuit: stim.Circuit, data_qubits=None, *, live_rule=None, z_reset_idle=None):
    """Per-TICK live sets and measurements.

    ``live_rule="gate"`` (DEFAULT since the Option-1 round, user decision 2):
      * A qubit idling in a Z eigenstate is NOT live: at the start of the
        circuit, after R, after MR (it is in |0>), and after a measurement
        without reset (M/MX/MY end its use).
      * It becomes live at its first two-qubit gate or its first single-qubit
        gate that does not keep the Z basis (H, H_YZ, SQRT_X, ...); I, X, Y, Z,
        S, S_DAG keep it dormant (``keeps_z_basis``). It stays live until its
        measurement.
      * RX / RY / MRX / MRY prepare a superposition. On hardware RX = R then H
        in the same slot, so the qubit is live from the end of that TICK (it
        is busy, hence not a victim, during the TICK itself).
      * Data qubits (MPP targets of cliffordea inner circuits) are live from
        the start: they hold the injected state.
    ``live_rule="prep"`` (Step-3 default, RESULTS_step3.md): live from any
      preparation (R*, MR*, or any first gate) to the measurement; MR*/R*
      keep the qubit live.
    ``live_rule="prep_zdormant"`` (Step-3 optional refinement
      ``z_reset_idle="not_live"``): as "prep", but after R / MR the qubit is
      dormant until its next gate (any gate, also I).
    ``z_reset_idle="live"`` / ``"not_live"`` (old keyword) selects "prep" /
      "prep_zdormant" when ``live_rule`` is not given.

    :return (live, measured): ``live[t]`` = qubits that are live during TICK t
        and are not themselves measured or reset in TICK t (they are the
        possible victims of a measurement in TICK t); ``measured[t]`` = qubits
        measured in TICK t.
    """
    rule = _resolve_live_rule(live_rule, z_reset_idle)
    if data_qubits is None:
        data_qubits = find_data_indices(circuit)
    state = set(data_qubits)  # live between TICKs
    live, measured = [], []
    for layer in split_by_ticks(circuit):
        busy, meas, after = set(), set(), set(state)
        for name, qubits, gd in _hardware_ops(layer):
            if gd.produces_measurements or gd.is_reset:
                busy.update(qubits)
                if gd.produces_measurements:
                    meas.update(qubits)
                if gd.is_reset and rule != "prep" and name in ("R", "MR"):
                    after.difference_update(qubits)  # dormant in |0> until a gate
                elif gd.is_reset:  # RX/RY/MRX/MRY (and R/MR under "prep"): live afterwards
                    after.update(qubits)
                else:  # M, MX, MY: not live until the next preparation
                    after.difference_update(qubits)
            elif (rule == "gate" and gd.is_single_qubit_gate
                  and keeps_z_basis(name)):
                pass  # a Z-basis-preserving gate leaves the qubit as it was
            else:  # a gate prepares (or keeps) the qubit
                after.update(qubits)
        gated = after - busy
        live.append(frozenset((state | gated) - busy))
        measured.append(frozenset(meas))
        state = after
    return live, measured


def final_layer_status(circuit: stim.Circuit) -> dict:
    """User decision 3: the final measurement layer is exempt from the readout
    rule only IF all its measurements are simultaneous (one TICK) and any
    basis changes happen before it.

    Final layer = the last TICK containing a (non-MPP) measurement. Checked:
      * ``no_gate_at_or_after``: no unitary gate (any single- or two-qubit
        gate, I included) in that TICK or later, on any qubit. Resets after it
        are allowed (cliffordea's trailing reset layer). MX/MY in the final
        TICK count as "basis change before" (on hardware MX = H, then M).
      * ``simultaneous``: no other measurement after the last unitary gate,
        i.e. the measurements that end the circuit are not split over
        several TICKs.
    :return: {"final_tick", "exempt": bool, "no_gate_at_or_after",
        "simultaneous", "reasons": [...]}.
    """
    meas_ticks, gate_ticks = [], []
    for t, layer in enumerate(split_by_ticks(circuit)):
        for name, qubits, gd in _hardware_ops(layer):
            if gd.produces_measurements:
                meas_ticks.append(t)
            elif not gd.is_reset:
                gate_ticks.append(t)
    if not meas_ticks:
        return dict(final_tick=None, exempt=False, no_gate_at_or_after=True,
                    simultaneous=True, reasons=["no measurements"])
    final = max(meas_ticks)
    last_gate = max(gate_ticks, default=-1)
    no_gate = last_gate < final
    simultaneous = all(t == final for t in meas_ticks if t > last_gate)
    reasons = []
    if not no_gate:
        reasons.append(f"unitary gate in TICK {last_gate} >= final measurement TICK {final}")
    if not simultaneous:
        reasons.append("final measurements split over TICKs "
                       f"{sorted({t for t in meas_ticks if t > last_gate})}")
    return dict(final_tick=final, exempt=no_gate and simultaneous,
                no_gate_at_or_after=no_gate, simultaneous=simultaneous, reasons=reasons)


def readout_violations(circuit, embedding, data_qubits=None, *, final_layer=None,
                       live_rule=None, z_reset_idle=None):
    """Strict readout-line rule.

    Measuring any qubit dephases its whole readout line (r + c). At every
    mid-circuit measurement of qubit m in TICK t, every other qubit on the
    same line that is live during TICK t is a violation, whatever the roles
    (data / ancilla / flag) of m and the victim. Qubits measured or reset in
    the same TICK are not victims (a simultaneous readout of the line is
    harmless to them).

    ``final_layer``:
      * ``"auto"`` (DEFAULT, user decision 3): the last TICK containing a
        measurement is exempt only if ``final_layer_status`` says so;
        otherwise it is checked like any other.
      * ``"exempt"``: unconditionally exempt (first-ex.md / Step-3 default).
      * ``"check"``: always checked.
    ``live_rule`` / ``z_reset_idle``: see ``liveness`` (default "gate").
    """
    final_layer = DEFAULT_FINAL_LAYER if final_layer is None else final_layer
    if final_layer not in FINAL_LAYER_MODES:
        raise ValueError(f"final_layer must be one of {FINAL_LAYER_MODES}, not {final_layer!r}")
    if data_qubits is None:
        data_qubits = find_data_indices(circuit)
    data_qubits = set(data_qubits)
    live, measured = liveness(circuit, data_qubits, live_rule=live_rule,
                              z_reset_idle=z_reset_idle)
    ticks = [t for t, ms in enumerate(measured) if ms]
    if not ticks:
        return []
    final_tick = ticks[-1]
    exempt = final_layer == "exempt" or (
        final_layer == "auto" and final_layer_status(circuit)["exempt"])
    by_line: defaultdict[int, list[int]] = defaultdict(list)
    for q, p in embedding.items():
        by_line[readout_line(p)].append(q)
    out = []
    for t in ticks:
        if t == final_tick and exempt:
            continue
        for m in sorted(measured[t]):
            line = readout_line(embedding[m])
            for v in sorted(by_line[line]):
                if v != m and v in live[t]:
                    out.append(Violation("readout", dict(
                        tick=t, measured=m, measured_at=embedding[m],
                        victim=v, victim_at=embedding[v],
                        victim_role="data" if v in data_qubits else "ancilla/flag",
                        line=line)))
    return out


def continuing_data_violations(circuit, embedding, data_qubits=None):
    """Continuing-data strict rule (user, 2026-11-01 evening; RESULTS_continuing_search.md).

    The data qubits (MPP targets) carry the state on into escape / grafting, so
    they are live from the start to beyond the end of the circuit. Every
    measurement of a non-data qubit, at whatever TICK (mid-check parity roots,
    final ancilla / flag readout, anything else), dephases its readout line and
    is a violation against every data qubit on that line. Simultaneity does not
    help, since the data are not measured. Equivalently: the readout lines of
    the data are disjoint from the lines of every measured qubit. A data qubit
    that is itself measured (not allowed inside the double check) is reported
    as kind "data_measured".

    One violation per (measurement event, data qubit) pair; a qubit measured
    twice on a data line counts twice.
    """
    if data_qubits is None:
        data_qubits = find_data_indices(circuit)
    data_qubits = set(data_qubits)
    by_line: defaultdict[int, list[int]] = defaultdict(list)
    for d in sorted(data_qubits):
        by_line[readout_line(embedding[d])].append(d)
    out = []
    for t, layer in enumerate(split_by_ticks(circuit)):
        for name, qubits, gd in _hardware_ops(layer):
            if not gd.produces_measurements:
                continue
            for m in qubits:
                if m in data_qubits:
                    out.append(Violation("data_measured", dict(tick=t, gate=name, qubit=m)))
                    continue
                line = readout_line(embedding[m])
                for d in by_line[line]:
                    out.append(Violation("readout_continuing", dict(
                        tick=t, measured=m, measured_at=embedding[m],
                        victim=d, victim_at=embedding[d], victim_role="data", line=line)))
    return out


def check_circuit(
        circuit: stim.Circuit,
        embedding: Embedding,
        *,
        grid: frozenset[Qubit] | None = WILLOW,
        max_degree: int = 4,
        ignore_readout: bool = False,
        data_qubits: tuple[int, ...] | None = None,
        readout: Literal["strict", "ignore"] = "strict",
        final_layer: Literal["auto", "exempt", "check"] | None = None,
        z_reset_idle: Literal["live", "not_live"] | None = None,
        live_rule: Literal["gate", "prep", "prep_zdormant"] | None = None,
        data_continue: bool = False,
) -> list[Violation]:
    """Return every constraint violation of ``circuit`` under ``embedding``.

    ``grid=None`` checks geometry only (unit axis-aligned steps between the
    embedded coordinates, e.g. the circuit's own QUBIT_COORDS).
    ``readout="ignore"`` (or the older ``ignore_readout=True``) turns the
    readout-line check off; see ``readout_violations`` for ``final_layer``.
    ``data_continue=True`` adds the continuing-data strict rule
    (``continuing_data_violations``) on top of the strict rule.
    """
    out: list[Violation] = []
    used = set()
    layers = split_by_ticks(circuit)
    for tick, layer in enumerate(layers):
        count: defaultdict[int, int] = defaultdict(int)
        for name, qubits, gd in _hardware_ops(layer):
            for q in qubits:
                count[q] += 1
                used.add(q)
        for q, n in sorted(count.items()):
            if n > 1:
                out.append(Violation("reuse_in_tick", dict(tick=tick, qubit=q, uses=n)))

    missing = sorted(q for q in used if q not in embedding)
    if missing:
        out.append(Violation("unmapped", dict(qubits=missing)))
        return out
    images = [embedding[q] for q in sorted(used)]
    if len(set(images)) != len(images):
        out.append(Violation("not_injective", dict(images=images)))
    if grid is not None:
        for q in sorted(used):
            if embedding[q] not in grid:
                out.append(Violation("off_grid", dict(qubit=q, at=embedding[q])))

    for tick, name, a, b in two_qubit_gates(circuit):
        if not is_edge(embedding[a], embedding[b], grid):
            out.append(Violation("non_neighbour", dict(
                tick=tick, gate=name, pair=(a, b), at=(embedding[a], embedding[b]))))

    for q, ps in sorted(partners(circuit).items()):
        if len(ps) > max_degree:
            out.append(Violation("degree", dict(qubit=q, partner_count=len(ps),
                                                partners=sorted(ps))))

    if readout not in ("strict", "ignore"):
        raise ValueError(f"readout must be 'strict' or 'ignore', not {readout!r}")
    if readout == "strict" and not ignore_readout:
        out += readout_violations(circuit, embedding, data_qubits, final_layer=final_layer,
                                  live_rule=live_rule, z_reset_idle=z_reset_idle)
        if data_continue:
            out += continuing_data_violations(circuit, embedding, data_qubits)
    return out


def summarize(violations: list[Violation]) -> dict[str, int]:
    s: defaultdict[str, int] = defaultdict(int)
    for v in violations:
        s[v.kind] += 1
    return dict(s)


# ---- embeddings -------------------------------------------------------------

SYMMETRIES = {
    "id": lambda r, c: (r, c),
    "rot90": lambda r, c: (c, -r),
    "rot180": lambda r, c: (-r, -c),
    "rot270": lambda r, c: (-c, r),
    "flip_r": lambda r, c: (-r, c),
    "flip_c": lambda r, c: (r, -c),
    "transpose": lambda r, c: (c, r),
    "antitranspose": lambda r, c: (-c, -r),
}


def grid_embeddings(circuit: stim.Circuit, grid: frozenset[Qubit] = WILLOW, coords=None):
    """All (symmetry, offset, embedding) placing the circuit's integer
    QUBIT_COORDS (or ``coords``) onto ``grid`` by a lattice symmetry plus
    translation. Empty if some coordinates are not integers."""
    coords = native_coords(circuit) if coords is None else coords
    if any(x != int(x) for xy in coords.values() for x in xy):
        return []
    out = []
    for name, f in SYMMETRIES.items():
        moved = {q: tuple(int(x) for x in f(*xy)) for q, xy in coords.items()}
        anchor = min(moved.values())
        for target in sorted(grid):
            dr, dc = target[0] - anchor[0], target[1] - anchor[1]
            emb = {q: (r + dr, c + dc) for q, (r, c) in moved.items()}
            if all(p in grid for p in emb.values()):
                out.append((name, (dr, dc), emb))
    return out


def extend_embedding(circuit, partial: Embedding, grid: frozenset[Qubit] = WILLOW, **kw):
    """Place the circuit qubits missing from ``partial`` on free grid qubits,
    brute force, minimising (non-neighbour gates, total Manhattan length of
    the two-qubit gates, total violations). Intended for a handful of extra
    qubits (e.g. 2 flags)."""
    import itertools
    used = {q for _, qs, _ in (x for layer in split_by_ticks(circuit)
                               for x in _hardware_ops(layer)) for q in qs}
    missing = sorted(used - set(partial))
    free = sorted(grid - set(partial.values()))
    gates = two_qubit_gates(circuit)
    best = None
    for spots in itertools.permutations(free, len(missing)):
        emb = {**partial, **dict(zip(missing, spots))}
        v = check_circuit(circuit, emb, grid=grid, **kw)
        length = sum(abs(emb[a][0] - emb[b][0]) + abs(emb[a][1] - emb[b][1])
                     for _, _, a, b in gates)
        key = (summarize(v).get("non_neighbour", 0), length, len(v), spots)
        if best is None or key < best[0]:
            best = (key, emb, v)
    return best[1], best[2]
