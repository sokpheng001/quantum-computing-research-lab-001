You are working unattended in /home/ubuntu/quantum001/google-quantum on a remote Linux server. The user is away; nobody can answer questions. Make reasonable decisions, record them, keep going.

READ FIRST, FULLY: ./first-ex.md, ./RESULTS_step3.md, ./RESULTS_g4.md, ./RESULTS_option1.md, and the code in ./nnflags/ (constraints.py, verify.py, equivalence.py, g4.py, search_option1.py, candidates.py, embed_search.py, plots.py). Reuse the Option-1 screen cache (results/option1_screen.json, results/option1_bases.csv) instead of recomputing.

GOAL (user): find a distance-3 T-cultivation double check that runs on Willow AND has fault distance 3, i.e. 0 malignant T configurations with <= 2 faults, or show clearly why none exists in the design space below.

BACKGROUND (from earlier runs): G4-style fold trees (ancilla root on a clear readout line) already satisfy every hardware rule; the best has 6 malignant 2-fault T configurations (G4: 7). Same-control Z flags (CX q->f twice) never removed a malignant configuration, because each hook window crosses the CX in which the hook qubit is a target. The paper's fix (d3a6f2) uses flags with TWO different controls. The square grid has no triangles, so a flag cannot touch two qubits that are themselves neighbours; a multi-control flag on Willow must sit on a free grid point whose neighbours (up to 4) are tree qubits that are diagonal / distance-2 from each other.

DESIGN SPACE
- Bases: the feasible abstract fold forests from the Option-1 screen (G4-type, ancilla roots on readout lines with nothing else live, code labelling optimised), ordered by best malignant T at 2 faults, plus G4's extracted double check itself (results/g4/, CX form) as an extra base. Try several Willow embeddings per base (rotations/translations/other shapes of the same abstract tree), because which grid points are free decides where flags fit.
- Flags: GENERALISED Z flags. A flag f is a free Willow qubit, prepared with R, receiving CX(q_i -> f) from one or more of its grid neighbours q_i (tree qubits), at chosen TICKs (existing idle slots or inserted TICKs; count added TICKs), measured with M and a DETECTOR. The detector must be deterministic (check with stim). This includes the old same-control flag and the paper's two-control flags. Also allow, as a secondary family, X flags (RX f, CX f -> q_i, MX f) if Z flags fail. Choose controls/times to cover the malignant configurations: use FaultCombinator.index_to_events on the base's malignant 2-fault T configurations and pick flag gates whose detector flips for at least one fault of each malignant pair (verify by stim/cliffordea, not by hand reasoning).
- Number of flags: primary search 1-2 flags per circuit. If no fault-distance-3 circuit is found with <= 2 flags, run ONE extra pass with 3 flags and label it clearly as beyond the user's 1-2 limit.
- Constraints, all strict: nearest-neighbour gates only, degree <= 4 for every qubit (flags add partners to tree qubits!), no qubit twice in a TICK, strict readout with live_rule="gate" and final_layer="auto". Flags should preferably be measured in the final simultaneous measurement layer; a mid-circuit flag measurement is allowed only if its readout line has nothing else live.
- Every circuit must pass check_equivalence (flags excluded from the time-reverse check) and verify().

SUCCESS = valid circuit with malignant T = 0 at 1 and 2 faults (max_fault_count 2). For each success also report: malignant T at 3 faults, malignant S at <= 2 faults (an S malignancy at <= 2 faults must be reported prominently; prefer circuits with 0), logical error per kept shot at p = 0.001 (as "1 in N", max_fault_count 2 and 3), n_flags, flag controls, added TICKs, total qubits, CX count, max degree.

STOPPING: stop when 10 successful circuits are found, OR the design space is exhausted, OR after 6 hours of search wall time, whichever comes first. Checkpoint to disk (results/zz_candidates.csv, every evaluated circuit with its malignant counts; stim files of successes and of the best non-successes in results/zz/). Run long jobs with nohup + log in ./logs/ and use the 12 cores.

IF NO SUCCESS: give the evidence, not just "none found": the best malignant T at 2 faults reached, and for the best bases which malignant pairs could not be covered and why (no free grid point adjacent to the needed controls, degree limit, detector not deterministic, readout conflict, ...). State precisely what part of the space was exhausted and what was only sampled.

FIGURES (PNG ONLY, never PDF; add to nnflags/plots.py, which saves PNG only): the best 3 circuits on Willow (tree, flags with their control CXs, parity qubit and readout line, hook qubits), a bar chart of malignant T at 2 and 3 faults for d3a6, d3a4, G4, best Option-1 candidate and the best ZZ-flag circuits, and (if any success) a TICK diagram of the best one. Take data/ancilla roles from the circuit's MPP targets (not by parsing text). Plain academic style, white background, colour-blind-safe with hatching/markers, no e-notation ticks.

HARD RULES
- NEVER edit ./cliffordea. Read source before using any new cliffordea function; cite file:line.
- Use ./.venv only; never touch /home/ubuntu/quantum001/venv or anything outside this folder. No git commits/pushes.
- Do not overwrite earlier results files (results/g4_result.json, results/option1_*): write new files.
- Report every number with its settings (distance, state, max_fault_count, noise model uniformly_depolarize, p = 0.001, readout rule). Rates as % or "1 in N", never e-notation. Times in KST with am/pm.
- All existing tests must still pass; add tests for the generalised flag generator (determinism, degree, equivalence with flags excluded) and for any success (re-verify from its saved stim file).

REPORT: ./RESULTS_zzflags.md: top answer in 2-3 sentences (did we find a Willow-compatible fault-distance-3 circuit?), status table, the successes (or best attempts) table, search space explored vs sampled, figures list, decisions made without the user, open questions. Confirm `git -C cliffordea status --porcelain --ignored` is empty. Then STOP.
