# nnflags: nearest-neighbour flags for T-state cultivation on Willow

Python package used to find, check and draw the double-check circuits of this project. It wraps
[cliffordea](https://github.com/timchan0/cliffordea), which must be cloned into `google-quantum/cliffordea/`
and is never modified. Run from `google-quantum/` as `python -m nnflags.<module>`.

| Module | Purpose |
|---|---|
| `willow.py`, `data/` | the Willow 105-qubit grid and couplers (from Google's device file in cirq-google) and readout lines r + c |
| `constraints.py`, `continuing_data.py` | hardware rules: nearest-neighbour gates, at most 4 partners, the readout-line rule, and the continuing-data rule (no measured qubit on a data qubit's readout line) |
| `verify.py`, `equivalence.py` | exact fault-distance check with real T gates (through cliffordea) and a check that a circuit measures the intended logical operator |
| `g4.py`, `g6_continuing.py`, `google_check.py` | Google's circuits from Rosenfeld et al. (Fig. 2 = G4, Fig. 4 = G6), extracted and analysed |
| `search_option1.py`, `embed_search.py`, `candidates.py` | search over fold trees and their placements on the chip |
| `zzflags.py`, `search_zzflags.py` | flag generator (one- and two-control Z and X flags, GF(2) prefilter) and flag search |
| `search_continuing.py`, `continuing_validate.py`, `continuing_evidence.py` | the continuing-data search that found cs02, and its validation |
| `willow_noise.py`, `si1000.py` | noise models: Willow spec sheet, Willow calibration, SI1000; CX to native CZ + H conversion |
| `comparison.py`, `live_rule_table.py`, `step0.py`, `step1.py`, `step2.py` | the analysis steps reported in `../RESULTS_*.md` |
| `plots.py`, `plots_continuing.py`, `plots_si1000.py`, `crumble.py` | figures (PNG) and Crumble links |
| `tests/` | unit tests: `python -m pytest -q nnflags/tests` |
