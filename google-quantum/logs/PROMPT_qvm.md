You are working unattended in /home/ubuntu/quantum001/google-quantum on a remote Linux server. The user is away; nobody can answer questions. Make reasonable decisions, record them, keep going.

READ FIRST: ./RESULTS_g4.md, ./RESULTS_zzflags.md, ./RESULTS_comparison.md (all finished), and nnflags/ (verify.py, equivalence.py, g4.py, constraints.py, plots.py). Do NOT modify earlier results files; write new ones.

GOAL (user): implement our work inside Google's Quantum Virtual Machine (QVM) for Willow, as an independent experiment with Google's own software: cirq 1.7.0, cirq_google 1.7.0, qsimcirq 0.22.1 (already in ./.venv). Read the cirq_google source before using any function (cirq_google/engine/virtual_engine_factory.py: create_device_from_processor_id, load_device_noise_properties, load_median_device_calibration, create_default_noisy_quantum_virtual_machine, NoiseModelFromGoogleNoiseProperties, SimulatedLocalEngine) and cite file:line. Processor id "willow_pink" = the same Willow snapshot as our layout (willow_pink_d7v1-2024_08_16).

Circuits: success03 (main) and the next 2 best ZZ successes (results/zz/), G4 (native CZ+H, results/g4/ and its real coordinates) as the hardware reference, and d3a6 (best Willow placement, label it "what if": it breaks the readout rule).

WHERE TO PUT EVERYTHING (user's choice): the user created the folder ./qvm-google/ for this experiment.
All new QVM code, tests, results, figures and the report go INSIDE ./qvm-google/:
  qvm-google/qvm_willow.py (main code; import from nnflags for circuits/verify, do not copy it),
  qvm-google/tests/test_qvm.py, qvm-google/results/, qvm-google/figures/ (PNG only), qvm-google/logs/,
  qvm-google/RESULTS_qvm.md, qvm-google/README.md (how to rerun each experiment).
Do not add QVM code to nnflags/ and do not touch the user's own files (e.g. ./test..py).

EXPERIMENTS, in order:

E1. Conversion + Google device validation.
   - Convert each stim circuit to a cirq.Circuit on cirq.GridQubit(row, col) at its Willow positions, in Willow's native gate set (CZ + single-qubit gates as the device accepts them, measurements, resets). Check the conversion is faithful (e.g. stim -> cirq -> compare unitary / stabiliser flows on the Clifford version, or round-trip with stimcirq-style checks you write yourself; do not install packages).
   - Validate with the willow_pink device (device.validate_circuit). Report pass/fail and any rejected operation, and what you changed to make it pass (only gate decompositions; never change the logic).

E2. Real-T-gate correctness (noiseless, qsim).
   - Build the full cultivation-stage test the inner circuit belongs to: prepare the encoded state (state the method: e.g. ideal encoding of |+_L> followed by the transversal T pattern given by cliffordea's LOGICAL_S sublattices, as in cliffordea's conventions), then T^dagger layer, the double check, T layer, with REAL T gates (cirq.T / T**-1), not Clifford stand-ins.
   - Check: with no noise, every detector is 0 and the output logical state is the T state (fidelity 1 within numerical precision).

E3. Fault injection with real T gates (validates the Clifford fault analysis).
   - Using the fault list cliffordea enumerates (FaultCombinator.index_to_events), inject faults as explicit Pauli operators into the real-T qsim circuit and check, per configuration, whether it is kept (no detector fired) and whether the kept logical state is corrupted.
   - Exhaustive for all single faults; for 2 faults: all malignant configurations cliffordea reports for d3a6 and G4 (expected: kept and corrupted), plus a random sample (>= 2,000, seed fixed) of 2-fault configurations for success03 (expected: none kept-and-corrupted). Report agreement with cliffordea's malignant/benign classification; any disagreement must be reported prominently with the configuration.

E4. Noisy QVM run (Google's Willow noise model).
   - Build the noisy QVM for willow_pink (create_default_noisy_quantum_virtual_machine or the equivalent explicit NoiseModelFromGoogleNoiseProperties + qsim simulator); state exactly which noise channels the model includes (and that readout-line dephasing / crosstalk is NOT included if that is the case).
   - Sample each circuit (real T gates): acceptance rate (no detector fired) with a relative standard error < 1 % (report shots), and the kept-state logical infidelity estimate with its error bar, using an ideal noiseless decode/measurement of the logical H_XY at the end. State clearly that error rates near 1 in a million are far below what the shot count can resolve; give the upper bound instead.
   - Compare the QVM acceptance with the stim calibrated-noise acceptance from RESULTS_comparison.md; explain differences (different noise models).
   - Budget: at most ~2 hours of total QVM sampling wall time; use the 12 cores (qsim threads / parallel processes). Checkpoint to disk.

REPORT: ./qvm-google/RESULTS_qvm.md: top answer in 3 sentences (does Google's QVM accept success03 on Willow, does it work with real T gates, what acceptance/infidelity it shows), status table E1-E4, results tables, exactly what the QVM noise model includes and excludes, limitations, decisions made without the user. Figures (PNG ONLY, never PDF; plotting code in qvm-google/, saved to qvm-google/figures/): E3 agreement chart, E4 acceptance comparison (QVM vs stim) and infidelity with error bars. Plain academic style, white background, colour-blind-safe with markers/hatching, no e-notation ticks.

RULES: NEVER edit ./cliffordea. ./.venv only; do not install or uninstall packages; nothing outside this folder; no git commits. Rates as % or "1 in N", never e-notation. Times in KST with am/pm. Report every number with its settings. All existing tests (nnflags/tests and qvm-google/tests) must pass. Confirm `git -C cliffordea status --porcelain --ignored` is empty. Then STOP.
