
## Task B — ranking of the 936 Z-first depth-7 schedules, [[72]], 4 cycles, 100 trials (2026-10-14)

Key: min(dZ,dX) desc, then nontrivial min-weight sets (Z+X) asc, then all min-weight sets asc. Core (schedule-independent) keys: Z 17, X 14; a set is nontrivial if it uses a non-core fault.

Bound values: {3: 24, 6: 809, 5: 100, 4: 3}. Nontrivial sets per schedule: min 2, median 22, max 43.

Symmetry: T1 maps 936/936 and T2 maps 936/936 schedules into the Z-first set; **270 classes** (sizes {2: 72, 4: 198}); bounds agree within 248/270 classes.

**Bravyi S (id 212): rank 514 of 936, class 129** (class members [212, 310, 676, 774]).


Top 5:
| rank | id | class | dZ | dX | min-weight sets Z / X | nontrivial Z / X | X order / Z order |
|---|---|---|---|---|---|---|---|
| 1 | 744 | 1 | <= 6 | <= 6 | 7 / 6 | 5 / 5 | B2 A3 A1 A2 B3 B1 / B1 B3 A3 A1 A2 B2 |
| 2 | 540 | 2 | <= 6 | <= 6 | 5 / 8 | 5 / 6 | B1 A2 A1 A3 B3 B2 / B3 B2 A2 A1 A3 B1 |
| 3 | 873 | 3 | <= 6 | <= 6 | 7 / 6 | 6 / 5 | B3 A2 A3 A1 B2 B1 / B1 B2 A3 A2 A1 B3 |
| 4 | 716 | 4 | <= 6 | <= 6 | 7 / 7 | 6 / 6 | B2 A2 A3 A1 B3 B1 / B1 B3 A3 A1 A2 B2 |
| 5 | 750 | 5 | <= 6 | <= 6 | 8 / 6 | 7 / 5 | B2 A3 A1 A2 B3 B1 / B3 B1 A3 A1 A2 B2 |

Median:
| rank | id | class | dZ | dX | min-weight sets Z / X | nontrivial Z / X | X order / Z order |
|---|---|---|---|---|---|---|---|
| 469 | 243 | 142 | <= 6 | <= 6 | 16 / 15 | 13 / 11 | A2 B2 B3 B1 A1 A3 / A3 A1 B1 B3 B2 A2 |

Bottom 5:
| rank | id | class | dZ | dX | min-weight sets Z / X | nontrivial Z / X | X order / Z order |
|---|---|---|---|---|---|---|---|
| 932 | 934 | 268 | <= 3 | <= 3 | 8 / 9 | 8 / 9 | B3 A3 B2 A1 B1 A2 / A2 B1 A1 B2 A3 B3 |
| 933 | 156 | 265 | <= 3 | <= 3 | 10 / 8 | 10 / 8 | A2 B1 A1 B2 A3 B3 / B3 A3 B2 A1 B1 A2 |
| 934 | 417 | 269 | <= 3 | <= 3 | 8 / 10 | 8 / 10 | A3 B3 A1 B2 A2 B1 / B1 A2 B2 A1 B3 A3 |
| 935 | 568 | 270 | <= 3 | <= 3 | 9 / 10 | 9 / 10 | B1 A2 B2 A1 B3 A3 / A3 B3 A1 B2 A2 B1 |
| 936 | 52 | 270 | <= 3 | <= 3 | 8 / 13 | 8 / 13 | A1 B2 A2 B1 A3 B3 / B3 A3 B1 A2 B2 A1 |

Bravyi:
| rank | id | class | dZ | dX | min-weight sets Z / X | nontrivial Z / X | X order / Z order |
|---|---|---|---|---|---|---|---|
| 514 | 212 | 129 | <= 6 | <= 6 | 20 / 12 | 16 / 9 | A2 B2 B1 B3 A1 A3 / A1 A3 B1 B2 B3 A2 |

Figure: figures/hist_dcirc_936.png; table: results/ranking_936.csv
