# TASKS_core.md — the minimum path to the result (12 cores, 48 GB)

Only what the research question needs. Hours are wall-clock on this machine
with workers sized to memory ([[72]]: up to 12 workers; [[144]]: max 8).
Run everything detached (tmux/nohup), checkpoint every point to CSV, save raw
samples for every LER run.

Decoder fixed: BP min-sum (0.625) + OSD-CS order 7. p: [[72]] 0.002/0.004/0.006;
[[144]] 0.004/0.005. Cycles: 6 for LER, 4 for bounds. >= 50 failures per point.

| # | Task | Output | Hours |
|---|------|--------|-------|
| A | Phase 3.1: bounds + n_min + SAVED fault sets, Z-first 936, both bases | bounds_936.csv, faultsets/ | 4-8 |
| B | Phase 3.2-3.3: symmetry classes; ranking; Bravyi's rank | RESULTS.md table, hist figures | 1 |
| C | Phase 3.4: LER for best / worst / median / Bravyi, both bases | single_schedules_ler.png | 6 |
| D | Phase 4.1-4.2: pairwise fault-set overlap in top 20 -> 5 disjoint pairs + (best,best^-1); alternating bounds | pair_candidates.csv | 2 |
| E | Phase 4.3: LER for finalist pair vs best single | exp2_pairs_ler.png | 4 |
| F | Phase 5.1: [[144]] bounds for S, alt S/S^-1, finalist pair | exp_144_bounds.csv | 6-12 |
| G | Phase 5.2: verification checklist if any bound > 10 | note in RESULTS.md | 2-4 |
| H | Phase 5.3: [[144]] LER for S + any circuit bounding > 10 (else best pair at p=0.005 only) | exp_144_ler.png | 24-48 |
| I | Phase 2.5: p=0.002 resample on [[72]] (runs in gaps) | exp1 redraw | 6-8 |

Critical path: A -> B -> D -> F -> G  (ranking to gross-code bound) ~ 15-25 h.
Everything else (C, E, H, I) is confirmation by simulation and can run behind.

Schedule on this machine
  Day 1: A (8 workers) + the already-running [[144]] S/alt LER (4 workers) or I.
  Day 2: B, D, then F (8 workers) + C (4 workers).
  Day 3: G if needed, E, start H.
  Day 4: H continues; write-up.

Headline numbers, in the order they arrive
  1. Bravyi's rank among 936 and the number of symmetry classes      (end of day 1)
  2. Does n_min predict LER? (C vs B)                                 (day 2)
  3. Best alternating bound on [[144]]  -> >10 or not                (day 2-3)
  4. LER confirmation on [[144]]                                      (day 3-4)

Not in scope (already known or uninformative): X-first half of the sweep;
p = 0.001 or 0.008; 12-cycle runs; LER for S^-1 alone on [[144]]; any
single-schedule sweep on [[144]] (Bravyi: all <= 10); AlphaSyndrome lookup,
second noise model, decoder-robustness study (secondary, after the above).

Prompts
  K1 "Read TASKS_core.md. Confirm task A is saving fault sets with the DEM
      column key and running Z-first only; rebalance workers (A on 8, the
      [[144]] run on 4). Report when A finishes."
  K2 "Tasks B and D. Give me the ranking table, Bravyi's rank, the number of
      symmetry classes, and the 5 disjoint pairs with their alternating bounds."
  K3 "Task F on [[144]]: bounds for S, alt S/S^-1, and the finalist pair.
      If anything bounds > 10, run task G before reporting the number."
  K4 "Tasks C, E, H as cores free up. Then I. Save raw samples for all."