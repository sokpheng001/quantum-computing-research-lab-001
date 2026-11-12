# TASKS_partner_search.md — path-targeted partner selection
# Codes: [[72,12,6]] (control) -> [[90,8,10]] -> [[108,8,10]]
# The [[144]] work runs on the Mac mini. Do NOT run [[144]] on this server.

## Goal
Answer Bravyi et al. (2024) open question 4 on three codes: does alternating
Bravyi's schedule S with a second depth-7 schedule S' raise the circuit-level
distance above S's value? Method: find S's weakest fault paths, test every
possible partner S' exactly against them, then search only the survivors.

## Fixed settings (identical for every circuit and code)
- Decoder: BP min-sum (scaling 0.625) + OSD-CS order 7
- Noise: uniform circuit-level depolarising, same p on every location
- Bravyi's S: X = A2 B2 B1 B3 A1 A3, Z = A1 A3 B1 B2 B3 A2, Z first
- S_mirror:   X = B2 A2 A1 A3 B1 B3, Z = B1 B3 A1 A2 A3 B2, Z first
- Distance search: same trials, osd_order, seeds and cycle counts for every
  circuit within a code. Rerun S in the same batch as any comparison.
- Run detached (tmux/nohup). Checkpoint every row to CSV. Save every fault
  set found, with DEM column keys (type, qubits, round, cycle).
- Workers: up to 12 for [[72]] and [[90]]; check `free -g` before using 12
  on [[108]]; keep memory under ~70%.
- Outputs: results_partner/<code>/ and figures_partner/.

## Codes (confirm against Bravyi Table 1 first)
| Code | l, m | A | B | d | Bravyi d_circ(S) | min-weight target |
|---|---|---|---|---|---|---|
| [[72,12,6]]  | 6, 6  | x^3 + y + y^2 | y^3 + x + x^2 | 6  | <= 6 | 6 |
| [[90,8,10]]  | 15, 3 | x^9 + y + y^2 | 1 + x^2 + x^7 | 10 | <= 8 | 8 |
| [[108,8,10]] | 9, 6  | x^3 + y + y^2 | y^3 + x + x^2 | 10 | <= 8 | 8 |

Run order: [[72]] (Stages 0-4) -> control check -> [[90]] (Stages 0-5)
-> [[108]] (Stages 0-5).

## Stage 0 — setup and regression (must pass)
- Build the code: report n, k, check H_X H_Z^T = 0.
- S: noiseless detectors all zero, both bases, 2 and 6 cycles.
- Bound S, both bases, 4 and 6 cycles, 5 seeds.
- PASS = minimum found equals Bravyi's value (6, 8, 8). If not: STOP, report.

## Stage 1 — valid schedules for this code
- Enumerate all (x_order, z_order, z_first). Keep those with no same-round
  collision AND all-zero noiseless detectors, both bases.
- Report count (expect 936 per starting side). Save schedules.jsonl with
  each schedule's time-reverse id. Report the ids of S, S^-1, S_mirror.

## Stage 2 — S's weakest paths
- Collect every DISTINCT minimum-weight logical fault set for S (both bases,
  all seeds, 4 and 6 cycles).
- For each set: number of cycles it spans.
- Group into families under torus translations (x^i y^j shifts).
- Report: number of sets, number of families, one representative per
  family with its basis and cycle span.

## Stage 3 — exact screen of all partners (no search)
- For each valid S' (both starting sides), build alt [S, S'].
- Place each family representative so its faults fall in S cycles of the
  alternating pattern. If a multi-cycle set cannot be placed entirely in
  S cycles, mark it "broken by construction".
- verify_faultset exactly: trips a detector? flips an observable?
- Score(S') = number of families still undetected AND logical in alt [S, S'].
- Always include S' = S^-1 and S' = S_mirror explicitly.
- Report: histogram of scores; list of S' with score 0; scores of S^-1
  and S_mirror.

## Stage 4 — search the survivors
- Circuits: every S' with score 0 (if none, the 10 lowest scores), plus
  alt [S, S^-1] and alt [S, S_mirror].
- Bound each, both bases, 4 and 6 cycles, 5 seeds. Rerun S alongside.
- Exact-check every minimum-weight set found in any alt circuit against S,
  and every S set against each alt circuit.
- A circuit BEATS S only if its minimum over all seeds, bases and cycle
  counts is greater than S's minimum under the same settings.

## Control check (after [[72]] Stage 4, before [[90]])
- S gives 6.
- EVERY alternating circuit gives <= 6. If any gives 7 or more: STOP,
  it is a bug; report it.
- Agrees with earlier [[72]] runs (S, S^-1, alt [S, S^-1] all 6).
- Note: partners may catch all of S's weight-6 families in Stage 3 and
  still give 6 in Stage 4. That is expected (a weight-6 data-qubit logical
  always remains). Report how many partners did this.

## Stage 5 — logical error rate (only [[90]]/[[108]] circuits that beat S)
- S vs the winner, Z basis first, then X.
- p = 0.005 and 0.004 (>= 50 failures each); then p = 0.003 if the winner
  is equal or better at 0.004.
- 6 cycles. Save raw samples. Fit log p_L vs log p; report slope +- 1 sigma.

## Figures (PNG + PDF, show each one)
F1 (one panel per code): minimum weight found, x = circuit
   (S, S^-1, S_mirror, alt[S,S^-1], alt[S,S_mirror], top survivors),
   one dot per seed, circles = Z basis, triangles = X basis,
   dashed line at d, solid line at Bravyi's value, star = exactly verified.
   Caption: "values are upper bounds".
F2 (one panel per code): histogram of Stage 3 scores over all partners S'.
   Mark S^-1 and S_mirror.
F3 (only if Stage 5 runs): log-log logical error rate per cycle vs p,
   Z and X panels, S vs winner, 95% error bars, zero-failure points as
   upper-limit arrows, fitted slopes in legend.

## Summary for the user (put at the TOP of RESULTS_partner.md)
Table A — regression and verdict
| Code | Bravyi d_circ(S) | Our S | Stage 0 | Best alt circuit | Its bound | Beats S? |

Table B — partner screen
| Code | S min-weight families | Partners tested | Partners catching all families | Best survivor's bound |

Table C — logical error rate (only if Stage 5 ran)
| Code | Circuit | p | Z basis (95% CI) | X basis (95% CI) | Slope |

Then one plain-language sentence per code, e.g.
"[[90]]: no partner of S raises the distance above 8" or
"[[90]]: alt [S, S'#id] has upper bound 9 vs 8 for S; exact check confirms
S's weight-8 paths are detected".

## Rules for wording
- Never write "d_circ = 9" (or any improvement) unless an exact method
  confirms it. Otherwise write "upper bound 9".
- Any value is reported with seeds, cycles and trials used.