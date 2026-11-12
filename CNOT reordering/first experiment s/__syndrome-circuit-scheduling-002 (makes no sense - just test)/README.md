# 002 — L/R block schedules on [[72,12,6]] (docs/task.md)

**Question.** If each check touches its 3 Left-block data qubits and its 3 Right-block
data qubits in separate groups, does the circuit keep the full distance of 6?

**Code.** [[72,12,6]]. Data qubits 0–35 form the Left block, 36–71 the Right block.

## Testing stages

| stage | what is tested | status |
|---|---|---|
| 1. Code matrices | H_X, H_Z from 36×36 shift matrices; 3 L + 3 R targets per check | done |
| 2. Strategies A, B, C | Pure L/R block orders, in three time layouts | done: none is a valid circuit |
| 3. All valid schedules | Distance of all 1,872 valid depth-7 schedules, grouped by L/R structure | done |
| 4. Error rate | S against the most L/R-like distance-6 schedule and a distance-3 schedule | running |

## Main result

- Pure L/R block orders cannot be built: they either put two CNOTs on one qubit at
  the same time, or they break the commutation of X and Z checks.
- The closest valid form (4 L/R switches) never drops below distance 5, and 92% keep the maximum, 6.
- Every distance-3 schedule switches block at every CNOT (10 switches).

## Methods

- **Circuit.** Self-contained stim builder (`search_scheduler_72.py`); identical to 001's circuit.
- **Distance.** stim's search for undetectable logical errors (exploration limit 4, 3 cycles).
  task.md asked for a graph-based shortest path, but that tool cannot handle BB codes.
- **Decoder (error rate).** Same BP-OSD as 001 (OSD combination sweep order 7).

## Where to look

- **RESULTS.md** — all results with tables. **results_72code.json** — every L/R-like schedule reaching distance 6, with its 7-layer array.
- **figures/** — `dcirc_by_lr_switches.png`, `ler_72_lr.png`. **results/** — raw data.

## Folder layout

All four folders (001–004) use the same layout.
After a server restart, unfinished jobs resume by themselves about a minute after boot (`../resume_all.sh`, started at boot). Finished work is never repeated. A job you stop yourself with `./launch.sh stop` stays stopped after a restart.

| path | contents |
|---|---|
| `README.md` | this guide |
| `RESULTS.md` | results with tables (drivers add to it automatically) |
| `launch.sh` | `./launch.sh <driver.sh>` starts a job; `./launch.sh status`; `./launch.sh stop` (this folder's jobs only) |
| `driver_*.sh` | the pipeline(s) of this folder |
| `*.py` | the code the pipelines use |
| `docs/` | task plans and reference notes |
| `results/` | data (CSV, JSON) and job logs (`*.log`) |
| `figures/` | plots (PNG) |
| `archive/` | old scripts kept for the record, not used |

**Main files.** `bb72_matrices.py` (code matrices), `search_scheduler_72.py` (strategies, circuit builder, distance), `ler_72.py` (error rates), `make_figures_72.py`, `dcirc.py` (decoder, own copy). Pipeline: `driver_72lr.sh`. The task deliverable `results_72code.json` stays at the top, as task.md asks. Task: `docs/task.md`.

<!-- usage:start -->
## Machine time used

Measured from the job logs. Last updated Oct 15, 12:11 PM KST.

| stage | status | wall-clock time | CPU cores | peak memory |
|---|---|---|---|---|
| Distance search over all 1,872 valid schedules (includes Phases 1–2, which took seconds) | done | 3 h 9 min | 2 | about 0.6 GB |
| Error rates: S, L/R-like distance 6, distance 3 | done | 11 h 46 min | 2 | 0.6 GB |

**Sum of all stage times so far: 14 h 55 min**, about **30 core-hours**.
The machine has 12 CPU cores and 47 GB of RAM, shared by all four folders.
<!-- usage:end -->
