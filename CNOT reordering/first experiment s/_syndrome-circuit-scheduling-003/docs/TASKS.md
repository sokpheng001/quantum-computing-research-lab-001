# TASKS.md — instructions for Claude Code

Work through the phases in order. Do not start a phase until the previous
phase's PASS condition is met and recorded in RESULTS.md. Keep CLAUDE.md
updated with any change of definition. Never change the decoder settings
after Phase 0.3 is fixed; if you must, record it as a new experiment.

Conventions
- Every script writes to results/*.csv with a header and appends, never overwrites.
- Every result row carries: n, basis, cycles, p, shots, seed, schedule id(s).
- Log d_circ values as "<= k" (they are upper bounds from a heuristic search).
- Use multiprocessing (all cores) for anything that decodes shots.
- Save every schedule as a JSON line: {"id":..,"x":[..],"z":[..],"z_first":bool}.

---------------------------------------------------------------------------
PHASE 1 — VALIDATE THE TOOLS
---------------------------------------------------------------------------

1.1 Tighten dcirc_bound
  Goal: bounds for S, S^-1 and alternating S/S^-1 on [[72]] must satisfy
        bound(alt) >= min(bound(S), bound(S^-1)) in BOTH bases (Shaw & Terhal Prop. 3).
  Do:  in dcirc.py, make dcirc_bound run many randomised BP-OSD trials per logical
       (random channel probabilities, osd_order up to 20, different seeds), keep
       the minimum weight found; add an early stop once weight == code distance.
       Add a function min_weight_count(circuit, w) that counts distinct fault sets
       of weight w found across trials (for Phase 3.2).
  PASS: X-basis bounds for S and S^-1 drop to the same value as alt (expected 6).
  Record: results/bounds_exp1.csv

1.2 Reproduce Bravyi's [[72,12,6]] curve
  Do:  run_experiment1.py with case S only, cycles = 6, p = 0.001 0.002 0.003 0.005,
       shots chosen so that at least 50 failures are seen per point (increase shots
       at low p; use --skip_bound).
  PASS: logical error per cycle within a factor ~3 of Bravyi 2024 Fig. 2A at the
       same p (our noise model is uniform depolarising; theirs is similar but not
       identical, so exact agreement is not expected). Plot both on one log-log
       figure: figures/bravyi_reproduction.png.

1.3 Enumerate the depth-7 schedules
  Do:  new file enumerate_schedules.py:
       for every permutation of the X labels, every permutation of the Z labels,
       and z_first in {True, False}: build memory_circuit on [[72]] with p = 0,
       cycles = 2, in both bases; keep the schedule if all detectors are zero.
       Prune early: skip any (x_order, z_order, z_first) where some round has
       the X side and Z side on the same register (A with B^T or B with A^T).
       Write results/schedules.jsonl with ids 0..N-1. Also store, for each
       schedule, the id of its time-reverse (or -1 if the reverse is not valid).
  PASS: N == 936. If N != 936, STOP and report the count and three example
       schedules that were accepted/rejected; do not proceed until resolved.

---------------------------------------------------------------------------
PHASE 2 — EXPERIMENT 1: S vs S^-1 vs ALTERNATING on [[72]]
---------------------------------------------------------------------------

2.1 run_experiment1.py, both bases, cycles = 6, p = 0.002 0.004 0.006 0.008,
    shots >= 2000 per point (more at low p).
2.2 Report per case: d_circ bound (from 1.1), P_L per cycle vs p with
    binomial error bars, BP convergence fraction.
2.3 Figure: figures/exp1_ler_vs_p.png, three curves per basis.
2.4 Write a short paragraph in RESULTS.md: does alternation beat S? by how much?
    is the difference outside the error bars?
  PASS: all points have >= 30 failures; error bars drawn.

---------------------------------------------------------------------------
PHASE 3 — MAP ALL 936 SINGLE SCHEDULES
---------------------------------------------------------------------------

3.1 bounds_all.py: for every schedule in schedules.jsonl, d_circ bound in both
    bases on [[72]], cycles = 4, using the Phase 1.1 search. Parallel over
    schedules. Output results/bounds_936.csv: id, dZ, dX.
    Figure: figures/hist_dcirc_936.png.
3.2 For every schedule, count distinct minimum-weight fault sets (min_weight_count
    at w = dZ and w = dX). Add columns nZ, nX to bounds_936.csv.
3.3 Rank by (max(dZ,dX) desc, then nZ+nX asc). Report: top 5, bottom 5, median,
    Bravyi's rank, and the rank of AlphaSyndrome's [[72]] schedule if it is in
    the depth-7 set (fetch it from https://github.com/acasta-yhliu/asyndrome and
    convert; if it is not depth-7 uniform, say so and skip).
3.4 run_experiment1-style LER vs p for: best, worst, median, Bravyi.
    Figure: figures/single_schedules_ler.png.
  PASS: 936 rows complete in bounds_936.csv; ranking table in RESULTS.md.

---------------------------------------------------------------------------
PHASE 4 — EXPERIMENT 2: CHOSEN PAIRS
---------------------------------------------------------------------------

4.1 Pair A: best-ranked schedule B alternated with B^-1.
4.2 Pair B: two distinct top-10 schedules whose minimum-weight fault sets
    (from 3.2) have no fault in common. Choose by computing set intersections.
4.3 For each pair: alternating-circuit d_circ bound and LER vs p, same settings
    as Phase 2. Compare against the best single schedule.
4.4 Only if a pair beats the best single schedule outside error bars: try
    3-cycle patterns (A,B,C) built from the top 10.
  PASS: results/exp2_pairs.csv and figures/exp2_pairs_ler.png.

---------------------------------------------------------------------------
PHASE 5 — GROSS CODE [[144,12,12]]
---------------------------------------------------------------------------

5.1 Repeat Phase 2 on n = 144, cycles = 12. Expect decode ~5-10x slower.
5.2 Repeat Phase 4 winners on n = 144.
5.3 Headline: report whether any alternating circuit has d_circ bound > 10.
  PASS: results/exp_144.csv and figures/exp_144_ler.png.

---------------------------------------------------------------------------
PASTE-READY PROMPTS (one per phase; wait for PASS before the next)
---------------------------------------------------------------------------

P1: "Read CLAUDE.md and TASKS.md. Do Phase 1.1 only: make dcirc_bound robust
     as described, run it for S, S^-1 and alternating in both bases on [[72]],
     and show me the table. Stop at the PASS check."

P2: "Phase 1.2: reproduce Bravyi's [[72]] curve with run_experiment1.py,
     S only. Pick shots so each point has >= 50 failures. Produce
     figures/bravyi_reproduction.png and tell me the ratio to Bravyi's values."

P3: "Phase 1.3: write enumerate_schedules.py with the early pruning rule,
     run it, and report the count. If it is not 936, stop and show me
     examples of accepted and rejected schedules."

P4: "Phase 2: run experiment 1 fully, both bases, with error bars, and write
     the RESULTS.md paragraph."

P5: "Phase 3.1-3.3: bound all 936 schedules in parallel, build the histogram,
     and give me the ranking table with Bravyi's position."

P6: "Phase 3.4 and Phase 4: simulate the extremes, then the two chosen pairs.
     Does any pair beat the best single schedule?"

P7: "Phase 5: gross code. Start with S vs alternating S/S^-1 only."