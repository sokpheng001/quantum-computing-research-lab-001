"""Task B: every injective nearest-neighbour embedding of a circuit onto Willow.

Enumerates all injective maps from the circuit qubits to grid qubits such
that every two-qubit gate lands on a coupler (a subgraph-embedding search by
backtracking, not only rigid placements), and counts strict readout-line
violations for each (``constraints.readout_violations`` semantics, both with
the final measurement layer exempt and checked).

Usage: python -m nnflags.embed_search [--circuit d3a6] [--out results]
       python -m nnflags.embed_search --stim path/to/inner.stim --name google_dc
Writes results/embed_search_<name>.json (histograms, minima, examples).
"""
import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

import stim

from cliffordea import enum

from nnflags import constraints as C
from nnflags.willow import WILLOW, neighbours, readout_line


def interaction_graph(circuit: stim.Circuit) -> dict[int, set[int]]:
    """Qubits used by hardware ops -> distinct two-qubit partners."""
    g = {q: set() for layer in C.split_by_ticks(circuit)
         for _, qs, _ in C._hardware_ops(layer) for q in qs}
    for q, ps in C.partners(circuit).items():
        g[q] |= ps
    return g


def search_order(graph: dict[int, set[int]]) -> list[tuple[int, list[int]]]:
    """BFS order from a max-degree qubit; each entry (qubit, already-placed
    neighbours). Isolated components are started afresh (no placed neighbour)."""
    order, seen = [], set()
    for root in sorted(graph, key=lambda q: (-len(graph[q]), q)):
        if root in seen:
            continue
        queue = [root]
        seen.add(root)
        while queue:
            q = queue.pop(0)
            order.append((q, [p for p, _ in order if p in graph[q]]))
            for n in sorted(graph[q], key=lambda x: (-len(graph[x]), x)):
                if n not in seen:
                    seen.add(n)
                    queue.append(n)
    return order


def embeddings(graph, grid=WILLOW):
    """Yield every injective nearest-neighbour embedding (dict qubit -> (r, c))."""
    order = search_order(graph)
    nbrs = {p: set(neighbours(p, grid)) for p in grid}
    emb: dict[int, tuple[int, int]] = {}
    used: set = set()

    def rec(i):
        if i == len(order):
            yield dict(emb)
            return
        q, placed = order[i]
        if placed:
            cand = set.intersection(*(nbrs[emb[p]] for p in placed))
        else:
            cand = grid
        for p in sorted(cand - used):
            emb[q] = p
            used.add(p)
            yield from rec(i + 1)
            used.discard(p)
            del emb[q]

    yield from rec(0)


def readout_events(circuit, final_layer, live_rule=None, data_qubits=None):
    """[(tick, measured, victims)] for the strict rule (positions not yet fixed).
    ``final_layer`` / ``live_rule`` as in ``constraints.readout_violations``."""
    live, measured = C.liveness(circuit, data_qubits, live_rule=live_rule)
    ticks = [t for t, ms in enumerate(measured) if ms]
    exempt = final_layer == "exempt" or (
        final_layer == "auto" and C.final_layer_status(circuit)["exempt"])
    out = []
    for t in ticks:
        if t == ticks[-1] and exempt:
            continue
        out += [(t, m, sorted(live[t] - {m})) for m in sorted(measured[t])]
    return out


def count_violations(events, emb):
    n = 0
    for _, m, victims in events:
        line = readout_line(emb[m])
        n += sum(readout_line(emb[v]) == line for v in victims)
    return n


def run(circuit, name, out: Path, grid=WILLOW, sample_check=200, live_rule=None,
        final_layer="auto", suffix=""):
    """Histogram of strict conflicts over all embeddings. Key "exempt" = the
    final layer treated per ``final_layer`` ("auto": exempt only if
    ``constraints.final_layer_status`` holds; "exempt": unconditionally), key
    "check" = final layer always checked. Writes embed_search_<name><suffix>.json."""
    t0 = time.perf_counter()
    graph = interaction_graph(circuit)
    ev = {"exempt": readout_events(circuit, final_layer, live_rule),
          "check": readout_events(circuit, "check", live_rule)}
    hist = {fl: Counter() for fl in ev}
    best = {fl: None for fl in ev}
    by_event = {fl: Counter() for fl in ev}  # (tick, measured, victim) -> embeddings hit
    n = 0
    checked = 0
    for emb in embeddings(graph, grid):
        n += 1
        for fl, events in ev.items():
            k = count_violations(events, emb)
            hist[fl][k] += 1
            if best[fl] is None or k < best[fl][0]:
                best[fl] = (k, emb)
            if fl == "exempt":
                for t, m, victims in events:
                    for v in victims:
                        if readout_line(emb[v]) == readout_line(emb[m]):
                            by_event[fl][(t, m, v)] += 1
        if checked < sample_check and n % 997 == 1:
            # Cross-check the fast counter against check_circuit on a sample.
            vs = C.check_circuit(circuit, emb, grid=grid, live_rule=live_rule,
                                 final_layer=final_layer)
            assert all(x.kind == "readout" for x in vs), vs
            assert len(vs) == count_violations(ev["exempt"], emb)
            checked += 1
    rec = {
        "circuit": name, "grid": f"Willow, {len(grid)} qubits",
        "qubits": len(graph), "interaction_edges": sorted(
            {tuple(sorted((a, b))) for a in graph for b in graph[a]}),
        "is_tree": sum(len(v) for v in graph.values()) // 2 == len(graph) - 1,
        "embedding_count": n,
        "readout_events": {fl: [(t, m, vs) for t, m, vs in e] for fl, e in ev.items()},
        "histogram": {fl: dict(sorted(h.items())) for fl, h in hist.items()},
        "min_violations": {fl: b[0] for fl, b in best.items()},
        "example_min_embedding": {fl: b[1] for fl, b in best.items()},
        "embeddings_hit_per_violation_exempt": {
            f"tick {t}: M {m} vs {v}": c for (t, m, v), c in by_event["exempt"].most_common()},
        "fast_counter_cross_checked_against_check_circuit": checked,
        "live_rule": C._resolve_live_rule(live_rule, None), "final_layer": final_layer,
        "final_layer_status": C.final_layer_status(circuit),
        "runtime_s": time.perf_counter() - t0,
    }
    (out / f"embed_search_{name}{suffix}.json").write_text(json.dumps(rec, indent=1, default=str))
    return rec, graph


def mrx5_argument(circuit, out: Path):
    """d3a6: does every embedding have a victim of MRX 5 (TICK 6) among 9's
    other partners {8, 10, 12} on a grid point diagonal to 5 and adjacent to 9?"""
    graph = interaction_graph(circuit)
    live, _ = C.liveness(circuit)
    n = hit = 0
    for emb in embeddings(graph):
        n += 1
        p5 = emb[5]
        ok = any(readout_line(emb[v]) == readout_line(p5)
                 and abs(emb[v][0] - p5[0]) == 1 and abs(emb[v][1] - p5[1]) == 1
                 and v in live[6] for v in (8, 10, 12))
        hit += ok
    return {"embeddings": n, "with_mechanism": hit}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--circuit", default="d3a6")
    parser.add_argument("--stim", help="inner circuit file instead of a bundled DoubleCheck")
    parser.add_argument("--name")
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.stim:
        circuit, name = stim.Circuit.from_file(args.stim), args.name or Path(args.stim).stem
    else:
        fc = 2 if args.circuit.endswith("f2") else 0
        circuit = enum.circuits.DoubleCheck(distance=3, ancilla_count=6, flag_count=fc).INNER_CIRCUIT
        name = args.circuit
    rec, _ = run(circuit, name, out)
    if name == "d3a6":
        rec["mrx5_argument"] = mrx5_argument(circuit, out)
        (out / f"embed_search_{name}.json").write_text(json.dumps(rec, indent=1, default=str))
    for k in ("embedding_count", "is_tree", "histogram", "min_violations",
              "embeddings_hit_per_violation_exempt", "mrx5_argument", "runtime_s"):
        print(k, rec.get(k), flush=True)


if __name__ == "__main__":
    main()
