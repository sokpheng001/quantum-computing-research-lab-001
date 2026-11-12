# 004 — Three-circuit experiment on [[90,8,10]]

**Question.** On a third BB code, does alternating Bravyi's schedule with its time
reverse change the circuit-level distance or the logical error rate?

**Code.** [[90,8,10]]: l = 15, m = 3, A = x⁹ + y + y², B = 1 + x² + x⁷.
Bravyi et al. report a circuit-level distance of at most 8 for this code.

**Circuits.** S (Bravyi's schedule), S⁻¹ (its time reverse), alternating S/S⁻¹.
All three were checked: valid in both bases, 8 logical qubits.

## Testing stages

| stage | what is tested | status |
|---|---|---|
| 1. Distance | 5 independent searches × 600 trials per circuit and basis, 4 cycles | running |
| 2. Error rate | 6 cycles, both bases, p = 0.006, 0.005, 0.004, at least 30 failures | after stage 1 |

## Methods

- **Decoder (error rate).** Same BP-OSD as 001: serial min-sum BP, 100 iterations,
  OSD combination sweep order 7.
- **Distance search.** Same randomised BP-OSD fault-path search as 001 (OSD order 20);
  each result is an upper bound on the circuit-level distance.
- **Workers.** Adjust to the free CPU cores (2 to 8) at every step.

## Where to look

- **figures/exp_90_bounds.png** — distance found per circuit and basis.
- **figures/exp_90_three_ler.png** — logical error rate, Z and X panels.
- **RESULTS.md** — tables, added automatically. `./launch.sh status` shows this folder's job.

## Folder layout

All four folders (001–004) use the same layout.
After a server restart, unfinished jobs resume by themselves about a minute after boot (`../resume_all.sh`, started at boot). Finished work is never repeated. A job you stop yourself with `./launch.sh stop` stays stopped after a restart.

| path | contents |
|---|---|
| `README.md` | this guide |
| `RESULTS.md` | results with tables (drivers add to it automatically) |
| `CLAUDE.md` | settings and definitions used by Claude (shared definitions are in 001) |
| `launch.sh` | `./launch.sh <driver.sh>` starts a job; `./launch.sh status`; `./launch.sh stop` (this folder's jobs only) |
| `driver_*.sh` | the pipeline(s) of this folder |
| `*.py` | the code the pipelines use |
| `docs/` | task plans and reference notes |
| `results/` | data (CSV, JSON) and job logs (`*.log`) |
| `figures/` | plots (PNG) |
| `archive/` | old scripts kept for the record, not used |

**Main files.** `strong_search.py` (distance search), `run_ler.py` (error rates), `fig_bounds.py`, `fig_ler.py`. Pipeline: `driver_004.sh`.

<!-- usage:start -->
## Machine time used

Measured from the job logs. Last updated Oct 16, 08:52 AM KST.

| stage | status | wall-clock time | CPU cores | peak memory |
|---|---|---|---|---|
| Distance bounds, S / S⁻¹ / alternating, 5 seeds × 600 trials | done | 8 h 56 min | 2–8 (adapts to free cores) | 0.8 GB |
| Error rates, 6 cycles, p = 0.006 / 0.005 / 0.004 | done | 18 h 57 min | 2–8 (adapts to free cores) | 1.8 GB |

**Sum of all stage times so far: 1 day 3 h**, about **111 core-hours**.
The machine has 12 CPU cores and 47 GB of RAM, shared by all four folders.
Stages marked "adapts" change their core count with the free cores; their core-hours are counted at 4 cores.
<!-- usage:end -->
