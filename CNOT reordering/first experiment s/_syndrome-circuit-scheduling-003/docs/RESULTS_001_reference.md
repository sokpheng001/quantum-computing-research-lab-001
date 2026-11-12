# RESULTS.md — phase log (see TASKS.md for PASS conditions, CLAUDE.md for definitions)

Decoder fixed 2026-10-12: ldpc 2.4.1 BpOsdDecoder, serial min-sum, scaling 1.0,
100 iterations, OSD-CS order 7, DEM priors. Bound search: serial, 10 iterations,
OSD-CS order 20, random channel priors.

## Phase 1.1 — dcirc_bound tightened (2026-10-12)  **PASS**

[[72,12,6]], 6 cycles, p = 0.001, 600 randomised BP-OSD trials per configuration
(12 seeds x 50). Values are upper bounds. Data: results/bounds_exp1.csv.

| schedule | basis | d_circ | distinct min-weight fault sets found |
|---|---|---|---|
| S (id 212) | Z | <= 6 | 58 |
| S (id 212) | X | <= 6 | 69 |
| S^-1 (id 1307) | Z | <= 6 | 62 |
| S^-1 (id 1307) | X | <= 6 | 92 |
| alt S/S^-1 | Z | <= 6 | 68 |
| alt S/S^-1 | X | <= 6 | 75 |

bound(alt) >= min(bound(S), bound(S^-1)) holds in both bases (6 = 6). The earlier
X-basis values of 8 for S and S^-1 were an artefact of ldpc's parallel BP
schedule, which does not converge on these detector error models; the serial
schedule finds weight-6 paths within ~10 trials. Note that d_circ <= 6 is trivial
for every schedule on [[72]]: in the measurement round all data qubits idle
simultaneously, so a weight-6 code logical placed there is undetected.

## Phase 1.3 — enumeration of depth-7 schedules (2026-10-12)  **PASS (936 per starting side)**

enumerate_schedules.py: 6! x 6! x 2 = 1,036,800 candidates; pruning rule = no
round with the X side on an A label while the Z side is on a B label or vice
versa (same register -> every data qubit in two CNOTs in one round); validity =
all noiseless detectors zero, cross-checked against an algebraic criterion
(for every X-check/Z-check pair an even number of the two shared data qubits has
its Z-CNOT before its X-CNOT) on 300 random candidates: 298/300 agree, the 2
disagreements are collisions that stim serialises and accepts, i.e. the
algebraic + collision test is the stricter and correct one.

Count: **936 with Z first, 936 with X first, 1872 total**; every schedule's time
reverse is valid (reverse_id never -1). Bravyi et al. report "935 depth-7
alternatives" to their circuit, i.e. 936 with the starting side fixed as in
their Table 5, which is what we reproduce. Both S (id 212) and S^-1 (id 1307)
are in the set. Files: results/schedules.jsonl, results/schedules_72.json,
results/schedules_144.json (identical count for the gross code).

## Phase 1.2 — reproduction of Bravyi 2024 Fig. 2A, [[72,12,6]], S only, 6 cycles (2026-10-13)

| p | Z fails/shots | X fails/shots | our p_L/cycle (both types) | Bravyi fit | ratio ours/Bravyi |
|---|---|---|---|---|---|
| 0.002 | 35/30000 | 4/2000 | 5.28e-04 [2.7e-04,1.1e-03] | 1.02e-03 | 0.52 |
| 0.003 | 62/12000 | 61/10000 | 1.88e-03 [1.5e-03,2.4e-03] | 4.58e-03 | 0.41 |
| 0.004 | 33/1500 | 31/1500 | 7.16e-03 [5.1e-03,1.0e-02] | 1.40e-02 | 0.51 |
| 0.005 | 62/1024 | 79/1000 | 2.38e-02 [1.9e-02,3.0e-02] | 3.41e-02 | 0.70 |
| 0.006 | 165/1000 | 176/1000 | 6.04e-02 [5.2e-02,7.0e-02] | 7.11e-02 | 0.85 |
| 0.008 | 258/500 | 281/500 | 2.28e-01 [2.0e-01,2.5e-01] | 2.23e-01 | 1.02 |

Figure: figures/bravyi_reproduction.png. PASS condition: within a factor ~3 of Bravyi at the same p.

## Task B — ranking of the 936 Z-first depth-7 schedules, [[72]], 4 cycles, 100 trials (2026-10-13)

Key: min(dZ,dX) desc, then nontrivial min-weight sets (Z+X) asc, then all min-weight sets asc. Core (schedule-independent) keys: Z 17, X 14; a set is nontrivial if it uses a non-core fault.

Bound values: {3: 24, 6: 809, 5: 100, 4: 3}. Nontrivial sets per schedule: min 2, median 22, max 43.

Symmetry: T1 maps 936/936 and T2 maps 936/936 schedules into the Z-first set; **270 classes** (sizes {2: 72, 4: 198}); bounds agree within 248/270 classes.

**Bravyi S (id 212): rank 514 of 936, class 129** (class members [212, 310, 676, 774]).


Top 5:
| rank | id | class | dZ | dX | min-weight sets Z / X | nontrivial Z / X | X order / Z order |
|---|---|---|---|---|---|---|---|
| 1 | 744 | 1 | <= 6 | <= 6 | 7 / 6 | 5 / 5 | B2 A3 A1 A2 B3 B1 / B1 B3 A3 A1 A2 B2 |
| 2 | 540 | 2 | <= 6 | <= 6 | 5 / 8 | 5 / 6 | B1 A2 A1 A3 B3 B2 / B3 B2 A2 A1 A3 B1 |
| 3 | 873 | 3 | <= 6 | <= 6 | 7 / 6 | 6 / 5 | B3 A2 A3 A1 B2 B1 / B1 B2 A3 A2 A1 B3 |
| 4 | 716 | 4 | <= 6 | <= 6 | 7 / 7 | 6 / 6 | B2 A2 A3 A1 B3 B1 / B1 B3 A3 A1 A2 B2 |
| 5 | 750 | 5 | <= 6 | <= 6 | 8 / 6 | 7 / 5 | B2 A3 A1 A2 B3 B1 / B3 B1 A3 A1 A2 B2 |

Median:
| rank | id | class | dZ | dX | min-weight sets Z / X | nontrivial Z / X | X order / Z order |
|---|---|---|---|---|---|---|---|
| 469 | 243 | 142 | <= 6 | <= 6 | 16 / 15 | 13 / 11 | A2 B2 B3 B1 A1 A3 / A3 A1 B1 B3 B2 A2 |

Bottom 5:
| rank | id | class | dZ | dX | min-weight sets Z / X | nontrivial Z / X | X order / Z order |
|---|---|---|---|---|---|---|---|
| 932 | 934 | 268 | <= 3 | <= 3 | 8 / 9 | 8 / 9 | B3 A3 B2 A1 B1 A2 / A2 B1 A1 B2 A3 B3 |
| 933 | 156 | 265 | <= 3 | <= 3 | 10 / 8 | 10 / 8 | A2 B1 A1 B2 A3 B3 / B3 A3 B2 A1 B1 A2 |
| 934 | 417 | 269 | <= 3 | <= 3 | 8 / 10 | 8 / 10 | A3 B3 A1 B2 A2 B1 / B1 A2 B2 A1 B3 A3 |
| 935 | 568 | 270 | <= 3 | <= 3 | 9 / 10 | 9 / 10 | B1 A2 B2 A1 B3 A3 / A3 B3 A1 B2 A2 B1 |
| 936 | 52 | 270 | <= 3 | <= 3 | 8 / 13 | 8 / 13 | A1 B2 A2 B1 A3 B3 / B3 A3 B1 A2 B2 A1 |

Bravyi:
| rank | id | class | dZ | dX | min-weight sets Z / X | nontrivial Z / X | X order / Z order |
|---|---|---|---|---|---|---|---|
| 514 | 212 | 129 | <= 6 | <= 6 | 20 / 12 | 16 / 9 | A2 B2 B1 B3 A1 A3 / A1 A3 B1 B2 B3 A2 |

Figure: figures/hist_dcirc_936.png; table: results/ranking_936.csv

## Task D — candidate pairs, alternating d_circ bounds on [[72]], 4 cycles, 600 trials (2026-10-13)

| spec | dZ | dX | min-weight sets Z / X | nontrivial Z / X |
|---|---|---|---|---|
| 497+303 | <= 6 | <= 6 | 56 / 57 | 54 / 48 |
| 744 (best single) | <= 6 | <= 6 | 57 / 61 | 52 / 58 |
| 744+1517 | <= 6 | <= 6 | 53 / 70 | 51 / 62 |
| 716+497 | <= 6 | <= 6 | 75 / 50 | 70 / 43 |
| 744+321 | <= 6 | <= 6 | 60 / 64 | 56 / 59 |
| 540+391 | <= 6 | <= 6 | 53 / 74 | 51 / 71 |
| 540+750 | <= 6 | <= 6 | 64 / 84 | 61 / 78 |

**Finalist pair: 497+303** (highest min bound, then fewest nontrivial min-weight sets). Candidates: results/pair_candidates.csv

## Task G — verification of [[144]] bounds above S (2026-10-13)

4-cycle bounds (min over bases): 212: <= 11, 1307: <= 11, 212+1307: <= 11, 497+303: <= 10, 744+1517: <= 10, 744: <= 11

Bravyi et al. report d_circ <= 10 for S; this search gives <= 11 for S, so the criterion is "bounds strictly above S".
Circuits above S at 4 cycles: none.

Nothing to verify.

## Interpretation of tasks B, D, F, G (written 2026-10-14)

- Not every depth-7 schedule keeps d = 6 on [[72]]: 127 of 936 drop below it (100 to <= 5, 3 to <= 4,
  24 to <= 3). A lower bound found by the search is a real fault path, so these drops are definitive.
  Bravyi's S keeps 6 in both bases but ranks 514/936 on the number of nontrivial min-weight sets.
- Symmetry: 270 classes. Bounds agree in 248 of 270; in the other 22 the 100-trial search missed the
  lower value for some member. The true bound of a class is its lowest member value.
- Pairs on [[72]]: every candidate pair, and the best single schedule, stays at <= 6. As expected on
  [[72]], no pair can exceed d, so the pair choice there rests on path counts only.
- Gross code, 4 cycles, ~4000 trials each: S <= 11, S^-1 <= 11, alt S/S^-1 <= 12 (Z) / <= 11 (X),
  best single 744 <= 11, finalist pair 497+303 <= 11 (Z) / <= 10 (X), 744 + its reverse <= 10 both.
  Weight-10 paths exist for the [[72]]-selected circuits, so they are NOT better than S; since Bravyi
  reports 10 for S as well, the most likely reading is that all of these circuits sit at 10 and our
  search simply has not found S's weight-10 paths. No circuit beats S; task G had nothing to verify.
- Conclusion so far: ranking on [[72]] does not transfer to a distance gain on [[144]]. The only open
  candidate for a gain is alt S/S^-1 in the Z basis (<= 12), which needs a stronger search on S and
  on alt before it can be quoted.

## [[72]] finding — depth-7 orderings that reduce circuit-level distance (2026-10-14)

**127 of 936 valid depth-7 orderings reduce circuit-level distance, down to 3.**

| min(dZ, dX) upper bound | schedules |
|---|---|
| 5 | 100 |
| 4 | 3 |
| 3 | 24 |
| 6 (= d) | 809 |

Per basis: Z basis below 6 in 92 schedules {3: 24, 4: 3, 5: 65}, X basis in 97 {3: 23, 4: 1, 5: 73}; both bases in 62.
Each of these values is a fault path actually found, so the reduction is certain for the 4-cycle memory circuit.
The paths are short in time (hook errors), so they also occur in longer memory circuits.
Caveat: in 17 of the 270 symmetry classes the members disagree; if the symmetry holds, the 100-trial search
missed the lower value for some members, and taking each class minimum gives 142 schedules below 6. Quote 127 (directly found).

The 5 worst schedules:

| rank | id | dZ | dX | min-weight sets Z / X | X order | Z order |
|---|---|---|---|---|---|---|
| 936 | 52 | <= 3 | <= 3 | 8 / 13 | A1 B2 A2 B1 A3 B3 | B3 A3 B1 A2 B2 A1 |
| 935 | 568 | <= 3 | <= 3 | 9 / 10 | B1 A2 B2 A1 B3 A3 | A3 B3 A1 B2 A2 B1 |
| 934 | 417 | <= 3 | <= 3 | 8 / 10 | A3 B3 A1 B2 A2 B1 | B1 A2 B2 A1 B3 A3 |
| 933 | 156 | <= 3 | <= 3 | 10 / 8 | A2 B1 A1 B2 A3 B3 | B3 A3 B2 A1 B1 A2 |
| 932 | 934 | <= 3 | <= 3 | 8 / 9 | B3 A3 B2 A1 B1 A2 | A2 B1 A1 B2 A3 B3 |

In all five, both the X order and the Z order alternate between A and B labels, so consecutive CNOTs
of one ancilla alternate between the L and R data registers. Figure: figures/hist_dcirc_below6.png.
