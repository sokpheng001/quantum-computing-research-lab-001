# RESULTS_method3.md — one-cycle distance ranking (Method 3)

Task: docs/task.md. Rebuilt by ours/report_m3.py; last update 2026-10-25 04:51 PM KST. Server runs Track B only; Track A runs on the Mac mini.
All distances are upper bounds from Bravyi's randomised BP-OSD search unless stated otherwise.

## Summary

### Table 1 — Track A (Mac mini)

| Bravyi bound reproduced? | Section 6 setup | Weight-10 sets hidden in alt[S,S^-1] | in alt[S,S_mirror] | Verdict for [[144]] |
|---|---|---|---|---|
| not run on this server (Track A is the Mac mini's) | | | | |

### Table 2 — Track B

| Code | d1(S) | Bravyi value | max d1 over all schedules | # schedules above d1(S) | best alt[A,A^-1] | Beats S? |
|---|---|---|---|---|---|---|
| [[72,12,6]] | upper bound 6 (PASS) | <= 6 | upper bound 6 (1584 schedules) | 0 | none needed | no |
| [[90,8,10]] | upper bound 8 (PASS) | <= 8 | upper bound 8 (1780 schedules) | 0 | none needed | no |
| [[108,8,10]] | upper bound 8 (PASS) | <= 8 | pending | | | |

### Table 3 — circuit-level distance and logical error rate (extra stage, user request; not in task.md)

Circuits: S, alt[S, S^-1], A* (top-ranked schedule: at the maximum d1, the one whose search needed the most trials to reach it) and alt[A*, A*^-1]. Distance: Bravyi setup, 4 and 6 noisy cycles + 2 noiseless, X and Z faults, 5 seeds x 1000 trials (upper bounds). LER: stim circuit, full circuit-level depolarising noise, BP-OSD (min-sum 0.625, OSD-CS 7), 6 cycles; per-cycle rate with 95% range.

| Code | Circuit | d_circ upper bound (X 4c / X 6c / Z 4c / Z 6c) | LER/cycle Z, p=0.5% | X, p=0.5% | Z, p=0.4% | X, p=0.4% |
|---|---|---|---|---|---|---|
| [[90,8,10]] | S | 8 (8 / 8 / 8 / 8) | 0.45% (0.34–0.58%), 53/2000 | 0.47% (0.36–0.61%), 56/2000 | 0.10% (0.08–0.13%), 54/9000 | 0.11% (0.08–0.15%), 50/7500 |
| [[90,8,10]] | alt[S, S^-1] | 8 (8 / 8 / 8 / 8) | 0.47% (0.36–0.61%), 56/2000 | 0.43% (0.33–0.56%), 51/2000 | 0.13% (0.10–0.18%), 52/6500 | 0.13% (0.10–0.18%), 52/6500 |
| [[90,8,10]] | A* = #1277 | 8 (8 / 8 / 8 / 8) | 0.56% (0.44–0.71%), 66/2000 | 0.51% (0.40–0.66%), 61/2000 | 0.09% (0.07–0.12%), 56/10500 | 0.12% (0.09–0.15%), 52/7500 |
| [[90,8,10]] | alt[A*, A*^-1] = #1277 + #268 | 8 (8 / 8 / 9 / 8) | 0.42% (0.33–0.53%), 62/2500 | 0.66% (0.51–0.85%), 58/1500 | 0.10% (0.07–0.13%), 55/9500 | 0.13% (0.10–0.17%), 54/7000 |

### Per code

- [[72,12,6]]: no depth-7 schedule has a one-cycle distance above 6 (Bravyi setup, 1 noisy cycle, X and Z faults, >= 200 trials per fault type and schedule, up to 9000 for any schedule above 6), so no alternation can beat Bravyi's schedule.
- [[90,8,10]]: no depth-7 schedule has a one-cycle distance above 8 (Bravyi setup, 1 noisy cycle, X and Z faults, >= 200 trials per fault type and schedule, up to 9000 for any schedule above 8), so no alternation can beat Bravyi's schedule.

## [[72,12,6]]

### B0 — regression: PASS

Schedules: 1872 valid (S = #212, S^-1 = #1307). Bravyi mapping sX = [idle,1,4,3,5,0,2], sZ = [3,5,0,1,2,4,idle] equals S: True. d1(S): X-type faults upper bound 6 (3000 trials), Z-type upper bound 6 (3000 trials); min 6 vs Bravyi 6.

### d1 of all schedules

Histogram of d1 (min over X/Z faults; after re-runs): {'3': 48, '5': 240, '6': 1584}.  At the fixed 200-trial budget: {'3': 48, '5': 240, '6': 1584}.
Maximum: upper bound 6, reached by 1584 schedules (ids: [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43] ...).
Schedules with d1 above d1(S) after up to 9000 trials per fault type: 0 [].
Table: results_method3/72/d1_72.csv (id, d1_Z, d1_X, trials, ...).

## [[90,8,10]]

### B0 — regression: PASS

Schedules: 1872 valid (S = #212, S^-1 = #1307). Bravyi mapping sX = [idle,1,4,3,5,0,2], sZ = [3,5,0,1,2,4,idle] equals S: True. d1(S): X-type faults upper bound 8 (3000 trials), Z-type upper bound 8 (3000 trials); min 8 vs Bravyi 8.

### d1 of all schedules

Histogram of d1 (min over X/Z faults; after re-runs): {'6': 30, '7': 62, '8': 1780}.  At the fixed 200-trial budget: {'6': 30, '7': 62, '8': 1265, '9': 508, '10': 7}.
Maximum: upper bound 8, reached by 1780 schedules (ids: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39] ...).
Schedules with d1 above d1(S) after up to 9000 trials per fault type: 0 [].
Table: results_method3/90/d1_90.csv (id, d1_Z, d1_X, trials, ...).

## [[108,8,10]]

### B0 — regression: PASS

Schedules: 1872 valid (S = #212, S^-1 = #1307). Bravyi mapping sX = [idle,1,4,3,5,0,2], sZ = [3,5,0,1,2,4,idle] equals S: True. d1(S): X-type faults upper bound 8 (3000 trials), Z-type upper bound 8 (3000 trials); min 8 vs Bravyi 8.

Figures: figures_method3/F4_d1_hist.png; F6_ler.png (error rates) and F7_dcirc.png (distances) from the extra stage; F3 only if B3 finds a winner.
