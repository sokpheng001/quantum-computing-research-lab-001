# Test 1: first fault-distance-3 circuits vs Google's Fig. 2 double check (Google QVM)

**Purpose.** Check the first fault-distance-3 double checks we found (`success03`, `success04`, `success00`,
from the flag search) inside Google's own software (cirq, cirq_google, qsim, processor `willow_pink`, real T
gates). Google's as-run circuit **G4** (Fig. 2 of Rosenfeld et al.) is the reference.

**Experiments.**
- **E1:** conversion to native gates plus Google's device validation.
- **E2:** noiseless correctness with real T gates.
- **E3:** every single fault and every fault pair injected, compared with cliffordea.
- **E4:** noisy sampling with Google's Willow noise model.

**Result.** All circuits pass E1 and E2. E3 agrees with cliffordea in 73,261 of 73,261 configurations: the
three circuits have fault distance 3 and G4 has 2.

**Caveat.** These circuits break the readout-line rule when the data qubits continue (for example, success03
has 7 conflicts). That led to test 2 and the circuit cs02.

**Files.**
- `RESULTS.md`: the full report.
- `results/`: JSON results and resumable checkpoints.
- `figures/`: plots, including `zz_best_circuits.png`.
- `plots.py`: draws the figures.

The engine is `../qvm_willow.py`; run it from `google-quantum/`.
