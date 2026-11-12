> **Update (2026-10-31):** the readout rule was replaced by the strict live-interval rule (any measured qubit vs any live qubit on its r + c line). See [RESULTS_step3.md](RESULTS_step3.md) for the updated readout numbers, which supersede the readout results below.

# RESULTS — Steps 0–2 of first-ex.md (TASKS_nn_flags)

Run unattended on 2026-10-31, 06:00 pm – 06:12 pm KST. Steps 3 and later were **not** started.

| Step | Status | Why |
|---|---|---|
| 0 — reproduce baseline | **PASS** | d3a6: 4 malignant 2-fault configurations for T, 0 for S. d3a6f2: 0 malignant up to 2 faults for T (and S). Matches the plan exactly. |
| 1 — hardware model | **PASS** (with one finding) | Willow grid taken from Google's own device spec (105 qubits, 182 couplers, all nearest-neighbour). d3a6 passes the neighbour and degree checks on all 350 Willow placements. d3a6f2 fails exactly as the plan expects: 4 diagonal flag gates, qubit 6 with 6 partners, qubit 11 with 5. **Finding:** under the r+c readout rule as written, d3a6 itself has 1 readout conflict in every placement (see below). |
| 2 — custom verifier | **PASS** | `verify()` runs on cliffordea's own loader and enumeration code and reproduces Step 0 exactly: same summary table, same malignant fault indices, same rate. 9/9 pytest tests pass. |

Settings for every number below, unless stated otherwise: cultivated states S and T; noise model `enum.noise.uniformly_depolarize(INNER_CIRCUIT, noise_level=1e-3)` (cliffordea's uniform circuit-level depolarizing model, p = 1e-3, all TICKs noisy except the first and last); `FaultCombinator.get_kept_effects(..., max_fault_count=2)`; analyzer `CliffordLogicalAnalyzer` with default options.

---

## Step 0 — baseline (README "Complete enumeration workflow")

Code: `nnflags/step0.py`, a verbatim copy of the README workflow. Log: `logs/step0.log`. Results: `results/step0_{d3a6,d3a6f2}.json` and `*_summary.csv`. Ran at 06:02:53 pm KST.

### d3a6: `DoubleCheck(distance=3, ancilla_count=6)` (flag_count=0), max_fault_count=2

`FaultCombinator with 158 faults distributed among 19 detector signatures.`

```
                             configuration_count               weight
                                          benign malignant     benign malignant malignant_probability
cultivated_state fault_count
S                0                             1         0   1.000000      0.00              0.000000
                 1                             2         0   0.933333      0.00              0.000000
                 2                            34         0  14.208889      0.00              0.000000
T                0                             1         0   1.000000      0.00              0.000000
                 1                             2         0   0.933333      0.00              0.000000
                 2                            37         4   5.441111      0.21              0.037161
```

- **4 malignant 2-fault configurations for T and 0 for S**, as the plan expects. Fault distance for T is 2.
- Logical error rate per kept shot from `error_rates_per_kept_shot` at p = 1e-3, using the expansion truncated at 2 faults: T ≈ 0.000021 %, about **1 in 4.76 million**; S = 0 % (no malignant terms up to 2 faults).
- The 4 malignant T configurations, as (fault indices) → physical events from `combinator.index_to_events`. TICK numbers refer to the noisy circuit. Each one has acceptance 0.25 and fidelity 0.
  1. (74, 146): an X error on qubit 9 during the fold/unfold (TICK 3, 4, 8 or 9) plus a Y error on data qubit 0 at the last CX layer (TICK 10/11).
  2. (65, 148): an X error on data qubit 5 at TICK 3/4 plus a Y error on data qubit 8 at TICK 10/11.
  3. (111, 148): an X error on qubit 5 at TICK 8/9 plus a Y error on data qubit 8 at TICK 10/11.
  4. (54, 150): an X error on qubit 3 anywhere in TICK 3–9 plus a Y error on data qubit 7 at TICK 10/11.

  The X errors that need catching sit on qubits 3, 5 and 9, which is useful input for Step 3. The full event lists are in `results/step0_d3a6.json`.
- Timing: 0.03 s in total (building the circuit, analyzer and combinator 0.017 s; `get_kept_effects` 0.003 s).

### d3a6f2: `DoubleCheck(distance=3, ancilla_count=6, flag_count=2)`, max_fault_count=2

`FaultCombinator with 198 faults distributed among 50 detector signatures.`

```
                             configuration_count              weight
                                          benign malignant    benign malignant malignant_probability
cultivated_state fault_count
S                0                             1         0  1.000000       0.0                   0.0
                 1                             2         0  3.200000       0.0                   0.0
                 2                            37         0  4.671111       0.0                   0.0
T                0                             1         0  1.000000       0.0                   0.0
                 1                             2         0  3.200000       0.0                   0.0
                 2                            37         0  4.331111       0.0                   0.0
```

- **0 malignant configurations up to 2 faults for T** (and for S), as expected. Fault distance is at least 3 within the checked range.
- Logical error rate per kept shot at p = 1e-3, truncated at 2 faults: 0 % for both T and S.
- Timing: 0.03 s in total (`get_kept_effects` 0.002 s).

Nothing had to be adjusted: both numbers came out right on the first run with the README settings.

---

## Step 1 — hardware model (`nnflags/willow.py`, `nnflags/constraints.py`)

### Willow grid: source and status

- **Source:** Google's published device specification in Cirq, file `cirq_google/devices/specifications/willow_pink_d7v1-2024_08_16_device_spec_for_grid_device.proto.txt` from the `cirq-google==1.7.0` wheel. I downloaded it with `pip download` and did not install it into the venv. A copy is in `nnflags/data/` (sha256 `a9013ac5…cee5c`).
- The file lists **105 qubits** ("row_col") and **182 two-qubit couplers**. The couplers are **exactly** the pairs with |r−r'| + |c−c'| = 1, so the plan's definition of G matches Google's coupler list. This is checked in `tests/test_constraints.py::test_willow_matches_google_spec`.
- **Status: sourced, not an assumption.** One caveat is still open: I did not cross-check that this "willow_pink d7v1" snapshot is the same physical chip as in the Nature 2024 paper. The name (d7, Aug 2024) suggests it is. Nothing else depends on the exact list, because every function takes `grid=`.
- Layout (`#` = qubit; rows 0–12, cols 0–14):

```
 0 ......###......
 1 .....####......
 2 ....#######....
 3 ...########....
 4 ..###########..
 5 .############..
 6 ###############
 7 ..############.
 8 ..###########..
 9 ....########...
10 ....#######....
11 ......####.....
12 ......###......
```

### What `check_circuit(circuit, embedding, *, grid=WILLOW, max_degree=4, ignore_readout=False, data_in_use="persist")` checks

- It reports unmapped, non-injective and off-grid qubits.
- **non_neighbour:** any two-qubit gate whose endpoints are not an edge of G.
- **degree:** any qubit with more than 4 distinct two-qubit partners.
- **readout:** a qubit measured before the final measurement layer that shares r + c with a data qubit still in use. A qubit is not counted against itself.
- **reuse_in_tick:** a qubit used twice in one TICK.
- Passing `ignore_readout=True` (CLI: `python -m nnflags.step1 --ignore-readout`) turns the readout check off.
- `grid=None` checks the circuit's own QUBIT_COORDS geometry: a unit axis-aligned step counts as nearest-neighbour, and a diagonal step such as (1,1)–(1.5,0.5) does not.

### Results

Logs: `logs/step1.log` and `logs/step1_ignore_readout.log`. Results: `results/step1*.json` and `results/step1*.txt`. Runtime 42 s; almost all of it is the brute-force flag placement for d3a6f2.

**d3a6, native geometry:** 0 non-neighbour gates and 0 degree violations; max degree 4 (qubits 5 and 9). 1 readout conflict (see below).

**d3a6 on Willow:** there are 350 ways to place it (8 lattice symmetries × every translation that fits).
- **All 350 pass the neighbour, degree and reuse checks.**
- **All 350 have exactly 1 readout conflict.** The mid-circuit `MRX 5` at TICK 6 measures data qubit 5, the qubit holding the folded X parity. It always shares a readout line with one other data qubit: qubit 8 under id/rot180/transpose/antitranspose, and qubit 10 under the other four symmetries.
- With `--ignore-readout`, all 350 placements have 0 violations.

Primary embedding: native coordinates shifted by (+4,+4) (circuit qubit → Willow (r,c)):
`{0:(4,4), 1:(4,5), 2:(5,4), 3:(5,5), 4:(6,4), 5:(6,5), 6:(6,6), 7:(6,7), 8:(7,4), 9:(7,5), 10:(7,6), 11:(8,4), 12:(8,5)}`
Its only violation is `readout: tick=6, measured=5 at (6,5), data=8 at (7,4), line=11`.

**d3a6f2, native geometry (as in the paper):** this matches the plan's expectation exactly.
- **non_neighbour: 4 distinct diagonal flag gates**, CX 3→4, 6→4, 6→9 and 11→9, with flags at (1.5,0.5) and (2.5,0.5). Each is used twice (fold at TICK 3/4 and unfold at TICK 12/13), so there are 8 failing gate instances.
- **degree:** qubit 6 has **6** partners {3,4,5,7,9,11}; qubit 11 has **5** partners {6,9,10,12,14}.
- readout: 4 conflicts. `MRX 6` at TICK 8 conflicts with data qubit 10 (line 3). `M 4` and `M 9` at TICK 14 conflict with data qubits 3, 6 and 10.
- reuse_in_tick: none.

**d3a6f2 on Willow:**
- I kept the 13 shared qubits in the d3a6 primary placement (matched by native coordinates) and placed the 2 flags on the free Willow qubits that minimise first the number of non-neighbour gates, then the total gate length. Result: flag 4 → (5,6), flag 9 → (6,3).
- 6 non-neighbour gate instances remain: CX 6–4 and CX 6–9 / 11–9, each in fold and unfold. 2 degree violations remain (qubit 6: 6, qubit 11: 5). 3 readout conflicts.
- **These failures cannot be removed by placement:** qubit 6 has 6 partners and Willow allows at most 4. Flag 9's two partners (qubits 6 and 11) are adjacent to each other, so no grid point neighbours both, and here all their grid neighbours are already taken.

---

## Step 2 — custom-circuit verifier (`nnflags/verify.py`)

- `verify(stim_circuit_full, stim_circuit_inner, max_fault_count=2, noise_level=1e-3, states=("T","S"))` accepts either `stim.Circuit` objects or file paths.
- **Reuse, not reimplementation:**
  - It writes the two circuits to a temporary directory laid out like the bundled `stim_files/<name>/{inner,full}.stim`.
  - It then builds the object with cliffordea's own `LogicalMeasurement.__init__`, through a subclass that only overrides `_CIRCUIT_PARENT`. So DATA_INDICES, STABILIZER_GENERATORS and LOGICAL_S come from cliffordea's `find_data_indices`, `find_stabilizer_generators` and `find_logical_s_gate`.
  - After that it runs the README workflow unchanged: `uniformly_depolarize` → `CliffordLogicalAnalyzer` → `FaultCombinator.get_kept_effects` → `summarize_contributions` / `error_rates_per_kept_shot`.
  - The malignant/benign counts it returns are the `configuration_count` columns of `summarize_contributions`.
- It returns `{"T": {k: {"benign", "malignant"}}, "S": {...}, "summary", "error_rate_per_kept_shot", "malignant_configurations", "fault_count", "signature_count", "data_indices", "runtime_s", "settings"}`.

### verify() on the bundled files vs Step 0 (`python -m nnflags.step2`, `logs/step2.log`, `results/step2.json`)

| circuit | T malignant (k = 0/1/2) | T benign (k = 0/1/2) | S malignant (k = 0/1/2) | summary identical to Step 0 | same malignant fault indices | same T rate | runtime |
|---|---|---|---|---|---|---|---|
| d3a6 | 0 / 0 / **4** | 1 / 2 / 37 | 0 / 0 / 0 | yes | yes: (74,146), (65,148), (111,148), (54,150) | yes | 0.03 s |
| d3a6f2 | 0 / 0 / **0** | 1 / 2 / 37 | 0 / 0 / 0 | yes | yes (none) | yes | 0.03 s |

### pytest (`.venv/bin/python -m pytest -p no:cacheprovider -v nnflags/tests`, `logs/pytest.log`)

```
nnflags/tests/test_constraints.py::test_willow_matches_google_spec PASSED
nnflags/tests/test_constraints.py::test_d3a6_passes_neighbour_and_degree_on_every_willow_embedding PASSED
nnflags/tests/test_constraints.py::test_d3a6f2_native_failures_match_plan PASSED
nnflags/tests/test_constraints.py::test_d3a6f2_cannot_be_nearest_neighbour_on_willow PASSED
nnflags/tests/test_constraints.py::test_readout_rule_and_toggle PASSED
nnflags/tests/test_constraints.py::test_reuse_in_tick_detected PASSED
nnflags/tests/test_verify.py::test_verify_reproduces_step0[d3a6-0-4] PASSED
nnflags/tests/test_verify.py::test_verify_reproduces_step0[d3a6f2-2-0] PASSED
nnflags/tests/test_verify.py::test_verify_accepts_in_memory_circuits PASSED
============================== 9 passed in 32.48s ==============================
```

`test_verify_reproduces_step0` checks the following against the plain `DoubleCheck` path: the summary DataFrame (counts and weights) is identical, DATA_INDICES, STABILIZER_GENERATORS, LOGICAL_S and INNER_CIRCUIT are identical, and the fault and signature counts match.

As a health check of the environment, I also ran cliffordea's own suite: `tests/enum tests/accept` gave **327 passed in 15 s** (`logs/cliffordea_tests.log`). I ran it with `-p no:cacheprovider` and redirected bytecode, so nothing was written into the repo.

---

## Environment

- **Python 3.12.3**, local venv `./.venv` (`python3 -m venv`). The shared `/home/ubuntu/quantum001/venv` was not touched. conda is not installed.
- **cliffordea** commit **`27385c688ed40d595eab4e2378dccb5c4d32dd9a`** (2026-09-23, "Replace 'distance-three (-five)' with 'distance-3 (-5)'"); pyproject version 0.18.11.
- **Installed:** stim 1.16.0, numpy 2.5.4, pandas 3.1.0, scipy 1.18.1, pymatching 2.4.0, ldpc 2.4.1, symft 2026.10.8, sinter 1.16.0, tqdm 4.70.1, pytest 9.2.0, plus the rest of pyproject's dependency list (ipykernel, ipywidgets, matplotlib, snakeviz, statsmodels). Full pinned list: `requirements-lock.txt` (also `logs/pip_freeze.txt`).
- **How cliffordea is made importable without touching it:** cliffordea itself is **not** pip-installed, because an editable install could write build metadata into the checkout. Instead `.venv/.../site-packages/cliffordea_src.pth` points to `./cliffordea`.
- **Bytecode redirect:** `00_pycache_prefix.pth` sets `sys.pycache_prefix = ./.pycache`, so no `__pycache__` is created inside `./cliffordea`.

### cliffordea names used (file:line in `cliffordea/cliffordea/…`, commit above)

| name | defined at |
|---|---|
| `enum.circuits.DoubleCheck` | `enum/circuits/main.py:81` |
| `LogicalMeasurement` (and its `__init__`, used by verify) | `enum/circuits/main.py:11` (`__init__` at :17) |
| `_STIM_FILES_DIR` (located through `LogicalMeasurement.__init__.__globals__` to find the bundled files) | `enum/circuits/main.py:8` |
| `find_data_indices` | `enum/circuits/_base.py:4` |
| `find_stabilizer_generators` / `find_logical_s_gate` (called inside `LogicalMeasurement.__init__`) | `enum/circuits/_base.py:17` / `:43` |
| `enum.noise.uniformly_depolarize` | `enum/noise/main.py:9` |
| `accept.CliffordLogicalAnalyzer` | `accept/logical_analyzers.py:224` |
| `enum.FaultCombinator` | `enum/combinators/fault_combinator.py:101` |
| `FaultCombinator.get_kept_effects` | `enum/combinators/fault_combinator.py:236` |
| `FaultCombinator.summarize_contributions` | `enum/combinators/fault_combinator.py:413` |
| `FaultCombinator.error_rates_per_kept_shot` | `enum/combinators/fault_combinator.py:164` |
| `FaultCombinator.index_to_events` | `enum/combinators/fault_combinator.py:374` |
| `FaultCombinator.fault_count` / `.signature_count` | `enum/combinators/fault_combinator.py:369` / `:472` |
| `enum.circuit_tools.split_by_ticks` (TICK layers in constraints.py) | `enum/circuit_tools.py:54` |

---

## Decisions I made without you

1. **cliffordea is not pip-installed.** It is made importable through a `.pth` path, with bytecode redirected to `./.pycache`, so nothing is ever written inside `./cliffordea`. All pyproject dependencies were installed with pip instead of conda, because conda is not available.
2. **Willow grid source:** I used the cirq-google `willow_pink_d7v1-2024_08_16` device spec, which is official Google data, rather than reconstructing the grid from paper figures.
3. **Readout-line rule interpretation:**
   - "Final layer" = the last TICK that contains a non-MPP measurement.
   - Data qubits = the MPP targets (cliffordea's `find_data_indices`).
   - A data qubit counts as "still in use" after any mid-circuit measurement, because data qubits carry the state to the end and beyond. The option `data_in_use="ops"` instead requires a later operation on that qubit; it gives the same result for d3a6.
   - A measured data qubit is not compared with itself.
4. **MPP, annotations and noise channels are ignored** by the gate checks. MPP is cliffordea's noiseless marker for where data qubits enter, not a hardware operation.
5. **d3a6f2 has no grid coordinates for its flags.** Its Willow embedding reuses the d3a6 placement and puts the flags on the best free qubits (fewest non-neighbour gates, then shortest gates). In addition, the plan's expected failure list is reported from the circuit's own QUBIT_COORDS, where the 4 gates are literally diagonal.
6. **Primary d3a6 embedding:** native coordinates + (4,4), near the chip centre. All 350 placements are reported in aggregate.

## Problems found

- **d3a6 breaks the readout-line rule as written, in every Willow placement.** In this double check the X parity is folded onto **data qubit 5** and measured mid-circuit (`MRX 5`, TICK 6). Under r+c lines, qubit 5 always shares a line with data qubit 8 or 10. Because the rule is meant to be a hard constraint in the final ranking, **every candidate built from d3a6 would fail it** unless that measurement is moved or exempted.
- Nothing in cliffordea itself was broken. Its 327 enum/accept tests pass, and the README workflow ran as written.
- Minor: `summarize_contributions` orders rows by the `cultivated_states` order passed in. My first Step 2 text comparison said "not identical" for that reason only. I fixed the comparison (it now uses the README order); the numbers were always the same.

## Open questions for you

1. **Readout rule vs d3a6's mid-circuit MRX on data qubit 5:** should a mid-circuit measurement of a *data* qubit, which is reset and reused (`MRX`), be exempt? Or should the rule apply only to ancillas and flags? Or is the r+c definition meant differently, for example per row or with Willow's actual readout multiplexing groups? As written, no d3a6-based candidate can ever have `readout_violations == 0`.
2. Should data qubits count as "in use" for the whole circuit (my default) or only while they still have operations (`data_in_use="ops"`)?
3. Do you want the Willow list cross-checked against the Nature 2024 paper's figure or supplement? The cirq-google spec is Google's own, but I have not confirmed that it is the same physical device.

## cliffordea untouched

```
$ git -C cliffordea status --porcelain --ignored
(empty output, exit code 0)
$ git -C cliffordea rev-parse HEAD
27385c688ed40d595eab4e2378dccb5c4d32dd9a
```

## Files

- `nnflags/`: `__init__.py`, `willow.py`, `constraints.py`, `verify.py`, `step0.py`, `step1.py`, `step2.py`, `data/willow_pink_…proto.txt`, `tests/test_constraints.py`, `tests/test_verify.py`
- `results/`: `step0_*.json`, `step0_*_summary.csv`, `step1*.json`, `step1*.txt`, `step2.json`
- `logs/`: `step0.log`, `step1.log`, `step1_ignore_readout.log`, `step2.log`, `pytest.log`, `cliffordea_tests.log`, `pip_install.log`, `pip_freeze.txt`
- `requirements-lock.txt`

## Figures

All figures are in `figures/`, each saved as PNG (200 dpi). They are made by `nnflags/plots.py` (`.venv/bin/python -m nnflags.plots`, about 3 s). The script only reads `results/step0_*`, `results/step1.json` and `results/step2.json`. It rebuilds the circuits with `DoubleCheck` only to get their two-qubit gate lists, and it recomputes the Step 1 violations on the stored embeddings, asserting they match `results/step1.json`. Unless a figure says otherwise, the settings are: distance 3, ancilla_count 6, flag_count 0 (d3a6) or 2 (d3a6f2), max_fault_count 2, noise `enum.noise.uniformly_depolarize`, p = 0.001. Colours are the Okabe–Ito colour-blind-safe palette; benign bars are plain blue and malignant bars are vermilion with hatching. No figure was skipped, because all the data each one needs exists.

- `figures/step0_configurations.{png,pdf}` (F1): kept configuration counts per fault count (0, 1, 2), benign vs malignant, for d3a6 and d3a6f2, with one panel for cultivated state T and one for S. Every bar is labelled with its count, so the only malignant bar (4 for d3a6, T, 2 faults) stands out, and every other malignant bar is a labelled 0.
- `figures/archive/step0_malignant_weight.{png,pdf}` (F2): for state T, the malignant weight per fault count (accept-weighted coefficient of p^k from `summarize_contributions`) and the malignant share of kept weight (%), d3a6 vs d3a6f2. d3a6 has 0.21 (3.72 %) at 2 faults and d3a6f2 has 0. The footnote gives the logical error per kept shot at p = 0.001, truncated at 2 faults: d3a6 1 in 4,760,490, d3a6f2 0.
- `figures/willow_grid.{png,pdf}` (F3): the 105-qubit / 182-coupler Willow grid from Step 1, with row 0 at the top. Qubits are dots, couplers are lines, and readout lines r + c (6–20) are light dashed diagonals labelled with their index. A note gives the source (cirq-google 1.7.0 `willow_pink_d7v1-2024_08_16` device spec) and says that r + c is first-ex.md's definition. Before drawing, the script asserts that the grid matches the spec file.
- `figures/archive/embedding_d3a6.{png,pdf}` (F4): d3a6 on Willow in the Step 1 primary placement (native coordinates + (4, 4)). Circuit qubit labels sit on the physical qubits (circles = data, squares = ancillas), and all 12 distinct two-qubit gates lie on couplers. The single readout-line conflict is drawn as a green dotted segment: `MRX 5` at (6, 5) at TICK 6 vs data qubit 8 at (7, 4), line 11.
- `figures/archive/embedding_d3a6f2.{png,pdf}` (F5): (a) d3a6f2 on Willow in the Step 1 placement, with flags 4 → (5, 6) and 9 → (6, 3). The 3 distinct non-neighbour gates (6–4, 6–9, 11–9) are drawn as dashed vermilion arcs. Qubits 6 and 11 have a red outline and are annotated "6 partners" and "5 partners". The 3 readout conflicts on line 11 are drawn green. (b) The same circuit on its native QUBIT_COORDS, with the 4 diagonal flag gates (3–4, 6–4, 6–9, 11–9) and the 4 native-coordinate readout conflicts (lines 2 and 3). The circuit can be placed on the grid, but not without violations: qubit 6 has 6 partners and Willow allows at most 4.
- `figures/archive/step2_verify_check.{png,pdf}` (F6): benign/malignant counts per fault count from Step 0 (`DoubleCheck`) and from Step 2 (`verify()` on the bundled Stim files), side by side. There is one panel for each combination of d3a6/d3a6f2 and T/S, and each panel title reads "identical". The footnote confirms from `results/step2.json` that the full summary table, the malignant T fault indices and the T rate also match.

Plotting decisions: the palette validator from the dataviz guidance could not be run because `node` is not installed, so I used the published Okabe–Ito palette and added hatching and marker shapes for redundancy. In F5(a) the non-neighbour gates are drawn as arcs that bend away from the other qubits, so they do not look like they pass through qubits 5 or 10. Readout-line indices are given in the legend of F4 and F5 rather than on the grid, where they would overlap the qubits.
