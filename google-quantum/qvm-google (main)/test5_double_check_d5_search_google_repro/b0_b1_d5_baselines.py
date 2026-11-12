"""Test 5, Part B, steps B0 and B1: the d = 5 double checks already in cliffordea.

B0 (baselines). For Gidney's d = 5 double check (d5a19) and Chan et al.'s flagged versions
(d5a19f3, d5a19f13, d5a19f18), all read from cliffordea's bundled stim files (cliffordea is
only read, never edited):
  * size: qubits, two-qubit gates, data qubits;
  * geometry at their own QUBIT_COORDS (square grid): non-nearest-neighbour gates, qubits with
    more than 4 partners (constraints.check_circuit with grid=None, readout off);
  * fault distance with real T: cliffordea's exact enumeration (nnflags.verify.verify, uniform
    depolarising noise, T and S) up to --max-faults faults.
B1 (Willow placement of Gidney's tree). Every lattice symmetry + translation of d5a19's own
coordinates that lands on the 105-qubit Willow grid; for each, the strict readout-line rule
(data measured at the end) and the continuing-data rule (data continue into escape).

    .venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b0_b1_d5_baselines.py" \
        [--max-faults 4] [--only d5a19,...]
    -> results/b0_<name>.json, results/b1_willow_placements.json, RESULTS_B0_B1.md
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import stim

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # google-quantum/
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from nnflags import constraints as C  # noqa: E402
from nnflags.continuing_data import data_qubits  # noqa: E402
from nnflags.verify import bundled_paths, verify  # noqa: E402
from nnflags.willow import WILLOW  # noqa: E402

RES = HERE / "results"
NAMES = ["d5a19", "d5a19f3", "d5a19f13", "d5a19f18"]
LABEL = {"d5a19": "Gidney et al. (original d = 5)", "d5a19f3": "Chan et al., 3 flags",
         "d5a19f13": "Chan et al., 13 flags", "d5a19f18": "Chan et al., 18 flags"}


def kst():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%b %d, %I:%M %p KST")


def log(*a):
    print(f"[{kst()}]", *a, flush=True)


def geometry(inner):
    emb = {q: (int(a), int(b)) for q, (a, b) in C.native_coords(inner).items()}
    v = C.check_circuit(inner, emb, grid=None, readout="ignore")
    s = C.summarize(v)
    used = {q for _, _, a, b in C.two_qubit_gates(inner) for q in (a, b)}
    far = sorted({tuple(sorted(x.detail["pair"])) for x in v if x.kind == "non_neighbour"})
    return dict(qubits=len(used | data_qubits(inner)), two_qubit_gates=len(C.two_qubit_gates(inner)),
                data=len(data_qubits(inner)), non_neighbour_gates=s.get("non_neighbour", 0),
                non_neighbour_pairs=len(far),
                max_partners=max(len(p) for p in C.partners(inner).values()),
                over_4_partners=s.get("degree", 0))


def fault_distance(counts, state):
    for k in sorted(counts[state]):
        if counts[state][k]["malignant"] > 0:
            return k
    return None  # > max faults


def b0(name, max_faults):
    full, inner_path = bundled_paths(name)
    inner = stim.Circuit.from_file(str(inner_path))
    out = dict(name=name, label=LABEL[name], geometry=geometry(inner))
    log(f"B0 {name}: geometry {out['geometry']}; enumerating up to {max_faults} faults")
    t0 = time.time()
    r = verify(full, inner_path, max_fault_count=max_faults)
    out.update(counts={s: r[s] for s in ("T", "S")}, fault_count=r["fault_count"],
               error_rate_per_kept_shot_p01=r["error_rate_per_kept_shot"],
               fault_distance={s: fault_distance(r, s) for s in ("T", "S")},
               max_faults=max_faults, runtime_s=round(time.time() - t0, 1))
    log(f"B0 {name}: fault distance T {out['fault_distance']['T']}, S {out['fault_distance']['S']} "
        f"(None = above {max_faults}); {out['runtime_s']} s")
    (RES / f"b0_{name}.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def b1():
    _, inner_path = bundled_paths("d5a19")
    inner = stim.Circuit.from_file(str(inner_path))
    data = tuple(sorted(data_qubits(inner)))
    placements = C.grid_embeddings(inner, WILLOW)
    rows = []
    for sym, off, emb in placements:
        strict = C.summarize(C.check_circuit(inner, emb, data_qubits=data))
        cont = C.summarize(C.check_circuit(inner, emb, data_qubits=data, data_continue=True))
        rows.append(dict(symmetry=sym, offset=off, strict=dict(strict), continuing=dict(cont),
                         strict_total=sum(strict.values()), continuing_total=sum(cont.values())))
    out = dict(placements=len(rows), rows=rows,
               best_strict=min((r["strict_total"] for r in rows), default=None),
               best_continuing=min((r["continuing_total"] for r in rows), default=None),
               zero_strict=sum(r["strict_total"] == 0 for r in rows),
               zero_continuing=sum(r["continuing_total"] == 0 for r in rows),
               kinds_continuing=dict(sum((Counter(r["continuing"]) for r in rows), Counter())))
    log(f"B1: {out['placements']} Willow placements; 0 violations: strict {out['zero_strict']}, "
        f"continuing {out['zero_continuing']}; best {out['best_strict']} / {out['best_continuing']}")
    (RES / "b1_willow_placements.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def one_in(x):
    return f"1 in {1 / x:,.0f}" if x and x > 0 else "0"


def report(rows, b1r, max_faults):
    L = [f"# Test 5, Part B, steps B0-B1: d = 5 baselines (written {kst()})", "",
         "Circuits: cliffordea's bundled d = 5 double checks (read only). Fault distance: cliffordea exact "
         f"enumeration with real T (uniform depolarising noise), up to {max_faults} faults; S = the Clifford "
         "stand-in, for comparison. Geometry: at the circuits' own square-grid coordinates.", "",
         "## B0: baselines", "",
         "| circuit | qubits | 2-qubit gates | non-neighbour pairs | max partners | fault distance, real T | fault distance, S | T error per kept shot, p = 0.1 % | enumeration time |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        g, fd = r["geometry"], r["fault_distance"]
        f = lambda k: str(k) if k is not None else f"> {max_faults}"
        L.append(f"| {r['label']} (`{r['name']}`) | {g['qubits']} | {g['two_qubit_gates']} | {g['non_neighbour_pairs']} | "
                 f"{g['max_partners']} | {f(fd['T'])} | {f(fd['S'])} | {one_in(r['error_rate_per_kept_shot_p01']['T'])} | {r['runtime_s']:,} s |")
    L += ["", "Malignant configuration counts (T), by number of faults:", ""]
    for r in rows:
        L.append(f"- `{r['name']}`: " + ", ".join(f"{k}: {v['malignant']}" for k, v in sorted(r["counts"]["T"].items(), key=lambda kv: int(kv[0]))))
    if b1r is not None:
        L += ["", "## B1: Gidney's d = 5 tree on Willow", "",
              f"- placements on the 105-qubit grid (lattice symmetry + translation of its own coordinates): **{b1r['placements']}**",
              f"- with 0 violations, data measured at the end (strict rule): **{b1r['zero_strict']}** (best: {b1r['best_strict']} violations)",
              f"- with 0 violations, data continuing (continuing-data rule): **{b1r['zero_continuing']}** (best: {b1r['best_continuing']} violations)",
              f"- violation kinds summed over placements (continuing): {b1r['kinds_continuing']}",
              "", "Only rigid placements of Gidney's own layout are tried here; re-embedding the tree "
              "(as in the cs02 search) is the next step if none is clean."]
    (HERE / "RESULTS_B0_B1.md").write_text("\n".join(L) + "\n")
    log("wrote", HERE / "RESULTS_B0_B1.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-faults", type=int, default=4)
    ap.add_argument("--only", default=",".join(NAMES))
    a = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    b1r = b1()
    rows = []
    for n in a.only.split(","):
        rows.append(b0(n, a.max_faults))
        report(rows, b1r, a.max_faults)
    log("done")


if __name__ == "__main__":
    main()
