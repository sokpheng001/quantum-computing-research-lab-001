# Test 6: does our simulation match Google's paper? (Rosenfeld et al., arXiv:2512.13908)

Created Nov 5, 2026 at the user's request (moved here from test 5, Part A). Goal: show that the simulation
behind our d = 3 result (Google's QVM, our stim / Clifft noise models, real T) agrees with what Google
reports for **its own circuits**, so the cs02 comparison can be trusted.

## Google's data release (downloaded with the user's OK, Nov 5)

Zenodo 10.5281/zenodo.17872003 (CC BY 4.0), in `references/zenodo_17872003/` (download script
`download_zenodo.sh`, started automatically after test 5's main d = 5 run; md5 checked; data is only read,
the notebook is not run). What it contains (from its README):

- per figure (fig2, fig3, fig4) and experiment: the circuits **as run on Willow** (`cirq_circuit_X/Z.json`, with
  the real non-Clifford rotations), a Clifford stim version (`stim_X/Z.stim`, T replaced, echo pulses as
  identities), and the **hardware data**: measurements, detection events, raw and corrected observables,
  plus the decoder's detector error models.
- It holds **hardware data, not Google's simulation values**. Google's simulated curves exist only as
  points in the paper's figures (kraus-sim, SI1000 at p = 0.30 % for Fig. 2, 0.23 % for Fig. 3).

## Plan (each step waits for the user's go-ahead)

| step | what | compared with |
|---|---|---|
| 0 | Inspect the release: circuits, shot counts, post-selection rule, how Google computes its numbers | - |
| 1 | Hardware numbers from Google's own data with our code: acceptance (retention) and post-selected logical values for Fig. 2 (injection, cultivation) and Fig. 3 (kickback tomography) | the values printed in the paper (e.g. retention 76 % injection, 8 % full KT circuit; KT error 1-2 in 10,000) |
| 2 | Simulate the **same released circuits** (real T) under SI1000 at Google's p, with our tools (qsim for 12-14 qubits, Clifft as a cross-check) | Google's simulated points (read off Figs. 2, 3, S19; approximate) |
| 3 | The same circuits in Google's QVM (`willow_pink` noise) and in our Willow calibration model | Google's hardware data from step 1 |
| 4 | Check that the released Fig. 2 double check is the G4 circuit we used as our baseline | our `results/g4/` files |

Pass criterion: our numbers agree with Google's within the statistical uncertainty, or within a stated
tolerance where values are read off a plot. If our Willow models disagree with the hardware data, report
by how much (Google's own simulation also misses some effects, e.g. leakage in Fig. 4).
