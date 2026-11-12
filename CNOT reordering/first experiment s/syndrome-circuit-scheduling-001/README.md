# 001 — Main experiment: CNOT schedules for BB codes

**Question.** Does the order of the CNOT gates in the syndrome circuit, or alternating two
orders from cycle to cycle, improve a bivariate bicycle (BB) code?
This is open question 4 of Bravyi et al., *Nature* 627, 778 (2024).

**Codes.** [[72,12,6]] and the gross code [[144,12,12]].

## Testing stages

| stage | what is tested | status |
|---|---|---|
| 1. Tools | Distance search, error-rate pipeline, Bravyi's [[72]] curve reproduced, all 936 valid depth-7 schedules found | done |
| 2. Three circuits on [[72]] | Bravyi's schedule S, its time reverse S⁻¹, and alternating S/S⁻¹ | done: all three equal |
| 3. All 936 schedules on [[72]] | Distance and fault-path count of every schedule, ranking | done: 127 of 936 lose distance, down to 3 |
| 4. Pairs on [[72]] | Pairs of top schedules alternated | done: no gain |
| 5. Best, median, worst on [[72]] | Error rate of three ranked schedules against S | running |
| 6. Three circuits on [[144]] | Distance bounds (5 seeds), then error rate at 6 cycles | running |

## Methods

- **Circuit.** Bravyi's depth-7 syndrome cycle (7 CNOT rounds plus measurement), built in stim.
- **Noise.** Uniform circuit-level depolarising noise at rate p on gates, idle qubits, resets and measurements.
- **Decoder (error rate).** BP-OSD from ldpc 2.4.1: serial min-sum BP, 100 iterations,
  OSD combination sweep order 7.
- **Distance search.** Randomised BP-OSD fault-path search (OSD order 20). It finds
  low-weight undetectable logical faults; each one gives an upper bound on the
  circuit-level distance.
- **Error rate.** Logical error rate per cycle, with 95% error bars, from at least 30 to 50 failures per point.

## Where to look

- **RESULTS.md** — every result with tables. **CLAUDE.md** — definitions and settings.
- **figures/** — plots. **results/** — raw data (CSV, JSON).
- `./launch.sh status` shows running jobs. Run scripts with `../venv/bin/python`.

## Folder layout

All four folders (001–004) use the same layout.
After a server restart, unfinished jobs resume by themselves about a minute after boot (`../resume_all.sh`, started at boot). Finished work is never repeated. A job you stop yourself with `./launch.sh stop` stays stopped after a restart.

| path | contents |
|---|---|
| `README.md` | this guide |
| `RESULTS.md` | results with tables (drivers add to it automatically) |
| `CLAUDE.md` | settings and definitions used by Claude |
| `launch.sh` | `./launch.sh <driver.sh>` starts a job; `./launch.sh status`; `./launch.sh stop` (this folder's jobs only) |
| `driver_*.sh` | the pipeline(s) of this folder |
| `*.py` | the code the pipelines use |
| `docs/` | task plans and reference notes |
| `results/` | data (CSV, JSON) and job logs (`*.log`) |
| `figures/` | plots (PNG) |
| `archive/` | old scripts kept for the record, not used |

**Main files.** Library: `bb_code.py` (circuits), `dcirc.py` (decoder and distance search). Pipeline: `driver_144three.sh`. Finished [[72]] scripts: `archive/72_done/`. Plans: `docs/TASKS.md`, `docs/TASK2.md`.

<!-- usage:start -->
## Machine time used

Measured from the job logs. Last updated Oct 16, 08:52 AM KST.

| stage | status | wall-clock time | CPU cores | peak memory |
|---|---|---|---|---|
| Stage 2 extra points on [[72]] (p = 0.002–0.008) and Bravyi reproduction | done | 2 h 46 min | 12 | about 3 GB |
| [[144]] distance bounds for S, S⁻¹, alternating (4 cycles) | done | 3 h 22 min | 12 | about 11 GB |
| [[144]] error rates at 12 cycles, S and alternating (stopped early) | done | 16 h 5 min | 8 | 34 GB |
| Stage 3: distance + fault paths of all 936 schedules on [[72]] | done | 7 h 24 min | 12 | about 3 GB |
| Stage 3–4: ranking, pair selection, pair distance bounds on [[72]] | done | 21 min | 12 | about 3 GB |
| [[144]] distance bounds for the chosen pairs | done | 3 h 18 min | 12 | about 11 GB |
| Stage 5 part 1: best / median / worst error rates on [[72]] | done | 3 h 8 min | 12 | about 3 GB |
| Stage 5 part 2: best / median / worst error rates on [[72]] | done | 15 h 11 min | 4 | 1.2 GB |
| [[144]] verification search, first version (replaced) | done | 1 h 38 min | 8 | about 7 GB |
| Stage 6: [[144]] three-circuit distance bounds, 5 seeds | done | 17 h 12 min | 8 | 7.3 GB |
| Stage 6: exact fault-path check and bounds report | done | 1 min | 1 | not measured |
| Stage 6: [[144]] three-circuit error rates, 6 cycles | done | 1 day 4 h | 8 | 8.5 GB |

**Sum of all stage times so far: 4 days 2 h**, about **808 core-hours** (some stages ran at the same time).
The machine has 12 CPU cores and 47 GB of RAM, shared by all four folders.

The first runs on Oct 12 (tool checks, schedule enumeration, first S / S⁻¹ / alternating run on [[72]]) were not timed; together they took a few hours on 12 cores.
<!-- usage:end -->
