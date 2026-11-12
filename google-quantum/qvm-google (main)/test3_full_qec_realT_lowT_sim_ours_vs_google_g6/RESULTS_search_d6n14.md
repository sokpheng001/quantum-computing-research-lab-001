# Test 3, step 1: a fault-distance-3 double check on G6's data (search_g6.py)

Written automatically by `search_g6.py` at the end of the run (Nov 3, 12:48 am KST).

## Settings

- fold depth <= 6, qubits <= 14 (tree), never-measured ancillas <= 1, roots m in 1,2, flags <= 2
- data fixed to G6's positions [(4, 5), (4, 7), (5, 4), (5, 6), (6, 5), (6, 7), (7, 6)] with G6's code; flag search: exact 2-cover, then greedy

## Space

- line patterns: 128
- forest placements with the data on G6's positions: 796
- distinct (tree, labelling) groups: 431
- sanity check, cs02's tree (placed on G6's data in step 0) found among them: **True**
- screen: malignant T pairs of the bare trees: {'5': 2, '6': 6, '7': 8, '8': 13, '9': 10, '10': 14, '11': 4, '12': 9, '13': 4, '14': 5, '15': 7, '17': 8, '18': 6, '19': 6, '20': 5, '22': 1, '24': 1, '26': 4, '27': 2, '29': 3, '30': 7, '31': 2, '32': 1, '33': 3, '34': 1, '35': 1, '38': 1, '40': 1, '1000000': 82}

## Result

- stop reason: 10 successes
- groups flagged: 217, circuits evaluated: 1457
- **successes: 11** (9 distinct circuits: #8 = #7 and #10 = #9 are the same circuit at two placements)

| # | base | qubits | CX | max partners | flags | malignant T at 3 faults | T error per kept shot (p = 0.1 %, mfc 3) |
|---|---|---|---|---|---|---|---|
| 0 | g6-00030 | 13 | 26 | 4 | `Zf11[q4@t3+q10@t4+q4@t16+q10@t17];Xf12[q4@t2+q4@t17]` | 355 | 1 in 3,875,150 |
| 1 | g6-00030 | 13 | 26 | 4 | `Zf11[q4@t2+q10@t3+q4@t15+q10@t16];Xf12[q10@t2+q10@t17]` | 384 | 1 in 2,633,280 |
| 2 | g6-00032 | 13 | 26 | 4 | `Zf11[q9@t2+q4@t3+q4@t15+q9@t16];Xf12[q4@t2+q4@t16]` | 317 | 1 in 3,886,598 |
| 3 | g6-00032 | 13 | 26 | 4 | `Zf11[q9@t3+q4@t4+q4@t16+q9@t17];Xf12[q9@t2+q9@t18]` | 381 | 1 in 2,099,942 |
| 4 | g6-00071 | 14 | 28 | 4 | `Zf12[q7@t2+q9@t3+q9@t15+q7@t16];Xf13[q9@t2+q9@t16]` | 326 | 1 in 4,022,889 |
| 5 | g6-00071 | 14 | 28 | 4 | `Xf12[q9@t3+q9@t17];Zf13[q7@t2+q9@t4+q9@t16+q7@t18]` | 326 | 1 in 2,670,380 |
| 6 | g6-00104 | 14 | 28 | 4 | `Zf12[q6@t3+q7@t4+q7@t16+q6@t17];Xf13[q6@t2+q6@t18]` | 338 | 1 in 2,088,924 |
| 7 | g6-00221 | 15 | 32 | 4 | `Zf13[q5@t3+q5@t6+q5@t14+q5@t17];Zf14[q3@t2+q10@t3+q10@t17+q3@t18]` | 344 | 1 in 2,047,061 |
| 8 | g6-00221 | 15 | 32 | 4 | `Zf13[q5@t3+q5@t6+q5@t14+q5@t17];Zf14[q3@t2+q10@t3+q10@t17+q3@t18]` | 344 | 1 in 2,047,061 |
| 9 | g6-00222 | 15 | 32 | 4 | `Zf13[q5@t3+q5@t6+q5@t14+q5@t18];Zf14[q4@t2+q10@t3+q10@t16+q4@t18]` | 351 | 1 in 2,428,130 |
| 10 | g6-00222 | 15 | 32 | 4 | `Zf13[q5@t3+q5@t6+q5@t14+q5@t18];Zf14[q4@t2+q10@t3+q10@t16+q4@t18]` | 351 | 1 in 2,428,130 |

## Files

- `results/g6_search_d6n14/success*.{inner,full}.stim`: the successes (Willow coordinates = G6's)
- `results/g6_search_d6n14/best_*.stim`: best non-successes
- `results/g6_search_d6n14/candidates.csv`, `bases.csv`, `state.json`
- log: `logs/search_g6_d6n14.log`

Next (not run): splice a success into G6 in place of TICKs 31-56 and compare with G6 as run (stim).
