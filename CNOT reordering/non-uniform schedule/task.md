# TASKS_nonuniform.md — Method 4: non-uniform depth-7 schedules

Rules: bravyi_ref/ unchanged, our code in ours/, run detached (tmux/nohup), checkpoint
every row. Up to 12 workers; if TASKS_mac.md is still running, use at most 6. Keep total
memory under ~33 GB. Outputs: results_nonuniform/, figures_nonuniform/.

## Setup (do this first, report before Part A)
- Read CLAUDE.md and, if available, results_mac/RESULTS_mac.md for context.
- Environments: our usual one (stim, ldpc >= 2) AND a separate one for bravyi_ref
  (ldpc < 2, bposd, python-mip). Confirm both import correctly.
- If bravyi_ref/ does not exist:
  `git clone https://github.com/sbravyi/BivariateBicycleCodes.git bravyi_ref`
- REUSE the distance search already built and validated for TASKS_mac.md
  (the copy of bravyi_ref/circuit_distance.py in ours/, e.g. ours/bravyi_d1.py).
  Do NOT write a new search. Name the file you are using.
- Regression before anything else: with that search, CONFIRM-level, d1(S) on [[90]] must be 8
  in both bases (and 8 on [[108]] before Part B7). If not: STOP and report.
- Extend the circuit builder to accept a per-ancilla schedule table; do not change the
  search code itself.

## Why this method
Method 3 proved that on [[90]] every UNIFORM depth-7 schedule (all ancillas use the same
layer order), alone or in any alternation, has a one-cycle fault path of weight <= 8.
To beat 8 while staying inside Bravyi's question 4 (depth-7 circuits), ancillas must
use DIFFERENT orders. Still depth 7, same qubits, same connectivity.

Key point: S's weight-8 paths come in families under torus translation. Changing the order
of ancillas in ONE place breaks only one copy; the translated copies survive and the
distance does not move. So the change must repeat across the torus. We do this with
"class schedules": split the ancillas into k classes by a group homomorphism
f: G -> Z_k (G = Z_l x Z_m), and give each class its own uniform order.
- [[72]]  (l=6,  m=6): Z_2 via x, y or xy; Z_3 via x or y
- [[90]]  (l=15, m=3): Z_2 impossible (l, m odd); use Z_3 (and Z_5 via x if useful)
- [[108]] (l=9,  m=6): Z_2 via y, Z_3 via x or y
- [[144]] (l=12, m=6): Z_2 via x, y or xy; Z_3 via x or y
Report every homomorphism used as (image of x, image of y).

Search settings for distance: Bravyi's (1 noisy cycle + 2 noiseless; osd_cs order 20;
max_iter 10000; ms_scaling_factor 0; random logical combinations), with
SCREEN = 2,000 trials, CONFIRM = 100,000 trials. A found path is a proof.

Order: Part 0 control on [[72]] -> Part A -> Part B on [[90]] -> Part B on [[108]].
[[144]] only if asked.

---------------------------------------------------------------------------------------
## PART 0 — CONTROL on [[72,12,6]] (check the non-uniform pipeline)
On [[72]] the code distance is 6 and S already reaches it, so NO schedule can exceed 6.
The non-uniform pipeline must reproduce that.
0.1 Regression: d1(S) = 6 in both bases (CONFIRM level). If not: STOP.
0.2 Build class schedules with each Z_2 and Z_3 homomorphism (Families 1 and 2 of Part B3,
    with S's weight-6 families in B4, all copies). Run B2 (validity) and B5 (screen d1).
    Report the time per candidate here; it sets the budget for [[90]] and [[108]].
    PASS = no class schedule has a confirmed d1 > 6. If any does: STOP, it is a bug.
    Report how many class schedules reach 6 and how many fall below.
0.3 Logical error rate check: pick one valid class schedule with d1 = 6 (call it N72).
    Run S and N72 with the SAME settings: p = 0.004 and 0.006, 6 cycles, both bases,
    Bravyi's decoder settings, >= 50 failures per point.
    PASS = N72 and S agree within 95% intervals, matching the earlier finding that all
    6-distance circuits on [[72]] perform alike. If they differ strongly, report it before
    continuing (it may be real, or a builder bug: check noiseless detectors again).
0.4 Report a short control table:
    | Check | Expected | Got | PASS? |

---------------------------------------------------------------------------------------
## PART A — understand the weak spot (on [[90]], schedule S)
A1. Collect S's weight-8 one-cycle fault sets (from TASKS_mac results or a CONFIRM run).
    Group them into translation families.
A2. For one representative per family, report in a table:
    - every fault: type (CNOT / idle / prep / meas), qubits, round
    - which faults are hook errors (ancilla fault that spreads through later CNOTs)
    - which ancillas are involved, and their class under each candidate homomorphism
    - the data-qubit error left at the end and which logical operator it equals
A3. Figure FA: the 15 x 3 torus with the involved data qubits and ancillas marked, arrows
    for hook spread. One panel per family (max 4 panels).
A4. One paragraph: why the path is undetected (which checks see it an even number of times).

---------------------------------------------------------------------------------------
## PART B — build and test class schedules (start with [[90]])
B1. General builder: a schedule is a table (ancilla, data qubit, round) for every CNOT.
    Generate it from a class assignment: class c uses uniform order O_c
    (x_order, z_order, z_first from the 1,872 list).
B2. Validity checks for every candidate (cheap, run first):
    - depth exactly 7 CNOT rounds (+ measurement), same stagger rule as Bravyi
    - no qubit in two CNOTs in the same round (check across classes!)
    - noiseless detectors all zero, both bases, 2 and 6 cycles
    Report the number of valid candidates at each stage.
B3. Candidates, k = 3 classes on [[90]] via each Z_3 homomorphism:
    - Family 1 (anchored on S): class 0 = S, classes 1 and 2 = any orders O1, O2.
      Do NOT enumerate all pairs blindly. First keep only O with d1(O) = 8 (from
      TASKS_mac). Then sample up to 20,000 valid (O1, O2) combinations per homomorphism,
      prioritising orders whose hook pattern differs from S on the ancillas found in A2.
    - Family 2 (two-class special case): classes 1 and 2 share the same order O.
      Enumerate all O with d1(O) = 8 (up to 1,780 per homomorphism).
    - Family 3 (anchored on the best uniform schedule): if the TASKS_mac.md results
      report a schedule A* with CONFIRMED d1(A*) > d1(S) on this code, repeat Families 1-2
      with A* in place of S (and use A*'s minimum-weight families in B4).
B4. EXACT SCREEN (no search): for each S weight-8 family from A1, test EVERY translated
    copy (not just one representative): in a class schedule, copies that sit on different
    class patterns behave differently. At minimum, test one copy per coset of the
    homomorphism's kernel; testing all copies is preferred. Place each copy into the
    candidate and run verify_faultset. Score = number of copies still undetected and
    logical. Keep only candidates with score 0.
B4b. Before B5 on each code: report the number of B4 survivors and the measured time per
    d1 screen. If B5 would take more than ~2 days, keep the 500 survivors with the most
    distinct hook patterns (or a random 500) and ask before running the rest.
B5. Distance SCREEN on survivors: d1, both bases. Keep candidates whose screen d1 > 8 in
    BOTH bases. CONFIRM those.
B6. For each candidate with CONFIRMED d1 > 8:
    - multi-cycle bound (4 and 6 cycles, both bases, 5 seeds), S rerun alongside
    - exact-check every minimum-weight set found
    - LER vs S: p = 0.005 and 0.004, Z basis first, >= 50 failures, 6 cycles, samples saved.
      Decoder = Bravyi's settings from bravyi_ref/decoder_run.py (min-sum,
      ms_scaling_factor 0, max_iter 10000, osd_cs order 7). Also run the winner
      alternated with its time-reverse.
B7. Repeat B3-B6 on [[108]] with Z_2 and Z_3 homomorphisms (regression first: d1(S) = 8).

Stop rules:
- If B4 leaves 0 candidates for every homomorphism: report "no class schedule of this
  kind breaks S's weight-8 families" and stop that code.
- If B5 leaves 0 candidates: same report for d1.

---------------------------------------------------------------------------------------
## Figures (PNG + PDF; show each one)
FA  Part A torus picture of S's weight-8 path(s).
FB  Funnel chart per code: candidates generated -> valid -> pass exact screen ->
    screen d1 > 8 -> confirmed d1 > 8.
FC  Histogram of screen d1 over all candidates that passed B4, S's value marked.
FD  Only if a winner exists: log-log LER vs p, Z and X panels, S vs winner,
    95% error bars, fitted slopes in the legend.

## Summary (top of results_nonuniform/RESULTS_nonuniform.md, plain language)
Table 0 — control on [[72]]
| Check | Expected | Got | PASS? |

Table 1 — weak spot of S on [[90]]
| Family | # copies | faults (hook / other) | ancillas involved | logical hit |

Table 2 — search funnel
| Code | Homomorphism | generated | valid | pass exact screen | screen d1 > t | confirmed d1 > t | best d1 |

Table 3 — winners (if any)
| Code | Candidate (classes, orders) | d1 | multi-cycle bound | LER p=0.005 Z/X | LER p=0.004 Z/X | vs S |

One plain sentence per code, e.g.
"[[90]]: no Z_3 class schedule breaks all of S's weight-8 families" or
"[[90]]: class schedule X has one-cycle distance 9 vs 8 for S, at the same depth".

## Wording rules
- All search values are upper bounds unless confirmed exactly.
- Every number states: code, homomorphism, cycles, trials, basis.
- Call these "non-uniform (class) depth-7 schedules"; do not call them depth-8.