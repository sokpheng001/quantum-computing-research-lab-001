# Test 3, step 1: a fault-distance-3 double check on G6's data (search_g6.py)

Written automatically by `search_g6.py` at the end of the run (Nov 3, 12:34 am KST).

## Settings

- fold depth <= 5, qubits <= 13 (tree), never-measured ancillas <= 1, roots m in 1,2, flags <= 2
- data fixed to G6's positions [(4, 5), (4, 7), (5, 4), (5, 6), (6, 5), (6, 7), (7, 6)] with G6's code; flag search: exact 2-cover, then greedy

## Space

- line patterns: 66
- forest placements with the data on G6's positions: 210
- distinct (tree, labelling) groups: 121
- sanity check, cs02's tree (placed on G6's data in step 0) found among them: **True**
- screen: malignant T pairs of the bare trees: {'6': 2, '7': 4, '8': 10, '9': 6, '10': 13, '11': 3, '12': 4, '13': 1, '17': 4, '19': 4, '20': 3, '21': 1, '22': 1, '26': 1, '30': 2, '32': 1, '40': 1, '1000000': 60}

## Result

- stop reason: design space exhausted
- groups flagged: 121, circuits evaluated: 705
- **successes: 0**

No circuit reached fault distance 3 on G6's data under the rules.
Best placeable circuits (malignant T pairs at <= 2 faults): [2, 2, 2, 2, 2]

## Files

- `results/g6_search/success*.{inner,full}.stim`: the successes (Willow coordinates = G6's)
- `results/g6_search/best_*.stim`: best non-successes
- `results/g6_search/candidates.csv`, `bases.csv`, `state.json`
- log: `logs/search_g6.log`

Next (not run): splice a success into G6 in place of TICKs 31-56 and compare with G6 as run (stim).
