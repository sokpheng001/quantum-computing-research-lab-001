# RESULTS: test 6, does our simulation match Google's paper? (written Nov 09, 05:39 PM KST)

Google's release: Zenodo 10.5281/zenodo.17872003 (Rosenfeld et al., arXiv:2512.13908), read-only in `references/zenodo_17872003/`. Code: `t6_step1_data.py`, `t6_step4_circuits.py`, `t6_sim.py`, `t6_report.py`, run by `run_t6.sh`. Kept = shots with no detection event (the paper's post-selection). ⟨O⟩ = 1 − 2 × (fraction of kept shots with observable 1). θ = injected polar angle; the T state is θ = π/4.

## Step 4: is our Google baseline the circuit Google ran?

| released circuit (as run) | ours | same gates every time step | same detectors | same observable | real T / T† in Google's cirq file |
|---|---|---|---|---|---|
| fig2/cultivation [X] | G4 | yes | yes | yes | 7 / 7 on 7 data qubits |
| fig2/cultivation [Z] | G4 | no (9 time steps differ) | yes | yes | 7 / 7 on 7 data qubits |
| fig3/with_idle_rounds [X] | G5 | yes | yes | yes | 21 / 21 on 7 data qubits |
| fig4/cultivation_N=2 [X] | G6 | yes | yes | yes | 7 / 7 on 7 data qubits |
| fig4/cultivation_N=2 [Z] | G6 | no (13 time steps differ) | no | no | 7 / 7 on 7 data qubits |

- Our G4 (from the paper's Crumble link, Sec. VII) is the X-tomography circuit Google ran for Fig. 2, gate for gate; G5 = Fig. 3 and G6 = Fig. 4 likewise. The released files add only one trailing idle time step and different detector coordinate labels. The Z files are the second tomography setting (different final basis change), so they are not expected to equal the Crumble circuit.

## Step 1: Google's numbers recomputed from its hardware data with our code

| experiment | shots | kept | retention | our detectors = Google's (first 200,000 shots, X basis) | Google's corrected file = our post-selected raw data |
|---|---|---|---|---|---|
| fig2/injection | 8,600,000 | 6,519,434 | 75.8 % | yes | 86 of 86 (basis, θ) settings |
| fig2/cultivation | 24,600,000 | 6,999,703 | 28.5 % | yes | 82 of 82 (basis, θ) settings |
| fig2/simulation | 24,600,000 | 7,027,582 | 28.6 % | yes | 82 of 82 (basis, θ) settings |
| fig3/injection | 21,500,000 | 4,257,016 | 19.8 % | yes | 43 of 43 (basis, θ) settings |
| fig3/without_idle_rounds | 2,150,000 | 388,774 | 18.1 % | yes | 43 of 43 (basis, θ) settings |
| fig3/with_idle_rounds | 30,100,000 | 1,559,013 | 5.2 % | yes | 43 of 43 (basis, θ) settings |
| fig3/with_idle_rounds_zoom | 7,700,000 | 677,465 | 8.8 % | yes | 11 of 11 (basis, θ) settings |
| fig3/simulation | 6,300,000 | 266,564 | 4.2 % | yes | 9 of 9 (basis, θ) settings |
| fig3/simulation_zoom | 4,200,000 | 271,023 | 6.5 % | yes | 6 of 6 (basis, θ) settings |
| fig4/injection_N=2 | 8,200,000 | 271,530 | 3.3 % | yes | 0 of 82 (basis, θ) settings |
| fig4/cultivation_N=2 | 8,200,000 | 126,476 | 1.5 % | yes | 0 of 82 (basis, θ) settings |
| fig4/cultivation_N=3 | 8,200,000 | 26,065 | 0.3 % | yes | 0 of 82 (basis, θ) settings |
| fig4/simulation_injection_N=2 | 820,000 | 31,241 | 3.8 % | yes | 0 of 82 (basis, θ) settings |

Key values at the T angle (θ = π/4), compared with the paper:

| quantity | our value from Google's data | paper |
|---|---|---|
| Fig. 2 injection retention | 76.2 % ± 0.19 % | about 76 % |
| Fig. 2 cultivation retention | 44.5 % ± 0.13 % | about 45 % (read off Fig. 2D) |
| Fig. 2 cultivation ⟨X⟩_L, ⟨Z⟩_L | 0.707, 0.697 (± 0.004) | near 0.70, 0.70 (Fig. 2C); ideal 0.707 |
| fig3/injection at θ = 0.250π: retention; wrong-sign rate among kept (raw) | 19.50 %; 435 of 97,492 = 1 in 224 (95 %: 1 in 204 to 1 in 247); Google's corrected file: 1 in 224 of 97,492 | about 1 in 230 (4.4(2) x 10^-3) |
| fig3/without_idle_rounds at θ = 0.250π: retention; wrong-sign rate among kept (raw) | 25.78 %; 230 of 12,891 = 1 in 56 (95 %: 1 in 49 to 1 in 64); Google's corrected file: 1 in 56 of 12,891 | – |
| fig3/with_idle_rounds at θ = 0.250π: retention; wrong-sign rate among kept (raw) | 8.32 %; 13 of 58,246 = 1 in 4,480 (95 %: 1 in 2,620 to 1 in 8,414); Google's corrected file: 1 in 4,480 of 58,246 | 1 in 10,000 to 1 in 5,000 (between 1x10^-4 and 2x10^-4), retention 8 % |
| fig3/with_idle_rounds_zoom at θ = 0.250π: retention; wrong-sign rate among kept (raw) | 9.13 %; 10 of 63,909 = 1 in 6,391 (95 %: 1 in 3,475 to 1 in 13,327); Google's corrected file: 1 in 6,391 of 63,909 | 1 in 10,000 to 1 in 5,000 (between 1x10^-4 and 2x10^-4), retention 8 % |
| fig3/simulation at θ = 0.250π: retention; wrong-sign rate among kept (raw) | 7.78 %; 5 of 54,459 = 1 in 10,892 (95 %: 1 in 4,668 to 1 in 33,544); Google's corrected file: 1 in 10,892 of 54,459 | – |
| fig3/simulation_zoom at θ = 0.250π: retention; wrong-sign rate among kept (raw) | 7.78 %; 5 of 54,459 = 1 in 10,892 (95 %: 1 in 4,668 to 1 in 33,544); Google's corrected file: 1 in 10,892 of 54,459 | – |
| **fig3 full cultivation circuit, both hardware runs combined (θ = π/4)** | retention 8.73 %; **23 of 122,155 = 1 in 5,311** (95 %: 1 in 3,540 to 1 in 8,378) | 1 in 10,000 to 1 in 5,000 (between 1x10^-4 and 2x10^-4), retention 8 % |

The wrong-sign rate is the fraction of kept shots whose kickback observable is 1, computed per θ closest to π/4 from raw data. For Fig. 2 and Fig. 3 Google's corrected file equals our post-selected raw data exactly; for Fig. 4 (grafting) Google decoded with Tesseract, which we do not re-implement here.

## Step 2: our simulator vs Google's simulator, our SI1000 at p = 0.30 % (the value the paper states)

Google's simulated shots are in the release (`fig2/simulation`, SI1000 at p = 0.30 % per the paper, 300,000 per basis per θ). z = (ours − Google) / combined standard error; |z| < 3 = agreement within statistics.

| θ (π) | retention: Google sim | ours | z | ⟨X⟩: Google sim | ours | z | ⟨Z⟩: Google sim | ours | z |
|---|---|---|---|---|---|---|---|---|---|
| 0.000 | 0.392 | 0.452 | +46.8 | 0.691 | 0.699 | +2.1 | 0.694 | 0.703 | +2.1 |
| 0.125 | 0.438 | 0.506 | +53.0 | 0.698 | 0.698 | -0.1 | 0.701 | 0.703 | +0.6 |
| 0.250 | 0.454 | 0.526 | +78.9 | 0.700 | 0.705 | +1.8 | 0.702 | 0.704 | +0.8 |
| 0.375 | 0.437 | 0.506 | +53.1 | 0.698 | 0.701 | +0.8 | 0.700 | 0.702 | +0.5 |
| 0.500 | 0.390 | 0.450 | +46.5 | 0.689 | 0.695 | +1.4 | 0.692 | 0.698 | +1.5 |
| 0.750 | 0.237 | 0.268 | +27.0 | 0.646 | 0.665 | +3.5 | 0.649 | 0.674 | +4.7 |
| 1.000 | 0.086 | 0.090 | +5.6 | 0.447 | 0.535 | +8.3 | 0.444 | 0.542 | +9.3 |
| 1.250 | 0.023 | 0.015 | -24.3 | -0.398 | -0.449 | -2.0 | -0.374 | -0.411 | -1.4 |
| 1.500 | 0.087 | 0.091 | +5.1 | 0.459 | 0.542 | +8.0 | 0.456 | 0.554 | +9.5 |
| 1.750 | 0.240 | 0.271 | +27.7 | 0.651 | 0.672 | +3.9 | 0.654 | 0.685 | +5.9 |

Retention: 0 of 10 angles agree within 3 standard errors (largest |z| 78.9). T-state quality ⟨X⟩, ⟨Z⟩: 12 of 20 agree (largest |z| 9.5).

## Step 2: our simulator vs Google's simulator, our SI1000 at p = 0.36 % (our fit, see the gap check below)

Google's simulated shots are in the release (`fig2/simulation`, SI1000 at p = 0.30 % per the paper, 300,000 per basis per θ). z = (ours − Google) / combined standard error; |z| < 3 = agreement within statistics.

| θ (π) | retention: Google sim | ours | z | ⟨X⟩: Google sim | ours | z | ⟨Z⟩: Google sim | ours | z |
|---|---|---|---|---|---|---|---|---|---|
| 0.000 | 0.392 | 0.396 | +3.2 | 0.691 | 0.698 | +1.8 | 0.694 | 0.697 | +0.6 |
| 0.125 | 0.438 | 0.446 | +6.5 | 0.698 | 0.707 | +2.2 | 0.701 | 0.704 | +0.7 |
| 0.250 | 0.454 | 0.462 | +9.1 | 0.700 | 0.705 | +1.7 | 0.702 | 0.702 | +0.0 |
| 0.375 | 0.437 | 0.446 | +6.6 | 0.698 | 0.708 | +2.7 | 0.700 | 0.706 | +1.5 |
| 0.500 | 0.390 | 0.397 | +4.8 | 0.689 | 0.692 | +0.6 | 0.692 | 0.696 | +0.8 |
| 0.750 | 0.237 | 0.239 | +1.0 | 0.646 | 0.655 | +1.5 | 0.649 | 0.654 | +0.8 |
| 1.000 | 0.086 | 0.080 | -8.1 | 0.447 | 0.501 | +4.8 | 0.444 | 0.477 | +2.9 |
| 1.250 | 0.023 | 0.016 | -21.3 | -0.398 | -0.405 | -0.3 | -0.374 | -0.446 | -2.9 |
| 1.500 | 0.087 | 0.082 | -6.9 | 0.459 | 0.495 | +3.2 | 0.456 | 0.496 | +3.7 |
| 1.750 | 0.240 | 0.241 | +1.2 | 0.651 | 0.671 | +3.6 | 0.654 | 0.671 | +3.1 |

Retention: 2 of 10 angles agree within 3 standard errors (largest |z| 21.3). T-state quality ⟨X⟩, ⟨Z⟩: 15 of 20 agree (largest |z| 4.8).

### Gap check: why our SI1000 at 0.30 % keeps more shots than Google's simulation

Per-detector firing rates at the T angle (X basis), ours ÷ Google's simulated shots (`t6_gap_check.py`; Google sim retention 45.3 %, hardware 45.6 %):

| our p | retention | detector rate ÷ Google's (mean over detectors) | spread |
|---|---|---|---|
| 0.30 % | 52.4 % | 0.83 | 0.03 |
| 0.33 % | 49.4 % | 0.90 | 0.04 |
| 0.36 % | 45.7 % | 0.98 | 0.04 |
| 0.39 % | 43.4 % | 1.05 | 0.05 |

Every detector is off by the same factor at 0.30 % (small spread), and one p (about 0.36 %) fits all detectors and the retention at once. So the circuits and detectors agree (step 4); the difference is one overall noise-strength factor: Google's SI1000 implementation at its stated p = 0.30 % is about 1.2× stronger than ours at 0.30 %. A likely cause is a convention detail in how the depolarising channels or idle windows are counted; Google's simulator code is not public, so we state the calibrated equivalence instead (our p ≈ 1.2 × Google's p).

## Step 3: simulation vs Willow hardware (Fig. 2 cultivation circuit)

| θ (π) | retention: hardware | QVM | SI1000 0.30 % (ours) | ⟨X⟩: hardware | QVM | ⟨Z⟩: hardware | QVM |
|---|---|---|---|---|---|---|---|
| 0.000 | 0.379 | 0.410 | 0.452 | 0.697 | 0.699 | 0.690 | 0.692 |
| 0.125 | 0.427 | 0.456 | 0.506 | 0.703 | 0.704 | 0.698 | 0.711 |
| 0.250 | 0.445 | 0.473 | 0.526 | 0.707 | 0.706 | 0.697 | 0.703 |
| 0.375 | 0.434 | 0.456 | 0.506 | 0.695 | 0.695 | 0.686 | 0.697 |
| 0.500 | 0.384 | 0.407 | 0.450 | 0.672 | 0.677 | 0.658 | 0.687 |
| 0.750 | 0.247 | 0.252 | 0.268 | 0.574 | 0.595 | 0.550 | 0.604 |
| 1.000 | 0.107 | 0.097 | 0.090 | 0.255 | 0.284 | 0.186 | 0.298 |
| 1.250 | 0.044 | 0.034 | 0.015 | -0.604 | -0.534 | -0.591 | -0.525 |
| 1.500 | 0.089 | 0.102 | 0.091 | 0.218 | 0.410 | 0.159 | 0.396 |
| 1.750 | 0.228 | 0.257 | 0.271 | 0.604 | 0.653 | 0.597 | 0.631 |

At the T angle: hardware retention 44.5 %, QVM 47.3 % (QVM / hardware = 1.06).

Injection only at θ = 0.250π: retention hardware 76.2 %, QVM 79.2 %, SI1000 0.30 % 76.8 %.

## Figures

- `figures/t6_fig2_retention.png`: retention vs injected angle (Google's Fig. 2D), hardware vs Google's simulation vs ours.
- `figures/t6_fig2_T_state.png`: the cultivated T state's ⟨X⟩, ⟨Z⟩ (Google's Fig. 2C), all four sources.

## Limits

- Steps 2 and 3 cover the Fig. 2 circuit (12 qubits). The Fig. 3 kickback circuit (14 qubits, error about 1 in 10,000) needs far more shots and is reported here from Google's data only (step 1).
- QVM = willow_pink median calibration (2024), not the calibration of the day Google took the data.
- Google's simulated points are their released shots, so step 2 compares shot data with shot data.
