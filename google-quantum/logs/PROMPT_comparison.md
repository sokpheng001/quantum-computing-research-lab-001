You are working unattended in /home/ubuntu/quantum001/google-quantum on a remote Linux server. The user is away; nobody can answer questions. Make reasonable decisions, record them, keep going.

READ FIRST: ./RESULTS_g4.md, ./RESULTS_option1.md, ./RESULTS_zzflags.md (just finished), and nnflags/verify.py, nnflags/g4.py, nnflags/plots.py. Do NOT modify earlier results files; write new ones.

TASK: complete the design comparison with the two missing metrics. Small, focused job; no new search.

Designs (all in cliffordea CX form, same noise model):
- d3a6 (DoubleCheck(3,6)), d3a6f2 (DoubleCheck(3,6,flag_count=2)), d3a4 (DoubleCheck(3,4)),
- G4 extracted, CX form and native CZ+H (results/g4/),
- best Option-1 candidate (results/option1/cand03.*),
- all ZZ-flag successes (results/zz/success*.{inner,full}.stim).

1. d3a6f2 at 3 faults: malignant T and S configuration counts at k = 0..3 and the T (and S) logical error per kept shot at p = 0.001 with max_fault_count 2 and 3, exactly as done for the other designs. Use verify() / cliffordea code paths (read source first; cite file:line).

2. Acceptance (post-selection) rate = probability a shot is kept (no detector fires), and attempts per kept shot = 1 / acceptance.
   - First look in cliffordea for an existing acceptance / keep-probability quantity (e.g. in FaultCombinator or its summary); read the source and use it if it exists, citing file:line, and state what it means (truncation order).
   - Independently, estimate it by stim Monte Carlo: take the same noisy inner circuit cliffordea analyses (enum.noise.uniformly_depolarize at the given p), sample detectors with stim's detector sampler, kept = no detector fired. Use enough shots for a relative standard error below 1% (report shots and the standard error). Do this at p = 0.0005, 0.001, 0.002 and 0.003 (user's list: 5e-4, 1e-3, 2e-3, 3e-3).
   - Check that the cliffordea value (if any) and the Monte Carlo agree to within their errors at p = 0.001; explain any difference.
   - Also report "T error per attempt" = T error per kept shot × acceptance, so designs with different discard rates are comparable.

3. Table and figure:
   - RESULTS_comparison.md: one table with rows = designs, columns = Willow-compatible?, qubits, flags, TICKs, CX count, malignant T at 1/2/3 faults, malignant S at <=2, T error per kept shot (mfc 3, p = 0.001), acceptance at p = 0.001 (± error), attempts per kept shot, T error per attempt. Then a short paragraph: does the fault-distance-3 Willow design keep its advantage once discards are counted? Be factual; state the settings.
   - figures/comparison_acceptance.png (PNG ONLY, never PDF): acceptance vs p for the main designs (d3a6, d3a6f2, G4-CX, best Option-1, best ZZ success), and a bar chart of T error per kept shot and per attempt at p = 0.001. Plain academic style, white background, colour-blind-safe with markers/hatching, no e-notation tick labels. Add the plotting code to nnflags/plots.py (PNG only).

4. REALISTIC WILLOW NOISE (user request, do after 1-3). The cirq_google calibration file
   .venv/.../cirq_google/devices/calibrations/willow_pink_d7v1-2024_08_16_calibration.json belongs to Willow
   (same snapshot as our layout file; 105 qubits, 182 pairs). Load it with cirq_google (Calibration + MetricsSnapshot).
   - Primary model = per-qubit / per-pair calibration: CZ error from two_qubit_parallel_cz_gate_xeb_pauli_error_per_cycle
     (state whether you subtract the single-qubit part of the XEB cycle, and why), single-qubit gate error from
     single_qubit_rb_pauli_error_per_gate, readout error per qubit from single_qubit_p00_error / p11_error (asymmetric),
     idling from single_qubit_idle_t1_micros (amplitude/phase damping approximated as Pauli twirl; T2 is not in the
     file, so state your assumption, e.g. T2 = T1 or a documented value) using gate durations: 1q ~25-35 ns,
     CZ ~42 ns, measurement 600 ns (Google proposal guidance), reset (state value). Document every number and source.
   - Secondary model = Willow spec-sheet averages, uniform: CZ 0.33 %, 1q 0.035 %, measurement 0.77 %, T1 = 68 us idling.
   - Apply to the circuits in NATIVE CZ + H form at their Willow positions (convert CX form with nnflags.equivalence /
     g4 helpers; check the conversion keeps the malignant counts under uniform noise). G4: use its own coordinates.
   - Check whether cliffordea's FaultCombinator accepts an arbitrary noisy stim circuit (read source, cite file:line).
     If yes, use it for malignant-weighted T error per kept shot; if not, explain and use the closest faithful route.
   - Rerun the same comparison under both models for success03 (and the best 3 successes), d3a6f2, G4 and unflagged
     d3a6: malignant T counts are noise-independent, so report T error per kept shot (mfc 3), acceptance (stim Monte
     Carlo, rel. s.e. < 1 %), attempts per kept T state, T error per attempt. d3a6 and d3a6f2 are not Willow-compatible:
     place them on their best Willow placement and say so; their numbers are "what if" only.
   - Table in RESULTS_comparison.md (section "Realistic Willow noise") and figure figures/comparison_willow_noise.png (PNG only).

5. Housekeeping: the user installed cirq / cirq_google / qsimcirq into ./.venv, which downgraded pandas (3.1.0 -> 3.0.6) and contourpy (1.4.0 -> 1.3.2). Run the FULL test suite and report the result; regenerate requirements-lock.txt from `.venv/bin/pip freeze`. Do not install or uninstall anything.

RULES: NEVER edit ./cliffordea. ./.venv only; nothing outside this folder; no git commits. Rates as % or "1 in N", never e-notation. Times in KST with am/pm. Report every number with its settings. Confirm `git -C cliffordea status --porcelain --ignored` is empty. Then STOP.
