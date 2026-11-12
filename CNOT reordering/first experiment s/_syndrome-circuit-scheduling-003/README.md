# 003 — Same as 001, decoded with BP-OSD-0 (closed)

**Status: closed on Oct 15.** Only the [[72]] runs at p = 0.006 and 0.004 were completed; the [[72]] p = 0.002
and [[144]] stages were cancelled as not needed. No job runs here and none will resume.

**Question.** Do the 001 conclusions still hold with a simpler, faster decoder?

**Only change from 001.** The decoder for logical error rates is **BP-OSD-0**
(OSD order 0) instead of BP-OSD with combination sweep order 7.
Circuits, noise and schedules are the same as in 001.

## Testing stages

| stage | what is tested | status |
|---|---|---|
| 1. [[72]] three circuits | S, S⁻¹, alternating; p = 0.006, 0.004 | done (p = 0.002 dropped: the 001 baseline is sufficient) |
| 2. [[72]] ranked schedules | Best, median, worst schedule against S; p = 0.006, 0.004 | done |
| 3. [[144]] three circuits | S, S⁻¹, alternating at 6 cycles; p = 0.005, 0.004 | cancelled by decision on Oct 15 (not needed) |

## Methods

- **Decoder.** ldpc 2.4.1 BP-OSD-0: serial min-sum BP, 100 iterations, then OSD order 0.
- **Distance.** Not recomputed. The distance search does not depend on the decoder,
  so the bounds are copied from 001 (see `docs/RESULTS_001_reference.md`).

## Where to look

- **RESULTS.md** — results of this folder. **figures/** — plots ending in `_osd0.png`.
- `./launch.sh status` shows this folder's job only.

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

**Main files.** `dcirc.py` (decoder set to BP-OSD-0), `run_ler.py`, `fig_ler.py`. Pipeline: `driver_003.sh`. Distance data copied from 001: `results/from_001/`. Reference: `docs/RESULTS_001_reference.md`.

<!-- usage:start -->
## Machine time used

Measured from the job logs. Last updated Oct 16, 08:52 AM KST.

| stage | status | wall-clock time | CPU cores | peak memory |
|---|---|---|---|---|
| [[72]] error rates at p = 0.006 and 0.004 (6 circuits, both bases) | done | 18 h 31 min | 2–8 (adapts to free cores) | not measured |
| Waiting for 001 to free the gross-code cores (no computing) | stopped before finishing | – | – | – |
| [[144]] three-circuit error rates, 6 cycles | not started | – | – | – |

**Sum of all stage times so far: 18 h 31 min**, about **74 core-hours**.
The machine has 12 CPU cores and 47 GB of RAM, shared by all four folders.
Stages marked "adapts" change their core count with the free cores; their core-hours are counted at 4 cores.
<!-- usage:end -->
