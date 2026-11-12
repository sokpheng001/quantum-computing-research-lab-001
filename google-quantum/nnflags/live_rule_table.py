"""Option-1 task A: strict readout conflicts under the refined live rule.

d3a6 and d3a4 (cliffordea inner circuits): every injective nearest-neighbour
embedding onto Willow (embed_search machinery), min + histogram. G4 and G5
(Rosenfeld et al. as-run circuits): their real Willow coordinates.

Rule variants (constraints.readout_violations):
  new        live_rule="gate",          final_layer="auto"   (DEFAULT)
  new_check  live_rule="gate",          final_layer="check"
  old        live_rule="prep",          final_layer="exempt" (Step-3 default)
  old_zdorm  live_rule="prep_zdormant", final_layer="exempt" (Step-3 option)

Usage: python -m nnflags.live_rule_table [--out results]
Writes results/live_rule_table.json.
"""
import argparse
import json
import time
from collections import Counter
from pathlib import Path

import stim

from cliffordea import enum

from nnflags import constraints as C
from nnflags import embed_search as E
from nnflags.verify import bundled_paths

DATA = Path(__file__).with_name("data") / "google_circuits"
VARIANTS = {
    "new": dict(live_rule="gate", final_layer="auto"),
    "new_check": dict(live_rule="gate", final_layer="check"),
    "old": dict(live_rule="prep", final_layer="exempt"),
    "old_zdorm": dict(live_rule="prep_zdormant", final_layer="exempt"),
}


def all_embeddings(circuit, data_qubits=None):
    """{variant: (min, histogram, victims Counter)} over every NN embedding."""
    graph = E.interaction_graph(circuit)
    events = {k: E.readout_events(circuit, v["final_layer"], v["live_rule"], data_qubits)
              for k, v in VARIANTS.items()}
    hist = {k: Counter() for k in VARIANTS}
    victims = {k: Counter() for k in VARIANTS}
    n = 0
    for emb in E.embeddings(graph):
        n += 1
        for k, ev in events.items():
            hist[k][E.count_violations(ev, emb)] += 1
            for t, m, vs in ev:
                for v in vs:
                    if emb[v][0] + emb[v][1] == emb[m][0] + emb[m][1]:
                        victims[k][f"tick {t}: M {m} vs {v}"] += 1
        if n % 4999 == 1:  # cross-check the fast counter on a sample
            for k, v in VARIANTS.items():
                assert E.count_violations(events[k], emb) == len(
                    C.readout_violations(circuit, emb, data_qubits, **v))
    return n, {k: dict(min=min(h), histogram=dict(sorted(h.items())),
                       events=[(t, m, vs) for t, m, vs in events[k]],
                       victims=dict(victims[k].most_common()))
               for k, h in hist.items()}


def real_coords(circuit):
    emb = {q: tuple(int(x) for x in p) for q, p in C.native_coords(circuit).items()}
    out = {}
    for k, v in VARIANTS.items():
        vs = C.readout_violations(circuit, emb, (), **v)
        out[k] = dict(count=len(vs), violations=[str(x) for x in vs])
    return emb, out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results")
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    rec = {"variants": VARIANTS}
    for name in ("d3a6", "d3a4"):
        circ = stim.Circuit.from_file(str(bundled_paths(name)[1]))
        n, res = all_embeddings(circ)
        rec[name] = dict(embedding_count=n, final_layer_status=C.final_layer_status(circ),
                         **res)
        print(name, n, {k: (r["min"], r["histogram"]) for k, r in res.items()}, flush=True)
    for key in ("G4", "G5"):
        g = stim.Circuit.from_file(str(DATA / f"rosenfeld2512_{key}.stim"))
        emb, res = real_coords(g)
        rec[key] = dict(embedding=emb, final_layer_status=C.final_layer_status(g), **res)
        print(key, {k: r["count"] for k, r in res.items()}, flush=True)
        for k, r in res.items():
            for v in r["violations"]:
                print("   ", k, v)
    rec["runtime_s"] = time.perf_counter() - t0
    (out / "live_rule_table.json").write_text(json.dumps(rec, indent=1, default=str))


if __name__ == "__main__":
    main()
