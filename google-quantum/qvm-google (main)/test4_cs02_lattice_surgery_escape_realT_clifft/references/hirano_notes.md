# Novelty check: Hirano, Toshio, Itogawa & Fujii, "Efficient magic state cultivation with lattice surgery"

arXiv 2510.24615 v2 (dated August 19, 2026). PDF: `2510.24615v2.pdf` (uploaded by the user, Nov 3, 2026).
Read on Nov 3, 2026 (text extracted with pypdf). Page numbers are the PDF's.

## What the paper does

- Proposes **MSC-LS**: keeps Gidney et al.'s injection and cultivation stages, and replaces the **escape**
  (the grafted code) with **lattice surgery + code expansion into a rotated surface code**, plus early
  rejection with a lookup table. Square-grid connectivity. (Abstract; Sec. IV, p. 6.)
- p. 6: "The protocol shares the injection and cultivation stages with the original magic state
  cultivation (MSC)." So the double check is **Gidney's, unchanged**.
- p. 7: lattice surgery "likewise preserves the fault distance d_color"; Sec. V (p. 11) checks this for the
  lattice-surgery step only, with ideal |+>_L / |0>_L inputs (fitted exponent about 2.9 / 3.3).
- Result: logical error comparable to MSC at about half the spacetime overhead (d_color = 3, p = 0.1 %).

## Answers to our two questions

1. **A d = 3 double check with fault distance 3 for the T state, nearest-neighbour? No.**
   - The double check is not modified (p. 6).
   - Simulations use Stim with **T replaced by S** (p. 10: "we replace T gates in the injection and
     cultivation stages with S gates ... output S|+> instead of T|+>"). This S stand-in is exactly where the
     T-specific loss of fault distance (Chan et al.) does not appear, so the paper neither sees nor fixes it.
   - Their "fault distance 3" statements concern the lattice-surgery escape, not the T double check.
2. **Willow's readout-line rule? No.** Generic square grid, uniform depolarising noise
   (p_phys = 0.1 %); no readout lines, no chip-specific layout, no device calibration.

## Conclusion for our paper

- **No overlap with our contribution** (a T double check with fault distance 3 under Willow's rules,
  verified with real T). Our novelty claim stands.
- **Related and complementary**: their escape is a square-grid alternative to the grafted code, and its
  code is public (github.com/yutakahirano/msc-ls). It could be a reference design for "our own escape for
  cs02". Their final code (d = 11 rotated surface code, 241 qubits) does not fit Willow (105 qubits), so it
  would need a smaller final distance.
- Cite as: square-grid cultivation with a lattice-surgery escape; uses an S stand-in, so the T-specific
  double-check problem is outside its scope.
- They report (S stand-in, p = 0.1 %): injection + cultivation stages about 1 in 5,000,000; lattice
  surgery about 1 in 1,250,000; end to end about 1 in 625,000 (p. 11), i.e. the escape dominates.

## Their public code (github.com/yutakahirano/msc-ls, commit e4c90b0, Apr 16, 2026), first look on Nov 3

Cloned read-only to `references/msc-ls-src/repo` (not run). Static check of their stim files with
`stim` (scratchpad script `inspect_stim2.py`); "adjacent" = coordinate offset (1, 1) in their diagonal layout:

| file | qubits used | 2-qubit pairs not adjacent | max partners |
|---|---|---|---|
| inject-check-3 (Gidney's injection + double check) | 15 | 0 | 4 |
| lattice-surgery-error-detection-3-to-3 | 33 | 10 | 7 |
| lattice-surgery-error-detection-3-to-5 | 66 | 10 | 7 |
| surface-code-3-to-7-expansion | 98 | 7 | 7 |

- **Correction (Nov 3, `RESULTS_hirano_escape.md`):** the 10 non-neighbour pairs and the >4-partner qubits in the
  table above are all noiseless CNOTs at TICK 5 (no DEPOLARIZE2 after them), i.e. the test circuit's ideal encoder of
  |+>_L into the colour code. Leaving those out, every hardware two-qubit gate of the escape is between nearest
  neighbours and no qubit has more than 4 partners: the escape's connectivity fits Willow. Not yet checked: the
  readout-line rule, and the orientation in which cs02's code must face the surface code.
- Size fits Willow by count for the 3 -> 3 and 3 -> 5 versions (33 and 66 qubits; Willow 105).
