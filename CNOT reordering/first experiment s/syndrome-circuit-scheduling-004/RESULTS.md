# RESULTS.md — folder 004: three-circuit experiment on the [[90,8,10]] BB code

Code: [[90,8,10]], l = 15, m = 3, A = x^9 + y + y^2, B = 1 + x^2 + x^7 (Bravyi et al. 2024).
Circuits: S (Bravyi's schedule), S^-1 (time reverse), alternating S/S^-1. All three verified:
noiseless detectors all zero in both bases, 360 detectors at 4 cycles, k = 8.
Decoder: the project's fixed BP-OSD (serial min-sum, scaling 1.0, 100 iterations, OSD-CS order 7).
Reference: Bravyi et al. report d_circ <= 8 for this code with schedule S.
Results are appended below by driver_004.sh.

## [[90,8,10]] three-circuit d_circ bounds (2026-10-14)

| circuit | basis | seed 1 | seed 2 | seed 3 | seed 4 | seed 5 | min over seeds | trials per seed |
|---|---|---|---|---|---|---|---|---|
| S | Z | <= 9 | <= 10 | <= 9 | <= 8 | <= 9 | <= 8 | 600 |
| S | X | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | 600 |
| S^-1 | Z | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | 600 |
| S^-1 | X | <= 10 | <= 10 | <= 9 | <= 9 | <= 10 | <= 9 | 600 |
| alt S/S^-1 | Z | <= 8 | <= 9 | <= 10 | <= 9 | <= 10 | <= 8 | 600 |
| alt S/S^-1 | X | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | 600 |

S: d_circ <= 8 (min over bases)
S^-1: d_circ <= 9 (min over bases)
alt S/S^-1: d_circ <= 8 (min over bases)
Z: bound(alt) = 8 vs min(bound(S), bound(S^-1)) = 8 -> Shaw-Terhal Prop. 3 consistent: True
X: bound(alt) = 9 vs min(bound(S), bound(S^-1)) = 9 -> Shaw-Terhal Prop. 3 consistent: True

Figure: figures/exp_90_bounds.png

## [[90,8,10]] three-circuit logical error rate, 6 cycles (2026-10-15)

| p | S (Bravyi) Z | S (Bravyi) X | S^-1 Z | S^-1 X | alt S/S^-1 Z | alt S/S^-1 X |
|---|---|---|---|---|---|---|
| 0.004 | 35/3000 (2.0e-03) | 36/4000 (1.5e-03) | 33/3000 (1.8e-03) | 40/5000 (1.3e-03) | 35/3000 (2.0e-03) | 42/4000 (1.8e-03) |
| 0.005 | 34/1000 (5.7e-03) | 30/1000 (5.1e-03) | 37/1000 (6.3e-03) | 34/1000 (5.7e-03) | 58/1500 (6.6e-03) | 35/1000 (5.9e-03) |
| 0.006 | 30/300 (1.7e-02) | 31/300 (1.8e-02) | 31/300 (1.8e-02) | 59/600 (1.7e-02) | 37/300 (2.2e-02) | 37/300 (2.2e-02) |
figure: figures/exp_90_three_ler.png

Figure: figures/exp_90_three_ler.png

## Why alternation gives no gain on [[90,8,10]] (exact check, 2026-10-15)

S's weight-8 fault path (Z basis) was mapped exactly into the alternating circuit (stim, physical fault
locations; ../syndrome-circuit-scheduling-001/step3_exact.py --n 90). It can be placed entirely in a
cycle where the alternating circuit runs S, and there it is still undetected and flips a logical.
So the alternating circuit keeps S's lightest path: d_circ(alt) <= 8 exactly, the same as S.
Alternation can only break paths that need two consecutive cycles of the same schedule; on [[90]]
the lightest path fits inside one cycle. (Contrast [[144]]: S^-1's weight-10 path spans two consecutive
S^-1 cycles, which the alternating circuit never has.) Output: results/step3_90_Z_212_w8.json
