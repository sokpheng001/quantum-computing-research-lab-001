# Willow layout cross-check: sources (retrieved 2026-10-31)

Reference list under test: rows 0..12 with inclusive column ranges
0:6-8, 1:5-8, 2:4-10, 3:3-10, 4:2-12, 5:1-12, 6:0-14, 7:2-13, 8:2-12, 9:4-11, 10:4-10, 11:6-9, 12:6-8
(105 qubits, 182 nearest-neighbour couplers).

## URLs tried

| URL | Outcome | Local file |
|---|---|---|
| https://quantumai.google/static/site-assets/downloads/willow-spec-sheet.pdf | 200, application/pdf, 1,459,143 B, 2 pages | willow-spec-sheet.pdf, spec_p2.png, spec_grid_top.png, spec_grid_bot.png |
| https://quantumai.google/hardware | 404 (not used) | - |
| https://quantumai.google/static/site-assets/downloads/hardware-experiment-proposal-guidance.pdf | 200, application/pdf, 1,149,319 B, 3 pages, "Published Dec 1, 2025" (NQCC/UK version) | hardware-experiment-proposal-guidance.pdf, hepg_text_clean.txt, hepg_p1.png |
| https://quantumai.google/static/site-assets/downloads/willow-early-access-program-instructions.pdf | 200, application/pdf, 827,055 B, 3 pages, PDF title "Willow Early Access Program Instructions", heading "Hardware Experiment Proposal Guidance / Published March 2026" | willow-early-access-program-instructions.pdf, eap_text_clean.txt, eap_p1..3.png |
| https://arxiv.org/pdf/2408.13687 (v1, 24 Aug 2024, main text + supplement) | 200, application/pdf, 3,825,803 B | arxiv_2408.13687.pdf, arxiv_text.txt, arxiv_fig1_top.png, arxiv_fig1a_zoom.png |
| https://api.github.com/repos/quantumlib/Cirq/contents/cirq-google/cirq_google/devices/specifications?ref=v1.7.0 | 200 | gh_specs.json |
| https://raw.githubusercontent.com/quantumlib/Cirq/v1.7.0/cirq-google/cirq_google/devices/specifications/willow_pink_d7v1-2024_08_16_device_spec_for_grid_device.proto.txt | 200 | willow_spec_v1.7.0.textproto |
| https://raw.githubusercontent.com/quantumlib/Cirq/v1.7.0/cirq-google/cirq_google/api/v2/program.py | 200 | v2_program.py |
| https://raw.githubusercontent.com/quantumlib/Cirq/v1.7.0/cirq-google/cirq_google/api/v2/__init__.py | 200 | v2_init.py |
| https://raw.githubusercontent.com/quantumlib/Cirq/v1.7.0/cirq-google/cirq_google/devices/known_devices.py | 200 (no Willow-specific content) | kd_v1.7.0.py |
| https://raw.githubusercontent.com/quantumlib/Cirq/v1.7.0/cirq-google/cirq_google/api/v2/qubit_conversion.py | 404 (wrong guess; function is in program.py) | - |
| https://raw.githubusercontent.com/quantumlib/Cirq/main/... (known_devices, qubit_conversion) | request hung, aborted; not used | - |
| https://api.github.com/search/code?q=... | 401 "Requires authentication"; not used | - |
| https://quantumai.google/cirq/google/devices | fetched via WebFetch (summarised by a small model, so quotes are approximate, not verified byte-for-byte) | - |
| Nature version (Nature 638, 920 (2025)) | not fetched; the arXiv v1 was used instead | - |

Text was extracted with pypdf and PyMuPDF. Figures were rendered with PyMuPDF and read visually.

## Q1. Willow spec sheet and proposal guidance

**Spec sheet** (willow-spec-sheet.pdf, "Published Dec 9, 2024"):
- p.1 text: "Number of qubits 105", "Average connectivity 3.47 (4-way typical)".
- p.2 is headed "Qubit grid" and shows a grid diagram. Each qubit circle is labelled "r, c" (for example "0, 6", "6, 14", "12, 8"). Exact note: "Note: The numbers inside the qubit grid refer to the row and column index".
- The labels are vector graphics, not text, so they were read off the rendered page at 4x zoom. Row 0 is at the top and column 0 at the left. Rows as drawn:
  0: 6-8 | 1: 5-8 | 2: 4-10 | 3: 3-10 | 4: 2-12 | 5: 1-12 | 6: 0-14 | 7: 2-13 | 8: 2-12 | 9: 4-11 | 10: 4-10 | 11: 6-9 | 12: 6-8
- In the drawing every pair of grid-adjacent qubits is joined by a blue coupler bar (checked visually, not one by one).
- The spec sheet says nothing about readout lines or multiplexing.
- **Conclusion: MATCH.** The qubit set is identical, with the same orientation (no rotation or reflection) and the same "row, col" convention.

**Hardware Experiment Proposal Guidance** (Dec 1, 2025 NQCC version, and the March 2026 version at willow-early-access-program-instructions.pdf):
- Page 1 of both has "Willow Qubit Grid", the same picture as spec-sheet p.2, with the same note, "The numbers inside the qubit grid refer to the row and column index" (checked visually on the rendered pages).
- Readout quotes from the March 2026 version, verbatim:
  - "Experiments should not contain mid-circuit measurements while trying to preserve the coherence of other qubits on the same readout line (readout lines run diagonally from the bottom left to upper right of the chip). However, reset gates are allowed."
  - "Readout lines run diagonally across the chip (i.e., such that in the diagram on page 2 of the spec sheet, row+col = const). Measuring any qubit on a readout line dephases the whole readout line. This is why in Google's error correction experiments (e.g., this one), the data and measure qubits are on separate readout lines."
  - "Measurements are comparatively slow (600 ns) compared to gates (~35 ns)."
  - The Dec 2025 version has the same wording except "(i.e. such that ...)" and "Experiments should be designed to run within a day ...".
- "Bottom left to upper right" fits r+c = const when row 0 is drawn at the top.
- In our coordinates, r+c runs from 6 to 20. That gives 15 readout lines, each holding exactly 7 qubits (computed).
- The documents do not say how many qubits each line holds, which resonator or feedline belongs to which line, or the line boundaries. They only give the rule row+col = const.

## Q2. Acharya et al., arXiv:2408.13687 (Nature 638, 920)

- Fig. 1 caption (verbatim): "a, Schematic of a distance-7 surface code on a 105-qubit processor. Each measure qubit (blue) is associated with a stabilizer (blue colored tile). ... We remove leakage from each data qubit (gold) via a neighboring qubit below it, using additional leakage removal qubits at the boundary (green)."
- Fig. 1a is drawn rotated 45 degrees. At 8x zoom I counted 49 gold data qubits (a 7x7 grid), 48 blue measure qubits (36 interior plus 3 on each of the 4 edges), 4 green leakage-removal qubits along the bottom, and 4 faded grey unused qubits (top-left corner and 3 along the top edge). That totals 105. These counts come from reading the figure visually.
- I mapped the drawing coordinates (X, Y) to (r, c) = ((X+Y)/2, (X−Y)/2), up to rotation, reflection and translation (scripts/fig1cmp.py). The resulting set equals our 105-qubit set exactly under a 90 degree rotation, and under 270 degrees, because our shape is symmetric under (r,c)->(12-r,14-c).
- Under that mapping, data qubits have r+c odd and measure, leakage and unused qubits have r+c even. So data and measure qubits sit on different r+c diagonals, which is what the proposal guidance says about separate readout lines.
- The roles look like this (D data, M measure, L leakage, G grey):
```
 0 ......LDM......
 1 .....MDMD......
 2 ....LDMDMDM....
 3 ...MDMDMDMD....
 4 ..LDMDMDMDMDM..
 5 .MDMDMDMDMDMD..
 6 LDMDMDMDMDMDMDG
 7 ..DMDMDMDMDMDM.
 8 ..MDMDMDMDMDG..
 9 ....DMDMDMDM...
10 ....MDMDMDG....
11 ......DMDM.....
12 ......MDG......
```
  The exact rotation that matches the chip's real labels cannot be fixed from the figure alone, since the figure carries no labels.
- Readout in the supplement (verbatim, Sec. I "Gates and Readout"): "Our measurement chain is similar to that of [1], though with Lumped Element Snake Amplifiers (LESAs) [2] replacing the previous impedance matched parametric amplifiers. The qubit frequency during readout, readout pulse duration, and readout pulse power are jointly optimized [3] to attain simultaneous high fidelity mid-circuit readout." A text search found no "multiplex", "feedline", "readout line" or "diagonal".
- **Conclusion: shape MATCH** (105 qubits, same shape up to a 45 degree drawing rotation). **Readout multiplexing: the paper does not describe it (arXiv v1 text).** The Nature-published version was not checked separately.

## Q3. Cirq

- The cirq v1.7.0 `cirq-google/cirq_google/devices/specifications/` directory lists `willow_pink_d7v1-2024_08_16_device_spec_for_grid_device.proto.txt`, alongside the rainbow and weber specs and README.md.
- Parsing that file (scripts/spec_cmp.py) gives 105 `valid_qubits`, identical to our list, and 182 unique qubit-pair targets.
- The file contains no readout or line information.
- From `cirq_google/api/v2/program.py` at v1.7.0, verbatim: "For `cirq.GridQubit`s this id `{row}_{col}` where `{row}` is the integer row of the grid qubit, and `{col}` is the integer column of the qubit." and `return f'{q.row}_{q.col}'`. Parsing goes the other way with `cirq.GridQubit(row=int(row), col=int(col))`, and the error text says "[q]<int>_<int>".
- quantumai.google/cirq/google/devices, as summarised by WebFetch (not verbatim), says there is a "Willow105 device ... a 105-qubit layout representing Google's Willow processor family". It mentions `cirq_google.SimulatedProcessorWithLocalDeviceRecord('willow_pink').get_device()` and `cirq.GridQubit(row, col)`. I did not check the Willow105 source definition.
- **Conclusion: MATCH.** The id format is "row_col", so GridQubit(row, col) gives "r_c", and the spec-sheet "r, c" labels use the same coordinates.
