# google-quantum: a fault-distance-3 magic-state double check for Google's Willow chip

## Purpose
Magic-state cultivation (Gidney, Shutty & Jones 2024) prepares a clean T state by checking it again and again
and discarding it at any sign of error. Google ran its distance-3 version on the Willow chip (Rosenfeld et al.,
arXiv:2512.13908). Chan et al. (arXiv:2609.17706) showed that with **real T gates** the "double check" in this
protocol has **fault distance 2**, not 3: a hook error inside the CNOT tree is turned by the T gates into an
error the check cannot see.

This project designs a double check that:
- runs on Willow (nearest-neighbour CZ only, at most 4 partners per qubit, Willow's readout-line rule);
- keeps the T state alive (the 7 data qubits are never measured);
- has **fault distance 3 with real T gates**.

The result is the circuit **cs02**: 12 qubits (7 data, 1 root, 2 helpers, a ZZ flag and an X flag) and 24 CNOTs.

## Main results (double check alone, real T gates)

| | Google's double check (G4, Fig. 4 readout rule) | cs02 |
|---|---|---|
| fault distance (exact enumeration, all fault pairs) | 2 (7 silent pairs) | **3** (0 silent pairs) |
| error per kept T state, Google's QVM, 8,000,000 shots | 1 in 20,832 | **1 in 121,322** (5.8× better, 95 % CI 4.2× to 8.1×) |
| acceptance | 76.7 % | 75.2 % |
| SI1000 sweep slope (error against p) | 2.17 | 3.04 |

More results are in the test folders: noisy input, other noise models, chip positions, the mechanism, and distance 5.

## Layout

| Path | What it is |
|---|---|
| `RESULTS_*.md` | reports of the design search, in order: `steps0-2` (setup, Willow rules), `g4` (Google's circuit), `option1`, `zzflags` (flag search), `continuing_data` and `continuing_search` (the search that found cs02), `comparison`, `step3` |
| `SUMMARY_improvements.md` | one-page summary of the improvements |
| [`nnflags/`](nnflags/) | Python package: Willow rules, circuit search, flag search, verification |
| [`qvm-google (main)/`](qvm-google%20(main)/) | tests 1–7 in Google's Quantum Virtual Machine and other simulators; `MASTER_RESULTS.md` is the single source of the headline numbers |
| `results/` | circuit files (`.stim`) and search outputs; cs02 is `results/continuing/success02.{full,inner}.stim` |
| `figures/` | figures (PNG), for example `cs02_on_willow_grid.png` and `google_vs_cs02_on_willow.png` |
| [`draft00-manuscript_cultivation_cs02/`](draft00-manuscript_cultivation_cs02/) | LaTeX manuscript draft (Overleaf) |
| `requirements-lock.txt` | exact Python package versions used |

## Setup
1. Python 3.12. Create a virtual environment in this folder and install the packages:
   `python -m venv .venv && .venv/bin/pip install -r requirements-lock.txt`
2. Clone cliffordea into this folder and do not modify it:
   `git clone https://github.com/timchan0/cliffordea cliffordea`
3. Test 6 only: download Google's data release (Zenodo DOI 10.5281/zenodo.17872003) into
   `qvm-google (main)/test6_reproduce_google_willow_simulation_and_hardware_data/references/zenodo_17872003/`.

Run every command from this folder, for example
`.venv/bin/python -m pytest -q nnflags/tests`.
