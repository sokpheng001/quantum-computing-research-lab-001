# qvm-google (main): our Willow cultivation circuits in Google's Quantum Virtual Machine

Every test here runs our circuits and Google's circuits through Google's own software
(cirq 1.7.0, cirq_google 1.7.0, qsimcirq 0.22.1, processor `willow_pink`, the
`willow_pink_d7v1-2024_08_16` Willow snapshot, with real T gates) and compares them.

All commands run **from `google-quantum/`** with the project venv `.venv`. Paths with
spaces need quotes: `"qvm-google (main)/..."`. Nothing in `nnflags/` or `cliffordea/` is modified.

## Folder layout

| folder / file | purpose |
|---|---|
| `qvm_willow.py` | **shared QVM engine**: stim → cirq conversion, E1–E4, noise inventory. Its default output folder is test 1. |
| `tests/` | tests of the engine (`.venv/bin/python -m pytest -q "qvm-google (main)/tests"`) |
| `test1_fd3_circuits_vs_google_fig2/` | **Test 1 (Nov 1).** First fault-distance-3 circuits (success03, success04, success00) vs Google's G4 (Fig. 2) and Chan et al.'s d3a6. |
| `test2_cs02_continuing_data_vs_google/` | **Test 2 (Nov 1–2).** Our final circuit cs02 (fault distance 3, valid when the data continue) vs G4 (Fig. 2) and G4 G6-style (Fig. 4 way). |
| `test3_full_qec_realT_lowT_sim_ours_vs_google_g6/` | **Test 3 (Nov 2–, in progress).** Logical error rate of the full experiment (Google's injection + our double check + Google's grafting into the surface code, G6 / Fig. 4) with real T gates, using a low-T-count simulator (54+ qubits is too large for the QVM's state vector), vs Google's G6 as run. Done: cs02 does not fit G6 (steps 0, 0b); 9 fault-distance-3 double checks that fit G6 found (step 1). |

Each test folder has the same layout: `RESULTS.md` (report), `results/` (JSON + resumable
checkpoints), `figures/` (PNG only), `logs/`, and its own scripts.
Each test's `figures/` also holds the **layout figure of the circuits it tested** on the Willow grid
(test 1: `zz_best_circuits.png`, success03; test 2: `continuing_circuits.png`, cs02), since the QVM
is where Google's own device check accepted those layouts.

## The experiments (same in every test)

| | what it checks |
|---|---|
| **E1** | the circuit converts to Willow's native gates and passes Google's device validation (couplers, qubits) |
| **E2** | noiseless, with real T gates: every detector is 0 and the output is the T state |
| **E3** | every single fault and every pair of faults injected with real T gates agrees with cliffordea; counts the pairs kept with a wrong T state (0 = fault distance 3) |
| **E4** | noisy sampling with Google's Willow noise model: acceptance and T error per kept T state |

## Headline results

All circuits at the same 8,000,000 shots unless noted; the full table with ratio CIs is `MASTER_RESULTS.md` (`master_results.py`).

| test | circuit | fault distance | QVM T error per kept T state | acceptance |
|---|---|---|---|---|
| 1 | G4 (Google, Fig. 2) | 2 | 1 in 18,460 (8 M shots) | 75.1 % |
| 1 | success03 | 3 | 1 in 78,277 | 65.5 % |
| 2 | G4 G6-style (Google, Fig. 4 way) | 2 | 1 in 20,832 (8 M shots) | 76.7 % |
| 2 | **cs02 (ours, final)** | **3** | **1 in 121,322** (8 M shots; 5.8× vs G6-style, 95 % CI 4.2× to 8.1×) | **75.2 %** |
| 3 | #0 (ours, fits G6 grafting) | 3 | 1 in 70,284 (8 M shots; 3.4×, 2.6× to 4.4×) | 71.4 % |

## Commands

Test 1 (engine defaults):

```
.venv/bin/python "qvm-google (main)/qvm_willow.py" e1 | e2 | e3 | noise
.venv/bin/python "qvm-google (main)/qvm_willow.py" e4 --shots-json '{"success03": 2000000}' --chunk 5000
.venv/bin/python "qvm-google (main)/test1_fd3_circuits_vs_google_fig2/plots.py"
```

Test 2 (any circuit given as stim files):

```
.venv/bin/python "qvm-google (main)/test2_cs02_continuing_data_vs_google/run_qvm.py" e1 --design NAME=results/continuing/success02
#   e2 | e3 [--workers 12] | e4 --shots 2000000
.venv/bin/python "qvm-google (main)/test2_cs02_continuing_data_vs_google/plots.py"
.venv/bin/python "qvm-google (main)/test2_cs02_continuing_data_vs_google/report.py"
bash "qvm-google (main)/test2_cs02_continuing_data_vs_google/run_all.sh"   # the whole test, in tmux
```

Notes
- E4 is resumable: finished chunks are kept, and seeds are CRC32(`<design>:<chunk>`), so a rerun reproduces the same shots.
- Each worker uses one qsim thread; parallelism comes from worker processes (12 by default).
