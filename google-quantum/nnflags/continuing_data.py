"""Readout check in "continuing-data mode" (user request, Nov 1 2026).

The 7 data qubits are treated as live through the final measurement layer, as if
they continue into the escape stage. Every flag / ancilla measurement in that
final layer then conflicts with any data qubit on the same readout line r + c.
Mid-circuit conflicts are unchanged (constraints.check_circuit, strict).

    .venv/bin/python -m nnflags.continuing_data
"""

import glob
import json
from pathlib import Path

import stim

from nnflags import constraints as C
from nnflags.willow import readout_line

MEASURES = {"M", "MX", "MY", "MR", "MRX", "MRY"}


def data_qubits(inner: stim.Circuit) -> set[int]:
    return {t.value for inst in inner if inst.name == "MPP" for t in inst.targets_copy()
            if t.is_x_target or t.is_y_target or t.is_z_target}


def final_layer_measured(inner: stim.Circuit) -> set[int]:
    """Qubits measured in the last TICK that contains a measurement."""
    layers, cur = [], []
    for inst in inner.flattened():
        if inst.name == "TICK":
            layers.append(cur)
            cur = []
        else:
            cur.append(inst)
    layers.append(cur)
    for layer in reversed(layers):
        meas = {t.value for inst in layer if inst.name in MEASURES for t in inst.targets_copy()}
        if meas:
            return meas
    return set()


def continuing_data_conflicts(inner: stim.Circuit) -> list[dict]:
    emb = {q: (int(a), int(b)) for q, (a, b) in C.native_coords(inner).items()}
    data = data_qubits(inner)
    measured = final_layer_measured(inner) - data
    out = []
    for m in sorted(measured):
        for d in sorted(data):
            if readout_line(emb[m]) == readout_line(emb[d]):
                out.append(dict(measured=m, measured_at=emb[m], data=d, data_at=emb[d],
                                line=readout_line(emb[m])))
    return out


def strict_conflicts(inner: stim.Circuit, emb=None) -> list:
    """Continuing-data strict rule (constraints.continuing_data_violations) at the
    circuit's own QUBIT_COORDS (or ``emb``): every measurement of a non-data qubit,
    at any TICK, against every data qubit on its readout line."""
    if emb is None:
        emb = {q: (int(a), int(b)) for q, (a, b) in C.native_coords(inner).items()}
    return C.continuing_data_violations(inner, emb, data_qubits(inner))


def run():
    files = sorted(glob.glob("results/zz/success*.inner.stim"))
    files += ["results/g4/G4-CX.inner.stim", "results/g4/G4-native_CZH.inner.stim"]
    report = {}
    for f in files:
        inner = stim.Circuit.from_file(f)
        emb = {q: (int(a), int(b)) for q, (a, b) in C.native_coords(inner).items()}
        conf = continuing_data_conflicts(inner)
        mid = C.check_circuit(inner, emb)  # strict, default live rule and final-layer condition
        name = Path(f).name.replace(".inner.stim", "")
        report[name] = dict(continuing_data_conflicts=conf, n=len(conf), strict_default_violations=len(mid),
                            final_layer_measured=sorted(final_layer_measured(inner) - data_qubits(inner)))
        print(f"{name:22s} continuing-data conflicts: {len(conf)}  "
              + ", ".join(f"q{c['measured']}{c['measured_at']} vs data {c['data']}{c['data_at']} line {c['line']}"
                          for c in conf))
    Path("results/continuing_data.json").write_text(json.dumps(report, indent=1, default=str))
    return report


if __name__ == "__main__":
    run()


def reembed_search(inner: stim.Circuit, limit: int = 200_000):
    """All injective nearest-neighbour Willow embeddings of the circuit's 2-qubit-gate graph
    in which no measured (non-data) qubit shares a readout line with a data qubit,
    i.e. data and measured qubits sit on disjoint readout lines (continuing-data mode)."""
    from nnflags.willow import WILLOW, neighbours
    data = data_qubits(inner)
    qubits = sorted(C.native_coords(inner))
    adj = {q: set() for q in qubits}
    for inst in inner.flattened():
        if inst.name in ("CX", "CZ"):
            t = [x.value for x in inst.targets_copy()]
            for a, b in zip(t[::2], t[1::2]):
                adj[a].add(b)
                adj[b].add(a)
    start = max(qubits, key=lambda q: len(adj[q]))
    order, seen = [start], {start}
    while len(order) < len(qubits):
        nxt = max((q for q in qubits if q not in seen and adj[q] & seen), key=lambda q: len(adj[q] & seen))
        order.append(nxt)
        seen.add(nxt)
    found, pos, used = [], {}, set()

    def ok(q, p):
        line = readout_line(p)
        for o, po in pos.items():
            if (o in adj[q]) and p not in neighbours(po):
                return False
            if (q in data) != (o in data) and readout_line(po) == line:
                return False
        return True

    def rec(i):
        if len(found) >= limit:
            return
        if i == len(order):
            found.append(dict(pos))
            return
        q = order[i]
        placed_nb = [o for o in adj[q] if o in pos]
        cands = set(neighbours(pos[placed_nb[0]])) if placed_nb else set(WILLOW)
        for p in sorted(cands - used):
            if ok(q, p):
                pos[q] = p
                used.add(p)
                rec(i + 1)
                used.discard(p)
                del pos[q]

    rec(0)
    return found


def with_coords(inner: stim.Circuit, emb: dict) -> stim.Circuit:
    out = stim.Circuit()
    for inst in inner:
        if inst.name == "QUBIT_COORDS":
            q = inst.targets_copy()[0].value
            out.append("QUBIT_COORDS", [q], list(emb[q]))
        else:
            out.append(inst)
    return out
