"""Test 5, Part B, step B3: independent real-T check of the d = 5 results by sampling (Clifft).

For each circuit: ideal |T_L> (cliffordea's own encoder), ideal logical T^dagger layer, the double
check with cliffordea's OWN noise model (enum.noise.uniformly_depolarize at noise level p, so the
same noise as the exact enumeration), ideal logical T layer, ideal decode (inverse encoder,
T^dagger, H, Z measurement). All T gates are real T (Clifft = exact near-Clifford simulator).
Counted as everywhere else: error per kept T state = wrong logical bit among shots with no
detector fired and all decoded stabiliser bits 0 (= cliffordea's "per kept shot", which projects
onto the code space with a noiseless stabiliser round, Chan et al. Lemma 2).

Compared with (a) cliffordea's exact enumeration at the same p (up to --mfc faults) and (b) the
slope of log(error) vs log(p): fault distance d means slope -> d as p -> 0.

    .venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b3_clifft_check.py" \
        [--shots 200000000] [--threads 11]
    -> results/b3/<name>.json, RESULTS_B3_clifft.md, figures/b3_error_vs_p.png
"""
import argparse
import json
import math
import sys
import time
import zlib
from pathlib import Path

import clifft
import stim
from scipy.stats import beta

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b2_flags_d5 as F  # noqa: E402  (sys.path / cwd)

from cliffordea import accept, enum  # noqa: E402
from nnflags.verify import bundled_paths, load_measurement, verify  # noqa: E402

RES = HERE / "results" / "b3"
FIG = HERE / "figures"
S2 = HERE / "results" / "b2_search"
DESIGNS = {  # name -> (label, full, inner)
    "d5a19": ("Gidney et al. (FD 3)", *bundled_paths("d5a19")),
    "d5a19f3": ("Chan et al., 3 flags (FD 4, not nearest-neighbour)", *bundled_paths("d5a19f3")),
    "seed1035": ("ours #1035 (33 qubits, best rate)", S2 / "success_seed1035.full.stim", S2 / "success_seed1035.inner.stim"),
    "seed1019": ("ours #1019 (23 qubits, smallest)", S2 / "success_seed1019.full.stim", S2 / "success_seed1019.inner.stim"),
}
PS = [0.003, 0.005, 0.007, 0.01]
log, kst = F.log, F.kst


def _ops(c, mp):
    out = []
    for ins in c:
        ts = " ".join(str(mp[t.value]) for t in ins.targets_copy())
        out.append(f"{ins.name} {ts}")
    return out


def clifft_text(full_p, inner_p, p):
    m = load_measurement(stim.Circuit.from_file(str(full_p)), stim.Circuit.from_file(str(inner_p)))
    data = list(m.DATA_INDICES)
    n = len(data)
    an = accept.CliffordLogicalAnalyzer(data_indices=m.DATA_INDICES, stabilizer_generators=m.STABILIZER_GENERATORS,
                                        logical_s=m.LOGICAL_S)
    enc = an.encoder
    mp = {j: data[j] for j in range(n)}
    maj, mino = [], []
    for ins in m.LOGICAL_S:
        (maj if ins.name == "S" else mino).extend(t.value for t in ins.targets_copy())
    L = [f"H {data[-1]}", f"T {data[-1]}"] + _ops(enc.to_circuit("elimination"), mp)
    L += [f"T_DAG {' '.join(map(str, maj))}", f"T {' '.join(map(str, mino))}", "TICK"]
    noisy = enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=p)
    nrec, mpp_rec, ndet = 0, None, 0
    for ins in noisy.flattened():
        if ins.name == "QUBIT_COORDS":
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
        if ins.name == "OBSERVABLE_INCLUDE":
            continue
        args = f"({','.join(str(a) for a in ins.gate_args_copy())})" if ins.gate_args_copy() else ""
        L.append(f"{ins.name}{args} " + " ".join(str(t.value) for t in ins.targets_copy()) if ins.name != "TICK" else "TICK")
        nrec += ins.num_measurements
    L += [f"T {' '.join(map(str, maj))}", f"T_DAG {' '.join(map(str, mino))}"]
    L += _ops(enc.inverse().to_circuit("elimination"), mp)
    L += [f"T_DAG {data[-1]}", f"H {data[-1]}", "M " + " ".join(map(str, data))]
    for j in range(n - 1):
        L.append(f"DETECTOR rec[{j - n}]")
    L.append("OBSERVABLE_INCLUDE(0) rec[-1]")
    return "\n".join(L) + "\n", ndet, n - 1


def rate(x, k):
    lo = 0.0 if x == 0 else float(beta.ppf(0.025, x, k - x + 1))
    hi = float(beta.ppf(0.975, x + 1, k - x)) if x < k else 1.0
    return dict(events=x, of=k, rate=x / k if k else float("nan"), ci95=[lo, hi])


def run(name, p, shots, threads, mfc, target=50, chunk=100_000_000):
    _, full_p, inner_p = DESIGNS[name]
    txt, nd, nc = clifft_text(full_p, inner_p, p)
    progA = clifft.compile(txt, postselection_mask=[1] * (nd + nc), expected_observables=[0])
    progK = clifft.compile(txt, postselection_mask=[1] * nd + [0] * nc)
    seed = zlib.crc32(f"b3:{name}:{p}".encode())
    t0 = time.time()
    ev = kept = done = k = 0
    while done < shots and ev < target:
        n = min(chunk, shots - done)
        rA = clifft.sample_survivors(progA, n, seed=seed + 2 * k, threads=threads)
        ev += int(rA.logical_errors)
        kept += int(rA.passed_shots)
        done += n
        k += 1
    rK = clifft.sample_survivors(progK, min(done, 20_000_000), seed=seed + 1, threads=threads)
    sim = dict(shots=done, acceptance=rK.passed_shots / rK.total_shots,
               error=rate(ev, kept), wall_s=round(time.time() - t0, 1))
    r = verify(stim.Circuit.from_file(str(full_p)), stim.Circuit.from_file(str(inner_p)),
               max_fault_count=mfc, noise_level=p, states=("T",))
    sim["cliffordea_rate"] = r["error_rate_per_kept_shot"]["T"]
    sim["cliffordea_mfc"] = mfc
    return sim


def one_in(x):
    return f"1 in {1 / x:,.0f}" if x and x > 0 else "0 events"


def slope(rows):
    pts = [(math.log(p), math.log(r["error"]["rate"])) for p, r in rows if r["error"]["events"] >= 5]
    if len(pts) < 2:
        return None
    mx = sum(x for x, _ in pts) / len(pts)
    my = sum(y for _, y in pts) / len(pts)
    return sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)


def report(allres):
    L = [f"# Test 5, B3: independent real-T check of the d = 5 circuits by sampling (written {kst()})", "",
         "Clifft (exact near-Clifford, real T) with cliffordea's own uniform depolarising noise at each p; "
         "ideal T_L in, ideal decode. Compared with cliffordea's exact enumeration at the same p.", "",
         "| circuit | p | shots | acceptance | errors / kept in code | Clifft: error per kept T state (95 % CI) | cliffordea (exact, to k faults) |",
         "|---|---|---|---|---|---|---|"]
    for name, rows in allres.items():
        for p, r in rows:
            e = r["error"]
            L.append(f"| {DESIGNS[name][0]} | {100 * p:.1f} % | {r['shots']:,} | {100 * r['acceptance']:.1f} % | "
                     f"{e['events']} / {e['of']:,} | {one_in(e['rate'])} ({one_in(e['ci95'][1])} to {one_in(e['ci95'][0])}) | "
                     f"{one_in(r['cliffordea_rate'])} (k = {r['cliffordea_mfc']}) |")
    L += ["", "## Slope of log(error) vs log(p) (fault distance: slope -> FD as p -> 0)", "",
          "| circuit | fitted slope (points with >= 5 errors) |", "|---|---|"]
    for name, rows in allres.items():
        s = slope(rows)
        L.append(f"| {DESIGNS[name][0]} | {'n/a' if s is None else f'{s:.2f}'} |")
    L += ["", "At these p, higher-order terms still matter, so the fitted slopes sit between the fault distance "
          "and the next order; what matters is the comparison between circuits and the agreement with cliffordea.",
          "", "![error vs p](figures/b3_error_vs_p.png)", ""]
    (HERE / "RESULTS_B3_clifft.md").write_text("\n".join(L))


def figure(allres):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 4.6), dpi=150)
    colours = {"d5a19": "#888888", "d5a19f3": "#d08a2c", "seed1035": "#2a6db0", "seed1019": "#3a9a5b"}
    for name, rows in allres.items():
        xs = [100 * p for p, r in rows if r["error"]["events"] > 0]
        ys = [r["error"]["rate"] for p, r in rows if r["error"]["events"] > 0]
        lo = [r["error"]["rate"] - r["error"]["ci95"][0] for p, r in rows if r["error"]["events"] > 0]
        hi = [r["error"]["ci95"][1] - r["error"]["rate"] for p, r in rows if r["error"]["events"] > 0]
        ax.errorbar(xs, ys, yerr=[lo, hi], marker="o", ms=4, lw=1.5, capsize=2, color=colours[name], label=DESIGNS[name][0])
        cx = [100 * p for p, r in rows]
        cy = [r["cliffordea_rate"] for p, r in rows]
        ax.plot(cx, cy, ls=":", lw=1, color=colours[name])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("noise level p (%)")
    ax.set_ylabel("error per kept T state")
    ticks = [10 ** -k for k in range(2, 10)]
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"1 in {10 ** k:,}" for k in range(2, 10)])
    ax.set_xticks([0.3, 0.5, 0.7, 1.0])
    ax.set_xticklabels(["0.3", "0.5", "0.7", "1.0"])
    from matplotlib.ticker import NullFormatter
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.grid(True, which="major", lw=0.4, color="#dddddd")
    ax.set_title("d = 5 double checks, real T (Clifft); dotted = cliffordea exact", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "b3_error_vs_p.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=int, default=3_000_000_000, help="cap per point")
    ap.add_argument("--threads", type=int, default=11)
    ap.add_argument("--mfc", type=int, default=5)
    ap.add_argument("--only", default=",".join(DESIGNS))
    ap.add_argument("--ps", default=",".join(map(str, PS)))
    ap.add_argument("--figure-only", action="store_true", help="redraw the figure and report from results/b3/*.json")
    a = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    if a.figure_only:
        allres = {n: [tuple(x) for x in json.loads((RES / f"{n}.json").read_text())] for n in DESIGNS if (RES / f"{n}.json").exists()}
        report(allres)
        figure(allres)
        return
    allres = {}
    for name in a.only.split(","):
        rows = []
        for p in map(float, a.ps.split(",")):
            r = run(name, p, a.shots, a.threads, a.mfc)
            rows.append((p, r))
            log(f"{name} p={p}: {r['error']['events']} / {r['error']['of']:,} = {one_in(r['error']['rate'])}, "
                f"acc {r['acceptance']:.3f}, cliffordea {one_in(r['cliffordea_rate'])}, {r['wall_s']} s")
            (RES / f"{name}.json").write_text(json.dumps(rows, indent=1))
            allres[name] = rows
            report(allres)
            figure(allres)
    log("done")


if __name__ == "__main__":
    main()
