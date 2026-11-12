# Quantum error correction research

Research code, data and reports by Kim Chansokpheng (Pukyong National University, Busan) on quantum error
correction, with a focus on making fault-tolerant **magic states** (T states) on real superconducting hardware.

| Folder | Topic | Status |
|---|---|---|
| [`google-quantum/`](google-quantum/) | **Main project.** A magic-state cultivation "double check" for Google's Willow chip that restores fault distance 3 with real T gates (circuit **cs02**), compared with Google's own circuit in Google's simulator | active; manuscript draft inside |
| [`CNOT reordering/`](CNOT%20reordering/) | Can a different CNOT order in the syndrome circuit raise the circuit-level distance of bivariate bicycle (BB) codes? (open question 4 of Bravyi et al., *Nature* 2024) | closed: no schedule found that beats Bravyi's |
| [`surface code + magic state cultivation/`](surface%20code%20+%20magic%20state%20cultivation/) | Running the published cultivation code (Gidney, Shutty & Jones 2024) inside a small full-stack simulation pipeline | done |

Each folder has its own README that explains its purpose, layout and results.

## Not included in this repository
To keep the repository small and to respect other authors' work, these are left out (see `.gitignore`):
- **third-party code**, which you clone from its own repository:
  - `cliffordea`: [github.com/timchan0/cliffordea](https://github.com/timchan0/cliffordea), MIT. It goes in `google-quantum/cliffordea/`.
  - `BivariateBicycleCodes`: [github.com/sbravyi/BivariateBicycleCodes](https://github.com/sbravyi/BivariateBicycleCodes), Apache 2.0. It goes in each `bravyi_ref/`.
  - `Adaptive-qLDPC`: [github.com/UCL-CCS/Adaptive-qLDPC](https://github.com/UCL-CCS/Adaptive-qLDPC).
  - `msc-ls`: [github.com/yutakahirano/msc-ls](https://github.com/yutakahirano/msc-ls).
- **Google's data release** for the Willow cultivation experiment: Zenodo, DOI [10.5281/zenodo.17872003](https://doi.org/10.5281/zenodo.17872003). It is needed only for test 6 in `google-quantum/`.
- Python environments, caches, raw decoder samples (`*.npz`) and result files larger than 50 MB.

## Note on paths
The scripts were run on the author's server. Some shell scripts contain absolute paths such as
`/home/ubuntu/...`; change them to your own location before running.
