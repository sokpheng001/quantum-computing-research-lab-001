You are working unattended in /home/ubuntu/quantum001/google-quantum on a remote Linux server. The user has turned off their laptop; nobody can answer questions. Make reasonable decisions, record them, and keep going.

TASK
1. Read ./first-ex.md FULLY (every line) before doing anything else. It is the task plan (TASKS_nn_flags).
2. Do Steps 0, 1 and 2 of that plan ONLY. Do NOT start Step 3 or later. After Step 2, write the report (below) and stop.

HARD RULES
- Clone https://github.com/timchan0/cliffordea into ./cliffordea. NEVER edit any file inside ./cliffordea (no patches, no formatting, no generated files written into it). Import/wrap it only. If something in it is broken, work around it from ./nnflags and record the problem.
- Before using ANY cliffordea function or class, read its source (and the README). In the report, quote the exact function/class names you used and the file:line where each is defined. Do not guess names.
- Our code goes in ./nnflags/ (package) and tests in ./nnflags/tests/ (pytest).
- Python environment: conda is not installed. Create a local venv at ./.venv (python3 -m venv) and install what cliffordea's README / requirements / pyproject need, plus pytest. Do NOT install into or modify /home/ubuntu/quantum001/venv (shared). Pin and report all versions (python, stim, cliffordea commit hash, numpy, etc.).
- Do not touch any folder outside /home/ubuntu/quantum001/google-quantum. No git commits, no pushes.
- Run anything that could take more than a few minutes with nohup and a log file in ./logs/, and checkpoint results to disk, so partial results survive.
- Report every number with the settings used (distance, ancilla_count, flag_count, max_fault_count, cultivated state, noise model) and wall-clock timing.
- In the report, write rates as % or "1 in N", never e-notation. Write times in Korea time (KST, UTC+9) with am/pm.

STEP-SPECIFIC NOTES
- Step 0: use the README "Complete enumeration workflow". Expected: d3a6 -> 4 malignant 2-fault configurations for T, 0 for S; d3a6f2 -> 0 malignant up to 2 faults for T. If you get different numbers, do not "fix" them by changing settings silently: report exactly what you got and what you tried.
- Step 1 (Willow grid): there may be no official coordinate file for the 105-qubit Willow layout. Try to find a reliable source (e.g. the Nature 2024 paper "Quantum error correction below the surface code threshold" and its supplement / Zenodo data, Google's public device specs). If you cannot get a verified list, build the best-supported 105-qubit grid you can, mark it clearly in willow.py and in the report as an ASSUMPTION with its source, and make the rest of the code independent of the exact list. Implement the readout-line rule exactly as defined in first-ex.md (readout line = r + c), with a toggle to ignore it. Report the exact failing gates/qubits for d3a6f2 and compare with the plan's expectation (4 diagonal flag gates, qubit 6 with 6 partners, qubit 11 with 5).
- Step 2: verify() must reuse cliffordea's code paths (no reimplementation of the acceptance algorithm) and reproduce Step 0 exactly; prove it with a test.

REPORT (required, even if something fails)
Write ./RESULTS_steps0-2.md with:
- Top: a short status table (Step 0 / 1 / 2: PASS / FAIL / PARTIAL, one line why).
- Step 0: summaries (summarize_contributions output) for d3a6 and d3a6f2, timings.
- Step 1: the Willow grid used and its source/assumption status, the constraint-check results for both circuits and the embeddings used.
- Step 2: verify() results vs Step 0, test output (pytest summary).
- Environment: versions, cliffordea commit, the cliffordea functions used with file:line.
- Decisions made without the user, problems found, and open questions for the user.
- Confirm that `git -C cliffordea status --porcelain` is empty.
Then stop. Do not continue to Step 3.
