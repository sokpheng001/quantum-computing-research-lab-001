"""Writes RESULTS.md from the QVM results used by plots.py.

    .venv/bin/python "qvm-google (main)/test2_cs02_continuing_data_vs_google/report.py"
"""
import datetime as dt
import json

from plots import CRES, HERE, load


def one_in(x):
    return f"1 in {1 / x:,.0f}" if x > 0 else "0 events"


def main():
    ds = load()
    names = {"G4": "G4 (Google, as run in Fig. 2)", "G6s": "G4 G6-style (Google, as run in Fig. 4)",
             "cs02": "**cs02 (ours)**"}
    fd = {"G4": 2, "G6s": 2, "cs02": 3}
    e1 = json.loads((CRES / "e1_G4_G6style.json").read_text())["designs"]["G4_G6style"]
    e2 = json.loads((CRES / "e2_G4_G6style.json").read_text())["designs"]["G4_G6style"]
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %I:%M %p KST")
    L = [f"# RESULTS: cs02 vs Google's double check in the Google QVM (written {now})", "",
         "Figures: `figures/qvm_cs02_vs_google.png` (QVM results, code `plots.py`); `figures/continuing_circuits.png` "
         "(cs02 and cs07 on the Willow grid next to Google's G6, code `nnflags/plots_continuing.py`). "
         "Run: `run_all.sh`. QVM = cirq_google 1.7 + qsimcirq, processor `willow_pink`, "
         "its Willow noise model; real T gates.", "",
         "## Logical error and acceptance (E4, noisy QVM)", "",
         "| circuit | fault distance | shots | kept, in code space | errors | T error per kept T state (95 % CI) "
         "| acceptance | stim, Willow calibration model |", "|---|---|---|---|---|---|---|---|"]
    for d in ds:
        r, s = d["e4"], d["stim"]
        q = r["logical_error_given_code"]
        lo, hi = q["ci95"]
        L.append(f"| {names[d['key']]} | {fd[d['key']]} | {r['shots']:,} | {r['kept_code']:,} | {q['events']} "
                 f"| {one_in(q['rate'])} ({one_in(hi)} to {one_in(lo)}) | {100 * r['acceptance']:.1f} % "
                 f"| {one_in(s['rate_T'])}, acceptance {100 * s['mc']['acceptance']:.1f} % |")
    rate = {d["key"]: d["e4"]["logical_error_given_code"]["rate"] for d in ds}
    L += ["", f"- cs02 vs G4 G6-style (fair baseline when the data continue): "
          f"**{rate['G6s'] / rate['cs02']:.1f}× lower error** in the QVM.",
          f"- cs02 vs G4 as run in Fig. 2: **{rate['G4'] / rate['cs02']:.1f}× lower error** in the QVM.",
          "- The ratios carry the statistical uncertainty of the event counts above (the 95 % CIs).", "",
          "## Fault injection with real T gates (E3)", "",
          "| circuit | single faults agree | 2-fault configurations agree | kept with a wrong T state at 2 faults "
          "(real T / cliffordea) |", "|---|---|---|---|"]
    for d in ds:
        s = d["e3"]["summary"]
        L.append(f"| {names[d['key']]} | {s['single']['agree']:,} / {s['single']['n']:,} "
                 f"| {s['all2']['agree']:,} / {s['all2']['n']:,} | {s['all2']['real'].get('malignant', 0)} / "
                 f"{s['all2']['cliffordea'].get('malignant', 0)} |")
    L += ["", "## G4 G6-style device checks (E1, E2)", "",
          f"- E1: device validation {e1['device_validation']}; {e1['cz_pairs_on_couplers']} of "
          f"{e1['cz_pairs']} CZ pairs on couplers; flows equal: {e1['flows_equal']}; detector error model "
          f"equal: {e1['detector_error_model_equal']}; continuing-data conflicts: {e1['continuing_data_violations']}.",
          f"- E2 (noiseless, real T): all detectors zero: {e2['all_detectors_zero']}; minimum fidelity "
          f"{100 * e2['fidelity_min']:.6f} %.", "",
          "## Limitations", "",
          "- Simulation only: the QVM uses Willow's 2024 calibration (willow_pink), not the live device.",
          "- Double-check stage only (no escape / grafting); leakage and coherent errors are not modelled.",
          "- 'Kept, in code space' = shots with no detector fired, decoded with ideal stabiliser post-selection, "
          "as in test 1 (../test1_fd3_circuits_vs_google_fig2/RESULTS.md).", ""]
    (HERE / "RESULTS.md").write_text("\n".join(L))
    print(HERE / "RESULTS.md")


if __name__ == "__main__":
    main()
