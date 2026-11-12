"""Step 1: constraint checks of d3a6 and d3a6f2 (native geometry and on Willow).

Usage: python -m nnflags.step1 [--readout strict|ignore] [--ignore-readout]
                               [--final-layer exempt|check] [--out results]
--ignore-readout is the same as --readout ignore. Output files:
results/step1.{json,txt} (strict, final layer exempt), step1_ignore_readout.*,
step1_final_layer_check.* (strict, final measurement layer checked too).
"""
import argparse
import json
import time
from collections import Counter
from pathlib import Path

from cliffordea import enum

from nnflags import constraints as C
from nnflags.willow import WILLOW, ascii_map

PRIMARY = ("id", (4, 4))
"""Primary d3a6 embedding: native QUBIT_COORDS shifted by (+4, +4)."""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--readout", choices=("strict", "ignore"), default="strict")
    parser.add_argument("--ignore-readout", action="store_true", help="same as --readout ignore")
    parser.add_argument("--final-layer", choices=("exempt", "check"), default="exempt")
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    if args.ignore_readout:
        args.readout = "ignore"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    kw = dict(readout=args.readout, final_layer=args.final_layer)
    lines, record = [], {"readout": args.readout, "final_layer": args.final_layer,
                         "ignore_readout": args.readout == "ignore"}

    def log(s=""):
        print(s)
        lines.append(str(s))

    d3a6 = enum.circuits.DoubleCheck(distance=3, ancilla_count=6).INNER_CIRCUIT
    d3a6f2 = enum.circuits.DoubleCheck(distance=3, ancilla_count=6, flag_count=2).INNER_CIRCUIT

    for name, circ in (("d3a6", d3a6), ("d3a6f2", d3a6f2)):
        v = C.check_circuit(circ, C.native_coords(circ), grid=None, **kw)
        log(f"== {name}: native QUBIT_COORDS geometry (no grid) -> {C.summarize(v)}")
        for x in v:
            log(f"   {x}")
        record[f"{name}_native"] = [str(x) for x in v]

    # d3a6 on Willow: every lattice symmetry + translation that fits.
    embs = C.grid_embeddings(d3a6)
    stats = Counter()
    per_sym = {}
    for sym, off, emb in embs:
        v = C.summarize(C.check_circuit(d3a6, emb, **kw))
        nn_deg_ok = not (v.get("non_neighbour") or v.get("degree") or v.get("reuse_in_tick"))
        stats["nn_degree_ok" if nn_deg_ok else "nn_degree_fail"] += 1
        stats["readout_ok" if not v.get("readout") else "readout_fail"] += 1
        per_sym.setdefault(sym, Counter())[v.get("readout", 0)] += 1
    log(f"settings: distance 3, ancilla_count 6, flag_count 0 / 2; readout {args.readout}, "
        f"final measurement layer {args.final_layer}")
    log(f"\n== d3a6 on Willow: {len(embs)} embeddings (8 symmetries x translations) -> {dict(stats)}")
    log("   readout violations per embedding, by symmetry: "
        + "; ".join(f"{s}: {dict(c)}" for s, c in per_sym.items()))
    record["d3a6_all_embeddings"] = {"count": len(embs), "stats": dict(stats),
                                     "readout_by_symmetry": {s: dict(c) for s, c in per_sym.items()}}

    emb6 = next(e for s, o, e in embs if (s, o) == PRIMARY)
    v6 = C.check_circuit(d3a6, emb6, **kw)
    log(f"\n== d3a6 primary embedding {PRIMARY}: {emb6}")
    log(f"   violations: {C.summarize(v6)}")
    for x in v6:
        log(f"   {x}")
    log(ascii_map(marks={p: chr(ord('a') + q) for q, p in emb6.items()}))
    record["d3a6_primary"] = {"embedding": {q: p for q, p in emb6.items()},
                              "violations": [str(x) for x in v6]}

    # d3a6f2: the 13 shared qubits keep the d3a6 placement (matched by native
    # coordinates); the two flags go on the free Willow qubits that minimise
    # the number of non-neighbour gates.
    coords6 = C.native_coords(d3a6)
    coords_to_q6 = {xy: q for q, xy in coords6.items()}
    partial = {q: emb6[coords_to_q6[xy]] for q, xy in C.native_coords(d3a6f2).items()
               if xy in coords_to_q6}
    emb2, v2 = C.extend_embedding(d3a6f2, partial, **kw)
    log(f"\n== d3a6f2 on Willow: shared qubits as d3a6 primary, flags placed by "
        f"extend_embedding: {emb2}")
    log(f"   violations: {C.summarize(v2)}")
    for x in v2:
        log(f"   {x}")
    log(ascii_map(marks={p: chr(ord('a') + q) for q, p in emb2.items()}))
    record["d3a6f2_willow"] = {"embedding": emb2, "violations": [str(x) for x in v2]}

    record["runtime_s"] = time.perf_counter() - t0
    log(f"\nruntime_s: {record['runtime_s']:.2f}")
    suffix = ("_ignore_readout" if args.readout == "ignore" else
              "_final_layer_check" if args.final_layer == "check" else "")
    (out / f"step1{suffix}.txt").write_text("\n".join(lines) + "\n")
    (out / f"step1{suffix}.json").write_text(json.dumps(record, indent=1, default=str))


if __name__ == "__main__":
    main()
