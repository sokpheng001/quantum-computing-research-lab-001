# Test 3: full experiment with real T, our double check vs Google's (G6, Rosenfeld et al. Fig. 4)

Goal: the logical error rate of the full experiment, Google's injection (TICKs 0-30) +
double check (TICKs 31-56) + Google's grafting into the surface code (TICKs 57-124),
with **real T gates**, run twice: once as Google ran it (G6) and once with our
fault-distance-3 double check spliced in place of Google's. G6 has 54+ qubits, far too
many for a state-vector simulation (about 144 PB), but only 15 non-Clifford gates
(1 injection rotation + 7 T + 7 T-dagger), so a **low-T-count (stabiliser-rank)
simulator** is used, with Google's Willow noise exported from the QVM and Google's device
check on the spliced circuit. The simulator is first cross-checked against the QVM on
the 12-qubit cs02 double check.

Folder renamed on Nov 3, 2026 (was `test3_grafting_vs_google_fig4`).

## Step 0: does an existing circuit fit G6? (`check_g6_fit.py`, Nov 2, 2026) — DONE

- G6's 7 data sit at (4,5), (4,7), (5,4), (5,6), (6,5), (6,7), (7,6) and carry the
  7-qubit colour code with 7 specific weight-4 stabilisers.
- cs02 (and its twin cs03) has 26 Willow placements with its data exactly on those
  positions (readout lines still clean), but **0 of them carry G6's code**: the
  grafting would graft the wrong code. cs00, cs01, cs04-cs09 cannot even put their data there.
- Sanity check: 168 of the 5,040 data maps preserve the code (the code's symmetry group), as expected.
- Result: `results/g6_fit.json`, log `logs/check_g6_fit.log`.

## Step 0b: why not? (`diagnose_g6_fit.py`, Nov 2, 2026) — DONE

- On the grid an ancilla only touches the data around its own grid point. Around G6's data
  diamond only **4 free grid points touch 3 or more data**: (4,6), (5,5), (5,7), (6,6), all
  next to the central data qubit (5,6). The other 4 nearby points touch only 2 data.
- cs02 needs **4 such spots at once**: 3 fold ancillas (q0, q3, q7), each touching a specific
  group of 3 data, and the Z flag (q10), touching a specific pair.
- Checking all 168 code-preserving maps one requirement at a time: in **every** map at
  least one of the four has no grid point next to all of its data (best case: exactly one
  fails: q7, q3 or q10, depending on the map). It is a geometric shortage, not a readout or
  fault-distance problem.
- Result: `results/g6_diagnosis.json`, log `logs/diagnose_g6_fit.log`.

**Conclusion:** no existing circuit can be spliced in. Next step (not started, waiting for
the go-ahead): a new search with data and code fixed to G6's, then the splice and a stim
comparison (54 qubits is too large for a real-T QVM state-vector simulation).

## Step 1: search for a double check that fits G6 (`search_g6.py`, `run_search.sh`, Nov 3, 2026) — DONE

- Same method as the cs02 search, with the data and the code fixed to G6's.
- Stage A (cs02's size: fold depth <= 5, <= 13 tree qubits): 0 successes (best: 2 malignant pairs). `RESULTS_search.md`.
- Stage B (fold depth <= 6, <= 14 tree qubits): **9 distinct fault-distance-3 circuits** (11 successes, 2 repeats),
  13-15 qubits, max 4 partners. Best: #4 (14 qubits, ZZ + X flags), 1 in 4,022,889 per kept T state at uniform
  p = 0.1 % (mfc 3), vs 1 in 1,869,957 for Google's double check as run in G6. `RESULTS_search_d6n14.md`,
  files `results/g6_search_d6n14/`.

## Next (each step waits for the go-ahead)

1. Survey exact low-T-count simulators (SOFT, Clifft, Qiskit extended stabiliser, own code).
2. QVM real-T check (E1-E4) of #4 (and #2 as backup) on their own.
3. Cross-check the chosen simulator against the QVM on cs02.
4. Splice into G6, device check, noiseless real-T check, then the comparison with Google's G6.

## Step 2: QVM real-T check of all 9 G6-fit circuits (`qvm_g6fit.py`, `run_qvm_g6fit*.sh`, Nov 3, 2026) — DONE

- All 9 pass Google's device check (E1), the noiseless real-T check (E2) and real-T fault injection
  (E3: 0 malignant 2-fault configurations, so fault distance 3 with real T).
- E4 (first 4,000,000 shots each, then all extended to 8,000,000 on Nov 3 evening, the same as Google's
  baselines and cs02; `../test2_cs02_continuing_data_vs_google/run_baseline_8M.sh`): 2.4-4.1x lower error per
  kept T state than Google's double check as run in G6 (1 in 20,832, 76.7 %). Ratio CIs in `../MASTER_RESULTS.md`. `RESULTS_qvm_g6fit.md`, `figures/qvm_g6fit_vs_google.png`.

**Chosen circuit: #0** (`results/g6_search_d6n14/success00.{inner,full}.stim`), noted by the user on Nov 3.
13 qubits (one more than Google's 12), ZZ + X flags, fault distance 3 with real T.
QVM, 8,000,000 shots: 1 in 70,284 per kept T state (95 % CI 1 in 55,244 to 1 in 90,876; 66 errors in 4,638,735
kept), 3.4x lower than Google's (95 % CI 2.6x to 4.4x; at 4,000,000 shots it was 1 in 82,830, 3.9x), acceptance 71.4 % (Google 76.7 %; 1.40 vs 1.30 attempts per good T state).
Best balance of error and acceptance among the 9, statistically tied with #1 (1 in 71,364, 71.7 %); #5, #2
and #4 have slightly lower error, within the CIs, but 62-65 % acceptance. Candidate for the splice into G6.
