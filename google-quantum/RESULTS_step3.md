# RESULTS — strict readout rule, impossibility check, Google cross-checks, Step 3 (first-ex.md)

Run unattended on 2026-10-31, 09:17 pm – 10:55 pm KST. Step 4 was **not** started.

| Task | Status | One line |
|---|---|---|
| A — strict readout rule + live intervals | **PASS** | Implemented in `constraints.py` (strict default, `readout="ignore"` / `--readout ignore` / `--ignore-readout` toggle). 37 tests pass (`logs/pytest_step3.log`). d3a6: 1 strict conflict at the primary placement; 1 or 2 across the 350 placements; 0 with readout ignored. |
| B — impossibility check | **PASS (argument confirmed)** | All **182,968** injective nearest-neighbour embeddings of d3a6 onto Willow were enumerated. **Minimum strict conflicts = 1**, so none has 0. In **every** embedding, MRX 5 (TICK 6) hits one of 8, 10 or 12 on the grid point diagonal to 5 and adjacent to 9. |
| C — layout cross-check + Google circuit | **PASS / PARTIAL** | Layout: our 105-qubit list is identical, row by row, to Google's Willow spec-sheet grid, with the same (row, col) labels. Google's March 2026 guidance states the r + c readout lines verbatim. Crumble link found and converted; it is **identical to cliffordea's bundled d3a4**. Its neighbour/degree check passes. verify() gives fault distance 2 (12 malignant 2-fault T configurations). **Expected 0 readout conflicts, got ≥ 1:** every one of its 38,640 Willow embeddings has exactly 1. Google's own as-run cultivation circuit (Rosenfeld et al. Fig. 2) has **0** at its real Willow coordinates. |
| D — figures | **PASS** | The dotted line style is fixed in F4, F5(a) and F5(b). All figures were regenerated under the strict rule, with the readout mode in each footnote. New: F7 (Google circuits on Willow), F8 (histogram over all embeddings), F9 (Step 3 counts). |
| E — Step 3 candidate generator | **PASS** (generator); **0 candidates pass strict readout** | `nnflags/candidates.py`, 12 unit tests. Counts per category are below. Everything that passes neighbour/degree/reuse passes with readout ignored; **nothing** passes strict readout, as task B predicts. Options for you are listed at the end. |

Settings used throughout, unless a line says otherwise: distance 3, ancilla_count 6, flag_count 0 (d3a6) or 2 (d3a6f2); Willow 105-qubit grid; readout mode **strict** with the final measurement layer exempt. For verify() runs: max_fault_count 2, cultivated states T and S, noise `enum.noise.uniformly_depolarize` (cliffordea `enum/noise/main.py:9`), p = 0.001.

---

## A. Strict readout rule with per-qubit live intervals

### Rule as implemented (`nnflags/constraints.py`: `liveness`, `readout_violations`, `check_circuit`)

- **Readout line** = r + c. This is now Google's documented rule, not only first-ex.md's (see C).
- **Conflict.** At every mid-circuit measurement of a qubit m in TICK t, every **other** qubit on m's line that is **live** in TICK t is a violation. The roles of m and the victim do not matter: data, ancilla and flag all count. Each violation records `tick, measured, measured_at, victim, victim_at, victim_role, line`.
- **Live interval** (your answer 2):
  - A qubit becomes live at its preparation: a reset (R/RX/RY), an MR*, or its first gate if it has no reset.
  - A measurement without reset (M/MX/MY) ends liveness until the next reset or gate.
  - MR/MRX/MRY measure and reset, so the qubit stays live.
- **MPP injection marker** (decision, your default): data qubits, i.e. cliffordea's `find_data_indices` (`enum/circuits/_base.py:4`), are **live from the start of the circuit**, because they hold the injected state. The noiseless MPP is not a hardware operation and is ignored by every gate check.
- **Same TICK.** Qubits measured or reset in the same TICK as m are not victims. A simultaneous readout of the line, or a reset, does not damage them. This is also how Google's own circuits measure several qubits of one line at once (see C).
- **"Mid-circuit"** means before the final measurement layer, as first-ex.md defines it. `final_layer="check"` also checks the final layer. I report it as a second number because the data qubits continue after the double check.
- **Optional refinement, off by default:** `z_reset_idle="not_live"`. After a Z-basis reset (R, MR), a qubit is in |0⟩, which readout dephasing cannot disturb, so it only becomes live at its next gate. I added this because Google's guidance talks about "preserving the coherence" of other qubits, and because it is exactly what separates Google's G5 circuit from a 0 count (see C). The default stays your literal rule.
- **Toggle:**
  - `check_circuit(..., readout="strict" | "ignore")`. The old `ignore_readout=True` still works.
  - CLI: `python -m nnflags.step1 --readout strict|ignore [--final-layer exempt|check]`. `--ignore-readout` is still accepted.
  - The old `data_in_use` option was removed, because the new live intervals replace it.
- **Fix found on the way:** `_hardware_ops` used to pass annotations such as `QUBIT_COORDS` through as "gates". That made every qubit live at TICK 0. It now keeps only unitary gates, resets and measurements.

### Tests

New file `nnflags/tests/test_readout.py` (11 tests) uses hand-made circuits on one readout line. They cover:
- a victim that is live vs one not yet prepared;
- first gate as preparation;
- MR keeping the qubit live;
- ancilla-vs-ancilla conflicts;
- M without reset ending liveness until the next R;
- the measured qubit never being its own victim, and simultaneous readout;
- a reset in the same TICK not being a victim;
- other lines;
- the final layer exempt vs checked;
- a data qubit measured without reset;
- the strict/ignore toggle;
- d3a6 native.

`nnflags/tests/test_crumble_embed.py` (5 tests) covers the Crumble converter, the `z_reset_idle` refinement, the d3a4 equality and the embedding search.

**Existing test changed because of the new rule:** only `test_constraints.py::test_readout_rule_and_toggle`. The violation key `data` became `victim`, and the test now also checks `readout="ignore"`. Its expected pair, (5, 8), is unchanged.

Full suite (`logs/pytest_step3.log`): **37 passed**. Of these, 9 are the earlier tests, all still passing; the rest are 11 readout, 5 Crumble/embedding and 12 candidate tests.

### Step 1 rerun (`logs/step1.log`, `logs/step1_readoutignore.log`, `logs/step1_finallayercheck.log`; `results/step1*.json`; old-rule outputs kept in `results/legacy_rule_steps0-2/`)

| circuit / placement | readout ignore | strict (final layer exempt) | strict, final layer checked | old data-only rule (Steps 0–2) |
|---|---|---|---|---|
| d3a6 native coordinates | 0 | **1**: MRX 5 (TICK 6) vs data 8 | 6 | 1 |
| d3a6 primary placement (native + (4, 4)) | 0 | **1**: MRX 5 at (6, 5) vs data 8 at (7, 4), line 11 | 6 | 1 |
| d3a6, 350 rigid placements | 0 in all 350 | 1 in 180 (id, rot180, transpose, antitranspose); **2** in 170 (rot90, rot270, flip_r, flip_c) | 6 in 180, 8 in 170 | 1 in all |
| d3a6f2 native coordinates | 0 (plus 8 non-neighbour, 2 degree) | **6** | 11 | 4 |
| d3a6f2 on Willow, flags placed per mode | 0 (flags 4 → (5, 6), 9 → (6, 3)) | **4** (flags 4 → (5, 6), 9 → (7, 7)) | 9 | 3 |
| d3a6f2 on Willow, ignore-mode flag placement | 0 | 6 | 11 | — |

- **Neighbour/degree/reuse results are unchanged.** d3a6 passes on all 350 placements. d3a6f2 still has 4 distinct diagonal gates natively (6 non-neighbour instances on Willow), qubit 6 with 6 partners and qubit 11 with 5.
- **What the strict rule adds:**
  - **Ancilla and flag victims.** In the 170 placements with 2 conflicts, MRX 5 also hits **ancilla 12** (or 2). In d3a6f2, MRX 6 also hits **flag 4/9**, and the flag readout `M 9` at TICK 14 hits ancillas 1 and 2.
- `extend_embedding` minimises non-neighbour gates, then gate length, then total violations. So the flag-9 spot of d3a6f2 differs by mode: (7, 7) under strict, (6, 3) under ignore. Both are listed above.

---

## B. Impossibility check — **confirmed**

Code: `nnflags/embed_search.py` (`python -m nnflags.embed_search --circuit d3a6`). Log: `logs/embed_search_d3a6.log`. Data: `results/embed_search_d3a6.json`. Runtime 3.7 s.

- d3a6's interaction graph has 13 qubits and 12 distinct CX pairs, and it is a **tree**: 0–1, 1–3, 2–3, 3–5, 4–5, 5–6, 5–9, 6–7, 8–9, 9–10, 9–12, 11–12.
- The search is a backtracking subgraph-embedding search. It starts from a degree-4 qubit and places each next qubit on a free grid neighbour of its already placed partner. It covers every injective map in which every CX lands on a Willow coupler, not only the 350 rigid placements.
- **Count: 182,968 injective nearest-neighbour embeddings.**
- A fast counter scored each embedding with the same live sets as `readout_violations`. It was checked against `check_circuit` on 184 sampled embeddings, plus 37 more in the unit test; they agreed.

| readout mode | min conflicts | histogram (conflicts: embeddings) |
|---|---|---|
| strict, final layer exempt | **1** | 1: 47,424 · 2: 135,544 |
| strict, final layer checked | **4** | 4: 29,220 · 5: 20,816 · 6: 18,908 · 7: 39,280 · 8: 34,840 · 9: 27,232 · 10: 9,504 · 11: 3,168 |

- **No embedding has 0 strict conflicts.** The only mid-circuit measurement is MRX 5 at TICK 6. At that moment all 12 other qubits are live: the 7 data qubits from the start, and the 6 RX-prepared ancillas until the final MX, apart from 5 itself.
- **The mechanism matches the main session's argument in all 182,968 of 182,968 embeddings.** 9 has 4 partners (5, 8, 10, 12), so on a degree-4 grid all 4 of its neighbours are occupied. Of 9's two side neighbours, exactly one lies on 5's r + c line, diagonal to 5, and it holds 8, 10 or 12, which are live at TICK 6.
- Victims per embedding:
  - 10: 64,996;
  - 8: 64,996;
  - 2: 57,240;
  - 12: 52,976;
  - 1: 43,128;
  - 7: 35,176.

  An embedding can have 2 victims.
- The argument uses nothing specific to Willow. It needs only a square grid with degree ≤ 4 and lines r + c, so it holds on any square grid. With the optional `z_reset_idle` refinement nothing changes either, because every victim is a data qubit or an RX-prepared ancilla.
- Consequence: **every circuit that contains d3a6's interaction tree with MRX 5 at a time when 8/10/12 are live has ≥ 1 strict conflict.** That covers every Step 3 candidate.

---

## C. Layout cross-check and Google-circuit validation

### C1. Willow layout and (row, col) convention — **match**

| source | URL | result |
|---|---|---|
| Willow spec sheet, "Published Dec 9, 2024", p. 2 "Qubit grid" | https://quantumai.google/static/site-assets/downloads/willow-spec-sheet.pdf | The grid diagram labels every qubit "r, c", with the note *"The numbers inside the qubit grid refer to the row and column index"*. I read the rendered page myself: rows 0–12 have column ranges 6–8, 5–8, 4–10, 3–10, 2–12, 1–12, 0–14, 2–13, 2–12, 4–11, 4–10, 6–9, 6–8. That is **identical to `nnflags/willow.py`**, with the same orientation (row 0 at the top, col 0 at the left), so there is no rotation or transpose. |
| Hardware Experiment Proposal Guidance, March 2026 | https://quantumai.google/static/site-assets/downloads/willow-early-access-program-instructions.pdf | Same grid on p. 1. Readout, verbatim: *"Readout lines run diagonally across the chip (i.e., such that in the diagram on page 2 of the spec sheet, row+col = const). Measuring any qubit on a readout line dephases the whole readout line. This is why in Google's error correction experiments (e.g., this one), the data and measure qubits are on separate readout lines."* Also: *"Experiments should not contain mid-circuit measurements while trying to preserve the coherence of other qubits on the same readout line (readout lines run diagonally from the bottom left to upper right of the chip). However, reset gates are allowed."* |
| Proposal guidance, Dec 2025 (UK/NQCC version) | https://quantumai.google/static/site-assets/downloads/hardware-experiment-proposal-guidance.pdf | Same labelled grid on p. 1. |
| Acharya et al., "Quantum error correction below the surface code threshold", arXiv:2408.13687v1 (Nature 638, 920) | https://arxiv.org/abs/2408.13687 | Fig. 1a is drawn rotated by 45° and has no labels. It contains 49 data + 48 measure + 4 leakage-removal + 4 unused = 105 qubits, and the set matches ours up to a rotation the figure cannot fix. Data qubits fall on odd r + c and all others on even r + c, consistent with "separate readout lines". The supplement has no readout-line or multiplexing statement. I checked arXiv v1 only, not the Nature version. |
| Cirq `program.py` (v1.7.0) | cirq-google `cirq_google/api/v2/program.py` | GridQubit id is `f'{q.row}_{q.col}'`, so the "row_col" ids of our spec file are (row, col). |

- Not reachable: https://quantumai.google/hardware (404). GitHub code search needed authentication (401). Fetches from Cirq's main branch hung.
- Local copies, untrusted downloads kept out of the repo: the scratchpad folder `/tmp/claude-1000/-home-ubuntu-quantum001-google-quantum/c75c77f0-fa5b-4bf2-9337-caf4a4727ecc/scratchpad/willow_xcheck/`. It has the four PDFs (sha256 spec sheet `53f451a5…aab2e4`, March 2026 guidance `a5f95bca…d14142`), page renders and `sources.md`.
- **Conclusion:** the cirq-google `willow_pink_d7v1` list, its (row, col) convention and the r + c readout rule all agree with Google's own documents.

### C2. The Crumble link of Chan, Strikis, Sun & Cai, arXiv:2609.17706v3, Section 5 — found

- **Paper:** "Diagnosing and Restoring the Degraded Fault Distance of Magic State Cultivation", v3 of 30 Sep 2026. https://arxiv.org/abs/2609.17706 and its HTML and PDF versions have the same link, byte for byte.
- **Sentence:** *"This degraded fault distance is experienced also by the distance-3 double check used in the experimental realisation of MSC [8] (Crumble link here): applying the same analysis to this slightly smaller circuit, we find it also has fault distance 2."* Ref. [8] = Rosenfeld et al., "Magic state cultivation on a superconducting quantum processor", arXiv:2512.13908 (Google).
- **The link (1,107 characters)** is stored verbatim in `nnflags/data/google_circuits/chan2609_sec5_experimental_double_check.url.txt`. `nnflags/crumble.py` converted it to `…full.stim`.
- **It is identical, as a `stim.Circuit`, to cliffordea's bundled `double_checks/d3a4/full.stim`.** cliffordea's docstring says the same: ``(3, 4, 0)`` "is the circuit used in experimental MSC [Rosenfeld2026]" (`enum/circuits/main.py:89`).
  - Its gate sequence equals the bundled `d3a4/inner.stim`, once the MPP framing and S layers are dropped and `MX 8; TICK; RX 8` is merged into `MRX 8`.
  - 11 qubits: data 0, 1, 4, 5, 6, 9, 10; ancillas 2, 3, 7, 8.
- The URL encodes the full (framed) circuit, so verify() used `full` = the converted Crumble circuit and `inner` = cliffordea's bundled `d3a4/inner.stim`.

Results (`python -m nnflags.google_check`; `logs/google_check.log`; `results/google_check.json`; `results/embed_search_d3a4.json`):

- **Neighbour/degree:** its native coordinates are a 45°-rotated lattice. Mapping (x, y) → (x + y, y − x) gives 0 non-neighbour gates and 0 degree violations; max partners 4 (qubits 5 and 8).
- **Strict readout: expected 0, found ≥ 1 everywhere.**
  - All **38,640** nearest-neighbour embeddings of its interaction tree onto Willow have **exactly 1** strict conflict, whether the final layer is exempt or checked. So do the 404 rigid placements of the rotated layout.
  - The conflict is always the mid-check measurement of ancilla 8 (TICK 6 of the inner circuit; `MX 8` in the full one) hitting an RX-prepared ancilla: 2 in 14,688 embeddings, 7 in 14,544, 3 in 9,408.
  - The cause is the same as for d3a6. Ancilla 8 has 4 partners (5, 6, 9, 10), so its diagonal grid points, one of them on its own line, are filled by circuit qubits.
- **verify()**, max_fault_count 2, uniformly_depolarize p = 0.001:

  | state | k = 0 | k = 1 | k = 2 |
  |---|---|---|---|
  | T, benign / malignant | 1 / 0 | 7 / 0 | 129 / **12** |
  | S, benign / malignant | 1 / 0 | 7 / 0 | 115 / 0 |

  So **fault distance 2** for T, as the paper says. Other numbers: 195 faults. T logical error per kept shot (truncated at 2 faults) ≈ 0.000028 %, **1 in 3,583,893**; S: 0.

### C3. Google's own as-run circuits (Rosenfeld et al., arXiv:2512.13908 appendix) — 0 conflicts

- **Source.** The agent that read Chan et al. also followed ref. [8], https://arxiv.org/html/2512.13908, which links the circuits actually run. All 7 links are stored verbatim in `nnflags/data/google_circuits/rosenfeld2512_crumble_urls.txt` (G0–G6 in paper order).
- **Coordinates.** G4 (Fig. 2 cultivation), G5 (Fig. 3 kickback tomography) and G6 (Fig. 4 grafting) use coordinates that all lie on Willow. They use CZ + H, measure in Z and are reset with R, with no MPP. G0–G3 are element sketches on abstract coordinates.
- **Willow reference.** Because r + c is symmetric under a transpose, the conflict counts do not depend on whether Crumble's (x, y) means (row, col) or (col, row).

| circuit | qubits | neighbour / degree | strict, final exempt | strict, final checked | strict + `z_reset_idle="not_live"` | conflicts if lines were r − c / rows / cols |
|---|---|---|---|---|---|---|
| **G4** Fig. 2 cultivation (as run) | 12 | 0 / 0 (max 4) | **0** | **0** | 0 | 2 / 16 / 13 |
| G5 Fig. 3 kickback tomography | 14 | 0 / 0 | 12 | 12 | **0** | 15 / 106 / 77 |
| **G6** Fig. 4 grafting N = 2 | 54 | 0 / 0 | **0** | **0** | 0 | 2 / 126 / 106 |

- **G4 passes the strict rule.** Its mid-circuit measurements are `M 1 4 6 9` (TICK 25) and `M 6 9` (TICK 40). The qubits in each group sit pairwise on the **same** lines, 16 and 18, are measured simultaneously, and no other G4 qubit lies on those lines. This is the hardware-validated pattern.
  - G4's double check measures the folded parities on **two** qubits, 6 and 9, each with its own detector.
  - Chan et al.'s d3a4 instead folds onto a **single** degree-4 ancilla, 8. In this sense the "slightly smaller circuit" is not a copy of the hardware placement.
- **G5's 12 conflicts are all of one kind.** Qubit 4 is reset at TICK 51 (and 106, 161), idles in |0⟩ without any gate until its next reset 30 TICKs later, and meanwhile `M 8 11` (TICK 65/80, …) on line 10 "hits" it. Under the optional `z_reset_idle="not_live"` refinement, G5 has 0.
- **Line orientation.** Only r + c gives 0 for G4 and G6. The alternatives r − c, rows and columns all give conflicts, which supports r + c independently of the documents.

---

## D. Figures (`python -m nnflags.plots`, ~10 s; PNG 200 dpi in `figures/`)

- **Line style fixed.** Readout-conflict segments were drawn with `annotate(..., arrowprops=dict(ls=...))`. Matplotlib's FancyArrowPatch drops that dash pattern, so they came out solid. They are now drawn with `ax.plot` in one shared dotted style (`READOUT_LINE`), used for the plot and the legend alike. The non-neighbour arcs had the same problem and are now real dashed quadratic Béziers. I checked the rendered PNGs: dotted in F4, F5(a), F5(b) and F7(b).
- Every Willow/embedding footnote now states: *"Readout rule: strict (measuring any qubit dephases its r + c line; victims = other qubits live at that TICK, any role; final measurement layer exempt)."*
- **Unchanged content:** F1 `step0_configurations`, F2 `step0_malignant_weight`, F6 `step2_verify_check`. They have no readout content and are regenerated as is.
- F3 `willow_grid`: the source note now cites the spec sheet (same grid and labels) and the March 2026 guidance (r + c lines).
- F4 `embedding_d3a6`: 1 strict conflict, drawn dotted. The footnote gives 1 in 180 / 2 in 170 rigid placements, and ≥ 1 in all 182,968 embeddings.
- F5 `embedding_d3a6f2`: (a) 4 strict conflicts on line 11, including flag 4 as a victim of MRX 6; (b) 6 native-coordinate conflicts (lines 2 and 3). All dotted.
- **F7 `google_circuits_on_willow` (new):**
  - (a) Google's as-run Fig. 2 cultivation circuit at its Willow coordinates. CZ couplers, the mid-circuit measured qubits (hatched diamonds) and their readout lines 16 and 18 are shown; **0 strict conflicts** (exempt and checked).
  - (b) The Chan et al. Sec. 5 circuit (= d3a4) in its best Willow embedding, with its unavoidable conflict (M 8 vs ancilla 2, line 7) and the verify() result (12 malignant 2-fault T configurations).
- **F8 `embedding_readout_histogram` (new):** strict-conflict histogram over all 182,968 d3a6 embeddings, final layer exempt vs checked, and over all 38,640 d3a4 embeddings. The bar at 0 is empty in every panel.
- **F9 `step3_candidates` (new):** Step 3 candidates per category, showing generated, passing neighbour/degree/reuse (= passing with readout ignored) and passing strict readout, on a log scale with plain-number ticks.

---

## E. Step 3 — candidate generator (`nnflags/candidates.py`)

Run: `nohup .venv/bin/python -m nnflags.candidates --workers 12`, 09:37 pm – 10:52 pm KST (4,529 s). Log: `logs/step3_candidates.log`. Summary: `results/step3_summary.json`. Per-candidate rows: `results/step3_candidates.csv.gz` (258,115 rows). The rows cover all of (c), (b) and a1, and every a2 pair that contains a hook flag. The other 3.6 M a2 pairs and the a3 sample are counted in aggregate only, to keep the CSV at 23 MB. verify()-sample circuits: `results/step3_sample/`.

### What the generator does (exactly the plan's three categories)

**(a) Z flags.** A flag f is a **free** Willow qubit adjacent to an existing qubit q. It gets `CX q f` at two slots t1 < t2 among the fold/unfold TICKs 2..10.
- **Slots.** A slot is either an existing TICK where q is idle (in place) or a **new TICK inserted** between TICKs k and k + 1 (k = 2..9). `added_ticks` = number of distinct inserted slots.
- **Validity.** A pair (t1, t2) is kept only if q is nothing but a CX *control* strictly between t1 and t2. Otherwise Z_q changes and the flag is not a deterministic detector; stim confirms this for every generated single flag, and a unit test checks the rejected case.
- **Ops around the CXs**, following d3a6f2's convention:
  - `R f` in the layer before t1;
  - `M f` either in the layer right after t2 ("next") or in the final MX layer ("final");
  - a `DETECTOR` on `M f`;
  - f joins the trailing R layer.
- **Detector lookbacks** are rebuilt from global measurement ids, so inserted measurements and TICKs never shift the original detectors. A test checks this.
- **Order.** Hook qubits 3, 5, 9 are generated first.

**(b) Fold permutations, keeping the time-reversal structure.**
- At the **layer level** (the plan's wording), the only order of the 4 fold layers (TICKs 2..5) that keeps the fold unitary is the **identity**. No two fold layers commute, which a stim tableau check confirms.
- I therefore also enumerated the gate-level version: every assignment of the 12 fold CXs to 4 layers, with no qubit twice per layer, that has the same fold unitary. The unfold is always the exact time reverse.
- That gives **6 folds (5 new)**. They are the 3! orders of 9's three commuting CXs 9→8, 9→12, 9→10, with CX 12→11 always before CX 9→12.

**(c) Re-embeddings.** All **350** rigid placements (8 rotations/reflections × translations). Flags (a) are generated on one central placement per symmetry, 8 in total, with the primary placement (native + (4, 4)) as the `id` representative.

### Counts (strict = strict readout with the final layer exempt; ignore = readout ignored)

| category | candidates | pass neighbour / degree / reuse | pass **ignore** readout | pass **strict** readout | strict conflicts per candidate |
|---|---|---|---|---|---|
| (c) re-embeddings, no flags | 350 | 350 | 350 | **0** | 1: 180 · 2: 170 |
| (b) fold re-layerings, primary placement, no flags (layer-level permutations: identity only) | 5 | 5 | 5 | **0** | 1: 5 |
| (a) 1 flag, 8 placements × 6 folds | 134,848 | 134,848 | 134,848 | **0** | min 1 (1: 46,020 · 2: 51,300 · 3: 11,408 · 4: 19,516 · 5: 5,092 · 6: 1,512) |
| (a) 2 flags, primary placement, original fold (all pairs with distinct flag positions) | **3,716,448** | 3,650,224 | 3,650,224 | **0** | min 1 (1: 1,413,663 · 2: 745,570 · 3: 594,088 · 4: 688,523 · 5: 123,747 · 6: 111,002 · 7: 37,097 · 8: 2,758) |
| (a) 3 flags, primary placement: exact count | **3,010,264,016** | not enumerated | — | **0 by task B** | — |
| (a) 3 flags, random sample (half contain a hook flag; seed 20261031) | 20,000 | 19,260 | 19,260 | **0** | min 1 |

Notes on the counts:
- **Exact totals for pairs and triples.** For each (placement, fold) these are the elementary symmetric polynomials of the number of flags per flag position. A unit test checks them against brute force. On the primary placement and original fold there are 2,828 single flags, 3,716,448 pairs and 3,010,264,016 triples. The enumerated pair count matches the formula exactly.
  - Pairs per fold variant (primary placement): 3,716,448 / 3,662,896 / 3,172,528 / 3,896,560 / 3,387,760 / 4,068,096.
  - Pairs on the other 7 placements (original fold): 3,716,448 each.
  - **Not enumerated:** pairs on the other 7 placements and 5 fold variants (about 27 M more), and all 3-flag sets. Strict readout fails for all of them by task B.
- **Why pairs fail neighbour/degree/reuse.** All 66,224 failures are **reuse_in_tick**: two flags on the same control q sharing a slot. No degree failure is possible, because a qubit with two free neighbours has at most 2 partners. Neighbour failures cannot occur by construction.
- **Extra readout columns.** No candidate in any category passes with the final layer checked either, nor with the optional `z_reset_idle="not_live"`.
- **By symmetry (a1).** The 4 symmetries whose MRX-5 victim is a data qubit (id, rot180, transpose, antitranspose) have 11,505 of 16,856 single-flag candidates at the minimum of 1 conflict. The other 4 have a minimum of 2.

### Hook-error prioritisation (Step 0: X hooks on qubits 3, 5, 9)

- **Qubits 5 and 9 can never get a Z flag of the plan's type.** Each has 4 partners, so on a degree-4 grid all of its grid neighbours are occupied. This holds in all 350 placements and in fact in all 182,968 embeddings, and a unit test checks it. A flag CX would also give them a 5th partner.
  - Their slot pairs exist only as inserted TICKs anyway: 5 is busy in every fold/unfold TICK, and 9 is idle only in TICK 6.
- **Qubit 3** has exactly 1 free neighbour in 340 of 350 placements, (5, 6) in the primary one, and 23 valid slot pairs. Hence 46 hook singles per (placement, fold): 2,208 among the a1 candidates, 122,912 hook-containing pairs, and 10,491 in the a3 sample.
- Free neighbours per qubit over the 350 placements are in `results/step3_summary.json` (`free_neighbours_per_qubit_over_350_placements`). Qubit 7 has the most (3 in 268 placements).

### verify() sample (20 calls, only to check that verify() accepts the generated circuits; not a search)

- **Circuits:** the 6 primary hook flags on qubit 3, 6 pairs (hook flag + random flag), 4 random single flags, and 4 fold variants.
- **Acceptance:** verify() ran on all 20 without error. Settings: `full` = bundled d3a6 full.stim, max_fault_count 2, uniformly_depolarize p = 0.001. Every sampled circuit is deterministic.
- **Malignant 2-fault T counts in the sample**, recorded as an observation and not analysed further:
  - 4 for every flagged circuit, i.e. no change from d3a6 for these particular flags;
  - 5 for each of the 4 fold re-layerings.
- Per-circuit results are under `verify_sample` in `results/step3_summary.json`.

### No candidate can pass strict readout — options for you (not implemented)

- **Why.** Task B shows that every nearest-neighbour embedding of d3a6's interaction tree has ≥ 1 strict conflict. The MRX 5 at TICK 6 always shares its line with a live 8, 10 or 12 at the grid point diagonal to 5 and adjacent to 9.
- **What cannot fix it.** Flags only add qubits and measurements. Re-embedding and fold re-layering keep the tree and the MRX 5. So **no Step 3 candidate of the plan's three categories can reach 0 strict conflicts**; the 0 in every row above is forced, not a search outcome.
- **Concrete ways out**, with what the data here says about each:

1. **Measure the folded parity on qubits whose line holds nothing else live.**
   - This is what Google's as-run circuit does: `M 6 9` at TICK 40 of G4, both on line 18 with no other circuit qubit there; also `M 1 4 6 9` at TICK 25, on lines 16 and 18.
   - For d3a6 this means ending the fold on one or more qubits of degree ≤ 2 whose diagonal grid points are free or not live at that moment. Two measured qubits could share one line and be read together; simultaneously measured qubits are not victims.
2. **Change the fold tree.**
   - The obstruction needs a qubit of degree 4 (9, and 8 in d3a4) adjacent to the measured qubit. A fold tree whose measured qubit has no degree-4 neighbour, e.g. a path or "comb" tree with maximum degree 3 near the measurement point, avoids the forced diagonal occupant.
   - This also frees grid neighbours for flags on the hook qubits; 5 and 9 have none today.
3. **Move the mid-circuit measurement off qubit 5** to a fresh ancilla adjacent to the end of the fold (one extra CX). It must be chosen so that its r + c line has no live qubit at that TICK.
4. **Delay preparation / shorten live intervals of the victims.**
   - Example: if 12 (an ancilla, a victim in 52,976 embeddings) were prepared after TICK 6, it could no longer be hit.
   - Data victims (8, 10) cannot be delayed: they hold the state. In 43,120 of the 182,968 embeddings every victim of MRX 5 is an ancilla (1, 2 or 12); in the other 139,848 at least one victim is a data qubit.
   - Even for the ancilla-only embeddings, d3a6's ancillas 1, 2 and 12 already take part in the fold (TICKs 2–3) and the unfold, so they cannot simply be prepared later. This option works only together with a re-timed fold in which the victim ancilla's first CX comes after the mid-check measurement.
5. **SWAP or move a victim off the line before the measurement and back after.** This costs extra CX layers and noise, and the victim must be swapped onto a qubit not on the line.
6. **Accept the optional `z_reset_idle="not_live"` refinement and/or re-time ancilla resets.** Only Z-reset, idle ancillas benefit. d3a6's ancillas are RX-prepared, so this does not help as is. It does explain why Google's G5 is clean.
7. **Use readout-line-aware embedding as a hard constraint** in a redesigned double check (any of 1–3). `embed_search.py` can certify 0-conflict embeddings for a new interaction tree in seconds.

---

## Files

- **New code:**
  - `nnflags/embed_search.py` (task B);
  - `nnflags/crumble.py` (Crumble URL → stim);
  - `nnflags/google_check.py` (task C);
  - `nnflags/candidates.py` (Step 3).
- **Changed code:**
  - `nnflags/constraints.py`: `liveness`, strict `readout_violations`, `readout`/`final_layer`/`z_reset_idle` options, annotation fix in `_hardware_ops`, `grid_embeddings(coords=)`;
  - `nnflags/step1.py`: `--readout`, `--final-layer`;
  - `nnflags/plots.py`: line styles, footnotes, F7–F9;
  - `nnflags/willow.py`: docstring only.
- **Tests:** `nnflags/tests/test_readout.py`, `test_crumble_embed.py` and `test_candidates.py` are new; `test_constraints.py` has the one-line change described in A.
- **Data:**
  - `nnflags/data/google_circuits/`: the Chan et al. URL and its stim conversion, Rosenfeld et al.'s 7 URLs plus the G0–G6 stim conversions, and the agent's `sources_agent.md`;
  - `nnflags/data/willow_xcheck_sources_agent.md`.
- **Results:**
  - `results/step1*.{json,txt}` (strict, ignore, final-layer-check), with the old-rule copies in `results/legacy_rule_steps0-2/`;
  - `results/embed_search_{d3a6,d3a4}.json`;
  - `results/google_check.json`;
  - `results/step3_summary.json`, `results/step3_candidates.csv.gz`, `results/step3_sample/*.stim`.
- **Logs:** `logs/step1*.log`, `logs/embed_search_d3a6.log`, `logs/google_check.log`, `logs/step3_candidates.log`, `logs/plots_step3.log`, `logs/pytest_step3.log`.

### Figures (`figures/`, PNG 200 dpi)

F1 `step0_configurations`, F2 `step0_malignant_weight`, F3 `willow_grid`, F4 `embedding_d3a6`, F5 `embedding_d3a6f2`, F6 `step2_verify_check`, **F7 `google_circuits_on_willow`** (new), **F8 `embedding_readout_histogram`** (new), **F9 `step3_candidates`** (new). Contents are described in D.

## cliffordea names used in this round (file:line in `cliffordea/cliffordea/…`, commit `27385c6`)

| name | where |
|---|---|
| `split_by_ticks` | `enum/circuit_tools.py:54` |
| `find_data_indices` | `enum/circuits/_base.py:4` |
| `find_stabilizer_generators`, `find_logical_s_gate` (via `LogicalMeasurement.__init__`; they read only MPP and S/S_DAG of the full circuit) | `enum/circuits/_base.py:17`, `:43` |
| `LogicalMeasurement.__init__` (inner-circuit conventions: MPP marker, MR vs M, trailing reset) | `enum/circuits/main.py:17`, docstring `:44-56` |
| `DoubleCheck` docstring: `(3, 4, 0)` "is the circuit used in experimental MSC [Rosenfeld2026]" | `enum/circuits/main.py:89` |
| `DoubleCheck(3, 4)` / bundled `double_checks/d3a4/{inner,full}.stim` | `enum/circuits/main.py:81`, `enum/circuits/stim_files/double_checks/d3a4/` |
| `uniformly_depolarize`, `CliffordLogicalAnalyzer`, `FaultCombinator.*` (through `verify()`, unchanged) | as listed in RESULTS_steps0-2.md |

## Decisions I made without you

1. **Data qubits are live from the start** (the MPP marker is not a preparation), as you suggested by default.
2. **Qubits measured or reset in the same TICK as the measured qubit are not victims.** Simultaneous readout of a line is how Google's own circuits measure (G4, G6).
3. **"Mid-circuit" = before the final measurement layer** (first-ex.md). The final-layer-checked number is reported alongside as `final_layer="check"`.
4. **Optional `z_reset_idle="not_live"` refinement** (off by default): a Z-reset qubit idling in |0⟩ is not live until its next gate. I added it only because G5 shows it matters. All headline numbers use your literal rule.
5. **verify() on the Crumble circuit** uses it as `full` and cliffordea's bundled `d3a4/inner.stim` as `inner`. The URL encodes only the framed full circuit; the inner circuit's gate sequence was checked to match it (MX + RX ↔ MRX).
6. **Google's as-run circuits (Rosenfeld et al. appendix) were added to the validation.** The Chan et al. link turned out to be cliffordea's idealised d3a4, not a hardware placement.
7. **Step 3 slot model:**
   - Flags may use inserted TICKs (the plan allows "insert new TICKs if needed"); a slot pair is kept only if Z_q is unchanged between the two CXs.
   - `R f` goes right before t1. `M f` is either "next" or "final", and both variants are generated.
   - f joins the trailing reset layer.
   - All three conventions copy d3a6f2 or cliffordea's inner-circuit rules.
8. **(b) was extended to gate-level re-layering**, because the plan's layer-level permutations give only the identity for d3a6.
9. **Scale of the enumeration:**
   - (c) all 350 placements;
   - (a1) all single flags on 8 symmetry representatives × 6 folds;
   - (a2) all pairs on the primary placement and original fold;
   - (a3) exact count plus a 20,000 random sample.

   The strict-readout outcome (0) is proven for all of them by task B, so enumerating the remaining ~27 M pairs and 3 billion triples was not needed for this step.
10. **For verify(), the candidate's `full` circuit is the bundled d3a6 full.stim.** Only its MPPs and S layers are read, and flags change neither.
11. **The web research was done by two helper agents.** Downloads were kept in the scratchpad and not executed. I read the spec-sheet grid myself from the rendered page.

## Open questions for you

1. **Expected 0 for the Google double check.** The Chan et al. Sec. 5 circuit (= cliffordea d3a4) has ≥ 1 strict conflict in every Willow embedding, while Google's as-run circuit G4 has 0. Should the d3 target design follow G4's pattern? That pattern is: measure the folded parities on two qubits that share a readout line with nothing else live.
2. **Idle |0⟩ qubits.** Should a Z-reset qubit idling in |0⟩ count as live (your literal rule, the default) or not (`z_reset_idle="not_live"`, under which Google's G5 is clean)?
3. **Final measurement layer.** Should it stay exempt? The data qubits continue after the double check, so physically the final MX on ancillas also dephases data on their lines. d3a6 has 6 such conflicts at the primary placement, and G4/G6 have 0 even with the final layer checked.
4. **Which option to pursue** (list at the end of E). In particular: may the fold tree and the measured qubit be changed (options 1–3)? Those are the only ones that can reach 0 strict conflicts with data victims. Or should Step 4 proceed with readout ignored and rank by readout conflicts later?

## cliffordea untouched

```
$ git -C cliffordea status --porcelain --ignored
(empty output, exit code 0)
$ git -C cliffordea rev-parse HEAD
27385c688ed40d595eab4e2378dccb5c4d32dd9a
```
