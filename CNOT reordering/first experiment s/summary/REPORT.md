# Progress report — CNOT scheduling for bivariate bicycle codes

**Status as of Thursday, Oct 15, 2026, 9:00 am KST.** Folders 001–004 under `quantum001/`.

## Research question

Bravyi et al. (*Nature* 627, 778, 2024), open question 4: can a different depth-7 CNOT order
in the syndrome circuit, or alternating two orders from cycle to cycle, improve a bivariate
bicycle (BB) code's circuit-level distance or logical error rate?

We test Bravyi's schedule **S**, its time reverse **S⁻¹**, the **alternating** circuit S/S⁻¹,
and the full set of 936 valid depth-7 schedules, on three codes: [[72,12,6]], [[90,8,10]] and
the gross code [[144,12,12]].

## Methods

- **Circuits.** Bravyi's syndrome cycle (7 CNOT rounds plus measurement), built with stim.
  Uniform circuit-level depolarising noise at rate p.
- **Logical error rate.** Noisy shots are sampled and decoded with BP-OSD (serial min-sum
  BP, 100 iterations, OSD order 7). Folder 003 repeats this with BP-OSD-0. Reported per cycle,
  with 95% error bars, from at least 30–50 failures per point.
- **Circuit-level distance.** Randomised BP-OSD search for the lightest set of faults that flips
  a logical without tripping any detector (thousands of trials, 5 independent seeds). Each value
  is an upper bound. Selected results are checked exactly with stim.
- Diagram: `summary/figures/method_pipeline.png`.

## Main results

### 1. Bad CNOT orders lose distance, and it shows in the error rate — confirmed

- **127 of 936** valid depth-7 orderings reduce the circuit-level distance of [[72,12,6]],
  down to 3. Bravyi's S keeps the full distance 6.
- All of the worst orderings switch between the Left and Right data blocks at every CNOT.
- The logical error rate confirms it. At p = 0.002, per cycle:

| schedule | Z | X |
|---|---|---|
| S (Bravyi) | 1.9e-4 | 3.3e-4 |
| best ranked (744) | 2.1e-4 | 2.2e-4 |
| median (131) | 2.1e-4 | 2.0e-4 |
| **worst (52), distance 3** | **7.2e-4** | **8.1e-4** |

The distance-3 schedule is 3.5–4× worse, and the gap grows as p falls. Best, median and S are equal.
(S in the X basis at p = 0.002 rests on only 4 failures, so its error bar is wide.)
Figures: `001/figures/hist_dcirc_below6.png`, `001/figures/single_schedules_ler.png`.

### 2. Among good schedules, none beats Bravyi's S on [[72]]

- S, S⁻¹ and alternating have the same error rate at every p from 0.002 to 0.008.
- The best-ranked schedule and the most L/R-structured distance-6 schedule (folder 002) also
  match S within error bars.
- Pure L/R block schedules (task.md strategies A, B, C) cannot be built as valid depth-7 circuits.

### 3. Circuit-level distance on all three codes

| code | S | S⁻¹ | alternating | Bravyi's value for S |
|---|---|---|---|---|
| [[72,12,6]] | 6 | 6 | 6 | 6 |
| [[90,8,10]] | 8 | 9 (no weight-8 path found yet; not verified) | 8 | 8 |
| [[144,12,12]] | **10** (Bravyi's path; our search only reached 11) | **10** | **11** (not yet verified) | 10 |

- All values are **upper bounds**: a fault path of that weight exists. A higher value can mean the
  search missed a lighter path, so a difference counts only after the lighter paths are checked exactly.
- **[[90]]:** alternating reaches 8, the same as S. No gain. S⁻¹ is S run backwards in time, so its true
  value is probably also 8; the 9 only means its weight-8 path was not found yet.
- **[[144]]:** the search found Bravyi's weight-10 value, in S⁻¹. The alternating circuit has
  stayed at 11 in 12,000 trials per basis, and S⁻¹'s weight-10 fault path cannot be placed
  inside the alternating circuit. **This is the one open sign of a possible gain.** It is not
  yet confirmed, because weight-10 paths are very rare for this search (one found in 12,000 trials).
- An exact check confirms the alternating circuit is at most 11 on the gross code.

Figure: `summary/figures/summary_dcirc.png`.

### 4. Logical error rate on [[90]] and [[144]] (in progress)

- **[[90]], 6 cycles:** S, S⁻¹ and alternating are equal within error bars at p = 0.005 and 0.006.
- **[[144]], 6 cycles, p = 0.005:** S 2.1e-3 (Z) and 2.6e-3 (X); S⁻¹ 3.4e-3 (Z). Other points running.
- **[[144]], 12 cycles (earlier run):** alternating equals S at p = 0.005 and 0.006.

Figure: `summary/figures/summary_ler.png`.

### 5. Decoder comparison on [[72]] (folder 003, in progress)

BP-OSD-0 gives about 20% more logical errors than BP-OSD order 7. An early hint that the
weaker decoder hurts S more than the other circuits did not hold up at p = 0.004.
Figure: `summary/figures/decoder_compare.png`.

## Conclusions so far

1. **Schedule choice matters mainly to avoid bad orderings.** 14% of valid depth-7 orders
   lose distance, and that costs up to 4× in logical error rate.
2. **No schedule or alternation beats Bravyi's S** on [[72]] or [[90]], in distance or error rate.
3. **The gross code is still open.** The alternating circuit may avoid the weight-10 fault
   paths that S⁻¹ (and, by Bravyi, S) have. That would be a positive answer to open question 4.

## Next steps

1. **Decide the gross-code question exactly.** Test the known weight-10 paths of S⁻¹ and S
   in the alternating circuit, and run a focused extra search for weight-10 paths in it.
2. Finish the gross-code error rates (6 cycles, both bases, p = 0.004 and 0.005).
3. Finish [[90]] error rates. (The BP-OSD-0 gross-code runs were cancelled as not needed.)

[[72]] is complete: its baseline results are final and no further [[72]] runs are planned.

## Still running

| folder | job | expected finish (KST) |
|---|---|---|
| 001 | [[144]] error rates, S / S⁻¹ / alternating | Friday, Oct 16, afternoon |
| 004 | [[90]] error rates | Thursday, Oct 15, evening |
| 003 | closed: [[72]] done at p = 0.006 and 0.004; [[144]] stage cancelled | – |

## Machine time used so far

| folder | wall-clock (sum of stages) | core-hours |
|---|---|---|
| 001 | 3 days 3 h | about 620 |
| 002 (finished) | 14 h 55 min | about 30 |
| 003 | 17 h 30 min | about 70 |
| 004 | 17 h 30 min | about 70 |

Server: 12 CPU cores, 47 GB RAM. All jobs run in the background and resume after a restart.
