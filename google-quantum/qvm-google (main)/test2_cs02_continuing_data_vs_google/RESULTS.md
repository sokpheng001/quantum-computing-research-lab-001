# RESULTS: cs02 vs Google's double check in the Google QVM (written 2026-11-03 08:37 PM KST)

Figures: `figures/qvm_cs02_vs_google.png` (QVM results, code `plots.py`); `figures/continuing_circuits.png` (cs02 and cs07 on the Willow grid next to Google's G6, code `nnflags/plots_continuing.py`). Run: `run_all.sh`. QVM = cirq_google 1.7 + qsimcirq, processor `willow_pink`, its Willow noise model; real T gates.

## Logical error and acceptance (E4, noisy QVM)

| circuit | fault distance | shots | kept, in code space | errors | T error per kept T state (95 % CI) | acceptance | stim, Willow calibration model |
|---|---|---|---|---|---|---|---|
| G4 (Google, as run in Fig. 2) | 2 | 8,000,000 | 4,411,869 | 239 | 1 in 18,460 (1 in 16,262 to 1 in 21,043) | 75.1 % | 1 in 20,234, acceptance 74.0 % |
| G4 G6-style (Google, as run in Fig. 4) | 2 | 8,000,000 | 4,603,871 | 221 | 1 in 20,832 (1 in 18,259 to 1 in 23,876) | 76.7 % | 1 in 24,121, acceptance 76.1 % |
| **cs02 (ours)** | 3 | 8,000,000 | 5,095,514 | 42 | 1 in 121,322 (1 in 89,754 to 1 in 168,336) | 75.2 % | 1 in 140,288, acceptance 75.2 % |

- cs02 vs G4 G6-style (fair baseline when the data continue): **5.8× lower error** in the QVM.
- cs02 vs G4 as run in Fig. 2: **6.6× lower error** in the QVM.
- The ratios carry the statistical uncertainty of the event counts above (the 95 % CIs).

## Fault injection with real T gates (E3)

| circuit | single faults agree | 2-fault configurations agree | kept with a wrong T state at 2 faults (real T / cliffordea) |
|---|---|---|---|
| G4 (Google, as run in Fig. 2) | 1,018 / 1,018 | 11,781 / 11,781 | 7 / 7 |
| G4 G6-style (Google, as run in Fig. 4) | 952 / 952 | 11,175 / 11,175 | 7 / 7 |
| **cs02 (ours)** | 1,203 / 1,203 | 13,041 / 13,041 | 0 / 0 |

## G4 G6-style device checks (E1, E2)

- E1: device validation {'H as cirq.H': 'PASS', 'H as PhasedXZGate (used)': 'PASS'}; 11 of 11 CZ pairs on couplers; flows equal: True; detector error model equal: True; continuing-data conflicts: 0.
- E2 (noiseless, real T): all detectors zero: True; minimum fidelity 100.000000 %.

## Limitations

- Simulation only: the QVM uses Willow's 2024 calibration (willow_pink), not the live device.
- Double-check stage only (no escape / grafting); leakage and coherent errors are not modelled.
- 'Kept, in code space' = shots with no detector fired, decoded with ideal stabiliser post-selection, as in test 1 (../test1_fd3_circuits_vs_google_fig2/RESULTS.md).
