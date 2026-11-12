# RESULTS — search under the "continuing-data strict" readout rule

Run unattended on 2026-11-01, 6:50 pm – 10:12 pm KST. Earlier results files are untouched; everything below is new.

## Answer (3 sentences)

**Yes: there are Willow double checks with fault distance 3 that also respect the readout rule when the data continue.** The search found 10, all with one ZZ flag plus one X flag on a one-root fold of depth 5; none was found with fold depth ≤ 4, where every base was screened and every promising one (≤ 14 malignant pairs) went through both flag searches. The best, `results/continuing/success02` (12 qubits, 24 CX), has 0 continuing-data conflicts, 0 strict violations and 0 malignant T configurations at ≤ 2 faults (350 at 3 faults); its T error per kept shot is 1 in 5,679,100 at uniform p = 0.1 % and 1 in 140,288 under the Willow calibration model, against 1 in 6,570,057 and 1 in 89,151 for success03 (7 conflicts) and 1 in 2,054,158 and 1 in 20,234 for G4 (2 conflicts).

**Naming.** To avoid a clash with the previous round's `results/zz/success03`, this report writes **cs00 … cs09** for `results/continuing/success00 … success09`. "success03" always means the old `results/zz/success03`.

## Status

| task | status | one line |
|---|---|---|
| Continuing-data check (reusable) | **PASS** | `constraints.continuing_data_violations` + `check_circuit(..., data_continue=True)` (`nnflags/constraints.py:272-311`, option `data_continue` at `:323`, applied at `:374-375`); wrapper `continuing_data.strict_conflicts`. success03 = **7**, G4 (CX and native) = **2**, hand-made clean circuit = **0**, G4 with q7 unmeasured = 0 (tests). |
| 1. G6 analysis | **DONE** | Google keeps data and measured qubits on disjoint lines (data 9 / 11 / 13, measured 10 / 12) and **never reads out G6's q12**, the one ancilla on a data line (G4's q7). G6: 0 strict, 0 continuing-data conflicts in the cultivation stage. |
| 2. Search (`nnflags/search_continuing.py`) | **SUCCESS: 10 found, stopped** (stopping rule) | Stage 1 (depth ≤ 4, ≤ 12 qubits, 1 or 2 roots, exhaustive): 0. Deep pass (exact 2-cover + wider greedy, 539 best keys): 0, best 1 malignant pair. Stage 2 (depth ≤ 5, ≤ 13 qubits, 1 root; sampled, smallest first): 10 successes after 1,347 of 35,710 queued keys. Search wall time 2 h 10 min (< 4 h). |
| 3a. Uniform p = 0.1 % comparison | **DONE** | cs02 1 in 5,679,100 per kept shot; acceptance 89.28 % ± 0.010 % (rel. s.e. 0.011 %); 1.120 attempts per kept shot. |
| 3b. Realistic Willow noise | **DONE** | Calibration: cs02 1 in 140,288 vs success03 1 in 89,151 vs G4 1 in 20,234. Spec sheet: 1 in 363,150 / 360,080 / 90,830. |
| 3c. Google QVM E1 / E2 / E3 | **PASS** | E1: `willow_pink` validates the device circuit; round trip, flows and DEM identical. E2: 0 detector fires in 2,000 shots, worst infidelity 0.000000000000024. E3: 1,203 / 1,203 single events and 13,041 / 13,041 two-fault configurations agree with cliffordea; no kept corrupted state. |
| 3d. QVM E4 (noisy) | **DONE** | 4,000,000 shots of cs02 in 9 min: acceptance 75.20 % ± 0.02 %, T error per kept shot 1 in 141,545 (95 % CI 1 in 238,828 to 1 in 89,561) vs success03 1 in 78,277 and G4 1 in 17,926. **Superseded (Nov 2):** extended to 8,000,000 shots, cs02 = 1 in 121,322 (95 % CI 1 in 89,754 to 1 in 168,336), 5.6× better than G4 G6-style (1 in 21,511) and 6.8× better than G4; see `qvm-google (main)/test2_cs02_continuing_data_vs_google/RESULTS.md`. |
| Figures (PNG only) | **DONE** | `qvm-google (main)/test2_cs02_continuing_data_vs_google/figures/continuing_circuits.png`, `figures/continuing_comparison.png`. No PDF written. |
| Tests | **PASS** | `nnflags/tests` 120 passed; `qvm-google/tests` 16 passed. |
| cliffordea untouched | **PASS** | `git -C cliffordea status --porcelain --ignored`: empty output. |

**Settings of every number unless a line says otherwise:** distance 3; cultivated states T and S; `enum.noise.uniformly_depolarize` (cliffordea `enum/noise/main.py:9`) at p = 0.001; `FaultCombinator.get_kept_effects` (`enum/combinators/fault_combinator.py:236`) with `CliffordLogicalAnalyzer` via `nnflags.verify.verify` (`nnflags/verify.py:47-100`); T error per kept shot = cliffordea `error_rates_per_kept_shot` (`fault_combinator.py:164-225`) truncated at max_fault_count (mfc) 3; CX form; Willow 105-qubit grid; strict rule `live_rule="gate"`, `final_layer="auto"` (constraints.py defaults) **plus** the continuing-data rule.

## The rule as implemented

`constraints.continuing_data_violations(circuit, embedding, data_qubits=None)` (`nnflags/constraints.py:272`):
- data = MPP targets (cliffordea `find_data_indices`);
- for **every** TICK and every measurement of a non-data qubit (mid-check MRX of the root, final MX / M of ancillas and flags, anything else), one violation per data qubit on the same line r + c. Simultaneity does not exempt anything, since the data are not measured;
- a measured data qubit is reported as kind `data_measured`;
- `check_circuit(..., data_continue=True)` adds these to the strict check, which still runs unchanged (`constraints.py:374-375`); wrapper `continuing_data.strict_conflicts` (`nnflags/continuing_data.py:58`).

Unit tests (`nnflags/tests/test_continuing.py`): success03 → 7 (same pairs as `continuing_data_conflicts`), G4-CX and G4-native → 2 (q7, line 19), a hand-made clean circuit → 0, G4 with q7 unmeasured → 0, G6 cultivation stage → 0, `data_measured` and the "simultaneous is not exempt" case, default `check_circuit` unchanged.

## 1. What Google's G6 does (`nnflags/g6_continuing.py`, `results/continuing_g6.json`)

G6 = Rosenfeld et al., arXiv:2512.13908, Fig. 4 "grafting N = 2 with cultivation" as run: 54 qubits, 124 TICKs, real Willow coordinates (`nnflags/data/google_circuits/rosenfeld2512_G6.stim`).

| item | G6 |
|---|---|
| cultivation data (targets of `I[T_gate]`, TICK 29) | 2 (4, 5), 4 (4, 7), 8 (5, 4), 10 (5, 6), 18 (6, 5), 20 (6, 7), 28 (7, 6) → **lines 9, 11, 13** |
| double-check ancillas | 3 (4, 6) line 10, 9 (5, 5) line 10, 11 (5, 7) line 12, 19 (6, 6) line 12, **12 (5, 8) line 13** |
| measurements in the cultivation stage | TICK 25: 3, 9, 11, 19; TICK 40 (mid check): 11, 19; TICK 55 (end of check): 3, 9, 11, 19 — all on lines 10, 12 |
| never measured | **q12**, on data line 13. It is only reset (TICK 56). Had it been read out with the others it would have hit data 20 (6, 7) and 28 (7, 6). |
| grafting | starts at TICK 57; first surface-code readout at TICK 90 |
| surface code after grafting | measure qubits on the **odd** lines 7–19, data on the **even** lines 8–18: disjoint by line parity. The cultivation data become surface-code measure qubits; the cultivation ancillas 3, 9, 11, 19 become surface-code data. |
| strict rule, whole G6 (gate rule; final layer auto or checked; data = cultivation data or none) | **0** |
| continuing-data rule on the cultivation stage (TICKs 0–56) | **0** |

**G4 ↔ G6.** G6's double check has G4's structure (7 data on three lines, two roots on one line, two more read-out ancillas on the other ancilla line, and one ancilla on a data line). G4: data lines 15, 17, 19; ancillas 1, 4 on line 16, roots 6, 9 on line 18, **q7 on data line 19** — the source of G4's 2 continuing-data conflicts. In Fig. 2 (G4) the data are read out in the same final TICK, so measuring q7 is harmless there; in Fig. 4 (G6), where the data continue, Google drops exactly that measurement.

**Google's layout pattern.** (i) Data on one line parity, every measured qubit on the other (here: data odd, measured even). Since r + c changes by 1 along every coupler, this is the grid's checkerboard colouring, so every CZ joins a data line to a measured line. (ii) The parity roots of the mid check share one line with nothing else on it. (iii) An ancilla that has to sit on a data line is not read out (its detector is given up).

**What dropping q7 costs in cliffordea** (G4-CX with q7's M and detector removed = "G4 G6-style"): continuing 0, strict 0, equivalence ok; malignant T 0 / 0 / 7 / 667 at 0–3 faults (G4: 0 / 0 / 7 / 671); T error per kept shot 1 in 1,869,957 (G4: 1 in 2,054,158). Still fault distance 2.

**How this guided the search.** (a) Roles follow lines: the search labels every readout line D (data), M (measured) or R (root only) and grows trees only consistently with the labels. (b) Variant "U": an internal node on a D line may be an ancilla that is never read out (G6's q12 trick), at most one per base. (c) Two-root forests at diagonal neighbours on one line (G4 / G6 roots).

## 2. Search

### Search space and method (`nnflags/search_continuing.py`)

- **Bases** = fold forests in canonical CX form (`search_option1.build` / `to_circuit`): parity root(s) measured MRX mid-check, every node X-collects its children ASAP, unfold = time reverse, ancillas MX at the end; 7 data; leaves are data; internal nodes data or ancillas (also trees whose internal nodes are all ancillas).
- **Enumerated as embedded forests on Z², root at the origin, with a label per readout line** (D / M / R; `grow_pattern`, partitioned by line-label pattern and run in parallel). A qubit's role is its line's label, so the line-disjointness is a pruning rule during the growth. Extra pruning: ≤ 7 (+U) data-line nodes, ≤ n − 7 ancillas, every M node needs a child, remaining capacity must reach both ends of the line interval, ASAP fold depth ≤ dmax.
- **Deduplication** modulo translation and the 4 line-preserving symmetries (id, transpose, rot180, antitranspose); grouped by abstract key (`Base.canon` with roles D / A / U). **All embeddings of a key are kept** (cap 3,000; never reached in the flagged keys), because the line pattern of the flags depends on the placement.
- **Screen**: per key the best of the 210 code labellings (verify, mfc 2, T only). Keys with best malignant T count ≤ 12 go to the flag search.
- **Flags** (≤ 2): generalised Z / X flags of `zzflags` (probes, exact GF(2) prefilter, same verify / equivalence requirements as `search_zzflags`). Placement = some embedding of the key + free lattice points adjacent to all controls, **not on a data line**, not on a root line if live at the mid check, and the whole thing fits on Willow after a translation (`Placer`).
- **Two flag searches**: the greedy two-level search of `search_zzflags` (`process`), and a new exact **2-cover** (`process_cover`): every placeable (basis, control set) gets its maximal sets of base malignant pairs it separates; every two sets whose union is all pairs give a candidate pair of flags, built and verified together.
- **Success** = `check_circuit(..., data_continue=True) == []` at the saved Willow placement, `check_equivalence` ok (flags excluded from the reverse check), 0 malignant T at 1 and 2 faults; then verify at mfc 3.

### Runs

| run | space | time (KST) | keys | circuits verified | successes | best malignant T at 2 faults |
|---|---|---|---|---|---|---|
| s1 | m = 1, 2 roots; depth ≤ 4; ≤ 12 tree qubits; ≤ 1 U; greedy | 7:46 – 8:40 pm (54 min) | 12,228 (all), 317 flagged | 6,629 | **0** | 1 (21 keys) |
| deep | the 539 one-root s1 keys with screen T2 ≤ 14; 2-cover + greedy (n1 60, k1 12, n2 24) | 8:41 – 9:00 pm (19 min) | 539 | 13,633 | **0** | 1 (28 keys) |
| s2 | m = 1; depth ≤ 5; ≤ 13 tree qubits; ≤ 1 U; 2-cover + greedy | 9:00 – 9:57 pm (57 min, of which 40 min enumeration) | 1,347 of 35,710 queued (+1,939 done in s1), 119 flagged | 3,097 | **10** (stopping rule) | 0 |

**Space sizes.**
- s1: 2,510 line-label patterns; 2,838,941 embedded bases (m1: 157,151; m2: 2,681,790); 12,228 abstract keys (m1 u0 479, m1 u1 1,460, m2 u0 2,471, m2 u1 7,818). Feasible (some labelling keeps the code): all m = 1 keys, 4,667 of 10,289 m = 2 keys.
- s2: 2,015 patterns; 9,490,503 embedded bases; 37,649 keys (u0 6,736, u1 30,913).

**Exhausted vs sampled.**
- **Exhausted:** s1 entirely (every key screened with all 210 labellings; every key with T2 ≤ 12 flag-searched); the deep pass on all 539 one-root keys with T2 ≤ 14.
- **Sampled:** s2 ran in the order (U count, tree size): all keys without U up to 10 tree qubits and 486 of the 11-qubit ones were processed; the 12–13-qubit keys and all U keys of depth 5 were not reached. Two-root forests at depth 5 were not enumerated (their best screen count at depth ≤ 4 was 13, far above the one-root bases).
- **Inside a key** (as in the ZZ round): the greedy keeps 40 / 60 level-1 flags and 8 / 12 frontier circuits; the 2-cover is exact for ≤ 12 base pairs in the single-flag-separation model but builds at most 40 / 60 combinations; only the best labelling per key.

### Successes (`results/continuing/success*.{inner,full}.stim`, ranked by T error per kept shot, mfc 3)

All: one root, all ancillas read out (no U ancilla needed), one two-control Z flag + one X flag, 0 strict and 0 continuing-data violations at the saved Willow placement, equivalence ok, malignant T 0 at 1 and 2 faults, malignant S 0 at ≤ 2 faults. Base screen T2 = 5 for s2-00670 / 01348 / 01350, 8 for s2-00617.

| rank | name | base (tree) | flags (TICKs of the saved file) | flag positions (r, c) | qubits | CX | max degree | TICKs (+added) | malignant T at 3 faults | T error per kept shot, mfc 3 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **cs02** | s2-00670 `A(D(),D(A(D(),D())),D(A(D(),D())))` | `Zf10[q8@t2+q5@t3+q5@t13+q8@t14]; Xf11[q5@t2+q5@t14]` | 10 → (3, 8), 11 → (2, 9) | 12 | 24 | 3 | 16 (+2) | 350 | **1 in 5,679,100** |
| 2 | cs07 | s2-01348 `A(A(D()),D(A(D(),D())),D(A(D(),D())))` | `Zf11[q9@t2+q6@t3+q6@t13+q9@t14]; Xf12[q6@t2+q6@t14]` | (3, 8), (2, 9) | 13 | 26 | 3 | 16 (+2) | 317 | 1 in 5,588,585 |
| 3 | cs06 | s2-01350 `A(A(D()),D(A(D(),D()),A(D(),D(),D())))` | `Zf11[q5@t2+q9@t3+q9@t13+q5@t14]; Xf12[q9@t2+q9@t14]` | (6, 7), (5, 8) | 13 | 26 | 4 | 16 (+2) | 370 | 1 in 5,200,769 |
| 4 | cs04 | s2-00670 | `Zf10[q8@t3+q5@t4+q5@t14+q8@t15]; Xf11[q8@t2+q8@t5+q5@t6+q5@t15]` | (3, 8), (4, 9) | 12 | 26 | 3 | 17 (+3) | 429 | 1 in 4,826,445 |
| 5 | cs09 | s2-01348 | `Zf11[q9@t3+q6@t4+q6@t14+q9@t15]; Xf12[q9@t2+q9@t5+q6@t6+q6@t15]` | (3, 8), (4, 9) | 13 | 28 | 3 | 17 (+3) | 399 | 1 in 4,742,157 |
| 6 | cs00 | s2-00617 `A(D(),D(),D(),D(A(A(D(),D()),D())))` | `Zf10[q1@t2+q6@t4+q6@t14+q1@t16]; Xf11[q2@t3+q2@t15]` | (3, 8), (4, 11) | 12 | 24 | 4 | 18 (+4) | 356 | 1 in 3,531,175 |
| 7 | cs01 | s2-00617 | `Zf10[q1@t2+q6@t4+q6@t14+q1@t16]; Xf11[q8@t3+q8@t15]` | (3, 8), (1, 7) | 12 | 24 | 4 | 18 (+4) | 388 | 1 in 3,357,264 |
| 8 | cs03 | s2-00670 | `Zf10[q8@t3+q5@t4+q5@t14+q8@t15]; Xf11[q8@t2+q8@t16]` | (3, 8), (4, 7) | 12 | 24 | 3 | 18 (+4) | 356 | 1 in 3,246,298 |
| 9 | cs08 | s2-01348 | `Zf11[q9@t3+q6@t4+q6@t14+q9@t15]; Xf12[q9@t2+q9@t16]` | (3, 8), (4, 7) | 13 | 26 | 3 | 18 (+4) | 323 | 1 in 3,153,833 |
| 10 | cs05 | s2-01350 | `Zf11[q5@t3+q9@t4+q9@t14+q5@t15]; Xf12[q5@t2+q5@t16]` | (6, 7), (7, 6) | 13 | 26 | 4 | 18 (+4) | 389 | 1 in 2,874,020 |

(Rates at mfc 2 are exactly 0 for all ten.)

**cs02 on Willow** (`qvm-google (main)/test2_cs02_continuing_data_vs_google/figures/continuing_circuits.png`, middle):
- root 0 (5, 10), line 15; ancillas 3 (3, 10) and 7 (5, 8), line 13; Z flag 10 (3, 8) and X flag 11 (2, 9), line 11;
- data 1 (6, 10), 2 (4, 10), 4 (2, 10), 5 (3, 9), 6 (5, 9), 8 (4, 8), 9 (6, 8) on lines 16, 14, 12;
- **data on even lines, every measured qubit on odd lines** — exactly Google's checkerboard pattern. The tree has no data–data and no ancilla–ancilla gate.
- Fold (5 layers): layer 1 CX 0→1, 3→4, 7→8; layer 2 CX 3→5, 7→9; layer 3 CX 2→3, 6→7; layer 4 CX 0→2; layer 5 CX 0→6. Depth 5 because the two depth-3 branches (2 ← 3 ← 4, 5 and 6 ← 7 ← 8, 9) enter the root one after the other. The flags add 2 TICKs (their first probes, before the fold, and the mirror ones after the unfold).
- The Z flag reads Z on data 8 and data 5 (two controls on line 12); the X flag reads X on data 5 at the start and the end.

### Why depth ≤ 4 failed and depth 5 works (evidence)

`results/continuing_cover_stats.json` (539 best one-root keys of s1, all labelled with their best labelling), `results/continuing_evidence.json`:

| question | abstract (any same-colour control set, no geometry) | placeable under the line rules |
|---|---|---|
| some single flag separates every base pair | 41 keys | 4 keys |
| two flags cover all base pairs (2-cover exists) | 356 keys | **86 keys** |
| some base pair cannot be separated by any placeable flag | — | 111 keys |
| greedy cover size 1 / 2 / 3 / 4 / none | 41 / 262 / 236 / 0 / 0 | 4 / 58 / 327 / 39 / 111 |

- **The line rule, not the flags, is the obstruction.** Abstractly most good bases admit two covering flags; with flags forced off the data lines (and off the root line when live) only 86 do. A flag adjacent to a data qubit on line L must sit on L ± 1, which must be a measured line; with data on several lines this leaves few free points, and two-control flags need a point adjacent to both controls.
- **Flag faults.** For the 86 keys with a 2-cover the two flags are usually both Z flags, and the circuit then keeps 1 malignant pair made of a Z error on a Z flag (kicked back onto its control) and an X-type data error; only an X flag separates it, so 2 flags are not enough there.
- **Best at depth ≤ 4:** 1 malignant pair (28 keys in the deep pass). Example `results/continuing/attempt_1` (s1 key `A(D(),D(),D(A(A(D()),D())),D(A(D())))`, ZZ + X flag, 13 qubits): malignant T 0 / 0 / 1 / 429, T error per kept shot 1 in 6,785,004 (mfc 2), 1 in 3,594,228 (mfc 3), calibration model 1 in 73,562. Its surviving pair is X-type on both faults and a **third** Z flag could separate it (65 control sets abstractly, 3 placeable). So with depth ≤ 4 a third flag (not run) looks necessary; with depth 5 it is not.
- **Two-root forests** never screened below 13 malignant pairs (s1); one root is clearly better under this rule.
- **Depth 5 gives the checkerboard.** With the parity alternation data / measured on every coupler, a d = 3 fold that collects 7 data through measured ancillas only needs longer chains (root → data → ancilla → data), which costs one more fold layer. All 10 successes are of this kind; the G6-style unmeasured ancilla was never needed.

## 3. Validation of the best (cs02) — `nnflags/continuing_validate.py`, `results/continuing_validation.json`

Run 9:57 – 9:59 pm KST. References recomputed with the same code (success03 and G4 reproduce RESULTS_comparison.md exactly).

### 3a. Uniform p = 0.1 %, CX form

Acceptance = stim Monte Carlo on the same noisy inner circuit, 10,000,000 shots, kept = no detector fired (± 1 s.e.); enumerated "T kept" includes cliffordea's noiseless final stabiliser postselection (mfc 3).

| design | qubits | CX | TICKs | continuing conflicts | strict | malignant T at 1 / 2 / 3 faults | malignant S at ≤ 2 (at 3) | T error per kept shot, mfc 3 | acceptance (MC) | attempts per kept shot | T error per attempt |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **cs02** | 12 | 24 | 16 | **0** | 0 | 0 / 0 / 350 | 0 (147) | **1 in 5,679,100** | 89.28 % ± 0.010 % | 1.120 | 1 in 6,360,832 |
| cs07 | 13 | 26 | 16 | 0 | 0 | 0 / 0 / 317 | 0 (120) | 1 in 5,588,585 | 88.42 % ± 0.010 % | 1.131 | 1 in 6,320,720 |
| cs06 | 13 | 26 | 16 | 0 | 0 | 0 / 0 / 370 | 0 (122) | 1 in 5,200,769 | 88.67 % ± 0.010 % | 1.128 | 1 in 5,865,607 |
| success03 (zz) | 13 | 26 | 16 | 7 | 0 | 0 / 0 / 286 | 0 (108) | 1 in 6,570,057 | 88.38 % ± 0.010 % | 1.132 | 1 in 7,434,195 |
| G4-CX | 12 | 24 | 12 | 2 | 0 | 0 / 7 / 671 | 0 (162) | 1 in 2,054,158 | 93.06 % ± 0.008 % | 1.075 | 1 in 2,207,295 |
| G4 G6-style (q7 unread) | 12 | 24 | 12 | 0 | 0 | 0 / 7 / 667 | 0 (162) | 1 in 1,869,957 | 93.42 % ± 0.008 % | 1.070 | 1 in 2,001,718 |

Relative standard errors of the acceptances are 0.008–0.011 % (< 1 %). Enumerated detectors-only acceptance (mfc 4) agrees with the MC within 0.02 percentage points for every row (cs02: 89.28 % both).

- cs02 is 2.8 × better per kept shot than G4 and 3.0 × better than the rule-compliant G4 G6-style, at 4 % more attempts.
- It is 14 % worse than success03 under uniform noise (more 3-fault malignant configurations, 350 vs 286), but success03 breaks the rule 7 times.

### 3b. Realistic Willow noise, native CZ + H at the circuits' own Willow positions

Models of `nnflags/willow_noise.py` (RESULTS_comparison.md): calibration (per qubit / coupler, `willow_pink_d7v1-2024_08_16`) and spec sheet; durations 1q 25 ns, CZ 42 ns, measurement 600 ns, reset 200 ns, reset error 0.1 % (assumptions as before). Conversion `willow_noise.cx_to_native` (G4: its own native extraction). Enumeration to mfc 4, table at mfc 3; acceptance from 4,000,000 MC shots with asymmetric readout. Malignant counts are unchanged by the conversion for every design (`native_uniform_counts_equal`).

| design | native TICKs | calibration: T error per kept shot, mfc 3 (mfc 4) | acceptance | attempts | spec sheet: T error per kept shot, mfc 3 (mfc 4) | acceptance | attempts |
|---|---|---|---|---|---|---|---|
| **cs02** | 29 | **1 in 140,288** (1 in 128,163) | 75.18 % ± 0.022 % | 1.330 | **1 in 363,150** (1 in 336,453) | 76.23 % ± 0.021 % | 1.312 |
| cs07 | 29 | 1 in 94,595 (1 in 85,999) | 73.30 % ± 0.022 % | 1.364 | 1 in 362,787 (1 in 335,716) | 74.31 % ± 0.022 % | 1.346 |
| cs06 | 30 | 1 in 74,765 (1 in 67,789) | 70.71 % ± 0.023 % | 1.414 | 1 in 317,556 (1 in 295,019) | 74.78 % ± 0.022 % | 1.337 |
| success03 (zz) | 29 | 1 in 89,151 (1 in 79,616) | 66.47 % ± 0.024 % | 1.504 | 1 in 360,080 (1 in 334,402) | 74.39 % ± 0.022 % | 1.344 |
| G4 (native) | 24 | 1 in 20,234 (1 in 18,925) | 73.99 % ± 0.022 % | 1.351 | 1 in 90,830 (1 in 88,786) | 79.00 % ± 0.020 % | 1.266 |
| G4 G6-style | 22 | 1 in 24,121 (1 in 22,551) | 76.08 % ± 0.021 % | 1.314 | 1 in 102,043 (1 in 99,859) | 81.19 % ± 0.020 % | 1.232 |

- **Under the calibration model cs02 is the best design of all**: 6.9 × better than G4, 5.8 × better than G4 G6-style and 1.6 × better than success03, with fewer attempts than success03 (1.330 vs 1.504) and about the same as G4 (1.351). Its acceptance is also higher than success03's (75.18 % vs 66.47 %); which calibration entries cause the difference was not isolated.
- Spec sheet (uniform device parameters): cs02 ≈ success03 (1 in 363,150 vs 1 in 360,080), 4.0 × better than G4.
- Truncation: mfc 3 → 4 changes the rates by 3–10 % (as in RESULTS_comparison.md).

### 3c. Google QVM (`qvm-google/qvm_continuing.py`, reusing `qvm_willow.py` unchanged; outputs `qvm-google/results/continuing/`)

Design `cont_success02` = cs02 converted with `willow_noise.cx_to_native`, H as `PhasedXZGate`, real `cirq.T` / `T**-1`, cliffordea's encoded T state (protocol of RESULTS_qvm.md). cirq 1.7.0, cirq_google 1.7.0, qsimcirq 0.22.1, processor `willow_pink`.

| experiment | result |
|---|---|
| **E1** device validation (`e1_cont_success02.json`, 9:58 pm) | `validate_circuit` PASS with H as `cirq.H` and as `PhasedXZGate`; 12 / 12 CZ pairs on couplers; all qubits on the device; round trip to stim identical; stabiliser flows equal; detectors deterministic; DEM identical; 31 moments: 24 CZ, 34 PhasedXZ, 6 measure, 6 reset, 14 T / T⁻¹; nnflags strict rule 0 violations; continuing-data rule 0 violations. |
| **E2** noiseless real T (`e2_cont_success02.json`) | 2,000 shots: 0 detector fires (6 detectors); ideal decode = T state in all 2,000 shots; worst infidelity with \|T_L⟩ over 5 qsim trajectories 0.000000000000024; cirq.Simulator fidelity 1.0. Negative control (T on every data qubit): acceptance 50.95 %, fidelity 0.50. |
| **E3** exhaustive fault injection vs cliffordea (`e3_cont_success02.json`, 9:58 pm, 11 processes) | 162 faults. Single events: 1,203 / 1,203 agree (1,167 rejected, 36 kept benign, 0 kept malignant). All 2-fault configurations: 13,041 / 13,041 agree (13,024 rejected, 17 kept benign, **0 kept malignant**); seeded random sample 2,000 / 2,000. Signatures and accept probabilities agree everywhere; all real-T detector outcomes deterministic. |
| **E4** noisy QVM | see below |

**E4 — noisy QVM** (`e4_cont_success02.json`, chunks in `e4_chunks/`). Settings as RESULTS_qvm.md: `NoiseModelFromGoogleNoiseProperties(load_device_noise_properties("willow_pink"))` applied with `noisy_moments`, qsim one thread per worker, 12 workers, chunks of 5,000 shots, seed CRC32("name:chunk"); ideal |T_L⟩ preparation and ideal decode outside the noise model. cs02: 4,000,000 shots, 9:58:28 – 10:07:32 pm KST (9 min 4 s wall, within the 30 min cap). success03 and G4 rows are from `qvm-google/results/e4.json` (RESULTS_qvm.md), same model and protocol.

| circuit | shots | acceptance (± 1 s.e.; rel. s.e.) | kept shots in the code space | logical errors | **QVM T error per kept shot** (exact 95 % CI) | one-sided 95 % upper bound | stim calibration model, mfc 3 / mfc 4 | infidelity of the kept state |
|---|---|---|---|---|---|---|---|---|
| **cs02** | 4,000,000 | **75.20 % ± 0.022 %** (0.029 %) | 2,547,803 (84.70 %) | 18 | **1 in 141,545** (1 in 238,828 to 1 in 89,561) | 1 in 95,453 | 1 in 140,288 / 1 in 128,163 | 15.30 % ± 0.02 % |
| success03 (zz) | 8,000,000 | 65.48 % ± 0.017 % (0.026 %) | 4,383,534 (83.68 %) | 56 | 1 in 78,277 (1 in 103,625 to 1 in 60,279) | 1 in 62,657 | 1 in 89,151 / 1 in 79,616 | 16.32 % ± 0.02 % |
| G4 | 4,000,000 | 75.06 % ± 0.022 % (0.029 %) | 2,204,846 (73.43 %) | 123 | 1 in 17,926 (1 in 21,568 to 1 in 15,024) | 1 in 15,433 | 1 in 20,234 / 1 in 18,925 | 26.57 % ± 0.03 % |

- **Superseded (Nov 2):** the table row above is the first 4,000,000-shot run. With 8,000,000 shots cs02 = 1 in 121,322 (42 errors), 6.8 × better than G4 and 5.6 × better than G4 G6-style (1 in 21,511, now run in the QVM); see test 2 RESULTS.md. The 4 M-shot statements below are kept as the record of that run.
- In Google's own Willow noise model cs02 is 7.9 × better than G4 per kept shot (the CIs do not overlap) at the same acceptance (75.20 % vs 75.06 %), and 1.8 × better than success03 with 10 percentage points higher acceptance (the cs02 and success03 CIs overlap slightly).
- The stim calibration-model values (mfc 3 and mfc 4) lie inside the QVM 95 % CI.
- The QVM does not model readout-line dephasing, so it cannot reward the rule itself; it shows that obeying the rule costs nothing in the modelled noise.

## Figures (PNG, 200 dpi; `python -m nnflags.plots_continuing --new ...`)

- `qvm-google (main)/test2_cs02_continuing_data_vs_google/figures/continuing_circuits.png`: left, Google's G6 cultivation double check as run; middle, cs02; right, cs07; on Willow. Blue bands = readout lines of data qubits, orange dashed lines = readout lines of measured qubits; circles = data, diamonds = parity root, filled squares = ancillas read out at the end, dashed square = G6's never-read ancilla q12, ▲ / ▼ = Z / X flags. Under each panel the two line sets and "disjoint: yes".
- `figures/continuing_comparison.png`: G4 (as run), G4 G6-style, success03, cs02, cs07, cs06: (a) malignant T at 2 faults, (b) at 3 faults, (c) continuing-data conflicts, (d) T error per kept shot at uniform p = 0.1 % (CX) and Willow calibration (CZ + H), "1 in N" log axis. Okabe–Ito colours with hatching; white background; no e-notation.

## Decisions made without the user

1. **Unmeasured ancillas allowed** (variant U, at most one per base), because Google's own G6 does exactly this with q12. They satisfy the rule as stated (a qubit that is never measured cannot dephase a line). All 10 successes turned out not to use it.
2. **Roles by line label.** In the all-measured variant a qubit's role is its line's role; this is the rule itself (a measured ancilla on a data line is a violation), not an extra restriction. Data internal nodes are allowed where their line is a data line.
3. **Reset is not a measurement**: resets do not dephase the readout line (as in all earlier rounds and in G6, which resets q12).
4. **Two-root forests only at diagonal neighbours on one line** (G4 / G6 root pattern); not enumerated at depth 5 because at depth ≤ 4 their best screen count was 13 malignant pairs vs 5 for one root.
5. **Screen threshold** T2 ≤ 12 for the flag search (successes of the ZZ round came from T2 10–11); the deep pass widened it to ≤ 14.
6. **Staged search** (s1 exhaustive, deep, s2 sampled by size) because the full depth-5 / 13-qubit / 2-root space did not fit in time or memory (s2 one-root alone: 9.5 M embeddings, 40 min to enumerate, 32 GB). Stage 2 stopped at the 10-success rule after 57 min; total search wall time 2 h 10 min.
7. **Exact 2-cover added** to the greedy search (deep pass, s2), with Z + X flag pairs tried first. 8 of the 10 successes were found by the greedy search after the 2-cover had found none (keys s2-00670 / 01348 / 01350, mode "cover+greedy"), 2 by the 2-cover itself (cs00, cs01, key s2-00617).
8. **Best = lowest T error per kept shot at mfc 3, uniform noise** (rule of the task): cs02 (also 12 qubits, the smallest).
9. **G4 G6-style** (G4-CX without q7's measurement) added as a reference: it is the circuit Google actually runs in G6 and it is rule-compliant.
10. **E4** run with 4,000,000 shots for cs02 only; success03 and G4 E4 numbers are taken from `qvm-google/results/e4.json` (RESULTS_qvm.md), same noise model and protocol.
11. The new circuits are named cs00–cs09 in this report; the files keep the search's names `results/continuing/success00–09`.

## Open questions for the user

1. Is the **depth-5 fold** acceptable? It adds 2 TICKs to the base (cs02: 16 CX-form TICKs, 29 native, the same as success03), and under the calibration model it still wins.
2. Is the **G6 trick** (an ancilla that is never read out) acceptable in general? It was allowed here but not needed.
3. Should the **unsampled part of stage 2** (12–13-qubit and U bases at depth 5) be run, e.g. for a lower 3-fault count than cs02's 350 (success03 has 286)?
4. Should **resets** be treated as line-disturbing too? Google's G6 resets q12 next to data, so it seems not.
5. Distance 5 under this rule.

## Files

- **Code (new):** `nnflags/search_continuing.py`, `nnflags/g6_continuing.py`, `nnflags/continuing_validate.py`, `nnflags/continuing_evidence.py`, `nnflags/plots_continuing.py`, `qvm-google/qvm_continuing.py`, `nnflags/tests/test_continuing.py`. **Extended:** `nnflags/constraints.py` (`continuing_data_violations`, `data_continue=`), `nnflags/continuing_data.py` (`strict_conflicts`).
- **Results:** `results/continuing_g6.json`; `results/continuing_screen.json` (s1 + s2 screen cache), `results/continuing_screen_s1_final.json`, `results/continuing_screen_deep.json`; `results/continuing_{candidates,bases}_{s1,deep,s2}.csv`; `results/continuing_state_{s1,deep,s2}.json`; `results/continuing_deep_keys.txt`; `results/continuing_cover_stats.json`; `results/continuing_evidence.json`; `results/continuing_validation.json` (final), `results/continuing_validation_firstpass.json` (first pass incl. cs00, cs01, attempt_0 / 1); `results/continuing/success00–09.*.stim`, `best_{s1,deep,s2}_*.stim`, `attempt_{0,1}.*.stim`.
- **QVM:** `qvm-google/results/continuing/{e1,e2,e3,e4}_cont_success02.json`, `e3_parts/`, `e4_chunks/`.
- **Logs:** `logs/search_continuing_{s1,deep,s2}.log`, `logs/continuing_g6.log`, `logs/continuing_validate.log`, `logs/continuing_cover_stats.log`, `qvm-google/logs/{e3,e4}_continuing.log`, `logs/pytest_continuing.log`, `logs/cliffordea_check_continuing.txt`.

## Tests and cliffordea

- `nnflags/tests`: **120 passed** in 97 s (102 earlier + 18 new in `test_continuing.py`: the 8 rule / G6 / enumeration / placement tests and a re-verification of each of the 10 saved successes from its stim files: both rules, equivalence, 0 malignant T at ≤ 2 faults). Log `logs/pytest_continuing.log`.
- `qvm-google/tests`: **16 passed** in 6 s. Log `logs/pytest_qvm_continuing.log`.
- `git -C cliffordea status --porcelain --ignored`: empty output, exit 0 (`logs/cliffordea_check_continuing.txt`, 0 bytes); HEAD 27385c688ed40d595eab4e2378dccb5c4d32dd9a.
- cliffordea names used are those of earlier rounds (`find_data_indices`, `uniformly_depolarize`, `FaultCombinator.get_kept_effects` / `index_to_events` / `error_rates_per_kept_shot`, `CliffordLogicalAnalyzer`), cited above.
- The user's `./test..py` was not touched. No git commit was made.
