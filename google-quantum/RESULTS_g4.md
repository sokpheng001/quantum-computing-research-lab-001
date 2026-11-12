# RESULTS — G4 fault distance and refined live rule (Option 1, tasks A and B)

Written on 2026-11-01 at 09:40 am KST, right after task B and before the Option-1 search (tasks C–E follow in `RESULTS_option1.md`).

## Headline

**Google's as-run double check (G4, Rosenfeld et al. arXiv:2512.13908 Fig. 2) has fault distance 2 in cliffordea, like d3a6 and d3a4.**
- It has **7 malignant 2-fault T configurations**.
- It has 0 malignant configurations at 0 and 1 faults, and 0 malignant S configurations up to 2 faults.

Settings: distance 3; cultivated states T and S; `enum.noise.uniformly_depolarize` (cliffordea `enum/noise/main.py:9`) at p = 0.001; `FaultCombinator.get_kept_effects`; `CliffordLogicalAnalyzer`. Rates are cliffordea's `error_rates_per_kept_shot`, truncated at max_fault_count.

| circuit | data + ancillas | 2q gates | TICKs (inner) | faults | T malignant k=0/1/2 | T benign k=0/1/2 | T malignant k=3 | T benign k=3 | S malignant k≤2 / k=3 | T logical error per kept shot, p = 0.001 (max_fault_count 2) | same (max_fault_count 3) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d3a6 (cliffordea `DoubleCheck(3, 6)`) | 7 + 6 | 24 CX | 12 | 158 | 0 / 0 / **4** | 1 / 2 / 37 | 415 | 1,436 | 0 / 82 | 0.000021 % = **1 in 4,760,490** | 1 in 3,568,591 |
| d3a4 (cliffordea `DoubleCheck(3, 4)` = Chan et al. Sec. 5 link) | 7 + 4 | 20 CX | 11 | 195 | 0 / 0 / **12** | 1 / 7 / 129 | 1,619 | 4,013 | 0 / 442 | 0.000028 % = **1 in 3,583,893** | 1 in 3,184,814 |
| **G4 extracted, CX form** (primary, comparable to d3a6) | 7 + 5 | 24 CX | 12 | 154 | 0 / 0 / **7** | 1 / 2 / 41 | 671 | 1,598 | 0 / 162 | 0.000041 % = **1 in 2,421,930** | 1 in 2,054,158 |
| G4 extracted, native CZ + H (G4's own TICKs) | 7 + 5 | 24 CZ | 24 | 154 | 0 / 0 / **7** | 1 / 2 / 41 | 671 | 1,598 | 0 / 162 | 0.00022 % = **1 in 447,652** | 1 in 314,362 |
| G4 CX form, as-run T_y frame | 7 + 5 | 24 CX | 12 | 154 | 0 / 0 / 7 | 1 / 2 / 41 | 671 | 1,598 | 0 / 162 | 1 in 2,421,930 | 1 in 2,054,637 |
| G4 native, as-run T_y frame | 7 + 5 | 24 CZ | 24 | 154 | 0 / 0 / 7 | 1 / 2 / 41 | 671 | 1,598 | 0 / 162 | 1 in 447,652 | 1 in 314,648 |
| G4 native, I placeholders kept (check) | 7 + 5 | 24 CZ | 24 | 154 | 0 / 0 / 7 | 1 / 2 / 41 | 671 | 1,598 | 0 / 162 | 1 in 447,652 | 1 in 314,362 |

- **Fault distance = 2 in every variant.** The variants agree configuration for configuration at k ≤ 3; only the weights differ.
- **CX vs native.** The native circuit has 12 extra H-only TICKs. They add idle and H noise, which is why its rate is about 5× higher at the same configuration counts. Use the CX row to compare with d3a6/d3a4 (same gate set and conventions). The native row is the hardware-like TICK structure under the same uniform noise model.
- **Ranking at p = 0.001, max_fault_count 2.** G4-CX (1 in 2.4 million) is worse than d3a6 (1 in 4.8 million) and d3a4 (1 in 3.6 million). It has fewer malignant configurations than d3a4 (7 vs 12) but larger malignant weight.
- Runtime: under 0.1 s per verify() call, 4 s for the whole script. Code: `nnflags/g4.py` (`python -m nnflags.g4 --max3`). Log: `logs/g4.log`. Data: `results/g4_result.json`. Stim files: `results/g4/*.{inner,full}.stim`.

### The 7 malignant 2-fault T configurations (G4 CX form; TICK numbers of the inner circuit)

TICK 1 is the RX/R preparation, TICKs 2–5 the fold, TICK 6 `MRX 9 / MR 6`, TICKs 7–10 the unfold, TICK 11 the ancilla readout. Each configuration pairs an **X error** on qubit 2, 4, 5 or 9 with a Y/Z error at the last unfold layers:

| fault indices | X-type hook | partner |
|---|---|---|
| (58, 120) | X on data 5 (TICKs 3–9, e.g. after CX 5→4 / 5→6) | Y on data 8 (TICKs 8–11) |
| (47, 124) | X on ancilla 4 (TICKs 3–6) | Z8·X9 at CX 9→8 (TICK 8) |
| (8, 129) | X on data 2 (TICK 1 idle, or TICKs 10–11) | Y3·X4 at CX 4→3 (TICK 9) |
| (8, 140) | X on data 2 (as above) | X9·Y10 at CX 9→10 (TICK 9) |
| (47, 152) | X on ancilla 4 (TICKs 3–6) | Y on data 2 (TICKs 10–11) |
| (67, 152) | X on ancilla 9 (TICKs 3–4) | Y on data 2 (TICKs 10–11) |
| (117, 152) | X on ancilla 9 (TICKs 8–9) | Y on data 2 (TICKs 10–11) |

**X-hook qubits of G4: 2, 4, 5, 9.** Full event lists: `results/g4_result.json` → `primary_malignant_T_events`.

---

## B. How the double check was extracted from G4

### What G4 is

`nnflags/data/google_circuits/rosenfeld2512_G4.stim` is the complete Fig. 2 experiment at Willow coordinates (12 qubits). It uses CZ + H, Z-basis M and R, and no MPP; the non-Clifford gates appear as tagged identities. TICK map (0-based, `split_by_ticks`):

| G4 TICKs | content |
|---|---|
| 0–3 | injection on qubit 5: `H_YZ[conjugate] S[injection] H_YZ[conjugate]` |
| 4–25 | encoding into the colour code; TICK 25 `M 4 1 6 9` (encoding checks) |
| 26 | `R 4 1 9 6` |
| 27–30 | **transversal T** on data 3 0 8 5 11 2 10: `I[conjugate] I[echo] I[T_gate] I[conjugate]` |
| **31–39** | **fold** (H / CZ layers) |
| **40, 41** | **`M 9 6`** (mid-check measurement), `R 9 6` |
| **42–50** | **unfold**: time reverse of 31–39, except that the H on ancillas 1 and 4 that opens the fold is applied at TICK 55 |
| 51–54 | **transversal T†**: `I[conjugate] I[echo] I[T_dagger_gate] I[conjugate]` |
| 55, 56 | H on all qubits but 7; M on all 12 (destructive readout) |

- **Data** = the T-gate targets 0, 2, 3, 5, 8, 10, 11. **Ancillas** = 1, 4, 6, 7, 9.
- **The double check** = TICKs 31–50, plus the ancilla part of the readout (TICKs 55–56). This is "the inner circuit within the two layers of T gates" in cliffordea's sense (`enum/circuits/main.py:42`).
- **Paper reading** (Rosenfeld et al., Sec. I, quoted by a helper agent that read arXiv HTML v1):
  - "the H^L gate is decomposed transversally onto each physical qubit as H^ = T^† X^ T^, where T^ ≡ e^{−iπσ_y/8} and T^† are applied non-conditionally, leaving the conditional X_L measurement as the main task."
  - So `[conjugate]` is read as the H_YZ basis change that turns the Z rotation into this Y rotation. The same tag sits around `S[injection]` at TICKs 0–2.
  - The paper does not define the tag in the text that was read; this reading is an inference and is marked as such.

### Conversion steps (every step; nothing else was changed)

1. **TICK 0:** G4's QUBIT_COORDS, and the noiseless cliffordea marker `MPP X3*X0*X8*X5*X11*X2*X10`. It defines DATA_INDICES (`_base.py:4`); the logical check is compared against it (`main.py:43-45`).
2. **TICK 1:** `R 4 1 9 6 7`. This is G4's TICK 26 plus **`R 7`**. G4 never resets qubit 7: it is in |0⟩ from the start of the experiment. The simulation confirms ⟨Z7⟩ = +1 at TICK 31. The inner circuit starts from scratch, so it needs the explicit reset.
3. **TICKs 2–21 = G4 TICKs 31–50, op for op.** Checked (`native_ticks_equal_g4_31_50 = true`). Two changes:
   - The identity placeholders `I[echo]` / `I[conjugate]` are dropped. cliffordea's noise model gives an `I` gate and an idle qubit the same DEPOLARIZE1(p) (`enum/noise/_noise.py:278-317`). Checked numerically: the "I placeholders kept" row is identical.
   - **`M 9 6` → `MR 9 6`**, because cliffordea requires MR for a measured ancilla that is used again (`main.py:46-50`; with plain M its noise would be switched off, `noise/main.py:83-88`). G4's following `R 9 6` TICK is **kept**, so the TICK structure is G4's.
4. **Ancilla readout:** `H 4 1 9 6`, then `M 4 1 9 6 7`. This is G4 TICKs 55–56 restricted to the ancillas. It commutes with the T† on the data, so it is placed right after the unfold, as in cliffordea's own inner circuits.
5. **Detectors:** G4's, restricted to these measurements:
   - forward check `M9 ⊕ MPP` (G4: `M9` alone, because its Clifford stand-in state is |+_L⟩, so ⟨X_L⟩ = +1 is known there);
   - `M6`;
   - final `M4`, `M1`, `M9 ⊕ M9mid` (the time-reversed check), `M6`, `M7`.
6. **Trailing `R 1 4 6 7 9`** (`main.py:51-53`). Result: **native** inner circuit (CZ + H, 24 TICKs).
7. **CZ + H → CX** (`equivalence.absorb_hadamards`, generic):
   - Every H is pushed into a per-qubit frame bit (actual state = H^h|φ⟩).
   - A CZ with exactly one framed qubit becomes a CX; R/M on a framed qubit become RX/MX.
   - H-only TICKs disappear, and `MR q; TICK; R q` collapses to one MR/MRX TICK. cliffordea's d3a4 uses the same convention for this experiment (`MX 8; TICK; RX 8` → `MRX 8`).
   - The frame after each ancilla preparation was chosen by exhaustive search to make every two-qubit gate a CX. Result: **0 non-CX gates**. Ancillas 1, 4, 6, 9 are RX-prepared and 7 is R-prepared.
   - Result (**CX form**, 12 TICKs, the same count as d3a6):

   ```
   MPP X3*X0*X8*X5*X11*X2*X10 | RX 4 1 9 6; R 7
   CX 4 0 1 5 9 11 6 2 | CX 4 3 5 6 9 10 | CX 5 4 9 8 6 7 | CX 9 5 7 6
   MRX 9; MR 6   (DETECTOR MRX9 ⊕ MPP; DETECTOR MR6)
   CX 9 5 7 6 | CX 5 4 9 8 6 7 | CX 4 3 5 6 9 10 | CX 4 0 1 5 9 11 6 2
   MX 4 1 9 6; M 7 | R 1 4 6 7 9
   ```

   Note that data qubits 5 and 8 are internal nodes of G4's fold tree (CX 5→6, 5→4, 9→5, 9→8). The X parity ends on ancilla 9; ancilla 6 reads Z7 (see below).
8. **Full circuit** (`g4.full_for`), laid out like cliffordea's bundled `full.stim`:
   - MPP Y_L and MPP X/Z plaquettes;
   - logical S† (S on 3 8 11, S_DAG on 0 2 5 10);
   - the inner body;
   - logical S (S on 0 2 5 10, S_DAG on 3 8 11) after the last unitary;
   - final MPP checks, whose detectors are solved with stim flows, and the Y_L observable.

   cliffordea reads only its MPPs and its 3rd/4th S instructions (`_base.py:17-71`). All its detectors are deterministic.
9. **T-gate convention.** cliffordea's analyzer pushes the data effect through T on the logical-S "majority" sublattice and T† elsewhere, i.e. Z rotations (`accept/logical_analyzers.py:178-189`). G4 uses a uniform T_y.
   - The as-run frame is a noiseless W = H_NYZ (majority) / H_YZ (minority), with W T_y† W† = T_z / T_z†. W† goes after the MPP marker and W into the trailing reset TICK. Both TICKs are noiseless (`noise/main.py:39-40`).
   - This maps G4's protocol exactly onto cliffordea's.
   - **Result: identical configuration counts, and an identical rate at max_fault_count 2.** At max_fault_count 3 the rates differ in the 4th digit: 1 in 2,054,637 vs 1 in 2,054,158.
   - Sensitivity check: a *wrong* frame (H or S on all data) changes the answer drastically (29–36 malignant 2-fault T configurations). So the frame is not ignored, and G4's result does not depend on the T_y/T_z convention.

### Faithfulness proof (`g4.faithfulness()`, all in `results/g4_result.json`)

| check | result |
|---|---|
| G4's state at TICK 31 (Clifford stand-in, T → I, stim TableauSimulator): ⟨X_P⟩ = ⟨Z_P⟩ = +1 for P = {0,3,10,11}, {2,3,8,10}, {5,8,10,11}; ⟨X_L⟩ = +1; ⟨Z7⟩ = ⟨Z1⟩ = ⟨Z4⟩ = ⟨Z6⟩ = ⟨Z9⟩ = +1 | **yes**: standard d=3 colour code in the standard frame, ancillas in \|0⟩ |
| cliffordea derivations on the extracted circuits (through verify's loader) | DATA_INDICES (0, 2, 3, 5, 8, 10, 11); stabiliser supports {0,3,10,11}, {2,3,8,10}, {5,8,10,11}; LOGICAL_S = `S 0 2 5 10` / `S_DAG 3 8 11`; they match the simulated state |
| same code as d3a6 up to relabelling (supports **and** logical-S sublattice) | **yes**: G4 → d3a6 data map {0→0, 2→7, 3→3, 5→11, 8→10, 10→5, 11→8} |
| what the mid measurements measure (fold tableau, Heisenberg) | **M 9 measures X_L** (·Z4 Z6 Z9 on fresh ancillas = +1): the forward H_XY check. **M 6 measures Z7**, a flag-like check of ancilla 7 |
| unfold vs fold (G4 TICKs 42–50 vs 31–39) | U_unfold · U_fold = H on 1, 4, 6, 9, i.e. the exact inverse up to the ancilla basis changes absorbed into the RX preparation and MX readout |
| same action on the code space: stim flows of **G4's own segment** (TICKs 26–56 minus the data readout), of the native extraction, and of the CX extraction | identical in all three: `X_L → rec` (measured); X_q → X_q for all 7 data; all 6 X/Z plaquettes → themselves; Z_aZ_b → Z_aZ_b (commutant of X_L preserved); **Z_L → Z_L impossible**. So each acts on the data as the projective X_L measurement |
| determinism (stim) | inner native, inner CX, both full circuits, and the as-run variants: all deterministic |
| equivalence checker (task C) on both extractions | (i) code, (ii) check, (iii) reverse, (iv) deterministic: all pass |

### Hardware view of the extracted circuits at G4's real coordinates (new live rule)

- Neighbour, degree (max 4) and reuse checks: 0 violations. Strict readout with the final layer exempt (its condition holds): 0.
- With the final layer *checked*: 2 conflicts, `M 7` (TICK 11 of the CX form) vs data 10 and 11 on line 19. In G4 itself those data are read out in the same TICK, so G4 has 0 either way.

---

## A. Refined live rule and the final-layer condition (`nnflags/constraints.py`)

### Rule (new default `live_rule="gate"`, user decision 2)

- A qubit idling in a Z eigenstate is **not live**. This covers the start of the circuit, after `R`, after `MR` (it is in |0⟩), and after a measurement without reset (M/MX/MY end its use).
- It **becomes live at its first two-qubit gate, or at its first single-qubit gate that does not keep the Z basis** (H, H_YZ, SQRT_X, …). `I`, `X`, `Y`, `Z`, `S` and `S_DAG` keep it dormant (`keeps_z_basis`, decided with stim tableaux). It stays live until its measurement.
- **RX / RY / MRX / MRY.** On hardware RX = R then H, so the qubit is **live from the end of that TICK**. During the TICK itself it is busy and so not a victim, as before.
- **Data qubits** (MPP targets) are live from the start: they hold the injected state.
- **Old variants kept:**
  - `live_rule="prep"` is the Step-3 default (live from any preparation; R/MR keep the qubit live).
  - `live_rule="prep_zdormant"` is the Step-3 option `z_reset_idle="not_live"`. Old callers that pass `z_reset_idle=` keep its old meaning.

### Final-layer condition (new default `final_layer="auto"`, user decision 3)

- `final_layer_status(circuit)`: the last TICK containing a measurement is exempt **only if** both of these hold:
  - (a) no unitary gate, `I` included, occurs in that TICK or later, so basis changes happen before it. Resets after it are allowed (cliffordea's trailing reset). MX/MY in the final TICK count as "basis change before" (MX = H then M).
  - (b) no other measurement happens after the last unitary gate, i.e. the final readout is one TICK (simultaneous).
- Otherwise the final layer is checked like any other.
- `final_layer="exempt"` (unconditional, Step 3) and `"check"` are still available.
- d3a6, d3a4, G4 and G5 all satisfy the condition.

### Strict conflicts under the new rule (Willow; d3a6/d3a4: every injective nearest-neighbour embedding; G4/G5: real coordinates)

| circuit | placements | **new rule** (gate + auto final layer): min / histogram | new rule, final layer checked | old rule (prep + exempt, Step 3) | old + z-reset dormant |
|---|---|---|---|---|---|
| d3a6 | 182,968 embeddings | **1** / 1: 47,424 · 2: 135,544 | 4 / 4: 29,220 · 5: 20,816 · 6: 18,908 · 7: 39,280 · 8: 34,840 · 9: 27,232 · 10: 9,504 · 11: 3,168 | 1 / same histogram | 1 / same |
| d3a4 | 38,640 embeddings | **1** / 1: 38,640 | 1 / 1: 38,640 | 1 / same | 1 / same |
| G4 (Fig. 2, as run) | real coordinates | **0** | 0 | 0 | 0 |
| G5 (Fig. 3, as run) | real coordinates | **0** | 0 | 12 | 0 |

- **d3a6 and d3a4 do not change.** Their victims (MRX 5 vs 8/10/12/1/2/7; MX 8 vs 2/7/3) are data qubits or **RX-prepared** ancillas, which are live under the new rule too.
- **G5 drops from 12 to 0.** Its 12 old conflicts were all ancilla 4 idling in |0⟩ after `R 4`.
- Code: `nnflags/live_rule_table.py`. Log: `logs/live_rule_table.log`. Data: `results/live_rule_table.json`. The fast counter was cross-checked against `readout_violations` on a sample of embeddings for every variant.

### Tests

- New file `nnflags/tests/test_live_rule.py` has 22 tests: the defaults; |0⟩ idling; two-qubit gates; Z-preserving vs basis-changing single-qubit gates (parametrised); RX = R + H; MR vs MRX; no-reset qubits; the final-layer condition (ok, gate in/after, split); d3a6 unchanged; and G4/G5 at real coordinates (0, with 12 for G5 under the old rule).
- Full suite: **59 passed** (37 old + 22 new).
- **Existing tests whose expectation changed, and why:**
  - `test_readout.py`: 8 tests (`test_first_gate_prepares`, `test_mr_keeps_live_and_ancilla_vs_ancilla`, `test_m_without_reset_ends_liveness_until_next_reset`, `test_measured_qubit_not_its_own_victim_and_simultaneous_readout`, `test_reset_in_same_tick_is_not_a_victim`, `test_other_line_never_a_victim`, `test_data_measured_without_reset_is_dead_until_prepared`, `test_check_circuit_modes`).
    - They encode the Step-3 rule (an R-reset ancilla is live). Under the new default, an R-reset idle ancilla is not a victim. Some of these toy circuits also end in two measurement-only TICKs, which the new final-layer condition treats as a split final layer.
    - They now pin `live_rule="prep", final_layer="exempt"` explicitly through the file's helper, with **unchanged expected pairs**. `test_d3a6_strict_native` was pinned the same way; it would also pass under the new default.
  - `test_crumble_embed.py::test_z_reset_idle_refinement`: its "strict" reference now passes `z_reset_idle="live"` (= old rule) explicitly. A new assertion checks that the new default equals the old refinement on that circuit.
