# Notes: Rosenfeld et al. (Google Quantum AI), "Magic state cultivation on a superconducting quantum processor"

arXiv 2512.13908 v1 (Dec 15, 2025), 28 pages incl. supplement. PDF uploaded by the user on Nov 4, 2026:
`Magic state cultivation on a superconducting quantum processor.pdf`. Read in full on Nov 4 (text via pypdf).
Page numbers are the PDF's. Quotes are verbatim.

## What they did
- Willow, 105 transmons, square lattice. Distance-3 colour code; superdense colour-code cycle (Lacroix et al.).
- Stages: injection (one physical qubit, "without fault-tolerance", also prepares the six stabilisers), cultivation
  (the double check), kickback tomography (KT) to measure the T error, grafting to a distance-5 surface code (54 qubits).
- Their T state is |T> = exp(-i pi sigma_y / 8)|0> (X/Z plane), i.e. the standard T|+> up to a transversal H_ZY,
  chosen so tomography uses the X and Z stabilisers (p. 2).
- H_L = T^dagger X T transversally; the X_L measurement is "folded" onto one helper qubit, then the circuit is
  time-reversed: stabilisers return, the observable is measured again, "and the helper qubits become additional error
  detectors" (p. 2). Fig. 1C: "flag detectors check for errors (flags, step 13)". Fig. S11: "three flag checks".
- Calibration: reinforcement learning (about 4 h before data), improves logical error and retention about 10x (Fig. S13).
- Echo X pulses between Hadamard pairs against low-frequency phase noise; without them performance is dominated by it (Sec. X).

## Results (hardware)
- Injection only: logical error 4.4(2) x 10^-3 at theta = pi/4 (p. 4), about 1 in 230.
- With cultivation, measured by KT (full circuit: injection, QEC cycle, 3 cultivation rounds, 4 QEC cycles):
  logical error "between 1x10^-4 and 2x10^-4" (about 1 in 10,000 to 1 in 5,000), data retained 8 % (p. 5); "about 40x".
  The circuit has 216 two-qubit gates and 54 measurements.
- Removing the QEC cycles: about 100x worse (single errors become logical: the double check measures no stabilisers).
- Grafting to d = 5: proof of principle; logical error per grafted QEC cycle 5.3 % (experiment) vs 0.8 % (simulation),
  attributed mainly to leakage (Fig. S22-S24).
- Simulations match with SI1000 at p = 0.30 % (Fig. 2) and p = 0.23 % (Figs. 3, 4).

## Hardware rules they mention
- Fig. S10(a): "We swap data and measure qubit pairs (black arrows) to satisfy readout line constraints."
  -> supports our readout-line rule (their own layout is constrained by readout lines).
- Sec. XIV: the grafting circuit redefines which sub-lattice is measured; readout parameters were not optimised for it,
  "leading to possible frequency collisions ... and subsequent leakage".

## Their simulators (Sec. XI)
- Figs. 2-3: `kraus-sim`, state-vector quantum trajectories, 12 (14) qubits reduced to 8.4 (10.2) in memory by reordering.
- Fig. 4 (54 qubits): `qevol`, "maintains superpositions of stabilizer states", "amenable ... given the modest number of
  T gates" -> the same idea as our Clifft choice for the full pipeline.
- Noise in all their simulations: SI1000 Pauli noise (plus coherent phase noise in Sec. X); leakage not modelled.

## Fault distance: what they claim, and the conflict with Chan et al. (important for our defence)
- Sec. VI (p. 11): the time reversal and flag checks are "crucial for achieving fault tolerance"; cultivation "extends the
  fault distance of the entire circuit to three". Fig. S10: flag detectors and the second observable measurement "together
  bring the fault distance of the circuit to three".
- Fig. S19 (p. 24): their simulated KT logical error "scales as p^3 ... expected, because cultivation increases the fault
  distance of the state to three".
- Conclusion (p. 7): "as the processor noise strength p improves, the magic state infidelity should drastically scale as p^3".
- Chan et al. (2609.17706, Sec. 5) find the experimental d = 3 double check has fault distance 2 for the T state, and our
  real-T fault injection finds 7 malignant 2-fault pairs in G4's double check.
- These are not necessarily contradictory: Google's p^3 statement is for the whole KT circuit (three cultivation rounds and
  four QEC cycles, measuring an upper bound), and is a fit over a finite p range; Chan's and ours are for the state after
  one double check (pre-escape). Not yet checked which explanation holds. A direct test is possible with Clifft (real T):
  fit the slope of Google's own KT circuit (Fig. 3, released as G5) and of one double check, over the same p range.

## What this means for our paper
- Cite for: the hardware demonstration; the readout-line constraint (Fig. S10a); their use of a stabiliser-superposition
  simulator for 54 qubits; the expectation of p^3 scaling that a fault-distance-3 double check (ours) actually delivers.
- Correction to our earlier wording: Google's double check is not "flag-free". Its helper qubits act as flags after the
  time reversal (three flag checks, Fig. S11). They do not catch the hook errors Chan identifies; cs02 adds two dedicated
  flags (ZZ + X) that do.
- Their hardware numbers (1 in 5,000-10,000 at 8 % retention, KT total circuit) are a different quantity from our
  pre-escape error per kept T state; do not compare them directly.
