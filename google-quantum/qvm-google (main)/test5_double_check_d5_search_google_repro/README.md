# Test 5: making the double-check result stronger (Google reproduction, d = 5)

Created Nov 4, 2026 (KST) at the user's request. Goal: strengthen our double-check work in two ways,
in this order. **Every part waits for the user's go-ahead before anything runs.**

| part | what | why | status |
|---|---|---|---|
| A | Reproduce Google's own simulations of their own circuits | shows our simulator can be trusted against Google's paper | planned |
| B | Extend the search method to the d = 5 colour code | a new result beyond d = 3 (Chan's d = 5 flags are not nearest-neighbour) | B0-B1 done; B2 search: 41 FD-4 NN circuits (`RESULTS_B2_search.md`); B3 Clifft check done Nov 5: agrees with cliffordea (`RESULTS_B3_clifft.md`) |

Rules (as in tests 1-4): real T gates; `.venv`; never edit cliffordea; same shots and counting rule for every
circuit; numbers as % or "1 in N"; PNG figures; long runs in tmux, writing their own report.

## Part A: reproduce Google's simulations (Rosenfeld et al., arXiv:2512.13908)

Google's released circuits: `google-quantum/nnflags/data/google_circuits/rosenfeld2512_G0-G6.stim`.

| step | what | Google's setting | ours |
|---|---|---|---|
| A0 | Get Google's simulated values | Zenodo data (doi 10.5281/zenodo.17872003), read only; if absent, values read off the figures (approximate) | needs the user's OK to download |
| A1 | Fig. 2: injection + double check, logical tomography (G4) | kraus-sim state vector, SI1000 p = 0.30 % | qsim (12 qubits), real T, SI1000 |
| A2 | Fig. 3: kickback tomography, full circuit (G5) | kraus-sim, SI1000 p = 0.23 %; logical error about 1-2 in 10,000, 8 % retained | qsim (14 qubits), same metric (KT upper bound) |
| A3 | Fig. S19: p sweep of the G5 circuit, slope | claimed p^3 | qsim / Clifft; also tests the fault-distance question (Chan: one double check has FD 2) |
| A4 | Our double check in Google's setup | - | inside the same A1/A2 circuits. Caution: cs02 cannot follow Google's injection (test 4 README, blocker 1); #0 can. cs02 only with an ideal injection, labelled as such |

Pass criterion for A1-A3: our numbers inside Google's error bars (or within a stated tolerance if read off a plot).

## Part B: the method at d = 5

Starting points already in cliffordea (`cliffordea/enum/circuits/stim_files/double_checks/`):

| circuit | meaning | fault distance (pre-escape double check) | nearest-neighbour on a square grid |
|---|---|---|---|
| d5a19 | Gidney's original d = 5 double check | 3 with real T (Chan) | yes (to be checked on Willow) |
| d5a19f3 | 3 flags | 4 | no (Chan's flags) |
| d5a19f13 | Chan's 13 flags | 5 | no |
| d5a19f18 | 18 flags | 5 | no |

Size: 19 data + up to 19 tree ancillas + flags, about 40-55 qubits: fits Willow (105) by count.

| step | what |
|---|---|
| B0 | Baselines: fault distance of d5a19 / f3 / f13 with real T (cliffordea, up to 4 faults); count the non-nearest-neighbour pairs of each on Willow |
| B1 | Place Gidney's d = 5 tree on Willow: nearest-neighbour, <= 4 partners, readout-line rule (incl. continuing data) |
| B2 | Nearest-neighbour flag search: first fault distance 4 (cheaper, like d5a19f3), then 5. Same method as cs02 (flag placement on free grid points, exact GF(2) prefilter, cliffordea verify), scaled to 19 data |
| B3 | Verification: Google device check; noiseless real-T check; fault injection up to 4 faults (cliffordea; sampled cross-check in Clifft, since 40-55 qubits is too large for qsim) |
| B4 | Noisy simulation in Clifft (Willow calibration Pauli model + SI1000), against Gidney's d5a19 and, as a reference, Chan's d5a19f13 |

Risks: the search space is far larger (19 data; the d = 3 code labelling step used all 210 labellings, not
possible at d = 5, so start from Gidney's tree and its fixed labelling); fault enumeration up to 4 faults
per candidate is slower (Chan: 15 s per circuit on a laptop). B1 may already fail on readout lines; then
report before changing the method.

Note on context (Chan Sec. 2.3): in MSC-5 the d = 5 double check follows growth from d = 3 and 3 (or 4)
stabiliser rounds. Here, as in Chan Sec. 5, we target the fault distance of the d = 5 double check itself
(error-free input).

## Not in this test

The full pipeline (injection + double check + escape) is done in test 4
(`../test4_cs02_lattice_surgery_escape_realT_clifft/`), not here (user, Nov 4).

## Suggested order

A (cheap, protects the main claim) -> B (the new result).
