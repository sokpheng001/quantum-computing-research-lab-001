"""Task C (item 4): Google's experimental double check under the strict readout rule.

Sources (copies in nnflags/data/google_circuits/):
  * chan2609_sec5_experimental_double_check.url.txt: the Crumble link in
    Section 5 of Chan, Strikis, Sun & Cai, arXiv:2609.17706v3 ("the distance-3
    double check used in the experimental realisation of MSC [8]").
  * rosenfeld2512_crumble_urls.txt: the Crumble links in the appendix of
    Rosenfeld et al., arXiv:2512.13908 ([8], Google), G0..G6 in paper order;
    G4 = "Figure 2: cultivation" (complete circuit as run), G5 = Figure 3
    kickback tomography, G6 = Figure 4 grafting. G4-G6 use Willow (row, col)
    coordinates.

Usage: python -m nnflags.google_check [--out results]
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import stim

from cliffordea import enum

from nnflags import constraints as C
from nnflags import embed_search
from nnflags.crumble import crumble_to_stim
from nnflags.verify import bundled_paths, verify
from nnflags.willow import WILLOW

DATA = Path(__file__).with_name("data") / "google_circuits"
GOOGLE = {"G4": "Fig. 2 cultivation (as run)", "G5": "Fig. 3 kickback tomography",
          "G6": "Fig. 4 grafting N=2 with cultivation"}
LINES = {  # alternative line definitions, implemented by remapping (r, c)
    "r+c": lambda p: p, "r-c": lambda p: (p[0], -p[1]),
    "row": lambda p: (p[0], 0), "col": lambda p: (0, p[1])}


def rotate45(coords):
    """Crumble/cliffordea d3a4 coordinates (diagonal lattice, half-integer
    ancillas) -> square-grid (r, c) = (x + y, y - x)."""
    return {q: (int(round(x + y)), int(round(y - x))) for q, (x, y) in coords.items()}


def hardware_layers(circuit, merge_mx_rx=False):
    """Per-TICK (name, targets) of hardware ops except MPP and S/S_DAG
    (the logical S layers exist only in the full circuit); empty TICKs dropped."""
    layers = []
    for layer in C.split_by_ticks(circuit):
        ops = tuple((n, tuple(qs)) for n, qs, _ in C._hardware_ops(layer)
                    if n not in ("S", "S_DAG"))
        if ops:
            layers.append(ops)
    if merge_mx_rx:  # full circuit: "MX q; TICK; RX q" == inner "MRX q"
        out, i = [], 0
        while i < len(layers):
            if (i + 1 < len(layers) and len(layers[i]) == 1 and layers[i][0][0] == "MX"
                    and layers[i + 1] == (("RX", layers[i][0][1]),)):
                out.append((("MRX", layers[i][0][1]),))
                i += 2
            else:
                out.append(layers[i])
                i += 1
        layers = out
    return layers


def counts(circuit, emb, data_qubits=None, **kw):
    v = C.readout_violations(circuit, emb, data_qubits, **kw)
    return len(v), [str(x) for x in v]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results")
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    rec = {}

    # ---- Chan et al. Sec. 5 Crumble link --------------------------------
    url = (DATA / "chan2609_sec5_experimental_double_check.url.txt").read_text().strip()
    full = crumble_to_stim(url)
    (DATA / "chan2609_sec5_experimental_double_check.full.stim").write_text(str(full))
    b_full, b_inner = bundled_paths("d3a4")
    inner = stim.Circuit.from_file(str(b_inner))
    r = {"url_chars": len(url), "qubits": full.num_qubits, "ticks": full.num_ticks,
         "identical_to_bundled_d3a4_full": full == stim.Circuit.from_file(str(b_full)),
         "bundled_d3a4_inner_matches_crumble_gates":
             hardware_layers(full, merge_mx_rx=True) == hardware_layers(inner),
         "data_qubits": C.find_data_indices(inner)}
    # Neighbour / degree on the circuit's own geometry, rotated by 45 degrees.
    rot = rotate45(C.native_coords(full))
    v = C.check_circuit(full, rot, grid=None)
    r["native_rotated45"] = {"embedding": rot, "summary": C.summarize(v),
                             "violations": [str(x) for x in v],
                             "max_degree": max(map(len, C.partners(full).values()))}
    # Rigid placements of the rotated layout on Willow.
    rigid = C.grid_embeddings(full, coords=rot)
    rr = {}
    for fl in ("exempt", "check"):
        hist = Counter()
        for _, _, emb in rigid:
            s = C.summarize(C.check_circuit(full, emb, final_layer=fl))
            assert not (s.keys() - {"readout"}), s
            hist[s.get("readout", 0)] += 1
        rr[fl] = dict(sorted(hist.items()))
    r["rigid_willow_placements"] = {"count": len(rigid), "strict_readout_histogram": rr}
    # Every nearest-neighbour embedding (task B machinery) of the inner circuit.
    es, _ = embed_search.run(inner, "d3a4", out)
    r["all_nn_embeddings"] = {k: es[k] for k in (
        "embedding_count", "is_tree", "histogram", "min_violations",
        "embeddings_hit_per_violation_exempt", "readout_events")}
    # Same check on the full circuit (MX 8; TICK; RX 8 instead of MRX 8).
    best = es["example_min_embedding"]["exempt"]
    r["min_embedding_full_circuit_strict"] = counts(full, best)
    r["min_embedding_inner_circuit_strict"] = counts(inner, best)
    # verify(): full = the Crumble circuit, inner = cliffordea's d3a4 inner.
    vr = verify(full, inner, max_fault_count=2)
    r["verify"] = {"T": vr["T"], "S": vr["S"], "fault_count": vr["fault_count"],
                   "error_rate_per_kept_shot": vr["error_rate_per_kept_shot"],
                   "malignant_T": vr["malignant_configurations"]["T"],
                   "summary_text": vr["summary"].to_string(), "settings": vr["settings"]}
    rec["chan2609_sec5"] = r

    # ---- Google's own circuits as run, at their Willow coordinates --------
    lines = (DATA / "rosenfeld2512_crumble_urls.txt").read_text().splitlines()
    urls = {lines[i][2:].strip(): lines[i + 1].strip()
            for i in range(len(lines)) if lines[i].startswith("# G")}
    for key, label in GOOGLE.items():
        g = crumble_to_stim(urls[key])
        (DATA / f"rosenfeld2512_{key}.stim").write_text(str(g))
        emb = {q: tuple(int(x) for x in p) for q, p in C.native_coords(g).items()}
        _, measured = C.liveness(g, ())
        gr = {"label": label, "qubits": g.num_qubits, "ticks": g.num_ticks,
              "all_on_willow": all(p in WILLOW for p in emb.values()),
              "embedding": emb, "measurement_ticks": {
                  t: sorted(m) for t, m in enumerate(measured) if m},
              "neighbour_degree": C.summarize(C.check_circuit(g, emb, readout="ignore",
                                                              data_qubits=())),
              "max_degree": max(map(len, C.partners(g).values()))}
        for fl in ("exempt", "check"):
            for zi in ("live", "not_live"):
                gr[f"strict_{fl}_zreset_{zi}"] = counts(g, emb, (), final_layer=fl,
                                                        z_reset_idle=zi)
        gr["alt_lines_strict_exempt_live"] = {
            name: counts(g, {q: f(p) for q, p in emb.items()}, ())[0]
            for name, f in LINES.items()}
        rec[key] = gr

    (out / "google_check.json").write_text(json.dumps(rec, indent=1, default=str))
    r = rec["chan2609_sec5"]
    print({k: r[k] for k in ("identical_to_bundled_d3a4_full",
                             "bundled_d3a4_inner_matches_crumble_gates", "data_qubits")})
    print("native rotated:", r["native_rotated45"]["summary"], "max deg",
          r["native_rotated45"]["max_degree"])
    print("rigid:", r["rigid_willow_placements"])
    print("all NN:", {k: r["all_nn_embeddings"][k] for k in
                      ("embedding_count", "histogram", "min_violations")})
    print("min emb full/inner:", r["min_embedding_full_circuit_strict"][0],
          r["min_embedding_inner_circuit_strict"][0])
    print("verify T:", r["verify"]["T"], "S:", r["verify"]["S"])
    print(r["verify"]["summary_text"])
    for key in GOOGLE:
        g = rec[key]
        print(key, g["label"], g["qubits"], g["all_on_willow"], g["neighbour_degree"],
              "maxdeg", g["max_degree"],
              {k: v[0] for k, v in g.items() if k.startswith("strict_")},
              g["alt_lines_strict_exempt_live"])


if __name__ == "__main__":
    main()
