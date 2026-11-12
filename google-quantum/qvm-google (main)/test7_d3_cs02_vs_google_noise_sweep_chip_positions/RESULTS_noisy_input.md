# Test 7, part D: noisy input to the double check (written 2026-11-11 10:30 PM KST)

Question: earlier runs start the double check from a **perfect** encoded T state. Does cs02 still beat Google's double check when the input is **noisy**, as after injection on the chip?

Setup (`t7_noisy_input.py`): the unencoded logical qubit is prepared at angle phi, then a logical depolarising error is applied **before** encoding (a valid but wrong code state, the failure mode of injection), at a strength giving Google's hardware wrong-state rate at the T angle (1 in 224, test 6, fig3/injection; or 1 in 56, fig3/without_idle_rounds); then the ideal encoder; then 0.1 % depolarising noise on each of the 7 data qubits; then the double check with real T gates under the noise model; then an ideal decode. The input noise is **identical for both circuits**. Kept = no detector fired; errors and Bloch components use kept shots in the code space, as in test 2 / MASTER_RESULTS.md. Only the double check is noisy apart from the input layer; this is not the full Fig. 2 flow (no noisy encoding circuit).

## 1. Error per kept T state at the T angle

| input / noise model | circuit | shots | acceptance | errors / kept in code | T error per kept T state (95 % CI) | cs02 better by (95 % CI) |
|---|---|---|---|---|---|---|
| perfect input (test 2) | Google G4 G6-style | 8,000,000 | 76.7 % | 221 / 4,603,871 | 1 in 20,832 (1 in 18,259 to 1 in 23,876) |  |
| perfect input (test 2) | cs02 (ours) | 8,000,000 | 75.2 % | 42 / 5,095,514 | 1 in 121,322 (1 in 89,754 to 1 in 168,336) | 5.8× (4.2× to 8.1×) |
| noisy input: 1 in 224 wrong + 0.1 % per data qubit, Google QVM | Google G4 G6-style | 8,000,000 | 76.1 % | 261 / 4,550,905 | 1 in 17,436 (1 in 15,445 to 1 in 19,761) |  |
| noisy input: 1 in 224 wrong + 0.1 % per data qubit, Google QVM | cs02 (ours) | 8,000,000 | 74.6 % | 63 / 5,039,977 | 1 in 80,000 (1 in 62,527 to 1 in 104,108) | 4.6× (3.5× to 6.0×) |
| noisy input: 1 in 56 wrong + 0.1 % per data qubit, Google QVM | Google G4 G6-style | 4,000,000 | 75.1 % | 152 / 2,246,309 | 1 in 14,778 (1 in 12,607 to 1 in 17,441) |  |
| noisy input: 1 in 56 wrong + 0.1 % per data qubit, Google QVM | cs02 (ours) | 4,000,000 | 73.6 % | 50 / 2,487,552 | 1 in 49,751 (1 in 37,737 to 1 in 67,030) | 3.4× (2.4× to 4.6×) |
| noisy input: 1 in 224 wrong + 0.1 % per data qubit, SI1000 p = 0.36 % | Google G4 G6-style | 4,000,000 | 68.2 % | 74 / 2,287,781 | 1 in 30,916 (1 in 24,626 to 1 in 39,372) |  |
| noisy input: 1 in 224 wrong + 0.1 % per data qubit, SI1000 p = 0.36 % | cs02 (ours) | 4,000,000 | 63.1 % | 41 / 2,200,116 | 1 in 53,661 (1 in 39,556 to 1 in 74,777) | 1.7× (1.2× to 2.5×) |

## 2. Bloch circle and retention against the input angle (Google QVM, noisy input 1 in 224)

Our frame: the T state is the +1 eigenstate of (X + Y)/√2, so it sits at ⟨X⟩ = ⟨Y⟩ = 0.707 (Google's Fig. 2 uses an equivalent rotated frame with X and Z). phi = input angle on the equator, T at phi = π/4.

| phi (π) | circuit | shots (X + Y) | retention | ⟨X⟩_L | ⟨Y⟩_L | kept in code (X + Y) |
|---|---|---|---|---|---|---|
| 0.250 | Google G4 G6-style | 40,000 | 76.50 % | 0.709 | 0.701 | 22,723 |
| 0.250 | cs02 (ours) | 40,000 | 74.63 % | 0.708 | 0.712 | 25,276 |
| 0.333 | Google G4 G6-style | 40,000 | 74.83 % | 0.698 | 0.700 | 22,488 |
| 0.333 | cs02 (ours) | 40,000 | 73.55 % | 0.709 | 0.710 | 24,708 |
| 0.417 | Google G4 G6-style | 40,000 | 71.41 % | 0.712 | 0.699 | 21,195 |
| 0.417 | cs02 (ours) | 40,000 | 69.79 % | 0.717 | 0.705 | 23,561 |
| 0.500 | Google G4 G6-style | 40,000 | 65.69 % | 0.714 | 0.697 | 19,561 |
| 0.500 | cs02 (ours) | 40,000 | 63.68 % | 0.710 | 0.712 | 21,358 |
| 0.583 | Google G4 G6-style | 40,000 | 57.77 % | 0.707 | 0.705 | 16,993 |
| 0.583 | cs02 (ours) | 40,000 | 56.76 % | 0.726 | 0.709 | 18,994 |
| 0.667 | Google G4 G6-style | 40,000 | 49.40 % | 0.702 | 0.705 | 14,420 |
| 0.667 | cs02 (ours) | 40,000 | 47.88 % | 0.703 | 0.690 | 15,838 |
| 0.750 | Google G4 G6-style | 40,000 | 39.93 % | 0.713 | 0.698 | 11,551 |
| 0.750 | cs02 (ours) | 40,000 | 38.52 % | 0.720 | 0.686 | 12,595 |
| 0.833 | Google G4 G6-style | 40,000 | 30.59 % | 0.691 | 0.694 | 8,582 |
| 0.833 | cs02 (ours) | 40,000 | 29.82 % | 0.733 | 0.688 | 9,446 |
| 0.917 | Google G4 G6-style | 40,000 | 21.79 % | 0.719 | 0.698 | 5,804 |
| 0.917 | cs02 (ours) | 40,000 | 21.19 % | 0.718 | 0.666 | 6,456 |
| 1.000 | Google G4 G6-style | 40,000 | 13.96 % | 0.718 | 0.692 | 3,385 |
| 1.000 | cs02 (ours) | 40,000 | 13.53 % | 0.709 | 0.701 | 3,780 |
| 1.083 | Google G4 G6-style | 40,000 | 8.40 % | 0.703 | 0.639 | 1,667 |
| 1.083 | cs02 (ours) | 40,000 | 7.90 % | 0.766 | 0.660 | 1,877 |
| 1.167 | Google G4 G6-style | 40,000 | 4.83 % | 0.673 | 0.644 | 533 |
| 1.167 | cs02 (ours) | 40,000 | 4.30 % | 0.802 | 0.681 | 522 |
| 1.250 | Google G4 G6-style | 40,000 | 3.60 % | 0.437 | 0.487 | 149 |
| 1.250 | cs02 (ours) | 40,000 | 3.02 % | 0.433 | 0.500 | 127 |
| 1.333 | Google G4 G6-style | 40,000 | 4.71 % | 0.612 | 0.730 | 515 |
| 1.333 | cs02 (ours) | 40,000 | 4.16 % | 0.570 | 0.669 | 565 |
| 1.417 | Google G4 G6-style | 40,000 | 8.40 % | 0.704 | 0.695 | 1,664 |
| 1.417 | cs02 (ours) | 40,000 | 7.79 % | 0.659 | 0.760 | 1,785 |
| 1.500 | Google G4 G6-style | 40,000 | 14.34 % | 0.688 | 0.722 | 3,491 |
| 1.500 | cs02 (ours) | 40,000 | 13.61 % | 0.703 | 0.721 | 3,828 |
| 1.583 | Google G4 G6-style | 40,000 | 21.57 % | 0.698 | 0.724 | 5,717 |
| 1.583 | cs02 (ours) | 40,000 | 21.10 % | 0.679 | 0.725 | 6,410 |
| 1.667 | Google G4 G6-style | 40,000 | 30.74 % | 0.683 | 0.724 | 8,621 |
| 1.667 | cs02 (ours) | 40,000 | 29.87 % | 0.686 | 0.729 | 9,574 |
| 1.750 | Google G4 G6-style | 40,000 | 39.96 % | 0.700 | 0.703 | 11,576 |
| 1.750 | cs02 (ours) | 40,000 | 38.70 % | 0.708 | 0.718 | 12,664 |
| 1.833 | Google G4 G6-style | 40,000 | 48.98 % | 0.706 | 0.714 | 14,238 |
| 1.833 | cs02 (ours) | 40,000 | 48.13 % | 0.705 | 0.719 | 16,007 |
| 1.917 | Google G4 G6-style | 40,000 | 57.75 % | 0.707 | 0.714 | 16,921 |
| 1.917 | cs02 (ours) | 40,000 | 56.23 % | 0.688 | 0.726 | 18,754 |
| 0.000 | Google G4 G6-style | 40,000 | 65.33 % | 0.708 | 0.701 | 19,442 |
| 0.000 | cs02 (ours) | 40,000 | 64.34 % | 0.698 | 0.701 | 21,535 |
| 0.083 | Google G4 G6-style | 40,000 | 71.27 % | 0.702 | 0.713 | 21,218 |
| 0.083 | cs02 (ours) | 40,000 | 69.96 % | 0.702 | 0.710 | 23,546 |
| 0.167 | Google G4 G6-style | 40,000 | 75.28 % | 0.706 | 0.709 | 22,493 |
| 0.167 | cs02 (ours) | 40,000 | 73.16 % | 0.700 | 0.702 | 24,754 |

## Figures

- `figures/t7_noisy_input_circle.png`: (a) Bloch circle, (b) zoom near the T state, (c) retention against the input angle.
- `figures/t7_noisy_input_error.png`: error per kept T state, perfect vs noisy input, both circuits.

Chunks read: 6784 (33,920,000 shots). Log: `logs/noisy_input.log`.
