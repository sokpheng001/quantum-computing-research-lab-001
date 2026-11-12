# RESULTS — design comparison: acceptance, attempts per kept shot, and realistic Willow noise

Run unattended on 2026-11-01, 3:46 pm – 3:59 pm KST. No new search. Earlier results files are untouched.

## Answer

**Yes: the fault-distance-3 Willow design keeps its advantage once discards are counted, under every noise model tried.**

- **Uniform noise, p = 0.1 %, CX form** (same model as the earlier rounds):
  - `success03` keeps 88.39 % of shots, against 93.08 % for G4-CX. So it needs 1.131 attempts per kept shot instead of 1.074 (5.3 % more).
  - Its T error is 3.2 times lower per kept shot (1 in 6,570,057 vs 1 in 2,054,158) and 3.4 times lower per attempt (1 in 7,432,643 vs 1 in 2,206,858).
- **Realistic Willow noise, native CZ + H form, at the circuits' Willow positions**, success03 vs G4:
  - **Calibration model** (per qubit / per coupler): T error per kept shot is 4.4 times lower (1 in 89,151 vs 1 in 20,234). The cost is 1.504 vs 1.352 attempts per kept shot (11 % more).
  - **Spec-sheet model**: 4.0 times lower (1 in 360,080 vs 1 in 90,830), at 1.344 vs 1.266 attempts (6 % more).
- **d3a6f2 is the only design with a lower T error per kept shot than success03 under uniform noise** (1 in 6,900,456, CX form). It is not Willow-compatible. Under realistic noise, on its best "what if" Willow placement, it is worse than success03: 1 in 66,424 (calibration) and 1 in 134,285 (spec sheet).
- **Realistic noise is much harsher than uniform p = 0.1 %.**
  - The rates per kept shot drop by a factor of 10 to 25, and acceptance falls to 64–79 %.
  - The main reason is idling. Every qubit waits through the 800 ns mid-circuit measure-and-reset, and T1/T2 errors build up during that wait.
  - At this noise strength, truncating at 3 faults underestimates the T error by 2–12 % (checked against 4 faults).

## Status

| Task | Status | One line |
|---|---|---|
| 1. d3a6f2 at 3 faults | **DONE** | T malignant 0 / 0 / 0 / 248 at k = 0..3; S 0 / 0 / 0 / 70. T error per kept shot 0 (mfc 2) and 1 in 6,900,456 (mfc 3); S error 0 and 1 in 60,786,275. |
| 2. Acceptance | **DONE** | cliffordea has no acceptance output; it was rebuilt exactly from cliffordea's kept effects and odds. The stim Monte Carlo agrees within 2 standard errors for 15 of the 16 designs at all 4 values of p. The exception is d3a4, which is explained by a cliffordea inconsistency: it counts d3a4's final readout flips, which the noisy circuit does not contain. |
| 3. Table + figure | **DONE** | Table below. `figures/archive/comparison_acceptance.png` (PNG only). |
| 4. Realistic Willow noise | **DONE** | Calibration and spec-sheet models, native CZ + H form. Malignant counts are unchanged by the conversion (all 6 designs). `figures/archive/comparison_willow_noise.png`. |
| 5. Tests, lock file | **PASS** | nnflags: **102 passed** (95 earlier + 7 new). cliffordea's own suite: **401 passed** under the downgraded pandas 3.0.6 / contourpy 1.3.2. `requirements-lock.txt` was regenerated from `.venv/bin/pip freeze`. |
| cliffordea untouched | **PASS** | `git -C cliffordea status --porcelain --ignored` gave empty output. |

## Settings (every number below unless a line says otherwise)

- distance 3; cultivated states T and S;
- noise `enum.noise.uniformly_depolarize` (cliffordea `enum/noise/main.py:9`) at p = 0.1 % = 0.001;
- `FaultCombinator.get_kept_effects` (`enum/combinators/fault_combinator.py:236`) with `CliffordLogicalAnalyzer`, through `nnflags.verify.verify` (`nnflags/verify.py:47-100`);
- "T error per kept shot" = cliffordea `error_rates_per_kept_shot` (`fault_combinator.py:164-225`), truncated at max_fault_count (mfc) 3 unless stated;
- acceptance = probability that no inner detector fires, from stim Monte Carlo on the same noisy inner circuit:
  - 10,000,000 shots at p = 0.1 % and 4,000,000 shots at the other p;
  - the relative standard error is at most 0.04 % everywhere (target < 1 %);
- attempts per kept shot = 1 / acceptance;
- T error per attempt = T error per kept shot × acceptance.

Code: `nnflags/comparison.py` (`python -m nnflags.comparison`). Data: `results/comparison.json`. Log: `logs/comparison.log`. Run: 3:49:34 – 3:51:52 pm KST.

## 1. d3a6f2 at 3 faults

Settings: `DoubleCheck(3, 6, flag_count=2)` bundled stim files (`verify.bundled_paths("d3a6f2")`), p = 0.1 %. There are 198 faults. Each verify() call takes 0.05 s.

| state | k = 0 malignant / benign | k = 1 | k = 2 | k = 3 | error per kept shot, mfc 2 | error per kept shot, mfc 3 |
|---|---|---|---|---|---|---|
| T | 0 / 1 | 0 / 2 | 0 / 37 | **248** / 1,499 | 0 | **1 in 6,900,456** |
| S | 0 / 1 | 0 / 2 | 0 / 37 | **70** / 1,390 | 0 | 1 in 60,786,275 |

- The k ≤ 2 counts match Step 0 (`results/step0_d3a6f2_summary.csv`).
- d3a6f2 has fault distance 3 in cliffordea, like the ZZ-flag successes. Its 248 malignant 3-fault T configurations are fewer than for any success (269–370), and its T rate is the lowest of all designs. It is not Willow-compatible: it needs 3 missing couplers, and qubit 6 has 6 partners (RESULTS_steps0-2.md).

## 2. Acceptance

### Does cliffordea already compute it? No. It was rebuilt from cliffordea's own quantities.

- **No acceptance output exists.** Neither `FaultCombinator` nor `summarize_contributions` returns a keep probability; `summarize_contributions` (`fault_combinator.py:413-468`) gives only relative weights.
- **Where the rate comes from.** `error_rates_per_kept_shot` (`:164-225`) returns malignant_odds / (benign_odds + malignant_odds).
  - Each kept configuration contributes `accept_probability × Π odds_i` over its faults (`_compile_odds_terms`, `:722-758`).
  - The odds come from `_bag_to_odds` (`:558-580`), using `_decomposed_probability` (`:584-605`).
  - The common factor Π_i (1 − q_i) over all faults cancels in this ratio.
- **What `nnflags/comparison.py` computes.** It multiplies that factor back in:

  P(kept) = Π_i (1 − q_i) × Σ_{k ≤ mfc} Σ_{kept configurations} a × Π_{i ∈ config} odds_i,  with q_i = odds_i / (1 + odds_i).

  This is exact apart from the truncation at mfc.
- **Truncation order.** It is a sum over kept configurations with at most mfc faults. So it slightly underestimates the keep probability. At p = 0.3 % the 4-fault term is at most 0.035 % of the total (G4-native).
- **Two meanings, depending on the analyzer:**
  - **"detectors only".** An accept-everything analyzer (`comparison.AcceptAll`, a subclass written in nnflags; cliffordea is not modified) makes kept = no inner detector fires. This is the same event as the Monte Carlo. Computed at mfc 4.
  - **"T kept".** `CliffordLogicalAnalyzer`'s `accept_probability` (`accept/logical_analyzers.py:370-403`) adds the noiseless final stabiliser postselection. This is the denominator of cliffordea's "per kept shot". Computed at mfc 3.
  - At p = 0.1 % the T-kept probability is 3–7 percentage points lower than detectors-only.

### Monte Carlo vs enumeration (detectors only)

Settings: same noisy inner circuit (`uniformly_depolarize(m.INNER_CIRCUIT, p)`), `compile_detector_sampler`; a shot is kept when no detector fired. Values are acceptance ± 1 standard error, in %.

| design | MC p = 0.05 % | MC p = 0.1 % | MC p = 0.2 % | MC p = 0.3 % | enumerated, detectors only, p = 0.1 % (mfc 4) | enumerated, T kept (detectors + final postselection), p = 0.1 % (mfc 3) | difference MC − enum (in MC s.e.) |
|---|---|---|---|---|---|---|---|
| d3a6 | 96.09 % ± 0.010 | 92.32 % ± 0.008 | 85.28 % ± 0.018 | 78.78 % ± 0.020 | 92.33 % | 88.78 % | -0.8 |
| d3a6f2 | 93.37 % ± 0.012 | 87.24 % ± 0.011 | 76.20 % ± 0.021 | 66.60 % ± 0.024 | 87.24 % | 82.81 % | -0.3 |
| d3a4 | 97.01 % ± 0.009 | 94.12 % ± 0.007 | 88.62 % ± 0.016 | 83.50 % ± 0.019 | 93.75 % | 91.00 % | +50.2 |
| G4-CX | 96.48 % ± 0.009 | 93.08 % ± 0.008 | 86.65 % ± 0.017 | 80.74 % ± 0.020 | 93.08 % | 89.79 % | +0.6 |
| G4-native | 92.53 % ± 0.013 | 85.69 % ± 0.011 | 73.61 % ± 0.022 | 63.36 % ± 0.024 | 85.67 % | 78.53 % | +2.0 |
| cand03 | 96.06 % ± 0.010 | 92.28 % ± 0.008 | 85.25 % ± 0.018 | 78.79 % ± 0.020 | 92.29 % | 88.68 % | -1.3 |
| success00 | 94.02 % ± 0.012 | 88.45 % ± 0.010 | 78.31 % ± 0.021 | 69.45 % ± 0.023 | 88.46 % | 84.68 % | -0.1 |
| success03 | 94.01 % ± 0.012 | 88.39 % ± 0.010 | 78.26 % ± 0.021 | 69.31 % ± 0.023 | 88.40 % | 84.68 % | -0.5 |
| success06 | 94.31 % ± 0.012 | 88.95 % ± 0.010 | 79.17 % ± 0.020 | 70.60 % ± 0.023 | 88.94 % | 85.02 % | +1.3 |
| success04 | 94.00 % ± 0.012 | 88.43 % ± 0.010 | 78.29 % ± 0.021 | 69.39 % ± 0.023 | 88.42 % | 84.77 % | +1.2 |
| success07 | 94.25 % ± 0.012 | 88.86 % ± 0.010 | 79.00 % ± 0.020 | 70.37 % ± 0.023 | 88.85 % | 84.99 % | +1.7 |
| success08 | 94.74 % ± 0.011 | 89.78 % ± 0.010 | 80.73 % ± 0.020 | 72.64 % ± 0.022 | 89.79 % | 85.95 % | -1.2 |
| success09 | 94.70 % ± 0.011 | 89.70 % ± 0.010 | 80.56 % ± 0.020 | 72.41 % ± 0.022 | 89.70 % | 85.92 % | -0.5 |
| success05 | 94.18 % ± 0.012 | 88.67 % ± 0.010 | 78.75 % ± 0.020 | 70.02 % ± 0.023 | 88.69 % | 84.91 % | -1.1 |
| success01 | 93.45 % ± 0.012 | 87.33 % ± 0.011 | 76.36 % ± 0.021 | 66.91 % ± 0.024 | 87.33 % | 82.79 % | -0.5 |
| success02 | 93.25 % ± 0.013 | 87.01 % ± 0.011 | 75.87 % ± 0.021 | 66.21 % ± 0.024 | 87.02 % | 82.79 % | -0.7 |

**Agreement.**
- At all 4 values of p, MC and enumeration agree within 2.0 standard errors for 15 of the 16 designs; the largest deviation is +2.0 for G4-native at p = 0.1 %.

**The exception is d3a4.**
- It is off by 22 to 53 standard errors (MC higher by 0.37 percentage points at p = 0.1 %).
- **Cause.** d3a4's bundled inner circuit ends with `MX 8 2 7 3` and has no trailing reset TICK.
  - `uniformly_depolarize` leaves the first and the last TICK noiseless (`enum/noise/main.py:39-40`), so these 4 readouts carry no flip in the noisy circuit.
  - FaultCombinator still treats every `MX` as an error location (`ONE_QUBIT_ERROR_EVENTS`, `enum/constants.py:5`; `cultivation_circuit.py:296-335`). It ignores the instruction's probability and weights every location at the global noise level (`fault_combinator.py:558-605`).
- **Check.** Adding `MX(0.001)` to that layer gives MC = 93.751 % ± 0.008 % (10,000,000 shots), against 93.748 % enumerated.
- **Consequence.** cliffordea's d3a4 rates include 4 readout errors that its own noisy circuit does not have. The other bundled and derived circuits end with a reset layer and are not affected. For d3a4 the table uses the stim value (the circuit as written).
- A test pins this down: `test_d3a4_final_readout_is_noiseless_in_stim_but_enumerated`.

## 3. Comparison table (uniform noise)

Settings: the "Settings" block above; p = 0.1 %.
- Malignant S at ≤ 2 faults is k = 0 + 1 + 2; the 3-fault count is in brackets.
- "Willow-compatible" is strict readout with `live_rule="gate"` and `final_layer="auto"`, as in the previous rounds.
- Rows are ranked as in RESULTS_zzflags.md. The ZZ successes 11 and 12 (base B0130) have no saved stim file and are not included.

| design | Willow-compatible? | qubits | flags | TICKs | 2q gates | malignant T at 1 / 2 / 3 faults | malignant S at ≤ 2 faults (at 3) | T error per kept shot, mfc 3 (mfc 2) | acceptance at p = 0.1 % (± 1 s.e.) | attempts per kept shot | T error per attempt |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d3a6 | no | 13 | 0 | 12 | 24 CX | 0 / 4 / 415 | 0 (82) | 1 in 3,568,591 (1 in 4,760,490) | 92.32 % ± 0.008 % | 1.083 | 1 in 3,865,298 |
| d3a6f2 | no | 15 | 2 | 16 | 32 CX | 0 / 0 / 248 | 0 (70) | 1 in 6,900,456 (0) | 87.24 % ± 0.011 % | 1.146 | 1 in 7,909,897 |
| d3a4 | no | 11 | 0 | 11 | 20 CX | 0 / 12 / 1619 | 0 (442) | 1 in 3,184,814 (1 in 3,583,893) | 94.12 % ± 0.007 % | 1.062 | 1 in 3,383,731 |
| G4-CX | yes | 12 | 0 | 12 | 24 CX | 0 / 7 / 671 | 0 (162) | 1 in 2,054,158 (1 in 2,421,930) | 93.08 % ± 0.008 % | 1.074 | 1 in 2,206,858 |
| G4-native | yes | 12 | 0 | 24 | 24 CZ | 0 / 7 / 671 | 0 (162) | 1 in 314,362 (1 in 447,652) | 85.69 % ± 0.011 % | 1.167 | 1 in 366,865 |
| cand03 | yes | 12 | 1 | 13 | 22 CX | 0 / 6 / 633 | 0 (194) | 1 in 1,524,994 (1 in 1,781,499) | 92.28 % ± 0.008 % | 1.084 | 1 in 1,652,511 |
| success00 | yes | 13 | 2 | 16 | 26 CX | 0 / 0 / 283 | 0 (101) | 1 in 6,110,492 (0) | 88.45 % ± 0.010 % | 1.131 | 1 in 6,908,053 |
| success03 | yes | 13 | 2 | 16 | 26 CX | 0 / 0 / 286 | 0 (108) | 1 in 6,570,057 (0) | 88.39 % ± 0.010 % | 1.131 | 1 in 7,432,643 |
| success06 | yes | 13 | 2 | 16 | 26 CX | 0 / 0 / 303 | 0 (101) | 1 in 4,267,098 (0) | 88.95 % ± 0.010 % | 1.124 | 1 in 4,797,304 |
| success04 | yes | 13 | 2 | 16 | 26 CX | 0 / 0 / 312 | 0 (114) | 1 in 6,412,602 (0) | 88.43 % ± 0.010 % | 1.131 | 1 in 7,251,591 |
| success07 | yes | 13 | 2 | 16 | 26 CX | 0 / 0 / 327 | 0 (111) | 1 in 4,229,521 (0) | 88.86 % ± 0.010 % | 1.125 | 1 in 4,759,549 |
| success08 | yes | 12 | 2 | 16 | 24 CX | 0 / 0 / 336 | 0 (122) | 1 in 4,365,631 (0) | 89.78 % ± 0.010 % | 1.114 | 1 in 4,862,489 |
| success09 | yes | 12 | 2 | 16 | 24 CX | 0 / 0 / 362 | 0 (134) | 1 in 4,319,798 (0) | 89.70 % ± 0.010 % | 1.115 | 1 in 4,815,856 |
| success05 | yes | 13 | 2 | 16 | 26 CX | 0 / 0 / 370 | 0 (159) | 1 in 4,139,319 (0) | 88.67 % ± 0.010 % | 1.128 | 1 in 4,668,022 |
| success01 | yes | 13 | 2 | 18 | 26 CX | 0 / 0 / 269 | 0 (93) | 1 in 3,410,303 (0) | 87.33 % ± 0.011 % | 1.145 | 1 in 3,905,278 |
| success02 | yes | 13 | 2 | 18 | 26 CX | 0 / 0 / 315 | 0 (119) | 1 in 3,178,731 (0) | 87.01 % ± 0.011 % | 1.149 | 1 in 3,653,204 |

**Does the fault-distance-3 Willow design keep its advantage once discards are counted?** Yes. Settings: uniform `uniformly_depolarize`, p = 0.1 %, CX form, T error truncated at 3 faults, acceptance = no inner detector fires.

- **Attempts.** The ZZ-flag successes keep 87.0–89.8 % of shots, against 92.3–93.1 % for the unflagged or one-flag Willow designs (G4-CX, cand03). Their two flag detectors and 4 extra TICKs cost 4–7 % more attempts per kept shot (success03: 1.131, G4-CX: 1.074).
- **Error per kept shot.** success03's T error per kept shot is 3.2 times lower than G4-CX's, 4.3 times lower than cand03's, and 1.8 times lower than d3a6's (not Willow-compatible).
- **Error per attempt.** Multiplying by the acceptance widens these gaps a little: 3.4, 4.5 and 1.9 times. The success's errors are rarer, and it also discards more of the shots that would have carried an error.
- **The only design ahead of success03 is d3a6f2**, which is not Willow-compatible. It is 5 % better per kept shot and 6 % better per attempt, at 1.146 attempts per kept shot.
- **Caveat on "per attempt".** T error per attempt counts a discarded shot as error-free. It rewards discarding, so the cost of discarding should be read from the attempts column, not from this column.

**Figure** `figures/archive/comparison_acceptance.png` (`python -m nnflags.plots --only comparison`, PNG 200 dpi):
- (a) Monte Carlo acceptance against p (0.05, 0.1, 0.2, 0.3 %) for d3a6, d3a6f2, G4-CX, cand03 and success03. Error bars are 1 standard error, smaller than the markers. The points are dodged horizontally by at most 5 % of p because d3a6 and cand03 overlap.
- (b) T error per kept shot and per attempt at p = 0.1 %, shown as "1 in N", N in millions; hatched bars are per attempt.
- Okabe–Ito colours with distinct markers, line styles and hatching; white background; no e-notation.

## 4. Realistic Willow noise

Code: `nnflags/willow_noise.py` (`python -m nnflags.willow_noise`). Data: `results/willow_noise.json`. Native and noisy circuits: `results/willow_noise/*.stim`. Log: `logs/willow_noise.log`. Run: 3:54:29 – 3:55:37 pm KST (70 s).

### Calibration source

- **File.** `.venv/lib/python3.12/site-packages/cirq_google/devices/calibrations/willow_pink_d7v1-2024_08_16_calibration.json` (cirq-google 1.7.0).
- **Loading.** The file is parsed into `cirq_google.api.v2.metrics_pb2.MetricsSnapshot` (`google.protobuf.json_format.ParseDict` of its `"metrics"` field) and wrapped in `cirq_google.Calibration`.
- **Coverage.** 105 qubits and 182 pairs. The qubit set equals `nnflags.willow.WILLOW`, and the pairs equal its 182 nearest-neighbour couplers (asserted in the code).

| metric (file name) | n | mean | median | min | max | used as |
|---|---|---|---|---|---|---|
| `single_qubit_idle_t1_micros` | 105 | 67.7 µs | 70.2 µs | 27.4 µs | 86.4 µs | T1 |
| T2 (derived, see below) | 105 | 50.1 µs | 49.0 µs | 4.5 µs | 99.2 µs | T2 |
| `single_qubit_rb_pauli_error_per_gate` | 105 | 0.053 % | 0.040 % | 0.022 % | 0.32 % | H gate: DEPOLARIZE1 |
| `single_qubit_rb_incoherent_error_per_gate` | 105 | 0.028 % | 0.023 % | 0.014 % | 0.20 % | for T_phi only |
| `single_qubit_p00_error` = P(read 1 \| 0) | 105 | 0.38 % | 0.37 % | 0.14 % | 1.03 % | readout of 0 |
| `single_qubit_p11_error` = P(read 0 \| 1) | 105 | 1.15 % | 1.06 % | 0.73 % | 1.98 % | readout of 1 |
| `two_qubit_parallel_cz_gate_xeb_pauli_error_per_cycle` | 182 | 0.41 % | 0.34 % | 0.056 % | 1.21 % | XEB cycle |
| CZ error used = XEB cycle − both 1q RB errors | 182 | 0.31 % | 0.25 % | 0 (3 pairs floored) | 1.09 % | CZ: DEPOLARIZE2 |

### Models

Common to both models: Pauli channels placed **after** each TICK's operations, as in cliffordea. The noise conventions follow `uniformly_depolarize`:
- the first (MPP) and last (trailing reset) TICKs are noiseless;
- data qubits are noisy from the MPP marker on;
- a qubit measured without reset gets no further noise.

**Durations:**
- 1q gate 25 ns (the low end of 25–35 ns; cirq_google's default microwave time);
- CZ 42 ns;
- measurement 600 ns (Google proposal guidance);
- **reset 200 ns (assumption: no value in the calibration file or the guidance at hand)**;
- MR = 600 + 200 = 800 ns.

A TICK lasts as long as its longest operation. Each qubit idles for (TICK duration − its own operation's duration).

**Primary model, "calibration"** (per qubit / per coupler, at each circuit's Willow positions):
- **CZ.** DEPOLARIZE2(e2), with e2 = XEB Pauli error per cycle − rb_pauli(a) − rb_pauli(b), floored at 0 (3 of 182 pairs).
  - **Subtracted, because** a parallel-XEB cycle is one random single-qubit gate on each qubit plus the CZ. Our circuits give each H its own DEPOLARIZE1, so the 1q part would otherwise be counted twice.
  - cirq_google's own converter does **not** subtract (`cirq_google/engine/calibration_to_noise_properties.py:164-176`).
  - A Pauli error per cycle e is the total probability of a non-identity Pauli, which is exactly stim's DEPOLARIZE2(e).
- **H.** DEPOLARIZE1(`single_qubit_rb_pauli_error_per_gate`).
- **Readout (asymmetric).**
  - In the Monte Carlo it is exact: each raw outcome is flipped with p00 if it is 0 and with p11 if it is 1, then converted to detection events by stim's `compile_m2d_converter`.
  - In the enumeration it is symmetric, (p00 + p11) / 2, because a cliffordea measurement location has one flip probability.
- **Reset.** X_ERROR(0.1 %) after R / MR. **This is an assumption**; the file has no reset error.
- **Idle.** Amplitude and phase damping for the idle time t, Pauli-twirled:
  - px = py = (1 − e^(−t/T1)) / 4, pz = (1 − e^(−t/T2)) / 2 − px;
  - applied as independent X_ERROR, Y_ERROR and Z_ERROR (they differ from the exclusive channel only at second order).
- **T2.** It is not in the file. 1/T2 = 1/(2 T1) + 1/T_phi, with T_phi derived from `single_qubit_rb_incoherent_error_per_gate` exactly as cirq_google does (`calibration_to_noise_properties.py:142-152`: T_phi = t_gate / (3 (incoherent − t_gate / (3 T1))), t_gate = 25 ns, and 10^10 ns if the bracket is ≤ 0). Median T2 = 49.0 µs.
- **Pairs without a coupler.** These occur only in d3a6f2's "what if" placement. They get the median calibrated CZ error, 0.25 %.

**Secondary model, "spec"** (Willow spec-sheet averages, uniform over qubits):
- CZ DEPOLARIZE2(0.33 %); 1q DEPOLARIZE1(0.035 %); readout 0.77 % symmetric;
- T1 = 68 µs, and T2 = T1 (assumption);
- the same durations and reset error as the primary model.

**Not modelled:** leakage, crosstalk, measurement-induced dephasing of neighbours (the strict readout rule excludes those placements instead), coherent CZ phase errors (the file's θ/φ metrics), and dynamical decoupling.

### Circuits: native CZ + H at Willow positions

- **G4.** Its own native extraction, `results/g4/G4-native_CZH.inner.stim` (24 TICKs, M then R as run), at its own coordinates.
- **Others.** CX form converted by `willow_noise.cx_to_native`.
  - **Frame rules.** It keeps an H-frame bit per qubit. A CX c→t needs c unframed and t framed at the CZ (H_t CZ H_t = CX). M / MR need frame 0 and MX / MRX need frame 1. RX = R with frame 1, MRX = MR with frame 1.
  - **H placement.** H gates are inserted lazily, as one H-only TICK before a TICK whose requirements differ. Data return to frame 0 before the last measurement TICK.
  - Equivalent to the inverse of `equivalence.absorb_hadamards`: absorbing the H's again gives 0 non-CX gates for every design.
- **Checks.** The converted circuits are deterministic (stim). verify() gives **identical malignant T and S configuration counts at k = 0..3** for the CX and native forms of all 6 designs (uniform p = 0.1 %, mfc 3; `uniform_check` in the JSON).
  - This check uses each design's CX-form full circuit, because cliffordea reads only its MPPs and its S / S_DAG instructions (`enum/circuits/_base.py:17-71`, `main.py:58-80`); the data indices come from the inner circuit's MPP.
  - Only benign counts differ, through the H locations.
- **Placements:**
  - successes and G4: their own QUBIT_COORDS, which are Willow-valid;
  - **d3a6:** `results/embed_search_d3a6.json` `example_min_embedding["exempt"]`, which has 1 strict readout conflict (the minimum over all 182,968 embeddings);
  - **d3a6f2:** `results/step1.json` `d3a6f2_willow` (the d3a6 placement plus the best free flag spots; 3 CZs on non-couplers, and qubit 6 has 6 partners).
  - **d3a6 and d3a6f2 are not Willow-compatible; their rows are "what if" only.**

### Does cliffordea's FaultCombinator accept an arbitrary noisy stim circuit?

**Partly.**
- **What it accepts.** `FaultCombinator.__init__` (`fault_combinator.py:106-124`) takes any noisy stim circuit and groups its error locations with `CultivationCircuit.group_error_events_by_location` (`cultivation_circuit.py:296-335`).
  - It recognises X/Y/Z_ERROR, measurement flips (`ONE_QUBIT_ERROR_EVENTS`, `enum/constants.py:5`), DEPOLARIZE1 and DEPOLARIZE2 (`combinators/_base.py:141-162`).
  - Other channels, such as PAULI_CHANNEL_1, are **skipped silently**. That is why the models above use only recognised channels; a test asserts it.
- **What it ignores.** The channel strengths. Each fault keeps only a "bag" of channel classes (`:112-131`), and every rate uses one global `noise_level` (`error_rates_per_kept_shot`, `:164-225`; `_bag_to_odds` / `_decomposed_probability`, `:558-605`).
- **What is used, therefore:**
  - The kept configurations, with their accept probabilities and fidelities, come from cliffordea's own `get_kept_effects`; these do not depend on the strengths.
  - The weights come from `comparison.odds_from_circuit`. It walks the same locations in the same order as `__init__` (aligned with `_event_fault_indices`, as `index_to_events` does, `:374-388`) and decomposes each location with cliffordea's `_decomposed_probability` at **that location's own strength**.
  - The odd-parity probability of a fault is then (1 − Π(1 − 2 q_e)) / 2, and the rate is cliffordea's formula with these odds.
- **Validation:**
  - On uniform circuits these odds equal cliffordea's own to about 1 part in 10,000,000,000,000 (test).
  - The detectors-only acceptance from these odds matches the Monte Carlo with symmetric readout within 1.5 standard errors for all 12 design × model pairs.

### Table: realistic Willow noise (native CZ + H, Willow positions)

Settings:
- T error per kept shot: cliffordea kept configurations with per-location odds, truncated at mfc 3 (mfc 4 is shown as a convergence check).
- Acceptance: stim Monte Carlo, kept = no detector fires. 4,000,000 shots for the two Willow models, 10,000,000 for uniform; relative standard error ≤ 0.04 %. Readout is asymmetric in the calibration model.
- "Expected faults per shot" = Σ_i q_i over all faults.
- The uniform rows are `uniformly_depolarize` at p = 0.1 % on the same native circuit.
- "Best 3 successes" = the 3 lowest T errors at mfc 3 in CX form: success03, success04, success00.

| design | model | TICKs (native) | malignant T at 3 faults | T error per kept shot, mfc 3 | same, mfc 4 (check) | acceptance, MC (± 1 s.e.) | attempts per kept T state | T error per attempt | expected faults per shot |
|---|---|---|---|---|---|---|---|---|---|
| success03 | uniform p = 0.1 % | 29 | 286 | 1 in 907,454 | — | 78.48 % ± 0.013 % | 1.274 | 1 in 1,156,289 | — |
| success03 | spec sheet | 29 | 286 | 1 in 360,080 | 1 in 334,402 | 74.39 % ± 0.022 % | 1.344 | 1 in 484,064 | 0.41 |
| success03 | calibration | 29 | 286 | 1 in 89,151 | 1 in 79,616 | 66.47 % ± 0.024 % | 1.504 | 1 in 134,121 | 0.60 |
| success04 | uniform p = 0.1 % | 30 | 312 | 1 in 817,295 | — | 77.76 % ± 0.013 % | 1.286 | 1 in 1,051,065 | — |
| success04 | spec sheet | 30 | 312 | 1 in 358,178 | 1 in 332,438 | 74.14 % ± 0.022 % | 1.349 | 1 in 483,130 | 0.41 |
| success04 | calibration | 30 | 312 | 1 in 89,380 | 1 in 79,753 | 66.18 % ± 0.024 % | 1.511 | 1 in 135,048 | 0.61 |
| success00 | uniform p = 0.1 % | 29 | 283 | 1 in 822,237 | — | 78.58 % ± 0.013 % | 1.273 | 1 in 1,046,329 | — |
| success00 | spec sheet | 29 | 283 | 1 in 370,063 | 1 in 342,937 | 74.37 % ± 0.022 % | 1.345 | 1 in 497,580 | 0.41 |
| success00 | calibration | 29 | 283 | 1 in 62,943 | 1 in 57,821 | 69.81 % ± 0.023 % | 1.432 | 1 in 90,158 | 0.57 |
| d3a6f2 (what if) | uniform p = 0.1 % | 27 | 248 | 1 in 1,224,966 | — | 78.06 % ± 0.013 % | 1.281 | 1 in 1,569,262 | — |
| d3a6f2 (what if) | spec sheet | 27 | 248 | 1 in 134,285 | 1 in 122,851 | 68.76 % ± 0.023 % | 1.454 | 1 in 195,293 | 0.57 |
| d3a6f2 (what if) | calibration | 27 | 248 | 1 in 66,424 | 1 in 59,541 | 64.49 % ± 0.024 % | 1.551 | 1 in 102,999 | 0.72 |
| G4 | uniform p = 0.1 % | 24 | 671 | 1 in 314,362 | — | 85.67 % ± 0.011 % | 1.167 | 1 in 366,945 | — |
| G4 | spec sheet | 24 | 671 | 1 in 90,830 | 1 in 88,786 | 78.98 % ± 0.020 % | 1.266 | 1 in 115,001 | 0.37 |
| G4 | calibration | 24 | 671 | 1 in 20,234 | 1 in 18,925 | 73.94 % ± 0.022 % | 1.352 | 1 in 27,364 | 0.63 |
| d3a6 (what if) | uniform p = 0.1 % | 22 | 415 | 1 in 620,124 | — | 85.25 % ± 0.011 % | 1.173 | 1 in 727,443 | — |
| d3a6 (what if) | spec sheet | 22 | 415 | 1 in 131,917 | 1 in 128,850 | 78.90 % ± 0.020 % | 1.267 | 1 in 167,197 | 0.37 |
| d3a6 (what if) | calibration | 22 | 415 | 1 in 25,068 | 1 in 24,159 | 79.18 % ± 0.020 % | 1.263 | 1 in 31,660 | 0.52 |

**Observations:**

- **The advantage holds.** success03 vs G4, the only Willow-valid pair compared like for like:

  | model | T error per kept shot, mfc 3 | mfc 4 | T error per attempt | attempts per kept shot |
  |---|---|---|---|---|
  | uniform p = 0.1 % | 2.9× lower | — | 3.2× lower | 1.274 vs 1.167 |
  | spec sheet | 4.0× lower | 3.8× lower | 4.2× lower | 1.344 vs 1.266 |
  | calibration | 4.4× lower | 4.2× lower | 4.9× lower | 1.504 vs 1.352 |

  - Under calibration noise, success03 is also 3.6 times better than d3a6 (what if) and 1.3 times better than d3a6f2 (what if).
- **Native conversion cost.** The CX → native conversion costs success03 a factor of 7.2 in T error at uniform p = 0.1 % (1 in 6,570,057 → 1 in 907,454; 16 → 29 TICKs). For G4 the factor is 6.5 (12 → 24 TICKs) and for d3a6 5.8. The extra H TICKs add idle and gate locations.
- **Realistic noise is far from uniform p = 0.1 %.**
  - **Expected faults per shot:** 0.37–0.41 (spec sheet) and 0.52–0.72 (calibration). A large single contribution is idling through the 800 ns mid-circuit MR: with median T1 and T2, px + py + pz ≈ 1.1 % per qubit there. The contributions were not broken down further.
  - **Truncation is no longer converged at 3 faults.** At mfc 4 the T error rises by 2–7 % for G4 and d3a6 and by 8–12 % for the flagged designs and d3a6f2. The mfc-3 numbers are the requested leading order; the success03 / G4 ratio changes by about 5 % between mfc 3 and 4 (4.4 → 4.2 calibration, 4.0 → 3.8 spec sheet). mfc 5 was not run.
  - **Spread across calibrated qubits.** success00 (1 in 62,943) and success03 (1 in 89,151) differ by 1.4× in the calibration model, against 1.03× in the spec-sheet model. Where a circuit sits on the chip matters at this level; the per-qubit cause was not analysed.
- **Readout asymmetry.** p11 (1.06 % median) is about 3 times p00 (0.37 %).
  - Exact asymmetric readout gives 1.1–1.6 percentage points higher acceptance than its symmetric mean in the calibration model (e.g. success03: 66.47 % vs 65.19 % ± 0.024 %).
  - This is consistent with most measured outcomes being 0.
  - The T error per kept shot uses the symmetric mean (enumeration limit, see above).
- **Counting the final stabiliser postselection as well** (cliffordea's "T kept" probability, calibration model): success03 55.07 %, G4 53.74 %, d3a6 59.65 %, d3a6f2 49.81 %. That is 1.816 vs 1.861 attempts per kept T state for success03 vs G4, so on that measure success03 needs *fewer* attempts than G4. Spec-sheet model: 66.76 % vs 69.31 %.
- **S state.** Calibration model, T vs S error per kept shot at mfc 3: success03 S 1 in 151,171, G4 S 1 in 83,085. The malignant S counts at ≤ 2 faults are 0 for all six designs.

**Figure** `figures/archive/comparison_willow_noise.png` (PNG 200 dpi): one group per design (success03, success04, success00, d3a6f2 what if, G4, d3a6 what if), with three bars per group: uniform p = 0.1 % native, spec sheet (hatched), and calibration (hatched). The panels are:
- (a) T error per kept shot, 1 in N, log axis;
- (b) acceptance (%);
- (c) T error per attempt, 1 in N.

## 5. Housekeeping

- **Full test suite** (`.venv/bin/python -m pytest -q nnflags/tests`): **102 passed** in 49.9 s (`logs/pytest_comparison.log`).
  - That is 95 earlier tests plus 7 new ones in `nnflags/tests/test_comparison.py`: odds route = cliffordea odds; rate assert and enumeration ≈ MC; the d3a4 discrepancy; native conversion keeps counts and round-trips (success03, d3a6); calibration loading and CZ subtraction; readout modes and recognised channels only.
- **cliffordea's own suite** under the downgraded packages (`pytest -q -p no:cacheprovider --rootdir=cliffordea cliffordea/tests`): **401 passed** in 18.6 s (`logs/pytest_cliffordea_comparison.log`).
  - The cache plugin was disabled so that nothing is written inside cliffordea. Bytecode goes to `./.pycache` via the venv's `00_pycache_prefix.pth`.
- **`requirements-lock.txt` regenerated from `.venv/bin/pip freeze`:** 60 → 91 lines.
  - Changed: pandas 3.1.0 → 3.0.6, contourpy 1.4.0 → 1.3.2.
  - Added: cirq-core 1.7.0, cirq-google 1.7.0, qsimcirq 0.22.1 and their dependencies (protobuf 6.33.6, grpcio 1.85.1, google-api-core 2.43.2, sympy 1.14.0, …).
  - Unchanged: stim 1.16.0, numpy 2.5.4, matplotlib 3.11.2.
  - Nothing was installed or uninstalled.

## Decisions made without you

1. **Acceptance definition.** "Acceptance" in the table is your definition (no inner detector fires), measured by Monte Carlo. cliffordea's "T kept" probability, which adds its noiseless final stabiliser postselection, is reported next to it, not instead of it.
2. **d3a4.** Its table row uses the stim acceptance of the circuit as written. Its cliffordea rate (taken from the earlier rounds and recomputed identically) still includes the 4 final readout flips; this is stated, not corrected.
3. **Monte Carlo shots.** 10,000,000 at p = 0.1 % and 4,000,000 elsewhere, fixed rather than adaptive. Every relative standard error is ≤ 0.04 %, well under the 1 % target. The seeds are a CRC32 of the design name and p (reproducible).
4. **Willow models.**
   - CZ error = XEB cycle − both 1q RB errors.
   - T2 derived as cirq_google does.
   - 1q gate 25 ns; **reset 200 ns and reset error 0.1 % are assumptions**; T2 = T1 in the spec-sheet model.
   - Idle noise also covers the remainder of a longer TICK, e.g. a qubit doing a 25 ns H in a 42 ns CZ TICK idles 17 ns. cliffordea's uniform model has no such term.
5. **Truncation.** The truncation stays at mfc 3, as requested; mfc 4 is reported as a check because it changes the realistic-noise rates by 2–12 %.
6. **Native form.** It was built with a new converter (`cx_to_native`), checked against `absorb_hadamards` and verify(). G4 keeps its own as-run native TICKs instead.
7. **Placements.**
   - **d3a6:** the minimum-conflict embedding from the earlier search. It was not re-optimised for calibration quality.
   - **d3a6f2:** the Step-1 placement, with non-couplers given the median CZ error.
   - **Successes and G4:** their saved coordinates. No search for better-calibrated regions was made (no new search).

## Files

- **Code:**
  - new: `nnflags/comparison.py` and `nnflags/willow_noise.py`;
  - extended: `nnflags/plots.py` (`--only comparison`: `fig_comparison_acceptance`, `fig_comparison_willow_noise`);
  - tests: `nnflags/tests/test_comparison.py`.
- **Data:** `results/comparison.json`, `results/willow_noise.json`, `results/willow_noise/<design>.native.inner.stim` and `<design>.<model>.noisy.stim`.
- **Figures:** `figures/archive/comparison_acceptance.png`, `figures/archive/comparison_willow_noise.png` (PNG only; there is no PDF in `figures/`).
- **Logs:** `logs/comparison.log`, `logs/willow_noise.log`, `logs/pytest_comparison.log`, `logs/pytest_cliffordea_comparison.log`, `logs/cliffordea_check_comparison.txt`.

## cliffordea untouched

```
$ git -C cliffordea status --porcelain --ignored
(empty output, exit code 0)        # logs/cliffordea_check_comparison.txt is 0 bytes
$ git -C cliffordea rev-parse HEAD
27385c688ed40d595eab4e2378dccb5c4d32dd9a
```
