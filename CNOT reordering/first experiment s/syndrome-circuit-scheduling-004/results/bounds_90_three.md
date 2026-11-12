| circuit | basis | seed 1 | seed 2 | seed 3 | seed 4 | seed 5 | min over seeds | trials per seed |
|---|---|---|---|---|---|---|---|---|
| S | Z | <= 9 | <= 10 | <= 9 | <= 8 | <= 9 | <= 8 | 600 |
| S | X | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | 600 |
| S^-1 | Z | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | 600 |
| S^-1 | X | <= 10 | <= 10 | <= 9 | <= 9 | <= 10 | <= 9 | 600 |
| alt S/S^-1 | Z | <= 8 | <= 9 | <= 10 | <= 9 | <= 10 | <= 8 | 600 |
| alt S/S^-1 | X | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | <= 9 | 600 |

S: d_circ <= 8 (min over bases)
S^-1: d_circ <= 9 (min over bases)
alt S/S^-1: d_circ <= 8 (min over bases)
Z: bound(alt) = 8 vs min(bound(S), bound(S^-1)) = 8 -> Shaw-Terhal Prop. 3 consistent: True
X: bound(alt) = 9 vs min(bound(S), bound(S^-1)) = 9 -> Shaw-Terhal Prop. 3 consistent: True
