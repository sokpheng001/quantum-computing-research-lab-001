# Test 7: cs02 vs Google's double check under many conditions, and why cs02 is better

**Purpose.** Check that cs02's advantage over Google's distance-3 double check holds under other noise models,
noise strengths, chip positions and noisy inputs, and find the exact mechanism behind it. Only circuits that
can run on Willow are compared.

| Part | Question | Report | Result |
|---|---|---|---|
| A | other noise models (uniform, SI1000, Willow spec, Willow calibration) | `RESULTS.md` | cs02 better in every model (3.0× to 5.8×) |
| B | SI1000 noise sweep, p = 0.05 % to 0.5 % | `RESULTS.md` | slopes 3.04 (cs02) vs 2.17 (Google); gain 13.7× at p = 0.05 % |
| C | every legal placement on the chip (calibration model) | `RESULTS.md` | median 1 in 111,425 (cs02, 160 placements) vs 1 in 47,451 (Google, 196 placements) |
| D | noisy input to the check (logical error at Google's measured injection rate + 0.1 % per data qubit) | `RESULTS_noisy_input.md` | 4.6× (3.5× to 6.0×) at input 1 in 224; 3.4× at 1 in 56; 1.7× under SI1000 p = 0.36 % |
| E | mechanism: where the improvement comes from | `MECHANISM.md` | Google's 7 silent pairs exist only with real T. cs02 without its flag alarms has 6 such pairs; with the flags it has 0, each caught with certainty |
| F | one input error plus one fault in the check | `RESULTS_input_plus_fault.md` | Google 4 silent-wrong pairs; cs02 0 of 3,912 |

**Scripts.**

| Script | Parts |
|---|---|
| `t7_d3_benchmarks.py`, `run_t7.sh` | A to C |
| `t7_noisy_input.py`, `t7_noisy_input_report.py`, `run_t7_noisy_input.sh` | D |
| `t7_mechanism.py`, `run_t7_mechanism.sh` | E |
| `t7_input_plus_fault.py`, `run_t7_input_plus_fault.sh` | F |

Figures are PNG files in `figures/`. Run from `google-quantum/` with the project environment.
