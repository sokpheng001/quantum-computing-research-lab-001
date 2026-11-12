# Manuscript draft: fault-distance-3 double check (cs02) for magic state cultivation on Willow

Draft v0.1, Nov 9, 2026. LaTeX (revtex4-2, APS/PRA style), for Overleaf.

## Overleaf
1. Overleaf → New Project → Upload Project → choose `manuscript_cultivation_cs02_overleaf.zip`.
2. Compiler: pdfLaTeX (default). Main document: `main.tex`. BibTeX runs automatically.
3. Red `[TODO: ...]` marks: author surname, co-authors, department, acknowledgments, code link, journal details.

Not compiled on the server (no LaTeX installed here); structure checked (braces, environments, citations,
labels, figure paths). Report any Overleaf error and it will be fixed.

## Files
- `main.tex`: the paper. `references.bib`: bibliography (arXiv metadata checked Nov 9).
- `figures/` (PNG, copied from the tests):

| figure | source |
|---|---|
| fig_layout_cs02.png | test2 / figures/continuing_circuits.png |
| fig_circuit_cs02.png | test2 / figures/cs02_circuit.png |
| fig_qvm_comparison.png | test2 / figures/qvm_cs02_vs_google.png |
| fig_si1000_sweep.png | test7 / figures/t7_si1000_sweep.png |
| fig_chip_positions.png | test7 / figures/t7_chip_positions.png |
| fig_validation_retention.png | test6 / figures/t6_fig2_retention.png |
| fig_d5_real_noise.png | test5 / figures/b4_real_noise.png (not yet used in the text) |

## Where every number comes from (all under `qvm-google (main)/`)
| section / table | source file |
|---|---|
| Table II (QVM main result), Table I (fault injection) | MASTER_RESULTS.md (tests 1-2) |
| Table III (noise models), Fig. 4 sweep, chip positions | test7_.../RESULTS.md |
| G6-fit circuits (#0 ... #9) | MASTER_RESULTS.md (test 3) |
| Sec. VI validation, Table IV | test6_.../RESULTS.md |
| Sec. VII distance 5, Table V | test5_.../RESULTS_B0_B1.md, RESULTS_B4_real_noise.md, logs/b4_clifft.log |
| cs02 structure (12 qubits, 24 CNOT, N3 = 350) | test2 figures (cs02_circuit.png, continuing_circuits.png) |

Rules followed: only Willow-runnable circuits in benchmark tables (no Chan et al. or Gidney d3a6 at d = 3);
Chan et al. as motivation only; rates written as "1 in N".
