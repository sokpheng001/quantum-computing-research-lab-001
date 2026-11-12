# First experiments on CNOT schedules for BB codes (001–004, method 2)

The first round of the CNOT-reordering project. Each subfolder has its own README with the question, setup and
results.

| Folder | Question |
|---|---|
| [`syndrome-circuit-scheduling-001/`](syndrome-circuit-scheduling-001/) | **Main experiment.** Does the CNOT order, or alternating two orders, improve a BB code? Logical error rate and circuit-level distance on [[72]], [[90]] and [[144]] |
| [`__syndrome-circuit-scheduling-002 (makes no sense - just test)/`](__syndrome-circuit-scheduling-002%20(makes%20no%20sense%20-%20just%20test)/) | test only: schedules that touch Left-block and Right-block data qubits in separate groups, on [[72]] |
| [`_syndrome-circuit-scheduling-003/`](_syndrome-circuit-scheduling-003/) | 001 repeated with a simpler decoder (BP-OSD-0); closed early |
| [`syndrome-circuit-scheduling-004/`](syndrome-circuit-scheduling-004/) | a third code, [[90,8,10]]: S, its time reverse, and their alternation |
| [`method2 for schedule reordering/`](method2%20for%20schedule%20reordering/) | method 2: search for a partner schedule S′ aimed at S's shortest fault paths |
| [`summary/`](summary/) | figures that compare all codes and experiments |

The later and more complete searches are in `../bb-code-reordering-cnot-running/` (uniform schedules) and
`../non-uniform schedule/`.
