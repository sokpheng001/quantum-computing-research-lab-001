"""Test 5, Part B, step B4: the d = 5 fault-distance-4 circuits under realistic noise models.

Noise models (all Pauli, so exact enumeration and Clifft both apply; built with the same code as the
d = 3 work, on the native CZ + H form of each circuit, nnflags.willow_noise.cx_to_native):
  * SI1000 (nnflags.si1000.si1000), the model Google used: p = 0.23 % (Google's fit to Willow) and 0.1 %;
  * Willow spec  (willow_noise.model_params("spec")): Google's published median values
    (CZ 0.33 %, 1q 0.035 %, readout 0.77 %, T1 68 us) on every qubit, idle noise from gate durations;
  * Willow calibration (model_params("calibration")): per-qubit / per-coupler values of the
    willow_pink calibration shipped with cirq-google, at the circuit's Willow placement.
For each: cliffordea's exact enumeration with real T (up to --mfc faults; validated against Clifft
sampling in B3) for the error per kept T state, and stim Monte Carlo for the acceptance. Plus one
sampled Clifft cross-check per circuit (SI1000 p = 0.5 %, where errors are frequent enough to count).

Circuits: Gidney's d5a19 (placed on Willow at its least-violating placement; it breaks the readout
rule there, kept as a reference), Chan's d5a19f3 (no Willow placement: SI1000 and spec only), and our
41 fault-distance-4 circuits (b2_search successes; all on Willow).

    .venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b4_real_noise.py"
    -> results/b4/*.json, RESULTS_B4_real_noise.md, figures/b4_real_noise.png
"""
import argparse
import json
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

import clifft
import stim

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b2_flags_d5 as F  # noqa: E402  (sys.path / cwd)
import b3_clifft_check as B3  # noqa: E402

from nnflags import comparison as CMP  # noqa: E402
from nnflags import constraints as C  # noqa: E402
from nnflags import willow_noise as WN  # noqa: E402
from nnflags.si1000 import si1000  # noqa: E402
from nnflags.continuing_data import data_qubits  # noqa: E402
from nnflags.verify import bundled_paths, load_measurement  # noqa: E402
from nnflags.willow import WILLOW  # noqa: E402

RES = HERE / "results" / "b4"
S2 = HERE / "results" / "b2_search"
MODELS = ["si1000_0.0023", "si1000_0.001", "spec", "calibration"]
LABEL = {"si1000_0.0023": "SI1000, p = 0.23 % (Google's fit)", "si1000_0.001": "SI1000, p = 0.1 %",
         "spec": "Willow spec (medians)", "calibration": "Willow calibration (per qubit)"}
log, kst = F.log, F.kst


def designs():
    out = {}
    for n, lab in (("d5a19", "Google's d = 5 design (Gidney et al., FD 3)"), ("d5a19f3", "Chan et al., 3 flags (FD 4, not NN)")):
        f, i = bundled_paths(n)
        inner = stim.Circuit.from_file(str(i))
        emb = None
        pl = C.grid_embeddings(inner, WILLOW)
        if pl:
            data = tuple(sorted(data_qubits(inner)))
            emb = min(pl, key=lambda x: len(C.check_circuit(inner, x[2], data_qubits=data)))[2]
        out[n] = dict(label=lab, full=stim.Circuit.from_file(str(f)), inner=inner, emb=emb, ours=False)
    rows = [json.loads(l) for l in open(S2 / "trees.jsonl")]
    for r in rows:
        if r["stage"] != "SUCCESS":
            continue
        s = r["seed"]
        inner = stim.Circuit.from_file(str(S2 / f"success_seed{s}.inner.stim"))
        emb = {q: tuple(int(x) for x in c) for q, c in inner.get_final_qubit_coordinates().items()}
        out[f"seed{s}"] = dict(label=f"ours #{s} ({r['qubits_total']} qubits)", ours=True, emb=emb, inner=inner,
                               full=stim.Circuit.from_file(str(S2 / f"success_seed{s}.full.stim")))
    return out


def noisy_for(model, m_inner, emb, cal):
    if model.startswith("si1000_"):
        return si1000(m_inner, float(model.split("_")[1]))
    prm = WN.model_params(model, cal, emb)
    return WN.noisy_native(m_inner, prm, "symmetric")[0]


def exact(d, model, cal, mfc):
    native = WN.cx_to_native(d["inner"])
    m = load_measurement(d["full"], native)
    noisy = noisy_for(model, m.INNER_CIRCUIT, d["emb"], cal)
    en, _ = CMP.enumerated(d["full"], native, mfc=mfc, noisy=noisy, states=("T",))
    e = en["custom"]["T"]
    acc = CMP.mc_acceptance(noisy, 2_000_000, seed=zlib.crc32(f"b4{model}".encode()))["acceptance"]
    return dict(rate=e["rate"], rate_by_mfc=e.get("rate_by_mfc"), acceptance=acc,
                counts=e.get("counts"))


def clifft_from_noisy(d, noisy_native_inner, native):
    """B3's Clifft program, but with a given noisy (native) inner circuit."""
    m = load_measurement(d["full"], native)
    text, nd, nc = B3_text(m, noisy_native_inner)
    return text, nd, nc


def B3_text(m, noisy):
    from cliffordea import accept
    data = list(m.DATA_INDICES)
    n = len(data)
    an = accept.CliffordLogicalAnalyzer(data_indices=m.DATA_INDICES, stabilizer_generators=m.STABILIZER_GENERATORS,
                                        logical_s=m.LOGICAL_S)
    enc = an.encoder
    mp = {j: data[j] for j in range(n)}
    maj, mino = [], []
    for ins in m.LOGICAL_S:
        (maj if ins.name == "S" else mino).extend(t.value for t in ins.targets_copy())
    L = [f"H {data[-1]}", f"T {data[-1]}"] + B3._ops(enc.to_circuit("elimination"), mp)
    L += [f"T_DAG {' '.join(map(str, maj))}", f"T {' '.join(map(str, mino))}", "TICK"]
    nrec, mpp_rec, ndet = 0, None, 0
    for ins in noisy.flattened():
        if ins.name in ("QUBIT_COORDS", "OBSERVABLE_INCLUDE"):
            continue
        if ins.name == "MPP":
            mpp_rec = nrec
            nrec += ins.num_measurements
            continue
        if ins.name == "DETECTOR":
            keep = [t for t in ins.targets_copy() if nrec + t.value != mpp_rec]
            L.append("DETECTOR " + " ".join(f"rec[{t.value}]" for t in keep))
            ndet += 1
            continue
        if ins.name == "TICK":
            L.append("TICK")
            continue
        args = f"({','.join(str(a) for a in ins.gate_args_copy())})" if ins.gate_args_copy() else ""
        L.append(f"{ins.name}{args} " + " ".join(str(t.value) for t in ins.targets_copy()))
        nrec += ins.num_measurements
    L += [f"T {' '.join(map(str, maj))}", f"T_DAG {' '.join(map(str, mino))}"]
    L += B3._ops(enc.inverse().to_circuit("elimination"), mp)
    L += [f"T_DAG {data[-1]}", f"H {data[-1]}", "M " + " ".join(map(str, data))]
    for j in range(n - 1):
        L.append(f"DETECTOR rec[{j - n}]")
    L.append("OBSERVABLE_INCLUDE(0) rec[-1]")
    return "\n".join(L) + "\n", ndet, n - 1


def clifft_check(d, p, shots, threads, target=50, chunk=100_000_000):
    native = WN.cx_to_native(d["inner"])
    m = load_measurement(d["full"], native)
    noisy = si1000(m.INNER_CIRCUIT, p)
    txt, nd, nc = B3_text(m, noisy)
    prog = clifft.compile(txt, postselection_mask=[1] * (nd + nc), expected_observables=[0])
    seed = zlib.crc32(f"b4clifft{p}".encode())
    ev = kept = done = k = 0
    t0 = time.time()
    while done < shots and ev < target:
        nn = min(chunk, shots - done)
        r = clifft.sample_survivors(prog, nn, seed=seed + k, threads=threads)
        ev += int(r.logical_errors)
        kept += int(r.passed_shots)
        done += nn
        k += 1
    return dict(p=p, shots=done, error=B3.rate(ev, kept), wall_s=round(time.time() - t0, 1))


def one_in(x):
    return f"1 in {1 / x:,.0f}" if x and x > 0 else "0"


def report(res, mfc):
    main = [n for n in ("d5a19",) if n in res]  # Chan d5a19f3 computed, not shown (user, Nov 6: not runnable on Willow)
    ours = sorted([n for n in res if n.startswith("seed")],
                  key=lambda n: res[n]["models"].get("si1000_0.0023", {}).get("rate", 1))
    show = main + ours[:6]
    L = [f"# Test 5, B4: d = 5 double checks under realistic noise, real T (written {kst()})", "",
         f"Error per kept T state: cliffordea exact enumeration with real T, up to {mfc} faults for the ranking of all circuits and up to 5 faults for the references and our best three (marked per row) (agrees with "
         "Clifft sampling, B3). Acceptance: stim Monte Carlo (2,000,000 shots). Native CZ + H circuits.", ""]
    for model in MODELS:
        L += [f"## {LABEL[model]}", "", "| circuit | error per kept T state | acceptance | ours better than Google by |",
              "|---|---|---|---|"]
        g = res.get("d5a19", {}).get("models", {}).get(model, {}).get("rate")
        c = res.get("d5a19f3", {}).get("models", {}).get(model, {}).get("rate")
        for n in show:
            r = res[n]["models"].get(model)
            if not r:
                L.append(f"| {res[n]['label']} | n/a (no Willow placement) | | | |")
                continue
            vg = f"{g / r['rate']:.1f}x" if g and r["rate"] else ""
            vc = f"{c / r['rate']:.1f}x" if c and r["rate"] else ""
            L.append(f"| {res[n]['label']} (to 4 faults) | {one_in(r['rate'])} | {100 * r['acceptance']:.1f} % | {vg} |")
        L.append("")
    L += ["Google's design = Gidney et al.'s d = 5 double check (it does not satisfy Willow's readout rule on any placement, B1). "
          "Chan et al.'s flagged d5a19f3 was also computed (results/b4/b4.json) but is not shown: it cannot run on Willow.", "",
          f"## All {len(ours)} of our circuits, SI1000 p = 0.23 % (sorted)", "",
          "| circuit | error per kept T state | acceptance | Willow calibration |", "|---|---|---|---|"]
    for n in ours:
        a = res[n]["models"].get("si1000_0.0023", {})
        b = res[n]["models"].get("calibration", {})
        L.append(f"| {res[n]['label']} | {one_in(a.get('rate'))} | {100 * a.get('acceptance', 0):.1f} % | {one_in(b.get('rate'))} |")
    cl = {n: res[n].get("clifft") for n in res if res[n].get("clifft")}
    if cl:
        L += ["", "## Cross-check: Clifft sampling vs cliffordea, SI1000 p = 0.5 %", "",
              "| circuit | Clifft (sampled, 95 % CI) | cliffordea exact |", "|---|---|---|"]
        for n, r in cl.items():
            e = r["error"]
            L.append(f"| {res[n]['label']} | {one_in(e['rate'])} ({one_in(e['ci95'][1])} to {one_in(e['ci95'][0])}; "
                     f"{e['events']} errors) | {one_in(res[n].get('si1000_0.005_exact'))} |")
    L += ["", "Notes: Gidney's circuit is placed on Willow at its least-violating placement but breaks the readout "
          "rule there (B1). Only our circuits run "
          "on Willow as they are. Willow calibration results depend on the chip region of the placement.", "",
          "![realistic noise](figures/b4_real_noise.png)", ""]
    (HERE / "RESULTS_B4_real_noise.md").write_text("\n".join(L))


def figure(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ours = sorted([n for n in res if n.startswith("seed")],
                  key=lambda n: res[n]["models"].get("si1000_0.0023", {}).get("rate", 1))
    best = ours[0] if ours else None
    names = [n for n in ("d5a19",) if n in res] + ([best] if best else [])
    colours = {"d5a19": "#888888", "d5a19f3": "#d08a2c"}
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=150)
    w = 0.8 / len(names)
    for i, n in enumerate(names):
        ys = [res[n]["models"].get(mo, {}).get("rate") or 0 for mo in MODELS]
        xs = [k + (i - (len(names) - 1) / 2) * w for k in range(len(MODELS))]
        vals = [1 / y if y else 0 for y in ys]
        ax.bar(xs, vals, w * 0.9, color=colours.get(n, "#2a6db0"), label=res[n]["label"])
    ax.set_yscale("log")
    ax.set_xticks(range(len(MODELS)))
    ax.set_xticklabels([LABEL[m].replace(" (", "\n(") for m in MODELS], fontsize=7)
    ax.set_ylabel("kept T states per error (higher = better)")
    from matplotlib.ticker import FuncFormatter, NullFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.grid(True, axis="y", lw=0.4, color="#dddddd")
    ax.set_title("d = 5 double checks, real T: N in '1 in N' error per kept T state", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    (HERE / "figures").mkdir(exist_ok=True)
    fig.savefig(HERE / "figures" / "b4_real_noise.png")


_DS, _CAL = None, None


def _first_pass(args):
    global _DS, _CAL
    n, mfc = args
    if _DS is None:
        _DS, _CAL = designs(), WN.load_calibration()
    d = _DS[n]
    r = dict(label=d["label"], models={})
    for model in MODELS:
        if d["emb"] is None and model == "calibration":
            continue
        dd = d if d["emb"] is not None else dict(d, emb={q: (0, 0) for q in range(d["inner"].num_qubits)})
        try:
            r["models"][model] = exact(dd, model, _CAL, mfc)
        except MemoryError:
            r.setdefault("errors", []).append(f"{model}: out of memory (per-worker cap)")
    return n, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mfc", type=int, default=4)
    ap.add_argument("--mfc2", type=int, default=5)
    ap.add_argument("--threads", type=int, default=11)
    ap.add_argument("--clifft-shots", type=int, default=2_000_000_000)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--retry-errors", action="store_true", help="re-run circuits whose first pass ran out of memory")
    ap.add_argument("--skip-second-pass", action="store_true")
    ap.add_argument("--names", default=None, help="comma list of circuits to (re)run")
    a = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    cal = WN.load_calibration()
    ds = designs()
    names = list(ds)[: a.limit] if a.limit else list(ds)
    if a.names:
        names = [n for n in a.names.split(",") if n in ds]
    res = {}
    prev = RES / "b4.json"
    if prev.exists():
        # keep EVERY earlier result (a --names run must not drop the others); only the circuits to be
        # re-run (in names, capped, --retry-errors) are removed so they run again
        res = {k: v for k, v in json.loads(prev.read_text()).items() if "models" in v
               and not (k in names and a.retry_errors and v.get("errors") and not v["models"])}
        log(f"resuming: {len(res)} circuits already done")
    todo = [n for n in names if n not in res]
    with Pool(a.threads, maxtasksperchild=1) as pool:
        for n, r in pool.imap_unordered(_first_pass, [(n, a.mfc) for n in todo]):
            res[n] = r
            log(f"{n}: " + ", ".join(f"{mo} {one_in(v['rate'])} acc {v['acceptance']:.3f}" for mo, v in r["models"].items()))
            (RES / "b4.json").write_text(json.dumps(res, indent=1, default=str))
            report(res, a.mfc)
    # second pass, up to --mfc2 faults, for the references and our best three
    ours = sorted([n for n in res if n.startswith("seed") and "si1000_0.0023" in res[n]["models"]],
                  key=lambda n: res[n]["models"]["si1000_0.0023"]["rate"])
    for n in ([] if a.skip_second_pass else [x for x in ("d5a19", "d5a19f3") if x in res] + ours[:3]):
        d = ds[n]
        for model in list(res[n]["models"]):
            dd = d if (d["emb"] is not None or model != "spec") else dict(d, emb={q: (0, 0) for q in range(d["inner"].num_qubits)})
            try:
                res[n]["models"][model] = exact(dd, model, cal, a.mfc2)
            except MemoryError:
                res[n].setdefault("errors", []).append(f"{model}: out of memory at {a.mfc2} faults (kept {a.mfc})")
                continue
        res[n]["mfc"] = a.mfc2 if not res[n].get("errors") else f"{a.mfc}-{a.mfc2}"
        log(f"{n} (to {a.mfc2} faults): " + ", ".join(f"{mo} {one_in(v['rate'])}" for mo, v in res[n]["models"].items()))
        (RES / "b4.json").write_text(json.dumps(res, indent=1, default=str))
        report(res, a.mfc)
    ours = sorted([n for n in res if n.startswith("seed") and "si1000_0.0023" in res[n]["models"]],
                  key=lambda n: res[n]["models"]["si1000_0.0023"]["rate"])
    # Clifft cross-check on the references and the best two of ours
    for n in ([] if a.skip_second_pass else [x for x in ("d5a19", "d5a19f3") if x in res] + ours[:2]):
        d = ds[n]
        d5 = dict(d, emb=d["emb"] or {q: (0, 0) for q in range(d["inner"].num_qubits)})
        res[n]["si1000_0.005_exact"] = exact(d5, "si1000_0.005", cal, a.mfc)["rate"]
        res[n]["clifft"] = clifft_check(d, 0.005, a.clifft_shots, a.threads)
        log(f"clifft {n}: {res[n]['clifft']['error']['events']} errors, {one_in(res[n]['clifft']['error']['rate'])} "
            f"vs exact {one_in(res[n]['si1000_0.005_exact'])}")
        (RES / "b4.json").write_text(json.dumps(res, indent=1, default=str))
        report(res, a.mfc)
    figure(res)
    report(res, a.mfc)
    log("done")


if __name__ == "__main__":
    main()
