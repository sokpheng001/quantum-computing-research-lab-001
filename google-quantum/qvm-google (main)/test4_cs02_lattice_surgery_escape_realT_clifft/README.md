# Test 4: cs02 + a lattice-surgery escape into a rotated surface code, real T, Clifft

Goal: the full magic-state pipeline with OUR double check (cs02): injection, cs02, and an escape by
lattice surgery into a rotated surface code (Hirano et al., arXiv 2510.24615, MSC-LS), on Willow's rules,
with **real T gates**. The pipeline (33-66+ qubits) is too large for the QVM's state vector, so it is
simulated with **Clifft** (exact near-Clifford simulator, real T, CPU; `pip install clifft==0.12.0` in
`.venv`, Nov 3, 2026), after Clifft is validated against Google's qsim.

References (moved here from `google-quantum/references/` on Nov 3): `references/2510.24615v2.pdf`,
`references/hirano_notes.md` (novelty check: no overlap with our work), `references/msc-ls-src/repo`
(their public code, read only, not run).

## Steps

| step | what | status |
|---|---|---|
| A1 | Clifft vs Google's qsim on the same noisy real-T double checks (Google G6-style, cs02, #0) | `validate_clifft.py`, tonight |
| A2 | Hardware needs of Hirano's escape (static analysis of their stim files) | done: nearest neighbour, <= 4 partners (`RESULTS_hirano_escape.md`) |
| A3 | Readout-line rule of the escape; how cs02's code must face the surface code on Willow | next |
| B | Build cs02 + Willow-placed escape; device check; noiseless real-T check; fault injection | after A3 |
| C | Same escape with Google's double check vs cs02, Clifft, real T, same noise | after B |

Run tonight: `bash run_tonight.sh` (tmux "test4"), writes `RESULTS_validation.md`.

## Paused (Nov 4, 2026, 7 pm KST): geometry blockers found before building the pipeline

The user asked for Google's Willow injection + cs02 + Hirano's escape. Two blockers, nothing built or run:

1. Google's injection (G4 TICKs 0-25) prepares exactly G6's code on the same diamond of data positions
   (G4's code shifted by (-3, -3) equals G6's, checked with stim; scratchpad `g4code.py`). cs02 cannot carry
   that code there (test 3, step 0), so Google's injection + cs02 needs a changed injection. #0 fits.
2. Hirano's lattice surgery attaches to Gidney's colour-code layout (data 1, 15, 31, 227, 241, 242, 257 in
   their files), which is a different arrangement from Google's diamond, so it cannot attach to Google's
   patch without redesigning the merge.

Options offered: (1) logical-level join (injection + double check + Hirano escape, data mapped logically,
not Willow-placed); (2) redesign the merge for Google's diamond, with #0; (3) our own injection for cs02.
The user chose to pause test 4 and return to understanding cs02.
