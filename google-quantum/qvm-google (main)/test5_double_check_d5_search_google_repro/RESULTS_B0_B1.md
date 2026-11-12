# Test 5, Part B, steps B0-B1: d = 5 baselines (written Nov 04, 07:10 PM KST)

Circuits: cliffordea's bundled d = 5 double checks (read only). Fault distance: cliffordea exact enumeration with real T (uniform depolarising noise), up to 4 faults; S = the Clifford stand-in, for comparison. Geometry: at the circuits' own square-grid coordinates.

## B0: baselines

| circuit | qubits | 2-qubit gates | non-neighbour pairs | max partners | fault distance, real T | fault distance, S | T error per kept shot, p = 0.1 % | enumeration time |
|---|---|---|---|---|---|---|---|---|
| Gidney et al. (original d = 5) (`d5a19`) | 38 | 74 | 0 | 4 | 3 | > 4 | 1 in 974,523,423 | 1.1 s |
| Chan et al., 3 flags (`d5a19f3`) | 41 | 86 | 3 | 5 | 4 | > 4 | 1 in 3,487,408,846 | 1.2 s |
| Chan et al., 13 flags (`d5a19f13`) | 51 | 126 | 13 | 7 | > 4 | > 4 | 0 | 1.9 s |
| Chan et al., 18 flags (`d5a19f18`) | 56 | 146 | 18 | 7 | > 4 | > 4 | 0 | 2.2 s |

Malignant configuration counts (T), by number of faults:

- `d5a19`: 0: 0, 1: 0, 2: 0, 3: 3, 4: 601
- `d5a19f3`: 0: 0, 1: 0, 2: 0, 3: 0, 4: 335
- `d5a19f13`: 0: 0, 1: 0, 2: 0, 3: 0, 4: 0
- `d5a19f18`: 0: 0, 1: 0, 2: 0, 3: 0, 4: 0

## B1: Gidney's d = 5 tree on Willow

- placements on the 105-qubit grid (lattice symmetry + translation of its own coordinates): **62**
- with 0 violations, data measured at the end (strict rule): **0** (best: 3 violations)
- with 0 violations, data continuing (continuing-data rule): **0** (best: 38 violations)
- violation kinds summed over placements (continuing): {'readout': 218, 'data_measured': 62, 'readout_continuing': 2136}

Only rigid placements of Gidney's own layout are tried here; re-embedding the tree (as in the cs02 search) is the next step if none is clean.
