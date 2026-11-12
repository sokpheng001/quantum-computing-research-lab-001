# RESULTS — Option 1: G4 baseline, refined live rule, equivalence checker, fold-tree search

Run unattended on 2026-11-01, 09:13 am – 10:30 am KST. The search ran 09:57 am – 10:21 am KST. No further step was started.

## Status

| Task | Status | One line |
|---|---|---|
| A — live rule + final-layer condition | **PASS** | New default `live_rule="gate"`, with the old rules kept as options. The final layer is exempt only if a checked condition holds. **Strict conflicts:** d3a6 min 1 (182,968 embeddings), d3a4 min 1 (38,640), G4 0, **G5 0** (was 12). |
| B — G4 fault distance | **PASS (faithful)** | **Fault distance 2.** G4's double check has **7 malignant 2-fault T configurations** (d3a6: 4, d3a4: 12) and 671 at 3 faults. T logical error per kept shot is 1 in 2,421,930 (CX form) and 1 in 447,652 (native CZ + H), at p = 0.001. Details: [RESULTS_g4.md](RESULTS_g4.md). |
| C — equivalence checker | **PASS** | `nnflags/equivalence.py`, 14 tests. d3a6, d3a4, d3a6f2 and the extracted G4 (native and CX) pass. 7 deliberately broken circuits fail. |
| D — search | **20 valid candidates found, then stopped** (as instructed) | Best: **6 malignant 2-fault T configurations** (better than G4's 7, worse than d3a6's 4). No candidate reaches 0. **The Z flags never lowered the 2-fault count of their base** (see "What the search shows"). |
| E — figures | **PASS** | 4 new PNGs (no PDF anywhere in `figures/`). |

Settings for every number unless stated otherwise:
- distance 3; cultivated states T and S;
- `enum.noise.uniformly_depolarize` (cliffordea `enum/noise/main.py:9`) at p = 0.001;
- `FaultCombinator.get_kept_effects` at max_fault_count 2 and 3;
- `CliffordLogicalAnalyzer`;
- Willow 105-qubit grid;
- readout **strict** with `live_rule="gate"`, final layer `"auto"`;
- nearest-neighbour gates, degree ≤ 4.

Rates are cliffordea's `error_rates_per_kept_shot`, truncated at the stated max_fault_count.

---

## A. Live rule and final-layer condition (recap; full text in RESULTS_g4.md § A)

**Rule.**
- A qubit idling in a Z eigenstate (after R or MR, at the start, or after M) is **not live**.
- It becomes live at its first two-qubit gate or its first single-qubit gate that does not keep the Z basis (H-like). `I`/Pauli/`S` keep it dormant. It stays live until its measurement.
- **RX = R then H on hardware**, so an RX/MRX-prepared qubit is live from the end of that TICK.
- Data (MPP targets) are live from the start.

**Options.** The old variants remain available:
- `live_rule="prep"` (Step-3 default);
- `live_rule="prep_zdormant"` (Step-3 `z_reset_idle="not_live"`);
- `final_layer="exempt"` (unconditional) and `"check"`.

**Final layer** (`final_layer_status`). It is exempt only if:
- no unitary gate (I included) occurs in or after the last measurement TICK, and
- the final readout is one TICK. MX/MY count as "basis change before".

| circuit | placements | new rule: min / histogram | new rule, final layer checked | Step-3 rule |
|---|---|---|---|---|
| d3a6 | 182,968 embeddings | **1** / 1: 47,424 · 2: 135,544 | 4 | 1 |
| d3a4 | 38,640 embeddings | **1** / 1: 38,640 | 1 | 1 |
| G4 | real coordinates | **0** | 0 | 0 |
| G5 | real coordinates | **0** | 0 | 12 |

---

## B. G4 result recap (full text, conversion steps and proofs: RESULTS_g4.md)

| circuit | T malignant k = 0/1/2/3 | T benign k = 2 | S malignant k ≤ 2 | T logical error per kept shot, p = 0.001 (max_fault_count 2 / 3) |
|---|---|---|---|---|
| d3a6 | 0 / 0 / 4 / 415 | 37 | 0 | 1 in 4,760,490 / 1 in 3,568,591 |
| d3a4 | 0 / 0 / 12 / 1,619 | 129 | 0 | 1 in 3,583,893 / 1 in 3,184,814 |
| **G4 extracted, CX form** | 0 / 0 / **7** / 671 | 41 | 0 | **1 in 2,421,930** / 1 in 2,054,158 |
| G4 extracted, native CZ + H | 0 / 0 / 7 / 671 | 41 | 0 | 1 in 447,652 / 1 in 314,362 |

**Faithfulness.**
- The native extraction equals G4's TICKs 31–50 op for op (I placeholders dropped, `M 9 6` → `MR 9 6`).
- The stim flows of G4's own segment and of both extractions are identical: X_L is measured, its commutant is preserved, and Z_L is not preserved.
- The code is d3a6's, through the relabelling {0→0, 2→7, 3→3, 5→11, 8→10, 10→5, 11→8}.

**T convention.** G4 uses T_y; cliffordea uses a T_z pattern. Mapped by a noiseless frame W, the result is identical. A wrong frame changes the answer, so the analysis does see the frame.

**X-hook qubits of G4: 2, 4, 5, 9.** Of these, 4, 5 and 9 have no free Willow neighbour, so G4 itself fails the design rule.

---

## C. Equivalence checker (`nnflags/equivalence.py`)

`check_equivalence(inner, full, flag_qubits)` uses cliffordea's own derivations through verify's loader (`find_data_indices`, `find_stabilizer_generators`, `find_logical_s_gate`) plus stim:

- **(i) Code.** There must be a bijection of data qubits onto d3a6's that maps the stabiliser supports **and** the logical-S sublattice.
- **(ii) Logical check.**
  - Forward check: the detector containing the MPP record has records R1 with stim flow `X_L -> rec[R1]`.
  - Time-reversed check: a later detector without the MPP contains R1 plus R2 with `X_L -> rec[R2]`.
  - Every generator of X_L's commutant passes unchanged; Z_L does not.
- **(iii) Time reverse.** Every H is pushed into a frame (`absorb_hadamards`: CZ + H → CX, RX/MX, H-only TICKs removed). The unfold's two-qubit layers must equal the fold's in reverse order, **and** U_unfold · U_fold = identity (stim tableaux). Flag gates are excluded.
- **(iv) Determinism.** Every detector must be deterministic (stim).

Tests (`tests/test_equivalence.py`, 14):
- **Pass:** d3a6, d3a4, d3a6f2 (flags 4, 9), extracted G4 native and CX.
- **Fail as required:**
  - wrong stabiliser support in the full circuit;
  - logical S on the wrong sublattice;
  - fold missing one CX (wrong check);
  - unfold layers swapped;
  - unfold re-layered with the *same* unitary (caught: not the exact layer reverse);
  - an extra non-deterministic detector;
  - missing forward detector;
  - G4 with one unfold CZ removed.

---

## D. Search (`nnflags/search_option1.py`)

### Search-space definition (G4-type double checks in canonical CX form)

- **Base.** A forest on Willow couplers with **m = 1 or 2** components:
  - each component is rooted at an **ancilla parity-measurement qubit**;
  - all leaves are data; internal nodes are data or ancillas;
  - **exactly 7 data** (the d=3 colour code).
- **Fold and unfold.**
  - The fold is CX(node → child), scheduled ASAP from the leaves.
  - The roots end up holding X_L and are measured together (`MRX`, one TICK, detector = roots ⊕ MPP).
  - The unfold is the exact time reverse. Then MX of all ancillas; each root's final MX ⊕ its mid MRX is the time-reversed check.
  - Ancillas are RX-prepared, and there is a trailing reset.
- **Roots.** At **G4's root position (9, 9)** for m = 1, and at **G4's two measured positions (9, 9) and (8, 10)**, which share line 18, for m = 2.
- **Readout lines.** No other forest qubit may sit on a root's readout line (decision 5: nothing else live on the parity qubits' lines).
- **Fold depth ≤ 4** (G4 and d3a6 have depth 4), and **n = 7 + k ≤ 11 qubits** before flags.
- **Code labelling.** 7! labellings fall into **210 classes** modulo the 24 code automorphisms that keep the plaquettes and the logical-S sublattice. For each abstract base, all 210 were verified and the one with the fewest malignant 2-fault T configurations (then lowest rate) was used.
- **Regions and symmetries.** Translations and the line-preserving symmetries (transpose, rot180, antitranspose) change neither verify() nor the readout rule. Growing trees around a fixed root covers every orientation of every shape. So "other regions" only differ by Willow's boundary, which the free-neighbour check sees.

| group (m, fold depth, n) | embedded bases | abstract bases (up to isomorphism) |
|---|---|---|
| m1, d3, n8 | 136 | 1 |
| m1, d4, n8 / n9 / n10 / n11 | 2,850 / 24,828 / 88,396 / 157,892 | 31 / 157 / 374 / 489 |
| m2, d3, n9 / n10 / n11 | 10,576 / 66,766 / 181,488 | 37 / 130 / 215 |
| m2, d4, n9 / n10 / n11 | 17,948 / 237,624 / 1,388,958 | 74 / 504 / 1,731 |
| **total** | **2,177,462** | **3,743** (× 210 labellings = **786,030** labelled bases) |

- **Not fully explored.** Every abstract base was screened, but only 34 bases were tried with flags before the stop at 20 valid candidates (51 flagged circuits evaluated).
- **m = 2 infeasible bases.** 1,204 of the 3,743 abstract bases (all m = 2) are **infeasible**. No labelling makes them a double check of the code, because some Z plaquette has odd overlap with one root's component and anticommutes with that root's MRX. stim's flow solver catches this, and these bases are skipped.

### Procedure

1. **Phase S (screen).** For every abstract base: verify() with each of the 210 labellings at max_fault_count 2; keep the best labelling; compute the X-hook qubits from `FaultCombinator.index_to_events` (fault_combinator.py:374).
   - A hook = a fault with data weight ≥ 2 in a malignant 2-fault T configuration. The hook qubit is the qubit carrying its X/Y events.
   - The hook window is those events' TICKs.
   - Best-labelling malignant 2-fault T counts over the 2,539 feasible abstract bases: **minimum 6** (7 bases); 7: 12; 8: 8; 9: 28; 10: 66; …; up to 57.
2. **Phase F (flag),** in global order of (best malignant T2, number of hook qubits, n, depth, rate):
   - **Design rule.** Every hook qubit needs a free Willow neighbour in the chosen embedding. Embeddings were tried until the rule held; up to 60 stored embeddings per base.
   - **Flags.** Per hook qubit, the single Z flag (free neighbour, `R` in the preparation TICK, `CX q→f` at t1 < t2 with q only a CX control in between, `M f` in the final TICK + DETECTOR) whose slot pair covers the most hook events. Then flag pairs on two hooks. At most one valid candidate per flag group.
3. **VALID.**
   - `check_circuit` strict: nearest-neighbour, degree ≤ 4, no reuse in a TICK, strict readout with the new live rule and the final-layer condition;
   - `check_equivalence` (flags excluded from (iii));
   - verify() at max_fault_count 2 and 3.
4. **Outcome.**
   - Of the 34 bases tried, 27 failed the design rule (a hook qubit without a free neighbour) and 7 were flagged.
   - Of 51 flagged circuits, 20 were valid and 31 failed `check_circuit` (the run logged only the category "constraints", not which check failed). None failed the equivalence checker.

### The 20 valid candidates (ranked by malignant T at 2 faults, n_flags, added TICKs, malignant T at 3)

All candidates:
- have m = 1 root, ancilla qubit 0 at Willow (9, 9), measured `MRX` mid-circuit on **readout line 18** with no other qubit on that line;
- have n = 11 tree qubits (7 data + 4 ancillas) and fold depth 4;
- have 0 strict readout conflicts and 0 malignant T configurations at 1 fault.

Flags are written `q<control>->(r, c) t<t1>,<t2>`, where `k.5` is a new TICK after TICK k. Stim files: `results/option1/candNN.{inner,full}.stim`. Data: `results/option1_candidates.csv`. Bases: `results/option1_bases.csv`.

| rank | id | base | flags (n) | added TICKs | CX | max deg | TICKs | mal. T 1 / 2 / 3 | benign T 2 | mal. S 2 | T LER per kept shot, mfc 2 | mfc 3 | runtime |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 6 | q8->(7,10) t5,7.5 (1) | 1 | 22 | 4 | 13 | 0 / **6** / 633 | 33 | 0 | 1 in 1,781,499 | 1 in 1,524,994 | 0.09 s |
| 2 | 0 | 3 | q8->(7,10) t5,7.5 (1) | 1 | 22 | 4 | 13 | 0 / **6** / 728 | 35 | 0 | 1 in 1,767,523 | 1 in 1,487,885 | 0.10 s |
| 3 | 1 | 3 | q2->(10,10) t5,7.5 (1) | 1 | 22 | 3 | 13 | 0 / **6** / 728 | 35 | 0 | 1 in 1,767,524 | 1 in 1,491,007 | 0.09 s |
| 4 | 2 | 3 | both of the above (2) | 1 | 24 | 4 | 13 | 0 / **6** / 730 | 35 | 0 | **1 in 2,269,811** | 1 in 1,843,535 | 0.10 s |
| 5 | 4 | 21 | q9->(10,10) t4,8.5 (1) | 1 | 22 | 3 | 13 | 0 / 8 / 713 | 36 | 2 | 1 in 523,713 | 1 in 496,017 | 0.10 s |
| 6 | 5 | 21 | q3->(7,10) t5,7.5 (1) | 1 | 22 | 4 | 13 | 0 / 8 / 713 | 36 | 2 | 1 in 530,228 | 1 in 501,479 | 0.09 s |
| 7 | 6 | 21 | both of the above (2) | 2 | 24 | 4 | 14 | 0 / 8 / 715 | 36 | 2 | 1 in 502,229 | 1 in 470,715 | 0.10 s |
| 8 | 7 | 28 | q9->(6,8) t4,8.5 (1) | 1 | 22 | 3 | 13 | 0 / 9 / 781 | 36 | 2 | 1 in 490,093 | 1 in 464,572 | 0.09 s |
| 9 | 13 | 31 | q5->(8,7) t4,8.5 (1) | 1 | 22 | 3 | 13 | 0 / 9 / 801 | 37 | 2 | 1 in 392,078 | 1 in 373,234 | 0.09 s |
| 10 | 14 | 31 | q2->(7,10) t5,7.5 (1) | 1 | 22 | 3 | 13 | 0 / 9 / 801 | 37 | 2 | 1 in 429,522 | 1 in 407,304 | 0.09 s |
| 11 | 15 | 31 | q8->(10,10) t5,7.5 (1) | 1 | 22 | 3 | 13 | 0 / 9 / 801 | 37 | 2 | 1 in 413,758 | 1 in 392,864 | 0.09 s |
| 12 | 19 | 33 | q2->(7,10) t5,7.5 (1) | 1 | 22 | 4 | 13 | 0 / 9 / 820 | 37 | 3 | 1 in 378,284 | 1 in 359,989 | 0.09 s |
| 13 | 10 | 30 | q9->(6,8) t4,8.5 (1) | 1 | 22 | 3 | 13 | 0 / 9 / 862 | 38 | 2 | 1 in 402,586 | 1 in 382,318 | 0.10 s |
| 14 | 11 | 30 | q2->(10,10) t5,7.5 (1) | 1 | 22 | 3 | 13 | 0 / 9 / 862 | 38 | 2 | 1 in 429,523 | 1 in 406,142 | 0.10 s |
| 15 | 8 | 28 | q0->(9,10) t6.5,8.5 (1) | 2 | 22 | 4 | 14 | 0 / 9 / 725 | 33 | 2 | 1 in 410,447 | 1 in 387,579 | 0.10 s |
| 16 | 18 | 31 | q2->(7,10) t5,7.5; q8->(10,10) t5,7.5 (2) | 1 | 24 | 3 | 13 | 0 / 9 / 803 | 37 | 2 | 1 in 451,057 | 1 in 426,122 | 0.10 s |
| 17 | 9 | 28 | q9->(6,8) t4,8.5; q0->(9,10) t6.5,8.5 (2) | 2 | 24 | 4 | 14 | 0 / 9 / 727 | 33 | 2 | 1 in 456,097 | 1 in 429,447 | 0.10 s |
| 18 | 16 | 31 | q5->(8,7) t4,8.5; q2->(7,10) t5,7.5 (2) | 2 | 24 | 3 | 14 | 0 / 9 / 803 | 37 | 2 | 1 in 378,397 | 1 in 356,616 | 0.10 s |
| 19 | 17 | 31 | q5->(8,7) t4,8.5; q8->(10,10) t5,7.5 (2) | 2 | 24 | 3 | 14 | 0 / 9 / 803 | 37 | 2 | 1 in 366,130 | 1 in 345,526 | 0.10 s |
| 20 | 12 | 30 | q9->(6,8) t4,8.5; q2->(10,10) t5,7.5 (2) | 2 | 24 | 3 | 14 | 0 / 9 / 864 | 38 | 2 | 1 in 378,398 | 1 in 355,715 | 0.10 s |

Tree of the best base (base 6; node index + role + Willow position, `<p` = parent):
`0A(9,9) 1A(10,9)<0 2D(10,10)<1 3D(11,9)<1 4D(9,8)<0 5D(8,9)<0 6A(8,8)<5 7D(8,7)<6 8A(7,9)<5 9D(6,9)<8 10D(7,8)<8`.
Base 3 is the same shape with a different lower branch. Hook qubits of base 6: 1, 3, 5, 8, 10.

### What the search shows

- **The tree shape alone gives at most a 1-configuration gain over G4.** The best fold forest in the space has 6 malignant 2-fault T configurations (G4: 7, d3a6: 4). This holds with the code labelling optimised and the strict readout rule satisfied by construction.
  - Its rate at max_fault_count 2 (base 6 unflagged: 1 in 1,719,894) is **worse** than G4-CX's 1 in 2,421,930. Fewer malignant configurations does not mean less malignant weight.
- **The Z flags (first-ex.md definition, same control at t1 and t2) did not remove any malignant 2-fault configuration** in any of the 20 candidates.
  - Each candidate has exactly its base's count (6, 8 or 9). The flags change only the 3-fault counts (±2) and the weights; the best rate is 1 in 2,269,811 for candidate 2 with 2 flags, against 1 in 1,690,796 for its base.
  - The likely reason is visible in the data, though I did not prove it fault by fault. Each hook window runs from the fold through the unfold (e.g. TICKs 3–9 on qubit 8), across the CX in which the hook qubit is the *target* (it is collected by its parent).
  - A same-control Z flag must keep Z_q unchanged, so it cannot span that CX: the best slot pairs cover TICKs 5–7 of 3–9.
  - Each malignant fault class keeps undetected events outside the flagged interval, so the configuration survives.
  - In addition, every top base has 4–5 hook qubits, more than 2 flags can cover.
- **Strict readout is no longer the obstacle.** Rooting the fold at an ancilla whose r + c line holds nothing else (G4's trick) gives 0 conflicts with the new live rule. All 31 rejected flagged circuits failed a hardware constraint introduced by the *flag* placement (the bases themselves pass); which check failed was not logged.
- **The design rule bites.** 27 of the 34 best bases had a hook qubit with no free Willow neighbour in any stored embedding.

---

## E. Figures (`python -m nnflags.plots --only option1`, PNG 200 dpi, white background, Okabe–Ito colours with hatching/markers)

- `figures/option1_g4_extracted.png`:
  - (a) G4's extracted double check (CX form) at G4's Willow coordinates: data/ancillas, the parity qubits 9 and 6 on readout line 18, and the X-hook qubits 2, 4, 5, 9;
  - (b) the circuit in time (TICK diagram);
  - footnote with the rates.
- `figures/archive/option1_conflict_table.png`: task-A strict conflicts for d3a6 / d3a4 (min over all embeddings), G4 and G5, under the new rule, the new rule with the final layer checked, and the Step-3 rule.
- `figures/archive/option1_best_candidates.png`: the top 3 valid candidates (ids 3, 0, 1) on Willow, showing CX gates, flags with their CX, the parity qubit and its readout line, and hook qubits.
- `figures/archive/option1_malignant_comparison.png`: malignant T configurations at 2 and 3 faults for d3a6, d3a4, G4 (CX) and the top 5 candidates.

Older figures were not regenerated: they are tied to `results/step1.json`, computed under the Step-3 rule. `plots.py` still writes PNG only; its docstring, which said "and PDF", was corrected.

---

## Tests

- `logs/pytest_option1.log`: **78 passed**.
  - 37 old tests;
  - 22 in `test_live_rule.py`;
  - 14 in `test_equivalence.py`;
  - 5 in `test_search_option1.py`.
- **Expectations changed because of the new live rule** (details in RESULTS_g4.md):
  - 9 tests in `test_readout.py` now pin `live_rule="prep", final_layer="exempt"` explicitly, with unchanged expected pairs. They encode the Step-3 rule, where an R-reset idle ancilla is live.
  - `test_crumble_embed.py::test_z_reset_idle_refinement` now passes `z_reset_idle="live"` explicitly.

## Files

- **Code:**
  - new: `nnflags/live_rule_table.py`, `nnflags/g4.py`, `nnflags/equivalence.py`, `nnflags/search_option1.py`;
  - changed: `nnflags/constraints.py` (live rules, `final_layer_status`), `nnflags/embed_search.py` (rule-aware `readout_events`, `run(live_rule=, final_layer=, suffix=)`), `nnflags/plots.py` (Option-1 figures, `--only option1`).
- **Results:**
  - `results/live_rule_table.json`;
  - `results/g4_result.json`, `results/g4/*.stim`;
  - `results/option1_candidates.csv`, `results/option1_bases.csv`, `results/option1_screen.json` (screen cache: all 3,743 abstract bases), `results/option1_state.json`, `results/option1/cand00–19.{inner,full}.stim`.
- **Logs:** `logs/live_rule_table.log`, `logs/g4.log`, `logs/search_option1.log`, `logs/pytest_option1.log`, `logs/timing.txt`.

## Decisions made without you

1. **Live rule.**
   - Z-preserving single-qubit gates (I, Paulis, S, S_DAG) do not make a qubit live. You named only "H or two-qubit gate"; G4's `I[echo]` on the never-reset qubit 7 is such a gate.
   - RX/RY/MRX/MRY are live from the end of their TICK (RX = R + H).
2. **Final-layer condition.**
   - MX/MY in the final TICK count as "basis change before".
   - Resets after it are allowed (cliffordea's trailing reset).
   - A split final readout makes the final TICK non-exempt.
3. **G4 extraction.**
   - The double check is TICKs 31–50 plus the ancilla readout.
   - I placeholders were dropped (noise-equivalent, checked numerically).
   - `M 9 6` → `MR 9 6`, with G4's `R 9 6` kept.
   - `R 7` was added (G4 never resets qubit 7).
   - The ancilla readout was moved before T† (it commutes).
   - The primary comparison is the **CX form** (H frames absorbed, `MR;R` merged as in cliffordea's d3a4). The native CZ + H form is reported too.
   - `[conjugate]` is read as H_YZ, from the paper's T = e^{−iπσ_y/8} and the injection block. The paper text read does not define the tag. The result is the same in both T conventions.
4. **Search space.**
   - The space is G4-type forests with *ancilla* roots and a plain X-parity fold. It has no copy ancillas and no G4-style 6/7 gadget, which keeps it enumerable and well defined.
   - Roots are at G4's positions; fold depth ≤ 4; n ≤ 11.
   - For each abstract base the code labelling is optimised over all 210 classes.
   - One embedding per abstract base: the first one that satisfies the design rule.
5. **"Prefer 0 malignant" vs "stop at 20".**
   - All 3,743 abstract bases were screened first (cheap, ~0.4 s each). Flagging then ran in order of best malignant count, so the first 20 valid candidates come from the best bases.
   - At most one valid candidate per flag group (per hook qubit, per hook pair), to avoid 20 near-duplicates from one base.
   - Unflagged bases are not counted as candidates unless they have 0 malignant configurations; none does. They are recorded in `results/option1_bases.csv`.
6. **Hook-qubit definition.** A fault of data weight ≥ 2 in a malignant 2-fault T configuration. Its hook qubit is the qubit carrying its single-qubit X/Y events (or the X/Y parts of two-qubit events). Flag slots maximise the number of covered hook events.

## Open questions for you

1. **The same-control Z flag cannot cover a hook window that crosses the CX in which the hook qubit is a target**, and that is where the hook windows of these fold trees sit. Should the next step allow Chan et al.-style **two-control (ZZ) flags** between tree neighbours (as in d3a6f2), placed nearest-neighbour? Or should the flag be allowed to straddle the target CX with a correction?
2. Should the space include **copy ancillas** and G4's **Z-check gadget** (qubits 6/7, `MR 6` measuring Z7)? G4 uses both. With them, G4 itself (7 malignant configurations) is a member, but it fails the design rule (hooks 4, 5, 9 have no free neighbour).
3. Extend to fold depth 5 or n = 12–13 (d3a6 has 13 qubits)? The screen cache makes this resumable: `--nmax 12`.
4. The candidates with fewer malignant configurations (6) still have a **higher** rate than G4-CX (1 in 1.8 million vs 1 in 2.4 million). Which ranking do you prefer: configuration count (as instructed) or rate?
5. Some candidates (ranks 5–20) have **2–3 malignant 2-fault *S* configurations**, while all baselines have 0. Should S malignancy be a filter?

## cliffordea untouched

```
$ git -C cliffordea status --porcelain --ignored
(empty output, exit code 0)        # logs/cliffordea_check_option1_agent.txt is 0 bytes
$ git -C cliffordea rev-parse HEAD
27385c688ed40d595eab4e2378dccb5c4d32dd9a
```

cliffordea names used in this round (file:line in `cliffordea/cliffordea/…`, commit `27385c6`):
- `LogicalMeasurement.__init__` and its inner-circuit docstring: `enum/circuits/main.py:17`, `:42-54`;
- `find_data_indices` / `find_stabilizer_generators` / `find_logical_s_gate`: `enum/circuits/_base.py:4` / `:17` / `:43`;
- `uniformly_depolarize`: `enum/noise/main.py:9` (noiseless first/last TICK `:39-40`; M removes the noise `:83-88`);
- NoiseModel rules: `enum/noise/_noise.py:209-317`;
- `_TransversalGate` / `LogicalAnalyzer` (T pattern from LOGICAL_S): `accept/logical_analyzers.py:56`, `:153-189`;
- `CliffordLogicalAnalyzer`: `:224`;
- `FaultCombinator.get_kept_effects` / `index_to_events` / `basis`: `enum/combinators/fault_combinator.py:236` / `:374` / `:124`;
- `split_by_ticks`: `enum/circuit_tools.py:54`.
