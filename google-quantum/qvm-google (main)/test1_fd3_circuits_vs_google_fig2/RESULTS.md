# RESULTS — our double checks in Google's Quantum Virtual Machine for Willow

Run unattended on 2026-11-01, 4:10 pm – 5:22 pm KST, with Google's own software: cirq 1.7.0, cirq_google 1.7.0, qsimcirq 0.22.1, processor `willow_pink` (`willow_pink_d7v1-2024_08_16`, the same Willow snapshot as our layout). Earlier results files are untouched. Everything new is in `qvm-google/`.

*Moved on 2026-11-02 into `qvm-google (main)/test1_fd3_circuits_vs_google_fig2/` (this report was `RESULTS_qvm.md`). Paths below are relative to this folder; the shared engine is `../qvm_willow.py`.*

*Circuit layout figure: `figures/zz_best_circuits.png` (success03 and two other fault-distance-3 circuits on the Willow grid; code `nnflags/plots.py --only zz`, moved here from `figures/archive/`).*

## Answer

1. **Device validation.** Google's Willow device model accepts success03 without changes, at its own Willow positions. The only conversion step is a gate decomposition: H is written as the device's native `PhasedXZGate`. The device accepts `cirq.H` as well.
2. **Real T gates.** With real `cirq.T` / `T**-1` gates and no noise, every detector is 0 and the output is the encoded T state to within 1 part in 10 trillion.
   - Injecting all 1,301 single error events and all 14,028 two-fault configurations of success03 reproduces cliffordea's classification exactly. None of them is kept with a corrupted state.
   - Across all five circuits, every one of 73,261 injected configurations agrees with cliffordea, including all 11 malignant 2-fault configurations of G4 and d3a6.
3. **Noisy QVM (Google's Willow noise model, 8,000,000 shots).** success03 keeps **65.48 % ± 0.02 %** of shots.
   - Its T error per kept code-space shot is **1 in 78,277** (56 events; 95 % CI 1 in 103,625 to 1 in 60,279).
   - G4, Google's own as-run check, gets 1 in 17,926 (4,000,000 shots). success03 is therefore 4.4 times better, the same factor as our stim calibration-model estimate.

## Status

| experiment | status | one line |
|---|---|---|
| E1 conversion + device validation | **PASS (5 / 5)** | stim → cirq on `GridQubit(row, col)`: CZ + `PhasedXZGate` + measure + reset + virtual-Z T. Round trip back to stim is identical instruction for instruction; stabiliser flows and detector error model are identical. `willow_pink` `validate_circuit` passes for all 5 circuits, with H as `cirq.H` and as `PhasedXZGate`. Nothing was rejected. |
| E2 real-T correctness (noiseless qsim) | **PASS (5 / 5)** | 2,000 shots per circuit: 0 detector fires and the ideal logical H_XY decode is +1 in every shot. State-vector fidelity with the encoded T state ≥ 1 − 1 in 14 trillion (worst 1 − 0.00000000000007). Negative control (T on every data qubit) is caught: about 50 % acceptance, fidelity 0.5. |
| E3 fault injection vs cliffordea | **PASS: 73,261 / 73,261 agree, 0 disagreements** | All single error events plus all 2-fault configurations, exhaustively, for every circuit (more than the requested sample). The seeded 2,000-pair samples are subsets. Kept / rejected, malignant / benign, detector signature and accept probability all agree. |
| E4 noisy QVM | **DONE** | 18,000,000 shots in 50 min 18 s of sampling wall time (budget 2 h). Every acceptance has relative s.e. ≤ 0.051 % (target < 1 %). QVM acceptance is within 1.1 percentage points of our stim calibration model. Logical error rates agree with the stim enumeration within the 95 % CIs. |
| Tests | **PASS** | `../tests`: **16 passed** (5.9 s). `nnflags/tests`: **102 passed** (49.8 s). |
| cliffordea untouched | **PASS** | `git -C cliffordea status --porcelain --ignored`: empty output, exit 0 (`logs/cliffordea_check.txt`, 0 bytes); HEAD 27385c688ed40d595eab4e2378dccb5c4d32dd9a. |

## Circuits

| name | role | source | Willow placement | moments (device circuit) | gates in the device circuit |
|---|---|---|---|---|---|
| success03 | **main**: ZZ + X flag, fault distance 3 | `results/zz/success03.{full,inner}.stim` (CX form) → `willow_noise.cx_to_native` | own QUBIT_COORDS | 31 | 26 CZ, 38 PhasedXZ (H), 7 measure, 7 reset, 14 T / T⁻¹ |
| success04 | 2nd best ZZ success (T error per kept shot, mfc 3, CX form) | `results/zz/success04.*` | own QUBIT_COORDS | 32 | 26 CZ, 38 PhasedXZ, 7 / 7, 14 T |
| success00 | 3rd best ZZ success | `results/zz/success00.*` | own QUBIT_COORDS | 31 | 26 CZ, 38 PhasedXZ, 7 / 7, 14 T |
| G4 | hardware reference: Google's as-run double check | `results/g4/G4-native_CZH.{full,inner}.stim` (its own native CZ + H TICKs, cliffordea T frame) | its real coordinates | 26 | 24 CZ, 42 PhasedXZ, 7 measure, 9 reset, 14 T |
| d3a6 | **what if**: breaks the strict readout rule | cliffordea bundled `DoubleCheck(3, 6)` → `cx_to_native` | `results/embed_search_d3a6.json` min-conflict embedding (1 readout conflict) | 24 | 24 CZ, 42 PhasedXZ, 7 / 7, 14 T |

- **Same circuits as the comparison round.** The native circuits are identical to `results/willow_noise/<name>.native.inner.stim` (checked in E1).
- **The strict readout rule is not part of cirq's device model.** `GridDevice.validate_circuit` checks only gates, qubits and couplers (`cirq_google/devices/grid_device.py:686-753`), so d3a6 passes it.
  - nnflags' own check (`constraints.check_circuit`: strict readout, `live_rule="gate"`, `final_layer="auto"`) still reports **1 readout violation for d3a6** and none for the other four.

## Method

### What was read in cirq_google, and used (paths under `.venv/lib/python3.12/site-packages/`)

- `cirq_google/engine/virtual_engine_factory.py`:
  - `MOST_RECENT_TEMPLATES` / `MEDIAN_CALIBRATIONS` `:44-54`. `willow_pink` maps to the device spec `willow_pink_d7v1-2024_08_16_device_spec_for_grid_device.proto.txt` and the calibration `willow_pink_d7v1-2024_08_16_calibration.json`.
  - `ZPHASE_DATA` `:62` covers rainbow / weber only.
  - `create_device_from_processor_id` `:346-357` → `GridDevice.from_proto`.
  - `load_median_device_calibration` `:141-168`.
  - `load_device_noise_properties` `:116-138`: for willow_pink the gate times come from the device (`:135`, `extract_gate_times_ns_from_device` `:471-505`), and there is no Z-phase data (`:131`).
  - `create_default_noisy_quantum_virtual_machine` `:427-467`: qsim simulator with `noise=NoiseModelFromGoogleNoiseProperties(load_device_noise_properties(...))` (`:452-457`), wrapped in a `SimulatedLocalProcessor` / `SimulatedLocalEngine` (`:460-468`).
- `cirq_google/engine/simulated_local_processor.py:105-107` and `validating_sampler.py:54-70`: every circuit run through the QVM is first checked by `device.validate_circuit`.
- `cirq_google/engine/calibration_to_noise_properties.py:93-226`: calibration → `GoogleNoiseProperties` (T1, Tphi, RB Pauli error, XEB Pauli error, p00 / p11, θ / φ entangler errors).
- `cirq_google/devices/google_noise_properties.py`:
  - `:191-193`: the 1q gates that receive gate error are ZPowGate, PhasedXZGate, MeasurementGate and ResetChannel.
  - `:209-239`: the coherent entangling part is subtracted from the CZ depolarisation.
  - `:241-250`: a PhasedFSim error gate is inserted after each CZ.
  - `:312-313`: a ZPowGate without `PhysicalZTag` is virtual, i.e. noiseless.
- `cirq/devices/superconducting_qubits_noise_properties.py:130-192` (thermal, depolarising, readout channels), `cirq/devices/noise_properties.py:76-133` (`noisy_moments`), `cirq/devices/thermal_noise_model.py:264-314` (per-moment idle / gate decoherence).
- `qsimcirq/qsim_simulator.py:254-258`: qsim applies `noise.noisy_moments(program, sorted(all_qubits))`.

### Conversion (E1)

- **Source.** Native CZ + H stim circuit (cliffordea layout).
  - TICK 0 (cliffordea's noiseless `MPP` marker of X^⊗7) and the last TICK (cliffordea's noiseless trailing ancilla reset) are not hardware operations, so they are dropped.
  - The detector that uses the MPP record keeps its other records. The MPP value is +1 deterministically for the ideal input (checked: ⟨X^⊗7⟩ = +1 after the T† layer).
- **Mapping:**
  - qubit i → `cirq.GridQubit(row, col)` of its Willow position;
  - `H` → `PhasedXZGate(axis_phase_exponent=-0.5, x_exponent=0.5, z_exponent=1)`, equal to H up to global phase;
  - `CZ` → `cirq.CZ`; `R` → `cirq.ResetChannel`; `M` → `cirq.measure` (one key per record);
  - `MR` → a measure moment followed by a reset moment.
- **T layers.** `cirq.T` / `cirq.T**-1` on the data qubits, by cliffordea's `LOGICAL_S` sublattices: T on the "S" (majority) targets, T† on the "S_DAG" (minority) targets. They are virtual Z gates on Willow.
- **Faithfulness checks** (`results/e1.json`):
  1. `PhasedXZGate` = H up to global phase.
  2. The cirq circuit converted back to stim (measure + reset → MR) is identical, TICK by TICK, to the native stim circuit.
  3. The round-tripped circuit, with the detectors put back, has exactly the same stabiliser flows (`has_all_flows` both ways), deterministic detectors, and an identical `uniformly_depolarize` detector error model.
  4. All CZ pairs are on device couplers (13 / 13, 13 / 13, 13 / 13, 11 / 11, 12 / 12).

### Protocol simulated (E2 – E4)

- **Prepare the encoded T state |T_L⟩** ideally (noiseless), in cliffordea's own frame:
  - the unencoded logical qubit is put in T·H|0⟩, the +1 eigenstate of (X + Y)/√2 (`LOGICAL_COEFFICIENTS['T']`, `accept/logical_analyzers.py:42`);
  - then cliffordea's encoder tableau (`CliffordLogicalAnalyzer.encoder`, `:281-287, 307-345`) is applied, converted to cirq gates;
  - check: ⟨Π_code⟩ = 1.
- **Device circuit** (validated; noisy in E4): T_L† layer → double check → T_L layer, with real T gates.
- **Ideal decode** (noiseless): inverse encoder, then T†·H on the logical qubit, then Z measurement of the 7 data qubits.
  - Bits 0–5 are the 6 stabilisers (0 = +1). Bit 6 is the logical H_XY (0 = T state).
  - This is the "noiseless final stabiliser postselection + logical check" of cliffordea's `CliffordLogicalAnalyzer`.
- **Why not "|+_L⟩ then the T pattern".**
  - The transversal T pattern is not a logical gate of the d = 3 colour code: T_pattern|+_L⟩ has only **56.25 %** weight in the code space (measured).
  - cliffordea's analyzer treats the state after the second T layer as the encoded T state in the code space. So the state entering the double check is T_pattern†|T_L⟩, which is outside the code space (also 56.25 %) but is an exact +1 eigenstate of X^⊗7. This is what the MPP marker asserts.
  - A first E2 attempt with the |+_L⟩ variant showed this, and the method was corrected before any reported run.

## E1 — conversion and device validation

Run 4:10 pm KST; 0.3 s. Data: `results/e1.json`. Command: `qvm_willow.py e1`.

| circuit | round trip identical | flows equal | detectors deterministic | DEM identical | `validate_circuit`, H as `cirq.H` | `validate_circuit`, H as `PhasedXZGate` (used) | CZ pairs on couplers | nnflags strict readout rule |
|---|---|---|---|---|---|---|---|---|
| success03 | yes | yes | yes | yes | PASS | PASS | 13 / 13 | 0 violations |
| success04 | yes | yes | yes | yes | PASS | PASS | 13 / 13 | 0 violations |
| success00 | yes | yes | yes | yes | PASS | PASS | 13 / 13 | 0 violations |
| G4 | yes | yes | yes | yes | PASS | PASS | 11 / 11 | 0 violations |
| d3a6 (what if) | yes | yes | yes | yes | PASS | PASS | 12 / 12 | **1 violation** |

- **Rejected operations:** none.
- **Changes made:** only the H → `PhasedXZGate` decomposition. It is not needed for validation; it is needed so that Google's noise model attaches the calibrated 1q gate error (an `HPowGate` gets no gate error in that model, `google_noise_properties.py:191-193`).
- **Negative test** (`test_device_rejects_a_cz_off_coupler`): a CZ to a non-neighbour is rejected by the same device.

## E2 — real-T correctness, no noise (qsim)

Run 4:12 pm KST; 29.9 s. Data: `results/e2.json`.

Settings:
- qsimcirq `QSimSimulator`, 1 thread, seed 2026;
- 2,000 shots per circuit for the detectors and for the ideal decode;
- 5 state-vector trajectories (seeds 0–4) for the fidelity, plus 1 trajectory of `cirq.Simulator` (complex128) as a cross-check.

| circuit | detector fires / 2,000 shots × 7 detectors | ideal decode ≠ T state / 2,000 | worst 1 − fidelity with \|T_L⟩ (qsim, 5 seeds) | cirq.Simulator fidelity | control: uniform T on all data, acceptance / fidelity |
|---|---|---|---|---|---|
| success03 | 0 | 0 | 0.000000000000040 | 1.0 | 49.95 % / 0.50 |
| success04 | 0 | 0 | 0.000000000000042 | 1.0 | 49.95 % / 0.50 |
| success00 | 0 | 0 | 0.000000000000042 | 1.0 | 49.10 % / 0.50 |
| G4 | 0 | 0 | 0.000000000000071 | 1.0 | 49.95 % / 0.50 |
| d3a6 | 0 | 0 | 0.000000000000056 | 1.0 | 49.90 % / 0.00 |

- **Exact result.** Every detector is 0 and the output is the T state: fidelity 1 to within 1 part in 10 trillion, which is floating-point rounding.
- **Negative control.** Applying T† / T to every data qubit (ignoring the sublattices) makes the first check fire in about half the shots. So the test can distinguish the right T pattern from a wrong one.

## E3 — fault injection with real T gates

Run 4:24 – 4:28 pm KST; 237 s on 12 processes. Data: `results/e3.json` (per design: `results/e3_parts/`). Log: `logs/e3.log`.

**Settings:**
- **cliffordea side.**
  - Faults come from `FaultCombinator(uniformly_depolarize(INNER_CIRCUIT, 0.001))` on the **native circuit that is actually run** (loaded through `nnflags.verify.load_measurement` with the design's full circuit).
  - The classification comes from `get_kept_effects(CliffordLogicalAnalyzer, max_fault_count=2, ("T",))`: kept = listed with accept > 0; malignant = fidelity ≠ 1.
- **Injected events.**
  - Each fault index is realised by its error events from `FaultCombinator.index_to_events`.
  - Pauli events (X / Y / Z_ERROR, two-qubit "E") are inserted as explicit `cirq.X/Y/Z` after all operations of their TICK, where cliffordea places noise.
  - Measurement-flip events flip the recorded bit classically.
- **Real-T side.**
  - qsim `run` (3 repetitions, to check that the detectors are deterministic) plus qsim `simulate` for the final state, on the full real-T circuit (ideal |T_L⟩ → T† layer → check with faults → T layer).
  - Kept = no detector fired and P(code) above 1 in a billion.
  - Malignant = fidelity with |T_L⟩ given code-space postselection below 1 − (1 in a million).
- **Signatures and accept probabilities.** The detector signature is compared with cliffordea's `CultivationCircuit.get_signature_and_effect`. The accept probability is compared with qsim's P(code) (tolerance 1 in a million).
- **Coverage.**
  - Singles: **every error event** of every fault.
  - Pairs: **every 2-fault configuration** (one representative event per fault, the first in a fixed sort order).
  - The requested random sample (2,000 pairs, seed 2026 + CRC32(name)) is a subset and is listed separately.

| circuit | faults | single events: injected / agree | kept benign / kept malignant (1 fault) | all 2-fault configs: injected / agree | kept benign / kept malignant (2 faults) | random sample (2,000): agree, kept malignant | cliffordea's malignant 2-fault configs: real T says kept and corrupted |
|---|---|---|---|---|---|---|---|
| success03 | 168 | 1,301 / 1,301 | 44 / 0 | 14,028 / 14,028 | 17 / **0** | 2,000 / 2,000, **0** | none exist |
| success04 | 174 | 1,340 / 1,340 | 51 / 0 | 15,051 / 15,051 | 17 / 0 | 2,000 / 2,000, 0 | none exist |
| success00 | 168 | 1,301 / 1,301 | 44 / 0 | 14,028 / 14,028 | 18 / 0 | 2,000 / 2,000, 0 | none exist |
| G4 | 154 | 1,018 / 1,018 | 43 / 0 | 11,781 / 11,781 | 41 / **7** | 2,000 / 2,000, 0 | **7 / 7** |
| d3a6 (what if) | 158 | 1,010 / 1,010 | 28 / 0 | 12,403 / 12,403 | 37 / **4** | 2,000 / 2,000, 1 | **4 / 4** |

- **Disagreements: none.** All 73,261 configurations agree with cliffordea on kept / rejected and malignant / benign. All have identical detector signatures and accept probabilities, and all real-T detector outcomes were deterministic.
- **The malignant G4 and d3a6 pairs are kept with a fractional accept probability.** For example, d3a6 (54, 151) = X on qubit 3 at TICK 5 + X6·Y7 at TICK 19 has accept probability 0.25 in cliffordea and 0.25000 in qsim, and the kept state has fidelity 0. The full list is in `results/e3.json` → `malignant2_rows`.
- **Fault distance in the real-T circuit.** success03, success04 and success00 keep no corrupted state with ≤ 2 faults, so cliffordea's Clifford fault analysis is confirmed with real T gates.
- The benign counts differ from the CX-form numbers of earlier rounds because the native circuits have extra H / idle locations. The malignant counts are the same (7 for G4, 4 for d3a6).

Figure: `figures/e3_fault_injection_agreement.png`
- (a) Configurations injected per circuit and class, log scale, labelled with % agreement.
- (b) Kept configurations at 1 and 2 faults: real-T qsim vs cliffordea. Bars are benign, markers are malignant.

## E4 — noisy QVM (Google's Willow noise model)

Data: `results/e4.json` (per-chunk checkpoints `results/e4_chunks/`), `results/noise_model.json`, `results/e4_engine_crosscheck.json`. Logs: `logs/e4.log`, `logs/crosscheck.log`.

**Settings:**
- Noise model `NoiseModelFromGoogleNoiseProperties(load_device_noise_properties("willow_pink"))`, i.e. exactly the model of `create_default_noisy_quantum_virtual_machine`.
- It is applied with `noisy_moments(device circuit, sorted(all its qubits))`, as qsim does.
- The ideal |T_L⟩ preparation and the ideal decode are noiseless and placed outside the noise model.
- qsimcirq `QSimSimulator(t=1)`, trajectory sampling; 12 worker processes; chunks of 5,000 shots; seed = CRC32("name:chunk").
- **Run times:** 4:28:27 – 4:57:18 pm KST (2,000,000 shots each), then an extension 4:57:36 – 5:19:03 pm KST (success03 to 8,000,000, G4 to 4,000,000). That is 50 min 18 s of sampling wall time; the machine was shared with another user's job during the first minutes.

**Definitions:**
- **Acceptance** = no detector fired. Standard error = √(a(1 − a)/N).
- **Logical error per kept shot** (cliffordea's definition, the primary figure) = among kept shots that also pass the ideal stabiliser check, the fraction whose ideal logical H_XY is −1. Exact Clopper–Pearson 95 % interval.
- **Infidelity of the kept state** = among kept shots, 1 − fraction (all stabilisers +1 and H_XY = +1), i.e. 1 − ⟨T_L|ρ|T_L⟩. Most of it is leaving the code space.

### Acceptance

| circuit | shots | kept | **QVM acceptance** (± 1 s.e.; rel. s.e.) | stim calibration model (4,000,000 shots) | stim spec-sheet model | QVM − stim calibration |
|---|---|---|---|---|---|---|
| success03 | 8,000,000 | 5,238,636 | **65.48 % ± 0.017 %** (0.026 %) | 66.47 % ± 0.024 % | 74.39 % ± 0.022 % | −0.99 pp |
| success04 | 2,000,000 | 1,309,557 | **65.48 % ± 0.034 %** (0.051 %) | 66.18 % ± 0.024 % | 74.14 % ± 0.022 % | −0.70 pp |
| success00 | 2,000,000 | 1,399,093 | **69.96 % ± 0.032 %** (0.046 %) | 69.81 % ± 0.023 % | 74.37 % ± 0.022 % | +0.15 pp |
| G4 | 4,000,000 | 3,002,488 | **75.06 % ± 0.022 %** (0.029 %) | 73.94 % ± 0.022 % | 78.98 % ± 0.020 % | +1.12 pp |
| d3a6 (what if) | 2,000,000 | 1,601,784 | **80.09 % ± 0.028 %** (0.035 %) | 79.18 % ± 0.020 % | 78.90 % ± 0.020 % | +0.91 pp |

The stim values are from RESULTS_comparison.md / `results/willow_noise.json`: native CZ + H, the same placements, asymmetric readout in the calibration model.

### Logical error and infidelity of the kept state

| circuit | kept, code space (% of kept) | logical errors | **QVM T error per kept shot** (95 % CI) | one-sided 95 % upper bound | stim calibration model, enumerated, mfc 3 / mfc 4 | QVM infidelity of the kept state (± 1 s.e.) |
|---|---|---|---|---|---|---|
| success03 | 4,383,534 (83.68 %) | 56 | **1 in 78,277** (1 in 103,625 to 1 in 60,279) | 1 in 62,657 | 1 in 89,151 / 1 in 79,616 | 16.32 % ± 0.02 % |
| success04 | 1,097,701 (83.82 %) | 20 | **1 in 54,885** (1 in 89,854 to 1 in 35,538) | 1 in 37,771 | 1 in 89,380 / 1 in 79,753 | 16.18 % ± 0.03 % |
| success00 | 1,142,715 (81.68 %) | 27 | **1 in 42,323** (1 in 64,222 to 1 in 29,089) | 1 in 30,690 | 1 in 62,943 / 1 in 57,821 | 18.33 % ± 0.03 % |
| G4 | 2,204,846 (73.43 %) | 123 | **1 in 17,926** (1 in 21,568 to 1 in 15,024) | 1 in 15,433 | 1 in 20,234 / 1 in 18,925 | 26.57 % ± 0.03 % |
| d3a6 (what if) | 1,207,293 (75.37 %) | 57 | **1 in 21,181** (1 in 27,965 to 1 in 16,348) | 1 in 16,988 | 1 in 25,068 / 1 in 24,159 | 24.63 % ± 0.03 % |

**Observations:**
- **success03 vs G4.** success03's T error per kept shot is 4.4 times lower than G4's (1 in 78,277 vs 1 in 17,926). The stim calibration model gives 4.4 (mfc 3) and 4.2 (mfc 4).
  - success03 is also 3.7 times better than d3a6 (what if), and better than success04 and success00, although their CIs overlap with success03's.
- **QVM vs stim enumeration.** For every circuit the stim mfc-4 value lies inside the QVM 95 % CI, and so does the mfc-3 value (success04's only just). The QVM point estimates are higher: by 2–45 % than mfc 4 (success03 2 %, G4 6 %, d3a6 14 %, success00 37 %, success04 45 %) and by 13–63 % than mfc 3.
  - This is in the expected direction: the enumeration is truncated at 3–4 faults and underestimates (RESULTS_comparison.md: mfc 3 → 4 adds 2–12 %), and the QVM noise model differs (see below).
- **Fraction of kept shots in the code space.** It is 83.7 % (success03) and 73.4 % (G4) in the QVM, against 84.5 % and 74.3 % from cliffordea's enumeration in the stim calibration model ("T kept" / "detectors only" acceptance). The 16–27 % kept-state infidelity is therefore almost entirely states outside the code space, which the next stage's stabiliser checks would catch. It is not logical error.
- **Resolution limit.** Error rates near 1 in a million are far below what these shot counts can resolve. An example is success03's 1 in 6,570,057 at uniform p = 0.1 % in CX form (RESULTS_comparison.md).
  - With 4,383,534 kept code-space shots, even zero events would only bound the rate at 1 in 1,461,178 (95 %).
  - Under Willow-level noise the rate is about 1 in 80,000, so it is resolved: 56 events, ± 13 % (1 s.e.).
  - For a low-noise operating point, only the enumeration (cliffordea) can give the number. The QVM can give only an upper bound at that scale, e.g. "≤ 1 in 1.46 million at 95 %" with 8,000,000 shots.

### Literal-QVM cross-check

- **Setup.** `create_default_noisy_quantum_virtual_machine("willow_pink", qsimcirq.QSimSimulator)` → `get_processor("willow_pink").get_sampler().run(device circuit, 20,000)`.
  - This path validates the circuit against the device, and it passed.
  - The QVM cannot run the ideal encoder (CX between non-adjacent data qubits is not device-valid), so this comparison starts from |0…0⟩.
- **Results** (success03, 20,000 shots each, run 5:20 – 5:21 pm KST):
  - The engine's noise model equals ours (value equality).
  - The 7 detector firing rates agree with the explicit noisy circuit from |0…0⟩ within |z| ≤ 2.2 (max over 7 detectors).
  - The engine took 31 s for 20,000 shots.

### What the QVM noise model includes (read back from the objects: `results/noise_model.json`)

| channel | where | parameters (willow_pink calibration, 105 qubits / 182 couplers) |
|---|---|---|
| **Thermal relaxation + pure dephasing** (Kraus amplitude damping 1/T1 and dephasing 1/Tphi; not Pauli-twirled) | after every physical moment, on **every qubit of the circuit**, for the moment's duration (= its longest gate). Measured qubits are skipped during their own measurement moment. Moments containing only virtual Z gates get none. | T1 median 70.2 µs (27.4–86.4). Tphi derived from RB incoherent error (median 75.9 µs, min 4.8 µs). Durations from the device spec: PhasedXZ 25 ns, CZ 42 ns, measure 600 ns, reset 160 ns, Z 0 ns. |
| **Depolarising error after each gate** | after PhasedXZ, CZ and reset. Value = calibrated Pauli error − decoherence already counted − (for CZ) the coherent entangling part. **Non-positive values are dropped.** | PhasedXZ: RB Pauli error, median 0.0034 % after subtraction; 36 of 105 qubits ≤ 0, i.e. none. CZ: full parallel-XEB Pauli error per cycle, **without** subtracting the 1q part; median 0.118 %; 78 of 364 ordered pairs ≤ 0. Reset: 104 of 105 ≤ 0, so effectively no reset gate error beyond thermal. |
| **Coherent CZ error** | `PhasedFSimGate(θ, φ)` after every CZ | median \|θ\| 0.022 rad, \|φ\| 0.037 rad (max 0.077 / 0.214 rad) |
| **Readout error** | generalised amplitude damping just before each measurement (a physical channel) | P(1\|0) = p00, median 0.37 %; P(0\|1) = p11, median 1.06 % |
| **T / T† gates** | virtual Z (`ZPowGate` without `PhysicalZTag`) | **noiseless** |

**Not included:**
- **readout-line dephasing**, i.e. measurement-induced dephasing of other qubits; this is why the strict readout rule exists, and it is **not modelled**;
- **crosstalk** (ZZ / spectator, parallel-gate crosstalk beyond what parallel XEB averages in);
- leakage;
- heating (no heat rate);
- Z-phase errors ζ / γ (no Z-phase data for willow_pink);
- correlated and non-Markovian noise, drift;
- noise on qubits outside the circuit;
- any timing or latency of mid-circuit measurement beyond the 600 ns + 160 ns moments;
- dynamical decoupling.

### Why the QVM and stim acceptances differ (by −1.0 to +1.1 percentage points)

The two models are built differently from the same calibration file:

| | QVM (cirq_google) | stim calibration model (RESULTS_comparison.md) |
|---|---|---|
| CZ error | full XEB Pauli error − decoherence − coherent θ/φ part, **plus** a coherent PhasedFSim | XEB − both 1q RB errors, Pauli DEPOLARIZE2 |
| idle / T1, T2 | Kraus amplitude + phase damping (biased towards \|0⟩) | Pauli-twirled X / Y / Z errors |
| reset | 160 ns; no extra error (dropped as ≤ 0) | 200 ns + 0.1 % X error (assumption) |
| readout | GAD channel before measurement; measured qubit has no T1 during readout | classical asymmetric flip of the outcome |
| first / last TICK | no MPP / trailing-reset TICK at all | noiseless, by cliffordea's convention |
| 1q gate error | RB Pauli − decoherence (often 0) | RB Pauli error in full |

- **Small net differences.** Several of these act in opposite directions: no reset error and smaller 1q errors raise the QVM acceptance; the larger CZ error and the coherent CZ rotations lower it. The net differences are small and change sign between designs.
- Observed: G4 (+1.1 pp) and d3a6 (+0.9 pp) come out higher in the QVM, success03 (−1.0 pp) and success04 (−0.7 pp) lower, success00 equal within 0.15 pp.
- These per-channel attributions were not isolated by ablation; they are the evident model differences, not measured contributions.

Figure: `figures/e4_acceptance_and_infidelity.png`
- (a) Acceptance, QVM vs stim calibration vs stim spec sheet, 1 s.e. error bars (smaller than the line width).
- (b) T error per kept shot on a "1 in N" log axis: QVM with exact 95 % CI, against the stim-enumerated calibration-model rates at mfc 3 and mfc 4.

## Limitations

1. **A model, not hardware.** It omits readout-line dephasing, crosstalk and leakage (table above).
   - The strict readout rule was built precisely because neighbouring readout dephasing is real on Willow. The QVM therefore cannot penalise d3a6's readout conflict; d3a6's "what if" numbers are optimistic.
2. **T gates are virtual Z and noiseless** in this frame.
   - Google's G4 experiment applies its T rotations as T_y (Y-axis microwave rotations, RESULTS_g4.md), which would carry 1q gate error.
   - The T layers sit outside the double check, so they do not change detector statistics. They would add a small error to the output state.
3. **Ideal preparation and decode.** The encoded T state is prepared ideally and decoded ideally, as in cliffordea's model of the stage. Errors from the injection / encoding stage and from later stages are outside this experiment.
4. **The device model checks only the gate set and connectivity** (`grid_device.py:716-753`), not timing, readout-line rules or moment structure.
5. **E3 pairs use one representative error event per fault.**
   - cliffordea groups events with the same signature and effect into one fault, so any member realises the fault in the Clifford picture.
   - All events were injected for single faults (5,970 events), and none differed from its fault's classification.
6. **Statistical precision.**
   - The QVM rates have a relative s.e. of 9–22 % (G4 9 % from 123 events, success03 13 % from 56, success04 22 % from 20).
   - success03 / success04 / success00 are not separated from each other at 95 %. success03 vs G4 is separated: the CIs do not overlap.
7. **Shared machine.** Another user's job shared the CPU at times, so the wall times are not benchmarks.

## Decisions made without the user

1. **Initial state = cliffordea's encoded T state**, prepared with cliffordea's own encoder tableau. The suggested "|+_L⟩ followed by the T pattern" was not used, because that state is only 56.25 % in the code space and is not cliffordea's convention (see Method).
2. **H → `PhasedXZGate`**, a gate decomposition only, so that Google's noise model applies the calibrated 1q gate error. Validation passes with either form.
3. **Dropped cliffordea's two noiseless bookkeeping TICKs** (the MPP marker and the trailing reset) from the device circuit. The detector that used the marker keeps its other records, since the marker is +1 for the ideal input. MR is written as measure + reset moments.
4. **Ideal preparation and decode are noiseless and outside the noise model**, so the main E4 path uses the explicit noisy circuit (the same noise model object and the same `noisy_moments` call as the QVM). It is cross-checked against the literal `SimulatedLocalEngine` (same model, consistent detector statistics).
5. **E3 was run exhaustively** for all 2-fault configurations of all five circuits, which is more than the requested ≥ 2,000 sample. The seeded sample is still reported. Measurement-flip events were applied as classical bit flips.
6. **Primary infidelity metric** = cliffordea's logical error per kept shot (ideal stabiliser postselection, then logical H_XY). The raw infidelity of the kept state w.r.t. |T_L⟩ is reported next to it.
7. **Shot allocation.**
   - 2,000,000 per circuit first, then success03 was extended to 8,000,000 and G4 to 4,000,000 to sharpen the main comparison.
   - 18,000,000 shots in total, 50 min 18 s wall time, within the 2 h budget.
8. **"Next 2 best ZZ successes"** = success04 and success00, the next lowest T error per kept shot at mfc 3 in CX form (RESULTS_comparison.md), as in the comparison round.

## Files

- **Code:**
  - `../qvm_willow.py` (shared engine): E1–E4, the noise inventory and the engine cross-check; imports `nnflags`, copies nothing.
  - `plots.py`: figures.
  - `qvm-google/tests/test_qvm.py`: 16 tests.
  - `qvm-google/README.md`: how to rerun each step.
- **Results:** `qvm-google/results/{e1,e2,e3,e4,e4_engine_crosscheck,noise_model}.json`, `results/e3_parts/`, `results/e4_chunks/` (3,600 chunk files).
- **Figures (PNG only; no PDF anywhere in `qvm-google/`):** `figures/e3_fault_injection_agreement.png`, `figures/e4_acceptance_and_infidelity.png`.
- **Logs:** `logs/e3.log`, `logs/e4.log`, `logs/crosscheck.log`, `logs/pytest_qvm.log`, `logs/pytest_nnflags.log`, `logs/cliffordea_check.txt` (0 bytes).
