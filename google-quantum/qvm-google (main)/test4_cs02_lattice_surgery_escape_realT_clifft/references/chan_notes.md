# Notes: Chan, Strikis, Sun, Cai, "Diagnosing and Restoring the Degraded Fault Distance of Magic State Cultivation"

arXiv 2609.17706v3 (Sep 30, 2026), 22 pages. PDF uploaded by the user on Nov 4, 2026
(`Diagnosing and Restoring the Degraded Fault Distance of Magic State Cultivation .pdf`). Read in full on Nov 4 (pypdf text).
Page numbers are the PDF's. Quotes are verbatim.

## Main findings
- Fault distance of the **final double check** with real T (exhaustive fault enumeration, standard uniform depolarising
  noise, App. G): distance 3 -> **2**, distance 5 -> **3** (S stand-in keeps 3 and 5). Fig. 1b, Fig. 6 (slopes 2, 3, 3, 5).
- Cause: X hook errors spread by CXs, rotated by the physical T gates into multi-qubit Clifford errors (Example 1:
  X_1 + Y_3 -> E = -(H+)_0 (H-)_13, kept with probability 1/4, then a logical error).
- d = 3 (Gidney's double check, Fig. 4): **4 malignant 2-fault configurations** (Fig. 7). d = 5: 3 malignant 3-fault and
  601 malignant 4-fault configurations, each with at least one X hook error.
- p. 9: **Google's experimental double check [8] also has fault distance 2** ("applying the same analysis to this slightly
  smaller circuit, we find it also has fault distance 2").
- In MSC-5, the d = 3 malignant pairs are caught by the later d = 5 double check; they degrade MSC-3 only.
- p. 9: using 7 ancillas instead of 6 does not help ("Varying ancilla count will not restore fault distance").
  Two single checks (short or long) do restore it at d = 3, but cost more spacetime and need non-local pipelining;
  they keep the double check because it is "the most amenable to 2D nearest-neighbour connectivity" (p. 4).

## Their flags
- d = 3 (Fig. 8 / Fig. 13): **2 Z-flag qubits** (prepared in |0>, Z-measured) and 4 extra CX layers; detect all 4
  malignant pairs. d = 5 (Fig. 9): 13 Z flags, 2 extra layers (one flag per consecutive pair of the GHZ tree, minus the 5 leaves).
- Hand-designed (Sec. 6.2): "the minimum number of Z flags, preferring short-range interactions".
- Not nearest-neighbour: "the existing interactions become next-nearest-neighbour ... we treat them as a proof of concept" (p. 10).

## Performance (Sec. 6.1, simulated with SymFT, real T, pre-escape, uniform depolarising noise)
- **d = 3: flags restore fault distance 3 (Fig. 10), but "For MSC-3 in practice we can see that these Z flags are
  overkill, since the malignant 2-fault configurations they detect barely outweigh the higher-fault-count configurations
  they introduce."** No d = 3 improvement factor is given.
- d = 5 (three stabiliser rounds before the d = 5 check, as Gidney): p = 0.1%: 4.9x lower error, 1.36x more attempts
  (abstract); p = 0.05%: 10.9x, 1.17x. True fault distance 3 -> 4 for this circuit; fitted slopes 3.8 -> 5.1.
  The "p^3 -> p^5" statement is for the four-round MSC-5 version (verified by Wan & Zapirain), which they did not simulate.
- Wan & Zapirain [29, App. H.3-4] confirm: flagged MSC-3, three-round MSC-5, four-round MSC-5 have fault distance 3, 4, 5.

## Future work they list (p. 12-13)
- "it would be interesting to devise a qubit layout that maintains nearest-neighbour connectivity. This should be
  combined with a more rigorous and systematic flag design process than the hand-optimised one" -> exactly our work
  (cs02: systematic search, nearest-neighbour, <= 4 partners, readout-line rule).

## What this means for us
- Our open question is literally their stated future work (quote above): cite it on the motivation slide.
- Their d = 3 flags are "overkill in practice" under uniform depolarising noise; cs02 at d = 3 gives 5.8x lower error
  than Google's G6-style circuit under Willow noise (QVM, 8M shots). Our toy-noise sweep (RESULTS_toy_p_sweep.md) shows
  the gain grows as p falls and disappears near p = 0.5%, consistent with their observation at higher p.
  An examiner may ask why our d = 3 gain is large when theirs is not: the baselines and noise models differ
  (Google's FD-2 circuit and Willow noise vs Gidney's circuit and uniform depolarising). Not yet tested head to head.
- Fault-pair counts differ by circuit: Gidney's d = 3 double check has 4 malignant pairs (Chan); Google's G4 double check
  has 7 in our real-T fault injection. Do not mix the two numbers.
- Their 4.9x is a d = 5 number; do not put it next to our d = 3 result.
- Related preprint announced alongside: Hartweg & Pineiro Orioli (2609.19116), tensor-network analysis of the T-S
  discrepancy and cultivation entirely on the rotated surface code. Not yet checked for overlap.
