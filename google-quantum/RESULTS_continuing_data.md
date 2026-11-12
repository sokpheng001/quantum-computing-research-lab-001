# RESULTS — readout check in "continuing-data mode"

Run on 2026-11-01, about 6:20 pm KST. Code: `nnflags/continuing_data.py` (`python -m nnflags.continuing_data`). Data: `results/continuing_data.json`, `results/continuing_data_reembed_success03.json`.

## Mode

- **Setting.** The 7 data qubits are treated as live through the final measurement layer, as if they continue into escape.
- **Conflict.** Every flag / ancilla measured in that layer conflicts with any data qubit on the same readout line r + c.
- **Mid-circuit rule.** Unchanged: strict, `live_rule="gate"`. It is still 0 for every circuit below.

## Conflict counts (final-layer flag / ancilla measurements vs continuing data)

| circuit | conflicts | pairs (measured qubit (r, c) vs data qubit (r, c), readout line) |
|---|---|---|
| success00 | 7 | q1 vs d6, d10 (line 12); q7 vs d2, d3, d9 (line 11); q8 vs d4 (line 10); q12 (X flag) vs d4 (line 10) |
| success01 | 7 | q1 (line 12) ×2; q7 (line 11) ×2; q8 (line 10); q11 (Z flag), q12 (X flag) vs d9 (line 9) |
| success02 | 7 | same pattern as success01 |
| **success03** | **7** | q1 (5, 7) vs d8 (6, 6), line 12; q2 (4, 7) vs d6 (5, 6) and d9 (6, 5), line 11; q3 (4, 6) vs d5 (3, 7) and d10 (5, 5), line 10; q11 (Z flag, 4, 5) vs d4 (3, 6), line 9; q12 (X flag, 7, 5) vs d8 (6, 6), line 12 |
| success04 | 7 | same lines as success03 (9, 10, 11, 12) |
| success05 | 2 | q3, q8 vs d10, line 15 |
| success06 | 4 | q3 (line 14) ×2; q8 (line 15) ×2 |
| success07 | 4 | same as success06 |
| success08 | 4 | q1 (line 12) ×2; q7 (line 11) ×2 |
| success09 | 4 | same as success08 |
| G4 (CX and native) | 2 | q7 (8, 11) vs d10 (9, 10) and d11 (10, 9), line 19 |

**No circuit has 0 conflicts in this mode.**
- G4 is not clean either. In Google's actual experiment the data are read out in the same final TICK, so G4 is clean as run.

## success03: can the conflicts be fixed?

### Moving the final-layer measurements earlier or later: no, as plain measurements

- In this mode the data qubits are live at every moment.
- An ancilla or flag on a data qubit's line therefore conflicts whenever it is measured.
- Earlier, it would also become a mid-circuit measurement that hits the other live ancillas.

### What does work in principle: rotate to Z and defer

- After the unfold, each ancilla or flag holds its detector bit as a Z-basis classical value, once its MX is turned into H + M.
- A qubit sitting in a Z eigenstate is not disturbed by readout-line dephasing. This is the user's own live rule: a qubit idle in |0⟩/|1⟩ is not live.
- So its measurement can be **deferred** until it coincides with a simultaneous readout that includes the data. That moment is exempt.
- **Cost.** These qubits are held longer. T1 decay during the wait flips |1⟩ → |0⟩, which mainly causes false detector fires (lower acceptance) rather than logical error. This was not simulated here.

### Re-embedding (moving the circuit on the chip): no

- **Search space.** All 32,964 nearest-neighbour Willow embeddings of success03's two-qubit-gate graph were enumerated.
- **Ignoring the mid-circuit rule:**
  - minimum 2 continuing-data conflicts (1,892 embeddings);
  - the remaining 2 are always fold-tree **ancillas**, never the flags;
  - the flags alone can always be placed with 0 conflicts.
- **With the strict mid-circuit rule as well:** 1,620 embeddings remain. Their minimum is **7**, so the present placement is already optimal under both rules.
- **Fault distance.** Re-embedding never changes it: verify() gives 0 malignant T configurations at ≤ 2 faults for the best re-embedding (`results/success03_continuing_data_best.inner.stim`).

## Meaning

The obstruction is the success03 **fold tree** itself, not the flags.
- Its data-data gates (8–9, 9–10) and ancillas 1, 2, 3, which sit between data qubits, force at least one ancilla onto a data line.
- Google's guidance says Google's error-correction layouts keep data and measure qubits on separate readout lines. Doing that here needs either
  - the rotate-and-defer readout above, or
  - a new search over fold trees with "data lines disjoint from measured-qubit lines" as a hard constraint.
