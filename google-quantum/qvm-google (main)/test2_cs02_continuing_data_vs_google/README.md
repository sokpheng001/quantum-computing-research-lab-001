# Test 2: cs02 vs Google's double check with continuing data (Google QVM)

**Purpose.** This is the main comparison. The T state must survive the check, so the 7 data qubits are never
measured. Under Willow's readout-line rule, no measured qubit may then share a readout line with a data qubit.

**Circuits.**
- **cs02 (ours):** fault distance 3, and it satisfies the rule.
- **Google's G4 G6-style:** Google's Fig. 2 double check with the one helper that sits on a data readout line left unmeasured, as Google does in its Fig. 4.

**Method.** Google's QVM (`willow_pink` noise model, real T gates). The double check alone, starting from a
perfect encoded T state and ending with an ideal decode, identical for both circuits. 8,000,000 shots each.

**Result.**

| | Google G4 G6-style | cs02 |
|---|---|---|
| wrong / kept in code space | 221 / 4,603,871 | 42 / 5,095,514 |
| error per kept T state | 1 in 20,832 | **1 in 121,322** |
| acceptance | 76.7 % | 75.2 % |

cs02 is **5.8× better** (95 % CI 4.2× to 8.1×). E3 fault injection confirms fault distance 3 (cs02: 0 of 13,041
pairs silent) against 2 (Google: 7 of 11,175).

**Files.**
- `RESULTS.md`: the full report.
- `run_all.sh`, `run_baseline_8M.sh`: run the test.
- `run_qvm.py`: registers the circuits with the engine.
- `plots.py`, `draw_circuit.py`, `report.py`: figures and the report.
- `figures/`:
  - `qvm_cs02_vs_google.png`: the QVM results;
  - `continuing_circuits.png`: the layouts;
  - `cs02_circuit.png`: the gate drawing.
