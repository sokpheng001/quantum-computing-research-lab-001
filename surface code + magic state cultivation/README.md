# Surface code + magic state cultivation in a full-stack pipeline

**Purpose.** Use the published magic-state cultivation code of Gidney, Shutty & Jones (2024, arXiv:2409.17595;
code and circuits in `Magic state cultivation/`, unchanged) inside a small full-stack simulation. The pipeline
compiles a circuit, counts its T gates, simulates surface-code memory, and takes the T-state cost and error from
cultivation, either simulated or taken from the paper.

**Validation against the paper** (p = 0.1 %, colour-code distance 3; `RESULTS_cultivation.md`, section 2):

| Stage | Shots | Our T error per kept state | Discarded | Paper |
|---|---|---|---|---|
| injection + cultivation ("ungrown") | 4,000,000,000 | 1 in 1,390,000 | 31.3 % | 1 in 1,670,000, 35 % |
| end to end (with escape, gap ≥ 69 dB) | 331,753,164 | 1 in 479,000 | 77.5 % | 1 in 333,000, 80 % |

Both are within a factor of 2 of the paper. As in the paper, the T state is simulated through its S-state stand-in,
with the error doubled (the paper's Assumption 3.1). Distance 5 was not simulated; the paper's values are used.

**Files.**

| File | What it does |
|---|---|
| `full_stack_sim.py` | the pipeline: compile, analyse, QEC, factory, execute |
| `cultivation_plugin.py` | adapter to the paper's circuit builders and samplers |
| `run_validation.py` | the validation run |
| `run_memory.py` | the surface-code memory sweep (`memory_results.csv`) |
| `run_all.sh` | runs everything |
| `write_results.py`, `plot_results.py`, `plot_circuits.py` | the report and the figures (`figures/`) |
| `TASKS_cultivation_plugin.md` | the plan |
| `cultivation_results.json`, `pipeline_results.json` | the results |
