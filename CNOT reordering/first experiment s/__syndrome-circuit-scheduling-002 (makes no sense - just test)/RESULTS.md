# RESULTS.md — folder 002: L/R block schedules on [[72,12,6]] (docs/task.md)

## Phase 1 — code matrices: PASS
H_X = [A | B], H_Z = [B^T | A^T] from 36×36 shift matrices; identical to folder 001.
Every check has 3 targets in the Left block (qubits 0–35) and 3 in the Right block (36–71); k = 12.

## Phase 2 — L/R strategies: none is a valid depth-7 circuit
1,296 schedules per strategy, three time layouts (results/phase2_strategies.json):

| strategy | layers 1–6, layer 7 buffer | staggered, Z first | staggered, X first |
|---|---|---|---|
| A: L then R | collision | collision | collision |
| B: R then L | collision | collision | collision |
| C: X uses A, Z uses B | random detectors | collision | collision |

Strategy C fails because every overlapping X/Z check pair shares one L and one R qubit, and C puts
the X CNOT first on L but the Z CNOT first on R (stim confirms random detectors).
None of the 518,400 schedules with both sides in layers 1–6 is valid (results/simultaneous_layout.json).

## Phases 3–4 — distance of all 1,872 valid schedules
stim search for undetectable logical errors, 3 cycles, exploration limit 4 (upper bound on d_circ).
task.md's graph-based shortest path cannot be used: BB-code faults trip 3+ detectors.

| L/R switches (X + Z) | schedules | d_circ 6 | d_circ 5 | d_circ 3 |
|---|---|---|---|---|
| 4 (most L/R-like valid form) | 1,728 | 1,584 | 144 | 0 |
| 10 (fully alternating) | 144 | 96 | 0 | 48 |

The maximum possible d_circ (6) is reached by 1,584 L/R-like schedules; their 7-layer arrays are in
results_72code.json. Every distance-3 schedule switches block at every CNOT.
Figure: figures/dcirc_by_lr_switches.png. Data: results/distance_72.csv.

## Error rates (running)
S (Bravyi) vs the first L/R-like d_circ = 6 schedule vs a fully alternating d_circ = 3 schedule,
6 cycles, both bases, p = 0.006 and 0.004, BP-OSD (OSD-CS order 7).
Data: results/ler_72.csv. Figure: figures/ler_72_lr.png (redrawn after every point).
