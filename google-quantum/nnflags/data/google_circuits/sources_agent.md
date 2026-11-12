# Sources: Crumble link for the experimental (Google) distance-3 double check

## Paper
- arXiv:2609.17706, "Diagnosing and Restoring the Degraded Fault Distance of Magic State Cultivation"
- Authors: Tim Chan, Armands Strikis, Zhu Sun, Zhenyu Cai
- Versions: v1 Tue 15 Sep 2026; v2 Thu 24 Sep 2026; v3 Wed 30 Sep 2026 (current, fetched 2026-10-31)
- Comments (v3): "15+7 pages, 11+2 figures; update acknowledgments, clarify fault distance definition, improve malignant fault configurations figure"

## The link (Section 5, "Fault Enumeration of Magic State Cultivation")
Exact sentence (HTML v3, last paragraph of Sec. 5):
> "This degraded fault distance is experienced also by the distance-3 double check used in the experimental realisation of MSC [8] (Crumble link here): applying the same analysis to this slightly smaller circuit, we find it also has fault distance 2."

- The anchor text is "here". Its target is saved verbatim in `crumble_url.txt` (1107 characters).
- Ref [8] = Emma Rosenfeld et al., "Magic state cultivation on a superconducting quantum processor" (2025), arXiv:2512.13908 (Google Quantum AI).
- Cross-check: the PDF (pdf.out, page 9) has a URI annotation that is byte-identical to the HTML href.
- The paper never uses the word "Willow". It calls the circuit "the distance-3 double check used in the experimental realisation of MSC [8]". Saying it ran on Willow comes from ref [8], not from this paper.
- What the URL encodes: 11 qubits (Q indices 0-10). 7 data qubits (0,1,4,5,6,9,10) form the d=3 colour code. 4 ancillas (2,3,7,8) are reset in X basis. The circuit is: ideal MPP stabiliser/Y-observable preparation; S/S_DAG layers; a CX encoding ladder; MX of qubit 8 (the first H_XY check); RX 8; the mirrored un-encoding; MX of ancillas 8,2,7,3; then ideal MPP stabiliser checks and the Y observable (OI(0)). In other words, it is the double-check stage only, with ideal MPP framing for the analysis. It is not the full cultivation/grafting experiment. The paper's Fig. 4 double check uses 6 ancillas, so this 4-ancilla circuit is the "slightly smaller circuit".
- No .stim file is linked from 2609.17706 for this circuit. The only code link is ref [23], https://github.com/timchan0/cliffordea (not inspected further). The Crumble URL itself encodes the circuit; I did not convert or reconstruct it.

## Other Crumble links in 2609.17706 (for disambiguation; not the experimental circuit)
1. Fig. 4 caption (Sec 2.3): MSC d=3 double check with Fig. 1(a) error events ("this Crumble link")
2. **Sec 5: experimental double check of [8] (the target, in crumble_url.txt)**
3. Sec 6: d=3 short single check of Itogawa et al. [27]
4. Sec 6: minimally modified long single check
5. Fig. 8 caption: Z-flagged d=3 double check
6. Fig. 9 caption: Z-flagged d=5 double check

## Google's own paper (ref [8]), checked for context
- https://arxiv.org/abs/2512.13908 returned 200. Title: "Magic state cultivation on a superconducting quantum processor".
- https://arxiv.org/html/2512.13908 returned 200. Its appendix gives Crumble links "for the explicit circuits used for each element", namely State injection circuit, Cultivation circuit, Grafting - adapt to new code, and Grafting - idling in new code. It also gives "complete circuits we ran for each figure": Figure 2 cultivation (cyan curve), Figure 3 kickback tomography (cyan), and Figure 4 grafting N=2 with cultivation (cyan). All 7 are saved verbatim in `google_paper_2512.13908_crumble_urls.txt` (G0-G6, in the paper's order).
- Data availability: https://doi.org/10.5281/zenodo.17872003. Zenodo API record 17872003 returned 200 with files fig2.zip (733 MB), fig3.zip (1.55 GB), fig4.zip (921 MB), README.md and Example_usage.ipynb. The README says each experiment dir contains `stim_X.stim` and `stim_Z.stim` (with `echo`-tagged identity gates in place of the hardware echo X gates) and `cirq_circuit_X/Z.json`. I did NOT download the zips (too large), so no Google .stim file is saved here.

## URLs tried
| URL | Result |
|---|---|
| https://arxiv.org/abs/2609.17706 | 200, metadata above |
| https://arxiv.org/html/2609.17706 | 200, 6 Crumble hrefs; target found |
| https://arxiv.org/pdf/2609.17706 | 200, PDF 1.7; page-9 link matches HTML exactly |
| https://arxiv.org/abs/2512.13908 | 200 |
| https://arxiv.org/html/2512.13908 | 200, 7 Crumble hrefs + Zenodo DOI |
| https://zenodo.org/api/records/17872003 | 200, file list above |
| https://zenodo.org/records/17872003/files/README.md?download=1 | 200, README describing stim files |

Raw downloads are in `dl/`.

## Chan et al. on hardware connectivity of their flagged circuits (fetched 2026-11-02, HTML v3)
Verbatim quotes (arXiv:2609.17706v3):
- **Section 6 (introduction, before Fig. 8):** "Our Z flags are 2D local in that each interacts only with a pair of neighbouring qubits, but they are not 2D _nearest-neighbour_ since the existing interactions become next-nearest-neighbour. We therefore do not intend for them to be physically implemented verbatim, but rather we treat them as a proof of concept."
- **Section 7 (Conclusion):** "One motivation for designing the Z-flagged circuits was to retain the use of the double check for its low spacetime cost under 2D connectivity constraints. As [Section 6] mentions however, the Z flags themselves complicate the connectivity to next-nearest-neighbour; it would be interesting to devise a qubit layout that maintains nearest-neighbour connectivity. This should be combined with a more rigorous and systematic flag design process than the hand-optimised one described in [Section 6.2]..."
- **Section 2.3:** "...uses the _double check_ in [Fig. 3(c)] as it is the most amenable to 2D nearest-neighbour connectivity." (the unflagged double check)
- **Section 7:** "Third, we design 2D-local flags that restore the degraded fault distance of T-state cultivation, and which are practical for distance 5."
- Not in the paper: "Willow", "square grid", "degree", "6 partners", "diagonal". Those specifics come from OUR placement analysis (RESULTS_steps0-2.md, Step 1: d3a6f2 on Willow needs 3 non-neighbour gate pairs; qubit 6 has 6 partners, qubit 11 has 5; Willow allows 4).
