"""Test 3, step 2 report: QVM results (real T, Willow noise) of the G6-fit double checks
#4 and #2 on their own, next to Google's double check as run in G6 and cs02 (test 2).
Writes RESULTS_qvm_g6fit.md and figures/qvm_g6fit_vs_google.png (PNG only).

    .venv/bin/python "qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6/report_qvm_g6fit.py"
"""
import datetime as dt
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
Q = HERE / "results" / "qvm"
T2 = HERE.parent / "test2_cs02_continuing_data_vs_google" / "results"

# key, label, results dir, fault distance, qubits
DESIGNS = [
    ("G4_G6style", "Google, as run in G6", T2, 2, 12),
    ("cont_success02", "cs02 (ours, does not fit G6)", T2, 3, 12),
] + [(f"g6fit{n:02d}", f"#{n} (ours, fits G6)", Q, 3, nq)
      # the 9 distinct G6-fit successes of results/g6_search_d6n14 (#8 = #7 and #10 = #9)
      for n, nq in [(2, 13), (4, 14), (0, 13), (1, 13), (3, 13), (5, 14), (6, 14), (7, 15), (9, 15)]]
SHORT = {"G4_G6style": "Google\nFD 2", "cont_success02": "cs02\nno fit",
         **{f"g6fit{n:02d}": f"#{n}" for n in range(11)}}


def one_in(x):
    return f"1 in {1 / x:,.0f}" if x > 0 else "0 events"


def get(d, exp, name):
    p = d / f"{exp}_{name}.json"
    if not p.exists():
        return None
    j = json.loads(p.read_text())
    return j["results"][name] if exp == "e4" else j["designs"][name]


def figure(rows, path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.3))
    for i, r in enumerate(rows):
        e4 = r["e4"]
        if e4 is None:
            continue
        q = e4["logical_error_given_code"]
        lo, hi = q["ci95"]
        a.errorbar(i, q["rate"], yerr=[[q["rate"] - lo], [hi - q["rate"]]], fmt="o", ms=7,
                   color="black" if r["fd"] == 2 else "tab:blue", capsize=3)
        a.annotate(f"{1 / q['rate']:,.0f}", (i, q["rate"]), xytext=(6, 0), textcoords="offset points",
                   va="center", fontsize=7)
        b.bar(i, 100 * e4["acceptance"], color="0.6" if r["fd"] == 2 else "tab:blue", width=0.6)
        b.text(i, 100 * e4["acceptance"] + 1, f"{100 * e4['acceptance']:.0f}", ha="center", fontsize=7)
    for ax in (a, b):
        ax.set_xticks(range(len(rows)))
        ax.set_xticklabels([SHORT[r["key"]] for r in rows], fontsize=8)
        ax.set_xlim(-0.6, len(rows) - 0.2)
    a.set_yscale("log")
    ticks = [1 / 200_000, 1 / 100_000, 1 / 50_000, 1 / 20_000]
    a.set_yticks(ticks)
    a.set_yticklabels([f"1 in {round(1 / t):,}" for t in ticks], fontsize=8)
    a.minorticks_off()
    a.set_ylim(1 / 250_000, 1 / 15_000)
    a.set_ylabel("T error per kept T state (95 % CI)\nlabels: 1 in N")
    a.set_title("(a) Logical error, Google QVM, real T", fontsize=10)
    b.set_ylim(0, 100)
    b.set_ylabel("acceptance (%), labels in %")
    b.set_title("(b) Acceptance", fontsize=10)
    fig.suptitle("Double check alone in Google's QVM (willow_pink noise, real T gates); "
                 "black / grey = fault distance 2, blue = fault distance 3", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    rows = []
    for key, label, d, fd, nq in DESIGNS:
        rows.append(dict(key=key, label=label, fd=fd, nq=nq, e1=get(d, "e1", key), e2=get(d, "e2", key),
                         e3=get(d, "e3", key), e4=get(d, "e4", key)))
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %I:%M %p KST")
    L = [f"# RESULTS: the 9 G6-fit double checks in the Google QVM (written {now})", "",
         "Each double check is simulated on its own (13-15 qubits fit the QVM's state vector), with real T "
         "gates and Google's Willow noise model (cirq_google 1.7 + qsimcirq, processor `willow_pink`), "
         "exactly as cs02 in test 2. Google's double check as run in G6 and cs02 are the test 2 results. "
         "Run: `run_qvm_g6fit.sh`; figure: `figures/qvm_g6fit_vs_google.png`.", "",
         "## Logical error and acceptance (E4, noisy QVM)", "",
         "| circuit | fault distance | qubits | shots | errors | T error per kept T state (95 % CI) | acceptance |",
         "|---|---|---|---|---|---|---|"]
    for r in rows:
        e4 = r["e4"]
        if e4 is None:
            L.append(f"| {r['label']} | {r['fd']} | {r['nq']} | not run | | | |")
            continue
        q = e4["logical_error_given_code"]
        lo, hi = q["ci95"]
        L.append(f"| {r['label']} | {r['fd']} | {r['nq']} | {e4['shots']:,} | {q['events']} | {one_in(q['rate'])} "
                 f"({one_in(hi)} to {one_in(lo)}) | {100 * e4['acceptance']:.1f} % |")
    rate = {r["key"]: r["e4"]["logical_error_given_code"]["rate"] for r in rows if r["e4"]}
    L.append("")
    for k in [d[0] for d in DESIGNS if d[0].startswith("g6fit")]:
        if k in rate and "G4_G6style" in rate and rate[k] > 0:
            L.append(f"- {k.replace('g6fit0', '#')} vs Google as run in G6: **{rate['G4_G6style'] / rate[k]:.1f}× lower error**.")
    L += ["", "## Device check and noiseless real-T check (E1, E2)", "",
          "| circuit | device validation | CZ pairs on couplers | continuing-data conflicts | E2 all detectors zero | E2 min fidelity |",
          "|---|---|---|---|---|---|"]
    for r in rows:
        e1, e2 = r["e1"], r["e2"]
        if e1 is None or e2 is None:
            L.append(f"| {r['label']} | not run | | | | |")
            continue
        L.append(f"| {r['label']} | {e1['device_validation'].get('H as PhasedXZGate (used)')} | "
                 f"{e1['cz_pairs_on_couplers']} / {e1['cz_pairs']} | {e1['continuing_data_violations']} | "
                 f"{e2['all_detectors_zero']} | {100 * e2['fidelity_min']:.6f} % |")
    L += ["", "## Fault injection with real T gates (E3)", "",
          "| circuit | single faults agree | 2-fault configurations agree | kept with a wrong T state at 2 faults (real T / cliffordea) |",
          "|---|---|---|---|"]
    for r in rows:
        if r["e3"] is None:
            L.append(f"| {r['label']} | not run | | |")
            continue
        s = r["e3"]["summary"]
        L.append(f"| {r['label']} | {s['single']['agree']:,} / {s['single']['n']:,} | {s['all2']['agree']:,} / "
                 f"{s['all2']['n']:,} | {s['all2']['real'].get('malignant', 0)} / {s['all2']['cliffordea'].get('malignant', 0)} |")
    L += ["", "## Limitations", "",
          "- Simulation only (Willow's 2024 calibration, willow_pink), double check alone: no injection, no grafting.",
          "- The splice into G6 (full experiment) needs a low-T-count simulator; not run yet.", ""]
    (HERE / "RESULTS_qvm_g6fit.md").write_text("\n".join(L))
    (HERE / "figures").mkdir(exist_ok=True)
    # figure: the two baselines, then the G6-fit circuits from lowest to highest error
    fit = sorted((r for r in rows if r["key"].startswith("g6fit") and r["e4"]),
                 key=lambda r: r["e4"]["logical_error_given_code"]["rate"])
    figure([r for r in rows if not r["key"].startswith("g6fit")] + fit, HERE / "figures" / "qvm_g6fit_vs_google.png")
    print(HERE / "RESULTS_qvm_g6fit.md")


if __name__ == "__main__":
    main()
