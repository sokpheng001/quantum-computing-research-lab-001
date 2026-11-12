# Test 4 side check: toy noise at lower p (Clifft, real T), Nov 4, 2026

Same toy noise as the validation (DEPOLARIZE1(p) on every qubit after every moment, no gate or measurement
errors; double check alone, ideal |T_L> in, ideal decode). NOT a Willow-noise result: it only shows how the
gap between fault distance 2 and 3 depends on p in this model. `toy_noise_p_sweep.py`; the run stopped at
the shell time limit after p = 0.05 % (log: `logs/toy_noise_p_sweep.log`); the p = 0.2 % and 0.5 % rows are the
Clifft rows of `RESULTS_validation.md`.

| p | Google G6-style (FD 2): errors / kept in code | error per kept T state | cs02 (FD 3): errors / kept in code | error per kept T state | Google / cs02 |
|---|---|---|---|---|---|
| 0.02 % | 215 / 1,900,868,155 | 1 in 8,841,247 | 52 / 1,867,103,529 | 1 in 35,905,837 | **4.1×** |
| 0.05 % | 1,580 / 1,761,412,596 | 1 in 1,114,818 | 482 / 1,684,306,001 | 1 in 3,494,411 | **3.1×** |
| 0.2 % | 2,940 / 120,522,075 | 1 in 40,994 | 2,172 / 100,861,843 | 1 in 46,437 | 1.1× |
| 0.5 % | 16,902 / 56,908,945 | 1 in 3,367 | 14,966 / 36,639,918 | 1 in 2,448 | 0.7× |

Acceptance (Google / cs02): 97.00 / 95.21 % at 0.02 %, 92.68 / 88.49 % at 0.05 %, 74.08 / 61.92 % at 0.2 %,
48.26 / 31.79 % at 0.5 %.

Reading: from 0.05 % to 0.02 % Google's error falls 7.9× (about p^2.3) and cs02's 10.3× (about p^2.5); the
advantage of fault distance 3 grows as p falls and disappears around p = 0.2 % in this idle-heavy toy model.
