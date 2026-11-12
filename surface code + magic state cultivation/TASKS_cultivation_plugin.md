# TASKS_cultivation_plugin.md — use the paper's cultivation code inside our pipeline

## Goal
Make `cultivation_plugin.py` run the real magic-state cultivation code from
Gidney, Shutty & Jones (2024), arXiv:2409.17595 (Zenodo doi:10.5281/zenodo.13777072),
so `full_stack_sim.py` uses simulated cultivation numbers instead of only the published table.

## Files in this project
- `full_stack_sim.py` — the full workflow (compile → analyse → QEC → factory → execute → result).
- `cultivation_plugin.py` — two placeholder functions to implement:
  `build_cultivation_circuit(p, d1)` and `keep_and_check(circuit, shots)`.
- The paper's archive, already downloaded, in the subfolder `Magic state cultivation/`:
  `circuits/`, `code/`, `stats.csv` (folder names contain spaces: always quote paths).
  NEVER edit `circuits/`, `code/` or `stats.csv`; write adapters in our own files only.
- `cultivation_plugin.py` finds them through `REF_DIR` (auto-detects `Magic state cultivation/`).

## Rules
- Do not guess the paper's function names: read their code and README first.
- Keep the paper's own noise model, postselection rules and decoder. Only wrap them.
- Simulate T as S (the paper's Assumption 3.1: T error ≈ 2 × S error); keep that factor
  in `simulate()` unless the paper's code already applies it — check and report.
- Run long jobs detached (tmux/nohup), checkpoint results to `cultivation_results.json`.
- Report every number with: p, d1, shots, kept shots, failures, ungrown vs end-to-end.

## Step 0 — environment
- Create a venv; install what the paper's code needs (read its requirements or imports:
  e.g. stim, sinter, pymatching, numpy, and any decoder it uses). Report versions.
- Also install what our pipeline needs: qiskit, qiskit-qasm3-import, stim, pymatching.
- Run the paper's own tests or example script once, unchanged. Report whether it works.

## Step 1 — map the paper's code (report before writing code)
Find and report, with file paths and function signatures:
1. the function(s) that build the cultivation circuit (injection + cultivation, and the
   escape / grafted version), and their parameters (noise strength, d1, final distance, …);
2. how the S-for-T (Clifford) variant is selected;
3. how they sample shots and apply postselection (which detectors cause a discard);
4. how the escape-stage decoding and complementary-gap cut are done;
5. how they compute logical error rate and discard rate in their figures.

## Step 2 — implement the plugin
In `cultivation_plugin.py`:
- `build_cultivation_circuit(p, d1)`: call the paper's generator with uniform noise p, target
  fault distance d1, S variant. Add a flag `stage="ungrown"|"end_to_end"`.
- `keep_and_check(circuit, shots)`: call the paper's sampling + postselection + decoding;
  return (kept_shots, logical_failures_among_kept).
- Keep the cache and the published fallback exactly as they are.

## Step 3 — validate against the paper (must pass before anything else)
At p = 1e-3, d1 = 3:
- ungrown: expect logical error ≈ 6e-7 and discard ≈ 35%;
- end-to-end: expect logical error ≈ 3e-6 and discard ≈ 80%.
Run enough shots for at least ~20 logical failures (likely tens of millions of shots;
first report the time per 1e6 shots and an estimate before the long run).
PASS = within roughly a factor of 2 of the paper's values (state the 95% interval).
Do NOT attempt d1 = 5 by brute force (errors ~1e-9 are out of reach); keep published values.

## Step 4 — connect to the pipeline
- Confirm `full_stack_sim.py` picks up the simulated numbers (`"source": "simulated"`).
- Run both examples in `full_stack_sim.py` and show the output.
- In the printed factory section, show whether each number is simulated or published.

## Step 5 — report (top of RESULTS_cultivation.md)
| setting | stage | shots | kept | failures | error (95% CI) | discard | paper value | PASS? |
Plus: environment versions, the paper-code functions used, run times, and any deviations.

## Step 6 — figures (PNG + PDF in `figures/`, show each one)
Use matplotlib. Every figure: axis labels with units, legend, error bars (95% CI) where
there are counts, and a caption line saying simulated vs published and the settings.

F1  Validation vs paper (most important)
    Two panels (ungrown, end-to-end) at p = 1e-3, d1 = 3.
    Left: logical error of kept T states — our value with 95% CI vs the paper's value.
    Right: discard rate — ours vs the paper's.
    Log scale for error. Mark PASS/FAIL in the title.

F2  Surface-code memory (Stim + PyMatching)
    Logical error per cycle vs physical error p (log-log), one line per distance d = 3, 5, 7,
    p from 2e-4 to 5e-3, >= 20 failures per point where feasible (upper-limit arrows if 0).
    Shows the threshold crossing and the suppression with d used by the pipeline.

F3  Cultivation error vs cost (like the paper's Fig. 1), from stats.csv
    x = expected qubit-rounds per kept T state (log), y = logical error (log),
    one marker per (p, d1, stage); highlight the settings our pipeline uses.
    If stats.csv lacks the cost column, plot error vs discard rate instead and say so.

F4  Pipeline results for the example circuits (from full_stack_sim.py)
    One bar chart per example: measured outcome counts over the shots, with the ideal
    probabilities as markers. Title: circuit name, T count, factory on/off, chosen d.

F5  Resource breakdown
    Stacked bar per example circuit: data qubits, factory qubits, routing qubits.

Also add `plot_results.py` that regenerates all figures from saved CSV/JSON results
(`cultivation_results.json`, a new `memory_results.csv`, and the pipeline outputs),
so figures can be rebuilt without rerunning simulations.