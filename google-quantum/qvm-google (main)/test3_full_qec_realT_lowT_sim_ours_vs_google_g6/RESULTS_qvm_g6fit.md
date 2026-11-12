# RESULTS: the 9 G6-fit double checks in the Google QVM (written 2026-11-03 08:37 PM KST)

Each double check is simulated on its own (13-15 qubits fit the QVM's state vector), with real T gates and Google's Willow noise model (cirq_google 1.7 + qsimcirq, processor `willow_pink`), exactly as cs02 in test 2. Google's double check as run in G6 and cs02 are the test 2 results. Run: `run_qvm_g6fit.sh`; figure: `figures/qvm_g6fit_vs_google.png`.

## Logical error and acceptance (E4, noisy QVM)

| circuit | fault distance | qubits | shots | errors | T error per kept T state (95 % CI) | acceptance |
|---|---|---|---|---|---|---|
| Google, as run in G6 | 2 | 12 | 8,000,000 | 221 | 1 in 20,832 (1 in 18,259 to 1 in 23,876) | 76.7 % |
| cs02 (ours, does not fit G6) | 3 | 12 | 8,000,000 | 42 | 1 in 121,322 (1 in 89,754 to 1 in 168,336) | 75.2 % |
| #2 (ours, fits G6) | 3 | 13 | 8,000,000 | 54 | 1 in 81,692 (1 in 62,610 to 1 in 108,744) | 65.0 % |
| #4 (ours, fits G6) | 3 | 14 | 8,000,000 | 53 | 1 in 80,207 (1 in 61,319 to 1 in 107,075) | 63.2 % |
| #0 (ours, fits G6) | 3 | 13 | 8,000,000 | 66 | 1 in 70,284 (1 in 55,244 to 1 in 90,876) | 71.4 % |
| #1 (ours, fits G6) | 3 | 13 | 8,000,000 | 65 | 1 in 71,364 (1 in 55,990 to 1 in 92,467) | 71.7 % |
| #3 (ours, fits G6) | 3 | 13 | 8,000,000 | 58 | 1 in 75,092 (1 in 58,088 to 1 in 98,891) | 64.8 % |
| #5 (ours, fits G6) | 3 | 14 | 8,000,000 | 49 | 1 in 84,949 (1 in 64,256 to 1 in 114,826) | 62.3 % |
| #6 (ours, fits G6) | 3 | 14 | 8,000,000 | 75 | 1 in 56,249 (1 in 44,873 to 1 in 71,512) | 66.6 % |
| #7 (ours, fits G6) | 3 | 15 | 8,000,000 | 57 | 1 in 73,826 (1 in 56,982 to 1 in 97,474) | 65.7 % |
| #9 (ours, fits G6) | 3 | 15 | 8,000,000 | 82 | 1 in 49,918 (1 in 40,216 to 1 in 62,764) | 64.2 % |

- #2 vs Google as run in G6: **3.9× lower error**.
- #4 vs Google as run in G6: **3.9× lower error**.
- #0 vs Google as run in G6: **3.4× lower error**.
- #1 vs Google as run in G6: **3.4× lower error**.
- #3 vs Google as run in G6: **3.6× lower error**.
- #5 vs Google as run in G6: **4.1× lower error**.
- #6 vs Google as run in G6: **2.7× lower error**.
- #7 vs Google as run in G6: **3.5× lower error**.
- #9 vs Google as run in G6: **2.4× lower error**.

## Device check and noiseless real-T check (E1, E2)

| circuit | device validation | CZ pairs on couplers | continuing-data conflicts | E2 all detectors zero | E2 min fidelity |
|---|---|---|---|---|---|
| Google, as run in G6 | PASS | 11 / 11 | 0 | True | 100.000000 % |
| cs02 (ours, does not fit G6) | PASS | 12 / 12 | 0 | True | 100.000000 % |
| #2 (ours, fits G6) | PASS | 13 / 13 | 0 | True | 100.000000 % |
| #4 (ours, fits G6) | PASS | 14 / 14 | 0 | True | 100.000000 % |
| #0 (ours, fits G6) | PASS | 13 / 13 | 0 | True | 100.000000 % |
| #1 (ours, fits G6) | PASS | 13 / 13 | 0 | True | 100.000000 % |
| #3 (ours, fits G6) | PASS | 13 / 13 | 0 | True | 100.000000 % |
| #5 (ours, fits G6) | PASS | 14 / 14 | 0 | True | 100.000000 % |
| #6 (ours, fits G6) | PASS | 14 / 14 | 0 | True | 100.000000 % |
| #7 (ours, fits G6) | PASS | 15 / 15 | 0 | True | 100.000000 % |
| #9 (ours, fits G6) | PASS | 15 / 15 | 0 | True | 100.000000 % |

## Fault injection with real T gates (E3)

| circuit | single faults agree | 2-fault configurations agree | kept with a wrong T state at 2 faults (real T / cliffordea) |
|---|---|---|---|
| Google, as run in G6 | 952 / 952 | 11,175 / 11,175 | 7 / 7 |
| cs02 (ours, does not fit G6) | 1,203 / 1,203 | 13,041 / 13,041 | 0 / 0 |
| #2 (ours, fits G6) | 1,496 / 1,496 | 13,203 / 13,203 | 0 / 0 |
| #4 (ours, fits G6) | 1,567 / 1,567 | 14,535 / 14,535 | 0 / 0 |
| #0 (ours, fits G6) | 1,535 / 1,535 | 13,530 / 13,530 | 0 / 0 |
| #1 (ours, fits G6) | 1,535 / 1,535 | 13,530 / 13,530 | 0 / 0 |
| #3 (ours, fits G6) | 1,652 / 1,652 | 13,203 / 13,203 | 0 / 0 |
| #5 (ours, fits G6) | 1,693 / 1,693 | 14,535 / 14,535 | 0 / 0 |
| #6 (ours, fits G6) | 1,777 / 1,777 | 14,196 / 14,196 | 0 / 0 |
| #7 (ours, fits G6) | 1,832 / 1,832 | 13,695 / 13,695 | 0 / 0 |
| #9 (ours, fits G6) | 1,787 / 1,787 | 14,028 / 14,028 | 0 / 0 |

## Limitations

- Simulation only (Willow's 2024 calibration, willow_pink), double check alone: no injection, no grafting.
- The splice into G6 (full experiment) needs a low-T-count simulator; not run yet.
