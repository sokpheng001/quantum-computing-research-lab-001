# Uniform schedules: one-cycle distance of every depth-7 CNOT order

**Purpose.** In a *uniform* schedule every ancilla uses the same CNOT layer order. Using Bravyi et al.'s own
distance search (reference code in `bravyi_ref/`, not included), compute the one-cycle circuit distance d1 of
**every** valid uniform depth-7 schedule. Any alternation can only beat Bravyi's schedule S if some schedule has
d1 above d1(S).

**Setup.**
- Noise: one noisy cycle followed by two noiseless cycles, as in Bravyi's `circuit_distance.py`.
- Search: BP-OSD with OSD-CS order 20.
- The search is first checked against Bravyi's value for S on each code.

**Results** (`RESULTS_method3.md`):

| Code | Schedules searched | Highest d1 found | Above d1(S)? |
|---|---|---|---|
| [[72,12,6]] | 1,872 | 6 | none above 6 |
| [[90,8,10]] | 1,872 | 8 | none above 8 |
| [[108,8,10]] | – | – | scan not finished (stopped) |

For [[90]] we also computed the circuit-level distance and the logical error rate of S, alt[S, S⁻¹], the
top-ranked schedule A* and alt[A*, A*⁻¹]. All four have distance 8 and the same logical error rate within
error bars.

**Files.**
- `task.md` (copy in `docs/`): the plan.
- `ours/`: our code.
  - `bravyi_d1.py`: vectorised port of Bravyi's search, checked identical to the reference;
  - `m3.py`: the stages;
  - `report_m3.py`: writes the report.
- `driver_method3*.sh`, `launch.sh`: run scripts.
- `results_method3/`: per-code tables.
- `figures_method3/`, `report_figure/`: figures.
