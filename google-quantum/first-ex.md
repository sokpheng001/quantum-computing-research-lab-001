# TASKS_nn_flags.md — nearest-neighbour flags for T-state cultivation (search + exact verification)

## Goal
Find double-check circuits for distance-3 T-state cultivation that
  (1) restore fault distance 3 (no malignant kept 2-fault configuration),
  (2) use only nearest-neighbour two-qubit gates on the Willow square grid,
  (3) give each qubit at most 4 coupling partners,
  (4) respect the readout-line rule (below),
with the lowest overhead. Later: distance 5 (target fault distance 4, or 5 with 4 rounds).

Baselines (from Chan, Strikis, Sun & Cai, arXiv:2609.17706):
  - original double check  d3a6   : fault distance 2 (4 malignant 2-fault configurations)
  - their flagged version  d3a6f2 : fault distance 3, but NOT nearest-neighbour
    (flags at square centres (1.5,0.5),(2.5,0.5) with diagonal gates; qubit 6 has 6 partners, qubit 11 has 5)

## Setup
- Clone https://github.com/timchan0/cliffordea into ./cliffordea (do not edit it; import it).
- Follow its README (conda env recommended). Python >= 3.10. Pin and report versions.
- Our own code goes in ./nnflags/ (new package). Tests in ./nnflags/tests/.

## Definitions (use these exact meanings)
- Hardware graph G = (V, E): V = Willow qubits (row, col) from the Willow grid (list in nnflags/willow.py);
  (r,c)-(r',c') in E iff |r-r'| + |c-c'| == 1 and both in V.
- Readout line of (r,c) = r + c. A qubit measured mid-circuit (anything measured before the final layer)
  must not share a readout line with a data qubit that is still in use after that measurement.
  Implement as a check that reports violations; treat as a hard constraint in the final ranking
  but allow it to be toggled off (flag --ignore-readout) for comparison.
- Embedding: an injective map from circuit qubits to V. Every two-qubit gate (CX/CZ) must map to an edge of E.
- Z flag: a fresh qubit f, R (reset to |0>) before use, target of CX(q -> f) at two time steps t1 < t2
  on the same control q, measured M (Z basis) after t2; its measurement is a new DETECTOR (expected 0).
  It catches X errors on q that occur between t1 and t2.
- Fault distance target at d=3: no malignant kept effect with fault count <= 2 for cultivated state "T".

## Step 0 — reproduce the baseline (must pass before anything else)
Using the cliffordea README "Complete enumeration workflow":
  circuit = enum.circuits.DoubleCheck(distance=3, ancilla_count=6)            # d3a6
  ... FaultCombinator(noisy_circuit).get_kept_effects(analyzer, max_fault_count=2, cultivated_states=("S","T"))
  -> confirm 4 malignant 2-fault configurations for T, 0 for S.
Repeat with flag_count=2 (d3a6f2) -> 0 malignant up to 2 faults for T.
Report both summaries (summarize_contributions) and the timing.

## Step 1 — hardware model (nnflags/willow.py, nnflags/constraints.py)
- willow.py: the 105-qubit Willow grid as a set of (row, col); neighbours(); readout_line().
- constraints.py: check_circuit(circuit, embedding) -> list of violations:
  non-neighbour 2q gates, qubits with > 4 distinct partners, readout-line conflicts,
  qubits used twice in one TICK.
- Test: d3a6 under an embedding onto Willow passes the neighbour/degree checks;
  d3a6f2 fails (report exactly which gates/qubits fail — expect the 4 diagonal flag gates,
  qubit 6 with 6 partners, qubit 11 with 5).

## Step 2 — custom-circuit verifier (nnflags/verify.py)
- Read cliffordea/enum/circuits/_base.py and main.py to see how DATA_INDICES,
  STABILIZER_GENERATORS and LOGICAL_S are derived from the bundled Stim files.
- Implement verify(stim_circuit_full, stim_circuit_inner, max_fault_count=2) -> dict with
  malignant/benign counts per fault count for "T" and "S", reusing cliffordea's code paths.
  Do not reimplement the acceptance algorithm.
- Test: verify() on the bundled d3a6 and d3a6f2 files reproduces Step 0 exactly.

## Step 3 — candidate generator (nnflags/candidates.py)
Start from d3a6 (the nearest-neighbour baseline) embedded on Willow.
Generate candidates by:
  (a) adding 1..3 Z flags on FREE Willow qubits adjacent to an existing qubit q,
      with CX(q -> f) at two TICKs t1 < t2 chosen among the fold/unfold TICKs where q is idle;
      insert new TICKs if needed (count added layers);
  (b) optionally permuting the order of commuting CX layers in the fold/unfold
      (keep the time-reversal structure of the double check);
  (c) optionally re-embedding the 13 qubits on a different Willow region (rotations/reflections).
Every candidate must pass constraints.check_circuit before verification.
Use the 4 malignant configurations from Step 0 (combinator.index_to_events) to prioritise:
  first try flags on qubits that carry the X hook errors in those configurations.

## Step 4 — search at distance 3 (nnflags/search.py)
- Exhaustive over (a) with 1 and 2 flags; then (b) on the best results.
- For each candidate: verify(max_fault_count=2). Keep those with 0 malignant T configurations.
- Also run max_fault_count=3 on survivors and record the malignant 3-fault count (lower is better).
- Save every evaluated candidate to results/d3_candidates.csv:
  id, n_flags, added_ticks, n_cx, max_degree, readout_violations, malignant_T_2, malignant_T_3,
  benign_T_2, runtime_s, stim_file path.
- Run long searches detached (nohup/tmux) and checkpoint the CSV.

## Step 5 — rank and compare
Rank valid candidates by: readout_violations == 0, then n_flags, added_ticks, malignant_T_3.
For the top 5, compute error_rates_per_kept_shot at p in {2e-4, 5e-4, 1e-3, 2e-3}
and compare with d3a6 and d3a6f2 in one table + one log-log plot (figures/d3_ler.png).
Write the best circuits as Stim files and print Crumble URLs (stim.Circuit.diagram('interactive-html')
or the crumble URL helper) so I can inspect them.

## Step 6 — report (RESULTS_nn_flags.md)
Top of file: a table baseline vs ours (fault distance, nearest-neighbour?, max degree,
readout-line OK?, flags, added layers, LER per kept shot at p=1e-3, attempts per kept shot if available).
Then: what the search tried, what failed and why, and the circuits found.

## Rules
- Never edit ./cliffordea; wrap it.
- Do not guess cliffordea function names: read the source and README first; quote what you used.
- After Steps 0, 1 and 2, stop and show me the results before continuing.
- Report every number with the settings used (distance, max_fault_count, noise model).

## Later (not now): distance 5
Same pipeline with DoubleCheck(distance=5, ancilla_count=19) as baseline (fault distance 3),
target: no malignant kept configuration with <= 3 faults (fault distance 4), then 5 with the
4-round variant. Use a heuristic search (greedy / simulated annealing) instead of exhaustive.