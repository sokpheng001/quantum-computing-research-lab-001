# RESULTS — generalised (two-control) flags on Willow: a fault-distance-3 T-cultivation double check

Run unattended on 2026-11-01, 12:47 pm – 3:42 pm KST.

## Answer

**Yes. 10 distance-3 T-cultivation double checks were found that run on Willow and have fault distance 3:** 0 malignant T configurations at 1 and at 2 faults.
- Each passes every strict hardware rule (nearest-neighbour CX, degree ≤ 4, no reuse in a TICK, strict readout with `live_rule="gate"` and `final_layer="auto"`), the equivalence checker (flags excluded from the reverse check) and stim determinism.
- Each uses **two flags**: one genuinely two-control **Z flag** (ZZ) and one same-control **X flag**.
- None has a malignant S configuration at ≤ 2 faults.
- The best (`success03`) has 286 malignant T configurations at 3 faults. Its T logical error per kept shot is 1 in 6,570,057 at p = 0.001 (max_fault_count 3), against 1 in 3,568,591 for d3a6 and 1 in 2,054,158 for G4.

**Z flags alone did not get there with ≤ 2 flags.** The best is 1 malignant pair, and the search for it was greedy, not exhaustive. The surviving pair is often made only of Z errors, which no Z flag can detect; that is why the X flag is needed.

## Status

| Task | Status | One line |
|---|---|---|
| Generalised flag generator (`nnflags/zzflags.py`) | **PASS** | Probe model plus an exact GF(2) prefilter, cross-checked against stim and verify(). Same-control, two-control and up-to-4-control Z and X flags. |
| Search, Z + X flags, ≤ 2 flags (`nnflags/search_zzflags.py`) | **SUCCESS: 10 found, stopped** (stopping rule) | 136 bases (G4 + the 135 best Option-1 bases), 4,645 circuits verified, 115 s (01:04 – 01:06 pm KST). |
| Search, Z flags only, ≤ 2 flags | **0 successes; whole base space run** | 2,540 bases, best = 1 malignant pair. 908 two-root bases crashed on a bug and were rerun after the fix (rerun 01:47 – 03:42 pm KST). |
| G4 as base | **Not fixable with ≤ 2 flags** | Best 2 malignant pairs, realisable or not. Its hooks 5 and 9 have degree 4 and so no free neighbour. |
| 3-flag pass | **Not run** | Not needed: successes were found with 2 flags. |
| Figures (PNG only) | **PASS** | 3 new figures in `figures/`; there is no PDF in `figures/`. |
| Tests | **PASS** | 95 passed (78 earlier + 17 new, including 10 re-verifications from the saved stim files). |
| cliffordea untouched | **PASS** | `git -C cliffordea status --porcelain --ignored` gave empty output (`logs/cliffordea_check_zzflags.txt`, 0 bytes). |

**Settings for every number unless stated:**
- distance 3; cultivated states T and S;
- `enum.noise.uniformly_depolarize` (cliffordea `enum/noise/main.py:9`) at p = 0.001;
- `FaultCombinator.get_kept_effects` (`enum/combinators/fault_combinator.py:236`) with `CliffordLogicalAnalyzer`;
- rates are `error_rates_per_kept_shot`, truncated at the stated max_fault_count;
- Willow 105-qubit grid;
- readout strict, `live_rule="gate"`, `final_layer="auto"`;
- CX form (the same gate set as d3a6, d3a4 and G4-CX).

## The successes (all valid; ranked by malignant S, flags, added TICKs, malignant T at 3 faults)

**Notation:**
- `Zf11[q4@t2+…]` = Z flag on qubit 11 with `CX q4 -> 11` at TICK 2, and so on.
- `Xf12[q3@t2+q3@t14]` = X flag on qubit 12 with `CX 12 -> q3` at TICKs 2 and 14.
- TICKs are those of the saved stim file.
- "base (T2)" = the Option-1 abstract base and its unflagged malignant 2-fault T count.

**Every row has:**
- one root (ancilla 0) measured `MRX` mid-circuit, with nothing else live on its readout line;
- flags prepared in TICK 1 (R / RX) and measured (M / MX) in the single final measurement layer together with the ancillas;
- 0 strict readout conflicts.

| rank | file (`results/zz/`) | base (T2) | flags | flag positions (Willow r, c) | added TICKs | TICKs | qubits | CX | max degree | malignant T at 1 / 2 / 3 faults | malignant S at ≤ 2 faults | T error per kept shot, mfc 2 | T error per kept shot, mfc 3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `success00` | B0060 (10) | `Zf11[q4@t2+q8@t4+q8@t12+q4@t14];Xf12[q3@t2+q3@t14]` | 11→(5, 4), 12→(4, 6) | 4 | 16 | 13 | 26 | 3 | 0 / 0 / 283 | 0 | 0 | 1 in 6,110,492 |
| 2 | `success03` | B0092 (10) | `Zf11[q10@t2+q3@t4+q3@t12+q10@t14];Xf12[q9@t2+q9@t14]` | 11→(4, 5), 12→(7, 5) | 4 | 16 | 13 | 26 | 3 | 0 / 0 / 286 | 0 | 0 | 1 in 6,570,057 |
| 3 | `success06` | B0132 (11) | `Zf11[q6@t3+q10@t4+q10@t12+q6@t13];Xf12[q6@t2+q6@t14]` | 11→(8, 9), 12→(9, 8) | 4 | 16 | 13 | 26 | 3 | 0 / 0 / 303 | 0 | 0 | 1 in 4,267,098 |
| 4 | `success04` | B0092 (10) | `Xf11[q9@t3+q9@t14];Zf12[q3@t2+q10@t3+q3@t12+q10@t14]` | 11→(7, 5), 12→(4, 5) | 4 | 16 | 13 | 26 | 3 | 0 / 0 / 312 | 0 | 0 | 1 in 6,412,602 |
| 5 | `success07` | B0132 (11) | `Xf11[q6@t2+q6@t14];Zf12[q10@t2+q6@t3+q10@t12+q6@t13]` | 11→(9, 8), 12→(8, 9) | 4 | 16 | 13 | 26 | 3 | 0 / 0 / 327 | 0 | 0 | 1 in 4,229,521 |
| 6 | `success08` | B0134 (11) | `Zf10[q4@t3+q9@t4+q9@t12+q4@t13];Xf11[q4@t2+q4@t14]` | 10→(4, 5), 11→(3, 6) | 4 | 16 | 12 | 24 | 3 | 0 / 0 / 336 | 0 | 0 | 1 in 4,365,631 |
| 7 | `success09` | B0134 (11) | `Xf10[q4@t2+q4@t14];Zf11[q9@t2+q4@t3+q9@t12+q4@t13]` | 10→(3, 6), 11→(4, 5) | 4 | 16 | 12 | 24 | 3 | 0 / 0 / 362 | 0 | 0 | 1 in 4,319,798 |
| 8 | `success05` | B0124 (11) | `Xf11[q10@t2+q10@t14];Zf12[q5@t2+q10@t3+q10@t13+q5@t14]` | 11→(7, 9), 12→(8, 8) | 4 | 16 | 13 | 26 | 3 | 0 / 0 / 370 | 0 | 0 | 1 in 4,139,319 |
| 9 | `success01` | B0060 (10) | `Zf11[q4@t3+q8@t5+q8@t13+q4@t15];Xf12[q4@t2+q4@t16]` | 11→(4, 5), 12→(3, 6) | 6 | 18 | 13 | 26 | 3 | 0 / 0 / 269 | 0 | 0 | 1 in 3,410,303 |
| 10 | `success02` | B0060 (10) | `Zf11[q4@t2+q8@t5+q8@t13+q4@t16];Xf12[q4@t3+q4@t15]` | 11→(4, 5), 12→(3, 6) | 6 | 18 | 13 | 26 | 3 | 0 / 0 / 315 | 0 | 0 | 1 in 3,178,731 |

- **The mfc-2 rate is exactly 0**, because no configuration with ≤ 2 faults is malignant. The mfc-3 rate is therefore the leading-order number.
- **Baselines at max_fault_count 3:**

  | circuit | Willow-compatible? | malignant T at 2 / 3 faults | T error per kept shot |
  |---|---|---|---|
  | d3a6 | no (strict readout) | 4 / 415 | 1 in 3,568,591 |
  | d3a4 | no (strict readout) | 12 / 1,619 | 1 in 3,184,814 |
  | G4-CX | yes | 7 / 671 | 1 in 2,054,158 |
  | best Option-1 candidate (cand03) | yes | 6 / 633 | 1 in 1,524,994 |

- **The smallest success is `success08`** (base B0134): 12 qubits (10 tree + 2 flags), 24 CX.
- **Every two-control Z flag is genuinely joint.** Removing the CXs of either control makes its detector non-deterministic (checked with stim for all 10).
- **Data and ancilla roles** come from the circuits' MPP targets (cliffordea `find_data_indices`).

**How the flags work** (example `success00`, base B0060; tree: root 0 ← 1, 5, 6; 1 ← 2, 3; 3 ← 4; 6 ← 7 ← 8 ← 9, 10).
- **Z flag 11** reads Z on data 4 before 4 is collected, and Z on ancilla 8 after 8 has collected its children. It reads both again, in mirror order, in the unfold.
  - Only the product of the four readings is deterministic.
  - So it detects X errors that cross the target CX of a hook qubit. The same-control flags of the Option-1 round could not span that CX.
  - Data 4 and ancilla 8 have the same grid colour (depth parity), so one free grid point (5, 4) touches both.
- **X flag 12** reads X on data 3 at the very start and the very end (two inserted TICKs). It detects Z errors on 3 during the whole check.
  - Z-type hook pairs are invisible to Z flags; this flag removes them.

## What the search does (`nnflags/zzflags.py`, `nnflags/search_zzflags.py`)

1. **Bases.**
   - G4's extracted double check (CX form, `g4.inner_cx`).
   - The 2,539 feasible abstract fold forests of the Option-1 screen cache (`results/option1_screen.json`, reused, not recomputed), each with its best code labelling, ordered by best malignant 2-fault T count, then rate.
   - An abstract tree is rebuilt from its canonical string (`zzflags.parse_canon`, `base_from_key`) with `search_option1.build/to_circuit`, so the circuit and labelling are exactly the screened ones.
2. **Probes.** A flag is a set of probes (q, slot, basis):
   - slot = an existing TICK where q is idle, or a new TICK k + 0.5;
   - Z probe = `CX q -> f`, which reads Z_q; X probe = `CX f -> q`, which reads X_q.
   - cliffordea puts each TICK's noise after its operations (`enum/noise/_noise.py:396-407`, idle noise `:402-407` via `_append_idle_error`, `:280`). So a probe at slot s sees the error events of TICKs < s (k + 0.5: ≤ k). Events are `(tick, name, targets)` (`enum/types.py:19`, `enum/cultivation_circuit.py:296`).
   - Each probe is back-propagated with stim (`PauliString.before`) through every TICK:
     - At R / MR the Z part is fixed and the X part becomes a random variable; at RX / MRX the reverse.
     - At the start, the data part is reduced modulo what is deterministic **both** in the code state **and** in cliffordea's inner circuit (data start in |0⟩⁷ plus the MPP X_L marker): the Z-plaquette span for Z flags, and {X_L} for X flags.
   - A probe set is a deterministic flag iff its syndromes XOR to 0. stim confirms this on every built circuit.
3. **Coverage prefilter (exact for the base's own faults).**
   - Malignant 2-fault T pairs and their fault classes come from `FaultCombinator.index_to_events` (`fault_combinator.py:374`).
   - One flag removes a pair (i, j) iff its bit is constant on class i, constant on class j, and different on the two. These are linear conditions over GF(2), solved per (basis, control set).
   - Checked against verify(): a Z flag on G4's q4 is predicted to remove one pair, and verify() goes from 7 to 6 (test).
4. **Control sets.** 1–4 tree qubits of the same grid colour, each of tree degree ≤ 3.
   - The grid is bipartite and tree edges are grid edges, so a flag can never touch a qubit and its parent. Every control of one flag has the same depth parity.
   - A degree-4 qubit has no free neighbour, and degree ≤ 4 holds automatically for nearest-neighbour gates.
5. **Two-level greedy search per base.**
   - **Level 1:**
     - Every maximal set of pairs that one realisable flag can remove is computed. This is exhaustive for ≤ 10 pairs; for more pairs it grows greedily from each single coverable pair.
     - The 40 best concrete flags (most pairs removed; Z before X; fewest controls; then min-weight, conflict-free probe choice) are built and verified.
   - **Level 2:**
     - The 8 best realisable level-1 circuits become bases, with their own flag faults included exactly.
     - A second flag must remove all their remaining pairs (exhaustive GF(2) test over all control sets). Up to 16 concrete flags are verified. If none works, the best 2 partial flags are recorded.
6. **Willow embedding** (`zzflags.embeddings`).
   - Backtracking subgraph embedding of tree plus flags (each flag adjacent to all its controls). Every CX lies on a coupler.
   - No other qubit that is live at the mid check may sit on the readout line of a mid-measured qubit. A flag counts as live there if it is an X flag or its first probe is at or before the mid TICK.
   - The tree centre is fixed at (6, 7). The radius-5 diamond around it lies inside Willow, so for a single-root tree this search is exhaustive up to translation. The root is no longer pinned to G4's (9, 9).
   - Realisability is checked **before** verify(), with the flag's exact liveness.
   - A success additionally needs an embedding under which `constraints.check_circuit` returns no violations; the first such embedding is saved in the stim file's QUBIT_COORDS.
7. **Validation of a success:**
   - `check_circuit` (strict defaults);
   - `check_equivalence(inner, full, flag_qubits)`;
   - verify at max_fault_count 2 and 3;
   - determinism of the inner and full circuits.
   - `tests/test_zzflags.py::test_saved_success_reverifies` re-does all of this from `results/zz/success*.stim`.

## Search space: explored vs sampled

| part | Z + X pass (canonical, `results/zz_candidates.csv`) | Z-only pass (`results/zz_candidates_zonly.csv` + `_zonly_m2fix.csv`) |
|---|---|---|
| bases | G4 + Option-1 bases B0000–B0134 (135 of 2,539, best T2 first); **stopped at 10 successes** | **all** 2,540 (G4 + 2,539) |
| control sets per flag | all same-colour sets of 1–4 tree qubits with degree ≤ 3 (exhaustive) | same, Z basis only |
| probe slots | every idle TICK and every inserted TICK in the fold/unfold (exhaustive in the GF(2) model) | same |
| level-1 flags verified | top 40 per base (**sampled** from the GF(2) solution sets) | top 40 |
| level-2 | 8 frontier circuits × all control sets (exhaustive GF(2) test of "removes all"), ≤ 16 verified | same |
| not covered | 2-flag combinations in which neither flag alone separates a pair; non-greedy choices of flag 1 beyond the frontier of 8; other code labellings of a base (only the best one from the screen) | same |
| circuits verified | 4,645 (276 rejected at build: detector not deterministic, 10 successes) | 71,827 (46,808 + 25,019); 0 reached 0 malignant at 2 faults |
| Willow embeddings | exhaustive up to translation for one-root trees; for two-root forests the second component is placed freely around a fixed first component (not proven exhaustive) | same |

**Counts in the Z + X pass:**
- Best malignant T count reached per base with 2 flags: 0 in 6 bases, 1 in 49, 2 in 55, 3 in 16.
- Of the 6 bases that reached 0, five gave the 10 successes (B0060, B0092, B0124, B0132, B0134).
- **The sixth, B0130, is a bug and not a physics failure.** It is a two-root base whose second root is a lone ancilla with no CX. My `Design.qubits` left that root out, so `check_circuit` reported it "unmapped".
  - After the fix (decision 11), B0130 was re-run alone: both of its circuits are **valid fault-distance-3 circuits**, with malignant T at 3 faults of 336 and 362, malignant S 0, and 1 in 4,383,024 and 1 in 4,337,014 at mfc 3 (`results/zz_B0130_recheck.json`).
  - They count as successes #11 and #12, found after the 10-success stopping point. Their stim files were not saved by the search.
- With one flag: best 1 in a single base, typically 2–4.

## Z flags only: why not

**Z-only pass** (generalised Z flags only, ≤ 2 flags):
- **Runs and size.** 01:06 – 01:46 pm KST for all 2,540 bases; then 01:47 – 03:42 pm KST rerunning the 908 two-root bases that had crashed.
  - 71,827 circuits verified (46,808 + 25,019). **0 with 0 malignant 2-fault T configurations**, realisable or not.
- **Best malignant T count reached per base** (2 flags, realisable):
  - 1 in 64 bases; 2 in 186; 3 in 372; 4 in 425; 5 in 246; 6 in 152; 7 or more in the remaining 1,095.
  - Two-root bases are all at 9 or more.
- **Best Z-only circuit** (`results/zz_zonly/best0.*.stim`, base B0021): `Zf11[q7@t2+q10@t3+q7@t12+q10@t13];Zf12[q1@t10+q1@t12]`.
  - 13 qubits, 26 CX, +3 TICKs.
  - Malignant T at 1 / 2 / 3 faults: 0 / **1** / 401; malignant S at ≤ 2 faults: 0.
  - T error per kept shot: 1 in 6,452,634 (mfc 2), 1 in 3,696,022 (mfc 3).
- **Caveat on two-root bases.** The two-root (m = 2) bases of the Z-only pass ran before the lone-root bug was fixed (decision 11). For bases whose second root has no CX, realisability may therefore have been judged too leniently. No circuit there reached 0 anyway, so this does not change the answer.

**The last surviving pair** (`results/zz_zonly_last_pair_evidence.json`, the 8 best Z-only bases):
- **B0018, B0121, B0122, B0123, B0055:** the pair is made only of Z errors.
  - Example (B0018): Z on ancilla 8 across TICKs 5–9 (it spans the mid check), plus Z on data 3 at the end.
  - No Z flag on any control set can separate it (0 sets); 19–41 X-flag control sets can.
- **B0021, B0010, B0001:** the pair is X on ancilla 1 across TICKs 4–9 plus Y on a data qubit at the end.
  - A third Z flag could separate it (6–17 control sets), but the 2-flag budget is spent.
  - The greedy level 2 found no second flag that removes everything left after any of the 8 best first flags.

## G4 (Google's as-run double check) as base

`results/zz_g4_evidence.json`, run separately, with a wider budget (60 level-1 flags, 12 frontier, 24 level-2):

| variant | best malignant T at 2 faults, 1 flag / 2 flags | note |
|---|---|---|
| Z + X, realisable | 3 / **2** | the best 2-flag circuits have **2 malignant S** configurations and T error 1 in 167,545 – 197,061 (mfc 2), worse than unflagged G4-CX (1 in 2,421,930) |
| Z only, realisable | 3 / 2 | same circuits |
| Z + X, abstract (no Willow check) | 3 / 2 | geometry is not the limit here |

- **Why G4 cannot be fixed.** G4's X-hook qubits are 2, 4, 5, 9 (RESULTS_g4.md). Qubits 5 and 9 have 4 tree neighbours, so no flag can touch them.
- Every one of the 7 pairs is separable by some single flag (13–15 realisable control sets for pairs 0–2, 4–6 for the others). No two flags separate all of them, even ignoring the grid.

## Figures (`python -m nnflags.plots --only zz`, PNG 200 dpi)

- **`qvm-google (main)/test1_fd3_circuits_vs_google_fig2/figures/zz_best_circuits.png`:** the 3 best successes on Willow. It shows:
  - the tree CXs, the Z flags (▲) and X flags (▼) with their control CXs labelled by TICK;
  - the parity qubit (◆) and its readout line;
  - the X-hook qubits of the unflagged base (vermilion outline);
  - the malignant counts, rates, qubits, CX count and degree.
- **`figures/archive/zz_malignant_comparison.png`:** malignant T at 2 and 3 faults for d3a6, d3a4, G4-CX, the best Option-1 candidate (cand03), the 3 best successes and the best Z-only circuit.
- **`figures/archive/zz_tick_diagram.png`:** the TICK diagram of the rank-1 success (`success00`; 16 TICKs = 12 of the base + 4 inserted).

## Files

- **Code:**
  - new: `nnflags/zzflags.py` (designs, probes, GF(2) prefilter, flag builder, Willow embedding, hook qubits) and `nnflags/search_zzflags.py` (driver);
  - extended: `nnflags/plots.py` (`--only zz`);
  - tests: `nnflags/tests/test_zzflags.py`.
- **Results:**
  - `results/zz_candidates.csv` (every evaluated circuit of the canonical Z + X pass, with its malignant counts), `results/zz_bases.csv` (per-base pairs, hook events and separability evidence), `results/zz_state.json`;
  - `results/zz/success00–09.{inner,full}.stim`, `results/zz/best0–4.*.stim` (best non-successes);
  - the Z-only pass: `results/zz_candidates_zonly.csv`, `results/zz_bases_zonly.csv`, `results/zz_zonly/`, the m = 2 rerun `*_zonly_m2fix*`, and `results/zz_zonly_best.json`;
  - `results/zz_g4_evidence.json`, `results/zz_zonly_last_pair_evidence.json`;
  - an aborted first run (lenient prefilter, see decision 9) (removed in the Nov 1 cleanup; superseded by the canonical run).
  - Earlier results files are untouched.
- **Logs:** `logs/search_zzflags.log`, `logs/search_zzflags_zonly.log`, `logs/search_zzflags_zonly_m2fix.log`, `logs/pytest_zzflags.log`, `logs/cliffordea_check_zzflags.txt`.

## Decisions made without you

1. **X flags were searched together with Z flags in the canonical pass**, with Z preferred at equal coverage, instead of only after Z failed. A separate Z-only pass over the whole space answers the "Z first" question. The 10-success stop was reached by the Z + X pass.
2. **Flag timing.** Flags are prepared in TICK 1 (R for Z flags, which stay dormant until their first CX; RX for X flags, live at once) and measured in the single final layer. This keeps the final-layer exemption.
   - The detector is the flag record, or the flag ⊕ MPP / mid records, choosing the smallest deterministic option.
   - No mid-circuit flag measurement was needed.
3. **Determinism model** = deterministic in both the code state and cliffordea's inner circuit (see step 2). The first version allowed X plaquettes for X flags. A new test caught it; it had only made some X candidates fail at build (276 rows).
4. **Greedy two-level search with an exact single-flag separation test.**
   - A pair counts as removed by two flags only when one flag alone separates it (sufficient, not necessary).
   - Up to 40 / 16 concrete flags per level are verified, and 8 level-1 circuits are carried to level 2.
5. **Any root position on Willow** (tree centre at (6, 7) in the search). Option-1 had pinned the root to G4's (9, 9). The readout rule is translation covariant, so this changes nothing except that free grid points near the boundary are not lost.
6. **Labelling:** only the best code labelling per base from the screen cache (not all 210).
7. **At most 2 successes per base were requested** (diversity); B0060 gave 3, because the cap is checked between frontier circuits.
8. **Reporting conventions.**
   - "Malignant S at ≤ 2 faults" = S malignant at 1 fault + at 2 faults.
   - The rate at mfc 2 is reported as 0 when nothing is malignant at ≤ 2 faults.
9. **Aborted first run.** It filtered flags by realisability as if every Z flag were dormant at the mid check. That wasted the verify() budget on flags that sit on the parity qubit's line. It was stopped after 130 bases. It had already found the first 6 of the same successes; its files are kept (removed in the Nov 1 cleanup; superseded by the canonical run), and the canonical run supersedes them.
10. **Bug in the Z-only pass.** Measurement-result flip events (MX, MRX) in two-root bases crashed `event_pauli` for 908 bases. They were fixed (such events flip no probe; test added) and those bases were rerun.
11. **Lone-root bug.** A root with no CX (a degenerate two-root base) was missing from `Design.qubits`, which broke the embedding and validation of B0130. It is fixed: every qubit with an operation is now included.

## Open questions for you

1. **Is one X flag acceptable?** Every fault-distance-3 circuit found needs one same-control X flag next to the ZZ flag. With Z flags only, ≤ 2 flags reached 1 malignant pair (greedy search). Should a 3-flag Z-only pass be run?
2. **Native gate set.** These are CX-form circuits, as in d3a6, d3a4 and G4-CX. On Willow each CX is CZ plus H, and the flags add 4 TICKs. Should the native CZ + H versions be built and verified? For G4 that conversion cost about a factor of 5 in rate (RESULTS_g4.md).
3. **Ranking.** The ranks above put added TICKs before the 3-fault count. The rate-best success is `success03` (1 in 6,570,057), and the smallest is `success08` (12 qubits, 24 CX). Which should be the headline circuit?
4. **G4 itself** cannot be brought to fault distance 3 with ≤ 2 flags: its hook qubits 5 and 9 have no free neighbour. Is a different tree (as found here) acceptable, or must the as-run G4 layout be kept?
5. **Distance 5.** Should this probe / GF(2) machinery now be applied to distance 5?

## cliffordea untouched

```
$ git -C cliffordea status --porcelain --ignored
(empty output, exit code 0)        # logs/cliffordea_check_zzflags.txt is 0 bytes
$ git -C cliffordea rev-parse HEAD
27385c688ed40d595eab4e2378dccb5c4d32dd9a
```

**cliffordea names used for the first time in this round** (file:line in `cliffordea/cliffordea/…`):
- noise placement after the operations: `enum/noise/_noise.py:337-407`;
- `FaultCombinator.__init__` / `basis`: `enum/combinators/fault_combinator.py:106-124`;
- `group_error_events_by_location`: `enum/cultivation_circuit.py:296`;
- `ErrorEvent`: `enum/types.py:19`;
- `ONE_QUBIT_ERROR_EVENTS`: `enum/constants.py:5`.

The others are as in RESULTS_option1.md.
