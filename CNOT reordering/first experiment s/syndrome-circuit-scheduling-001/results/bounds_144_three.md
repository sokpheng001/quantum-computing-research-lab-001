
## [[144]] three-circuit bounds: S, S^-1, alternating S/S^-1 (2026-10-14)

Multi-seed randomised BP-OSD search, 4 cycles, OSD-CS order 20, 10 serial min-sum iterations, random channel
priors; 5 independent seeds per circuit and basis. Values are upper bounds (a found fault path).

| circuit | basis | seed 1 | seed 2 | seed 3 | seed 4 | seed 5 | min over seeds | trials per seed |
|---|---|---|---|---|---|---|---|---|
| S | Z | <= 11 | <= 11 | <= 11 | <= 12 | <= 12 | <= 11 | 2400 |
| S | X | <= 11 | <= 11 | <= 11 | <= 11 | <= 11 | <= 11 | 2400 |
| S^-1 | Z | <= 11 | <= 11 | <= 11 | <= 11 | <= 11 | <= 11 | 2400 |
| S^-1 | X | <= 11 | <= 11 | <= 11 | <= 10 | <= 12 | <= 10 | 2400 |
| alt S/S^-1 | Z | <= 12 | <= 11 | <= 12 | <= 12 | <= 12 | <= 11 | 2400 |
| alt S/S^-1 | X | <= 11 | <= 11 | <= 11 | <= 11 | <= 11 | <= 11 | 2400 |

S: d_circ <= 11 (min over bases)
S^-1: d_circ <= 10 (min over bases)
alt S/S^-1: d_circ <= 11 (min over bases)
Z: bound(alt) = 11 vs min(bound(S), bound(S^-1)) = 11 -> Shaw-Terhal Prop. 3 consistent: True
X: bound(alt) = 11 vs min(bound(S), bound(S^-1)) = 10 -> Shaw-Terhal Prop. 3 consistent: True

Step 4 checks (noiseless detectors zero; detector count equal to S):

| circuit | cycles | basis | detectors | nonzero noiseless detectors / observables |
|---|---|---|---|---|
| S | 4 | Z | 576 | 0 / 0 |
| S | 4 | X | 576 | 0 / 0 |
| S | 6 | Z | 864 | 0 / 0 |
| S | 6 | X | 864 | 0 / 0 |
| S^-1 | 4 | Z | 576 | 0 / 0 |
| S^-1 | 4 | X | 576 | 0 / 0 |
| S^-1 | 6 | Z | 864 | 0 / 0 |
| S^-1 | 6 | X | 864 | 0 / 0 |
| alt | 4 | Z | 576 | 0 / 0 |
| alt | 4 | X | 576 | 0 / 0 |
| alt | 6 | Z | 864 | 0 / 0 |
| alt | 6 | X | 864 | 0 / 0 |

All Step 4 circuit checks pass: True

Step 3, exact mapping of each single schedule's lowest-weight fault sets into the alternating circuit
(only sets whose faults lie in cycles where alt runs that same schedule are mappable):

| single | basis | weight | sets | result |
|---|---|---|---|---|
| S^-1 | X | 10 | 1 | 1 not mappable (uses cycles where alt runs the other schedule) |
| S^-1 | X | 11 | 7 | 5 mappable: UNDETECTED and LOGICAL in alt; 2 not mappable (uses cycles where alt runs the other schedule) |
| S | X | 11 | 32 | 31 mappable: UNDETECTED and LOGICAL in alt; 1 not mappable (uses cycles where alt runs the other schedule) |
| S^-1 | Z | 11 | 29 | 1 mappable: UNDETECTED and LOGICAL in alt; 28 not mappable (uses cycles where alt runs the other schedule) |
| S | Z | 11 | 4 | 4 not mappable (uses cycles where alt runs the other schedule) |

Figure: figures/exp_144_bounds.png (lowest weight found vs trials, per seed).
