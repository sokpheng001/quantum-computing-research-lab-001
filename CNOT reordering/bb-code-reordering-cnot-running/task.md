# TASKS_method3.md — using Bravyi's reference code

Two tracks, one per machine. Do not run the same job on both.
- MAC MINI: Track A — close the [[144]] question.
- SERVER:   Track B — Method 3 (one-cycle distance ranking) on [[72]] (control), [[90]], [[108]].

## Setup (both machines)
- Clone github.com/sbravyi/BivariateBicycleCodes into `bravyi_ref/`. Keep its LICENSE
  (Apache 2.0). Never edit files in `bravyi_ref/`; copy a file into `ours/` before modifying
  it and record the change at the top of the copy.
- Confirm the schedule mapping: in decoder_setup.py, sX = ['idle',1,4,3,5,0,2] and
  sZ = [3,5,0,1,2,4,'idle']. Report which index means which layer, and confirm it equals
  our S (X = A2 B2 B1 B3 A1 A3, Z = A1 A3 B1 B2 B3 A2, Z first) up to the Z-side labelling.
- Run detached (tmux/nohup), checkpoint every row, save every fault set found
  (with its location: gate type, qubits, round, cycle).
- Memory: keep usage under ~70% (server < 33 GB, Mac < 22 GB).

## Search settings for ALL distance bounds (Bravyi's, from circuit_distance.py)
- 1 noisy cycle followed by 2 noiseless cycles (as in Bravyi's setup), unless a step says otherwise
- osd_method = osd_cs, osd_order = 20, max_iter = 10000, bp_method = min-sum,
  ms_scaling_factor = 0 (adaptive)
- target in each trial = random combination of logical operators (as Bravyi does)
- trials: 100,000 for [[144]]; scale down for smaller codes only if the regression still passes

---------------------------------------------------------------------------------------
## TRACK A — MAC MINI: close the gross-code question
A1. Run bravyi_ref/decoder_setup.py for [[144,12,12]], p = 0.003, num_cycles = 1, then
    bravyi_ref/circuit_distance.py unchanged. PASS = finds weight 10 for S (both bases).
    Save the weight-10 fault sets it finds.
A2. Read Bravyi et al. (arXiv:2308.07915) Section 6. Report, with the quoted sentence,
    whether the "all 936 variants give d_circ <= 10" result used the same one-noisy-cycle
    setup.
A3. EXACT CHECK (decisive). Map each weight-10 fault set from A1 into our builder's circuit
    and place it entirely inside one S cycle in the MIDDLE of:
      (a) S, S, S, S        (b) alt [S, S^-1]        (c) alt [S, S_mirror]
    (S_mirror: X = B2 A2 A1 A3 B1 B3, Z = B1 B3 A1 A2 A3 B2, Z first.)
    Use verify_faultset: does it trip any detector? does it flip an observable?
    - If undetected and logical in (b) and (c): alternation including S is <= 10.
      The [[144]] question is CLOSED negatively. Stop all [[144]] LER runs.
    - If detected in (b) or (c): report which faults are caught, and continue with A4.
A4. (only if A3 shows a set is detected) Bound alt [S, S^-1] and alt [S, S_mirror] with
    the Bravyi settings above but in an alternating circuit of 4 cycles; 5 seeds; rerun S
    in the same batch. Exact-check every minimum-weight set found.

---------------------------------------------------------------------------------------
## TRACK B — SERVER: Method 3, one-cycle distance ranking
Definition: d1(A) = lightest fault set confined to ONE noisy cycle of schedule A (Bravyi's
1-noisy-cycle setup) that trips no detector and flips a logical. Prop. 3 (Shaw & Terhal)
says alt [A, A^-1] has distance d1(A); any alternation using A is at most d1(A).

Codes:
| Code | l, m | A | B | Bravyi d_circ(S) |
|---|---|---|---|---|
| [[72,12,6]]  | 6, 6  | x^3+y+y^2 | y^3+x+x^2 | <= 6 |
| [[90,8,10]]  | 15, 3 | x^9+y+y^2 | 1+x^2+x^7 | <= 8 |
| [[108,8,10]] | 9, 6  | x^3+y+y^2 | y^3+x+x^2 | <= 8 |

B0. Regression per code with Bravyi's settings: d1(S) must equal Bravyi's value
    (6, 8, 8). If not: STOP and report.
B1. [[72]] control: d1 for all valid schedules (1,872). Expect max d1 = 6.
    If any schedule gives d1 > 6: STOP, it is a bug.
B2. [[90]]: d1 for all 1,872 schedules, both bases. Save results_method3/d1_90.csv
    (id, d1_Z, d1_X). If a schedule's d1 exceeds d1(S), re-run it with 3x trials to confirm.
B3. For each schedule A with confirmed d1(A) > d1(S):
    - build alt [A, A^-1]; check noiseless detectors are all zero
    - bound it (4 and 6 cycles, both bases, 5 seeds) and exact-check its minimum paths
    - if it beats S: LER vs S at p = 0.005 and 0.004, Z basis first, >= 50 failures,
      6 cycles, raw samples saved
B4. Repeat B2-B3 on [[108]].

---------------------------------------------------------------------------------------
## Figures (PNG + PDF; show each)
F5  Track A: table-figure of the exact check — rows = weight-10 fault sets from A1,
    columns = circuits (S, alt[S,S^-1], alt[S,S_mirror]), cells = "hidden" / "detected".
F4  Track B, one panel per code: histogram of d1 over all schedules; mark S and
    Bravyi's value; dashed line at d.
F3  (only if B3 finds a winner): log-log LER vs p, Z and X panels, S vs alt[A, A^-1],
    95% error bars, fitted slopes in legend.

## Summary (top of RESULTS_method3.md, plain language)
Table 1 — Track A
| Bravyi bound reproduced? | Section 6 setup | Weight-10 sets hidden in alt[S,S^-1] | in alt[S,S_mirror] | Verdict for [[144]] |

Table 2 — Track B
| Code | d1(S) | Bravyi value | max d1 over all schedules | # schedules above d1(S) | best alt[A,A^-1] | Beats S? |

Then one sentence per code, for example:
"[[90]]: no depth-7 schedule has a one-cycle distance above 8, so no alternation can beat
Bravyi's schedule" or "[[90]]: schedule #id has d1 = 9; alt[#id, #id^-1] has upper bound 9
versus 8 for S".

## Wording rules
- All search values are upper bounds; write "upper bound 9" unless an exact method confirms it.
- Always state code, cycles, trials, seeds and basis next to a number.