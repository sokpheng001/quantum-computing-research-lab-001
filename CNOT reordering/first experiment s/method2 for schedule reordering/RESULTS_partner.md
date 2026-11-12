# RESULTS_partner.md — path-targeted partner search (Method 2)

Task: docs/task.md. Rebuilt by report.py; last update 2026-10-17 08:40 AM KST. All distances are upper bounds from the randomised BP-OSD search unless marked as exactly verified.

## Summary

### Table A — regression and verdict

| Code | Bravyi d_circ(S) | Our S | Stage 0 | Best alt circuit | Its bound | Beats S? |
|---|---|---|---|---|---|---|
| [[72,12,6]] | <= 6 | <= 6 (300 trials/seed, 5 seeds, Z+X, 4+6 cycles) | PASS | alt [S, S^-1] | upper bound 6 | no |
| [[90,8,10]] | <= 8 | <= 8 (600 trials/seed, 5 seeds, Z+X, 4+6 cycles) | PASS | pending | | |
| [[108,8,10]] | <= 8 | pending | pending | | | |

### Table B — partner screen

| Code | S min-weight families | Partners tested | Partners catching all families | Best survivor's bound |
|---|---|---|---|---|
| [[72,12,6]] | 90 (weight 6) | 1871 | 0 | upper bound 6 (alt [S, S'#624]) |
| [[90,8,10]] | 9 (weight 8) | 1871 | 0 | — |
| [[108,8,10]] | pending | pending | | |

### Table C — logical error rate (only if Stage 5 ran)

Stage 5 did not run (it runs only for a [[90]] or [[108]] circuit that beats S).

### Verdict per code

- [[72,12,6]]: no partner of S raises the distance above 6 (best alternating circuit alt [S, S^-1]: upper bound 6 vs 6 for S; 300 trials/seed, 5 seeds, Z+X, 4+6 cycles).

## [[72,12,6]]

### Stage 0 — setup and regression: PASS

n = 72, k = 12, H_X H_Z^T = 0: True. S noiseless detectors all zero (both bases) at 2 and 6 cycles: True. S bound: minimum 6 (Bravyi 6), 300 trials/seed, 5 seeds, Z+X, 4+6 cycles.

| basis | cycles | seed 1 | seed 2 | seed 3 | seed 4 | seed 5 |
|---|---|---|---|---|---|---|
| Z | 4 | 6 | 6 | 6 | 6 | 6 |
| Z | 6 | 6 | 6 | 6 | 6 | 6 |
| X | 4 | 6 | 6 | 6 | 6 | 6 |
| X | 6 | 6 | 6 | 6 | 6 | 6 |

### Stage 1 — valid schedules

1872 valid depth-7 schedules (Z-first 936, X-first 936): no same-round collision and all-zero noiseless detectors in both bases (stim, every schedule). ids: S = 212, S^-1 = 1307, S_mirror = 676; time-reverse ids: {'S': 1307, 'Sinv': 212, 'Smirror': 1787}. File: results_partner/72/schedules.jsonl.

### Stage 2 — S's weakest paths (weight 6)

| basis | cycles | distinct sets | families | cycle spans of families |
|---|---|---|---|---|
| X | 4 | 122 | 22 | {1: 22} |
| X | 6 | 134 | 26 | {1: 26} |
| Z | 4 | 136 | 19 | {1: 19} |
| Z | 6 | 139 | 23 | {1: 23} |

One representative per family (first DEM column's physical location shown for each fault: Pauli, qubits, cycle):

- X|4 family 0 (24 sets, span 1 cycle(s)): Y@L2 c3; Y@L1 c3; Y@L3 c3; Y@L4 c3; Y@L21 c3; Y@L23 c3
- X|4 family 1 (18 sets, span 1 cycle(s)): Z@L2 c0; Z@L1 c0; Z@L3 c0; Z@L4 c0; Z@L21 c0; Z@L23 c0
- X|4 family 2 (18 sets, span 1 cycle(s)): Z@L2 c1; Z@L1 c1; Z@L3 c1; Z@L4 c1; Z@L21 c1; Z@L23 c1
- X|4 family 3 (18 sets, span 1 cycle(s)): Z@L2 c2; Z@L1 c2; Z@L3 c2; Z@L4 c2; Z@L21 c2; Z@L23 c2
- X|4 family 4 (17 sets, span 1 cycle(s)): Y@L2 c0; Y@L1 c0; Y@L3 c0; Y@L4 c0; Y@L21 c0; Y@L23 c0
- X|4 family 5 (3 sets, span 1 cycle(s)): Z@L0 c1; Z@R16 c1; Z@Z3 c1; Z@L28 c1; Z@L14 c1; Z@Z25 c1
- X|4 family 6 (3 sets, span 1 cycle(s)): XZ@L31,Z7 c3; XZ@L28,Z4 c3; XZ@L34,Z10 c3; XZ@L4,Z16 c3; XZ@L7,Z19 c3; XZ@L22,Z34 c3
- X|4 family 7 (2 sets, span 1 cycle(s)): XY@R6,Z24 c0; XY@R3,Z21 c0; XY@R9,Z27 c0; XY@R15,Z33 c0; XY@R18,Z0 c0; XY@R33,Z15 c0
- X|4 family 8 (2 sets, span 1 cycle(s)): Z@Z14 c1; Z@Z4 c0; Z@Z10 c0; Z@L21 c0; Z@R22 c1; Z@L28 c0
- X|4 family 9 (2 sets, span 1 cycle(s)): Z@L13 c1; Z@R29 c1; Z@R1 c1; Z@L27 c1; Z@L5 c1; Z@Z16 c1
- X|4 family 10 (2 sets, span 1 cycle(s)): Z@R12 c3; Z@L18 c2; Z@Z10 c3; Z@Z0 c2; Z@L17 c2; Z@Z30 c2
- X|4 family 11 (2 sets, span 1 cycle(s)): Y@L17 c3; Z@R27 c3; Y@L3 c3; XZ@L2,Z14 c3; XZ@L24,Z0 c3; Y@L25 c3
- X|4 family 12 (2 sets, span 1 cycle(s)): Y@L3 c3; XZ@L2,Z14 c3; XZ@L24,Z0 c3; Y@L25 c3; Y@L17 c3; XZ@L16,Z28 c3
- X|4 family 13 (1 sets, span 1 cycle(s)): Y@L3 c0; XY@R13,Z31 c0; XY@R5,Z23 c0; Y@L25 c0; Y@L17 c0; XY@R27,Z9 c0
- X|4 family 14 (1 sets, span 1 cycle(s)): Z@L3 c0; Z@R13 c0; Z@L17 c0; Z@R27 c0; Z@R5 c0; Z@L25 c0
- X|4 family 15 (1 sets, span 1 cycle(s)): Z@L11 c0; Z@R21 c0; Z@L19 c0; Z@R35 c0; Z@Z8 c0; Z@L33 c0
- X|4 family 16 (1 sets, span 1 cycle(s)): Z@L7 c0; Z@R23 c0; Z@Z10 c0; Z@L21 c0; Z@L35 c0; Z@Z32 c0
- X|4 family 17 (1 sets, span 1 cycle(s)): Z@L5 c1; Z@R15 c1; Z@L13 c1; Z@R29 c1; Z@R1 c1; Z@L27 c1
- X|4 family 18 (1 sets, span 1 cycle(s)): Z@Z8 c1; Z@Z5 c1; Z@Z17 c1; Z@Z2 c1; Z@Z26 c1; Z@Z32 c1
- X|4 family 19 (1 sets, span 1 cycle(s)): Z@L1 c2; Z@R17 c2; Z@L15 c2; Z@R25 c2; Z@R3 c2; Z@L29 c2
- X|4 family 20 (1 sets, span 1 cycle(s)): Z@L3 c2; Z@R13 c2; Z@R5 c2; Z@L25 c2; Z@L17 c2; Z@Z28 c2
- X|4 family 21 (1 sets, span 1 cycle(s)): Z@L3 c2; Z@Z14 c2; Z@Z0 c2; Z@L25 c2; Z@L17 c2; Z@Z28 c2
- X|6 family 0 (18 sets, span 1 cycle(s)): Y@L2 c5; Y@L1 c5; Y@L3 c5; Y@L4 c5; Y@L21 c5; Y@L23 c5
- X|6 family 1 (17 sets, span 1 cycle(s)): Y@L2 c0; Y@L1 c0; Y@L3 c0; Y@L4 c0; Y@L21 c0; Y@L23 c0
- X|6 family 2 (17 sets, span 1 cycle(s)): Z@L2 c2; Z@L1 c2; Z@L3 c2; Z@L4 c2; Z@L21 c2; Z@L23 c2
- X|6 family 3 (15 sets, span 1 cycle(s)): Z@L2 c1; Z@L1 c1; Z@L3 c1; Z@L20 c1; Z@L0 c1; Z@L22 c1
- X|6 family 4 (14 sets, span 1 cycle(s)): Z@L2 c3; Z@L1 c3; Z@L3 c3; Z@L4 c3; Z@L21 c3; Z@L23 c3
- X|6 family 5 (13 sets, span 1 cycle(s)): Z@L2 c0; Z@L1 c0; Z@L3 c0; Z@L4 c0; Z@L21 c0; Z@L23 c0
- X|6 family 6 (12 sets, span 1 cycle(s)): Z@L2 c4; Z@L1 c4; Z@L19 c4; Z@L5 c4; Z@L21 c4; Z@L0 c4
- X|6 family 7 (4 sets, span 1 cycle(s)): Z@R2 c2; Z@L28 c2; Z@L0 c2; Z@Z17 c2; Z@L14 c2; Z@Z25 c2
- X|6 family 8 (3 sets, span 1 cycle(s)): Z@L8 c1; Z@R18 c1; Z@Z11 c1; Z@L22 c1; Z@L30 c1; Z@Z33 c1
- X|6 family 9 (2 sets, span 1 cycle(s)): Z@Z8 c2; Z@Z5 c2; Z@Z23 c2; Z@Z29 c2; Z@Z32 c2; Z@Z35 c2
- X|6 family 10 (2 sets, span 1 cycle(s)): Z@Z7 c3; Z@L18 c3; Z@L10 c3; Z@Z21 c3; Z@L32 c3; Z@Z35 c3
- X|6 family 11 (2 sets, span 1 cycle(s)): Z@R5 c5; Y@L25 c5; Y@L3 c5; XZ@L2,Z14 c5; Y@L17 c5; XZ@L16,Z28 c5
- X|6 family 12 (2 sets, span 1 cycle(s)): XZ@L31,Z7 c5; XZ@L28,Z4 c5; XZ@L34,Z10 c5; XZ@L4,Z16 c5; XZ@L7,Z19 c5; XZ@L22,Z34 c5
- X|6 family 13 (1 sets, span 1 cycle(s)): XY@R12,Z30 c0; XY@R6,Z24 c0; XY@R9,Z27 c0; XY@R0,Z18 c0; XY@R21,Z3 c0; XY@R30,Z12 c0
- X|6 family 14 (1 sets, span 1 cycle(s)): Z@L5 c0; Z@R15 c0; Z@L13 c0; Z@R29 c0; Z@Z2 c0; Z@L27 c0
- X|6 family 15 (1 sets, span 1 cycle(s)): Z@Z14 c0; Z@Z5 c0; Z@Z20 c0; Z@Z26 c0; Z@Z29 c0; Z@Z32 c0
- X|6 family 16 (1 sets, span 1 cycle(s)): Z@L8 c2; Z@R18 c2; Z@L22 c2; Z@R32 c2; Z@R10 c2; Z@L30 c2
- X|6 family 17 (1 sets, span 1 cycle(s)): Z@L22 c2; Z@R32 c2; Z@R10 c2; Z@L30 c2; Z@L8 c2; Z@Z19 c2
- X|6 family 18 (1 sets, span 1 cycle(s)): Z@Z8 c2; Z@L19 c2; Z@Z12 c3; Z@Z2 c2; Z@R20 c3; Z@L26 c2
- X|6 family 19 (1 sets, span 1 cycle(s)): Z@L7 c3; Z@R23 c3; Z@L21 c3; Z@R31 c3; Z@R9 c3; Z@L35 c3
- X|6 family 20 (1 sets, span 1 cycle(s)): Z@L4 c3; Z@R14 c3; Z@R0 c3; Z@L26 c3; Z@L12 c3; Z@Z29 c3
- X|6 family 21 (1 sets, span 1 cycle(s)): Z@R0 c3; Z@L26 c3; Z@L4 c3; Z@Z15 c3; Z@L12 c3; Z@Z29 c3
- X|6 family 22 (1 sets, span 1 cycle(s)): Z@R4 c4; Z@L24 c4; Z@L2 c4; Z@Z13 c4; Z@L16 c4; Z@Z27 c4
- X|6 family 23 (1 sets, span 1 cycle(s)): Z@Z8 c4; Z@L19 c4; Z@Z12 c5; Z@Z2 c4; Z@R20 c5; Z@L26 c4
- X|6 family 24 (1 sets, span 1 cycle(s)): Y@L15 c5; Z@R25 c5; Z@R3 c5; Y@L29 c5; Y@L1 c5; XZ@L0,Z12 c5
- X|6 family 25 (1 sets, span 1 cycle(s)): Y@L0 c5; XZ@L5,Z17 c5; XZ@L27,Z3 c5; Y@L28 c5; Y@L14 c5; XZ@L13,Z25 c5
- Z|4 family 0 (25 sets, span 1 cycle(s)): X@L30 c2; X@L3 c2; X@L0 c2; X@L27 c2; X@L6 c2; X@L12 c2
- Z|4 family 1 (22 sets, span 1 cycle(s)): X@L30 c3; X@L3 c3; X@L0 c3; X@L27 c3; X@L6 c3; X@L12 c3
- Z|4 family 2 (20 sets, span 1 cycle(s)): X@L30 c0; X@L3 c0; X@L9 c0; X@L6 c0; X@L15 c0; X@L21 c0
- Z|4 family 3 (19 sets, span 1 cycle(s)): X@L30 c0; X@L3 c0; X@L0 c0; X@L27 c0; X@L6 c0; X@L12 c0
- Z|4 family 4 (18 sets, span 1 cycle(s)): X@L30 c1; X@L3 c1; X@L0 c1; X@L27 c1; X@L6 c1; X@L12 c1
- Z|4 family 5 (6 sets, span 1 cycle(s)): ZY@R9,X3 c0; X@L25 c0; X@L10 c0; ZY@R24,X18 c0; X@R10 c0; X@R25 c0
- Z|4 family 6 (5 sets, span 1 cycle(s)): X@R5 c3; X@L3 c3; X@L25 c3; X@R27 c3; X@R13 c3; X@L17 c3
- Z|4 family 7 (3 sets, span 1 cycle(s)): X@R0 c0; X@L4 c0; X@L26 c0; X@R28 c0; X@R14 c0; X@L12 c0
- Z|4 family 8 (3 sets, span 1 cycle(s)): X@R0 c2; X@L4 c2; X@L26 c2; X@R28 c2; X@R14 c2; X@L12 c2
- Z|4 family 9 (2 sets, span 1 cycle(s)): X@L30 c0; XZ@L3,X21 c0; ZY@L22,X4 c0; X@L27 c0; X@L6 c0; X@L12 c0
- Z|4 family 10 (2 sets, span 1 cycle(s)): XZ@L31,X13 c0; X@L25 c0; X@L1 c0; ZY@L14,X32 c0; X@L7 c0; X@L22 c0
- Z|4 family 11 (2 sets, span 1 cycle(s)): X@L33 c1; X@X26 c1; X@X11 c1; X@L12 c1; X@R12 c1; X@R33 c1
- Z|4 family 12 (2 sets, span 1 cycle(s)): X@R0 c1; X@L4 c1; X@L26 c1; X@R28 c1; X@R14 c1; X@L12 c1
- Z|4 family 13 (2 sets, span 1 cycle(s)): X@L30 c2; X@X29 c2; X@X8 c2; X@L15 c2; X@R30 c2; X@R15 c2
- Z|4 family 14 (1 sets, span 1 cycle(s)): XX@R4,Z22 c0; XX@R18,Z0 c0; XX@R1,Z19 c0; XX@R20,Z2 c0; XX@R2,Z20 c0; XX@R3,Z21 c0
- Z|4 family 15 (1 sets, span 1 cycle(s)): XX@R0,Z18 c0; X@L4 c0; X@L26 c0; XX@R28,Z10 c0; XX@R14,Z32 c0; X@L12 c0
- Z|4 family 16 (1 sets, span 1 cycle(s)): X@R0 c0; X@R19 c0; X@R1 c0; X@R2 c0; X@R3 c0; X@R23 c0
- Z|4 family 17 (1 sets, span 1 cycle(s)): X@R0 c1; X@R19 c1; X@R1 c1; X@R2 c1; X@R3 c1; X@R23 c1
- Z|4 family 18 (1 sets, span 1 cycle(s)): YX@R1,X31 c3; XZ@L26,X25 c3; YX@R16,X10 c3; XZ@L14,X13 c3; X@L23 c2; X@L20 c2
- Z|6 family 0 (19 sets, span 1 cycle(s)): X@L30 c2; X@L3 c2; X@L0 c2; X@L27 c2; X@L6 c2; X@L12 c2
- Z|6 family 1 (18 sets, span 1 cycle(s)): X@L30 c5; X@L3 c5; X@L33 c5; X@L27 c5; X@L9 c5; X@L18 c5
- Z|6 family 2 (16 sets, span 1 cycle(s)): X@L30 c0; X@L3 c0; X@L0 c0; X@L27 c0; X@L6 c0; X@L12 c0
- Z|6 family 3 (16 sets, span 1 cycle(s)): X@L30 c0; X@L24 c0; X@L0 c0; X@L33 c0; X@L6 c0; X@L21 c0
- Z|6 family 4 (15 sets, span 1 cycle(s)): X@L30 c3; X@L3 c3; X@L0 c3; X@L27 c3; X@L6 c3; X@L12 c3
- Z|6 family 5 (14 sets, span 1 cycle(s)): X@L30 c1; X@L3 c1; X@L33 c1; X@L27 c1; X@L9 c1; X@L18 c1
- Z|6 family 6 (9 sets, span 1 cycle(s)): X@L30 c4; X@L3 c4; X@L0 c4; X@L27 c4; X@L6 c4; X@L12 c4
- Z|6 family 7 (4 sets, span 1 cycle(s)): X@L30 c0; X@L3 c0; ZY@L25,X7 c0; XZ@L6,X24 c0; X@L15 c0; X@L21 c0
- Z|6 family 8 (4 sets, span 1 cycle(s)): ZY@L16,X34 c0; X@L3 c0; XZ@L33,X15 c0; X@L27 c0; X@L9 c0; X@L18 c0
- Z|6 family 9 (4 sets, span 1 cycle(s)): X@L30 c1; X@X29 c1; X@X8 c1; X@L15 c1; X@R30 c1; X@R15 c1
- Z|6 family 10 (4 sets, span 1 cycle(s)): X@R4 c3; X@L24 c3; X@L2 c3; X@R26 c3; X@R12 c3; X@L16 c3
- Z|6 family 11 (3 sets, span 1 cycle(s)): X@R0 c4; X@L4 c4; X@L26 c4; X@R28 c4; X@R14 c4; X@L12 c4
- Z|6 family 12 (2 sets, span 1 cycle(s)): XX@R0,Z18 c0; X@L4 c0; X@L26 c0; XX@R28,Z10 c0; XX@R14,Z32 c0; X@L12 c0
- Z|6 family 13 (2 sets, span 1 cycle(s)): X@R0 c5; X@L4 c5; X@L26 c5; X@R28 c5; X@R14 c5; X@L12 c5
- Z|6 family 14 (1 sets, span 1 cycle(s)): X@R0 c0; X@L4 c0; X@L26 c0; X@R28 c0; X@R14 c0; X@L12 c0
- Z|6 family 15 (1 sets, span 1 cycle(s)): X@R4 c1; X@R18 c1; X@R1 c1; X@R20 c1; X@R2 c1; X@R3 c1
- Z|6 family 16 (1 sets, span 1 cycle(s)): X@L34 c1; X@R22 c1; X@R8 c1; X@L6 c1; X@R30 c1; X@L20 c1
- Z|6 family 17 (1 sets, span 1 cycle(s)): X@L30 c2; X@X29 c2; X@X8 c2; X@L15 c2; X@R30 c2; X@R15 c2
- Z|6 family 18 (1 sets, span 1 cycle(s)): X@R17 c2; X@R30 c2; X@R12 c2; X@R13 c2; X@R14 c2; X@R34 c2
- Z|6 family 19 (1 sets, span 1 cycle(s)): X@R2 c2; X@L0 c2; X@L28 c2; X@R24 c2; X@R16 c2; X@L14 c2
- Z|6 family 20 (1 sets, span 1 cycle(s)): X@L30 c3; X@X29 c3; X@X8 c3; X@L15 c3; X@R30 c3; X@R15 c3
- Z|6 family 21 (1 sets, span 1 cycle(s)): X@L0 c4; X@X35 c4; X@X14 c4; X@L21 c4; X@R0 c4; X@R21 c4
- Z|6 family 22 (1 sets, span 1 cycle(s)): X@L0 c5; X@X35 c5; X@X14 c5; X@L21 c5; X@R0 c5; X@R21 c5

### Stage 3 — exact screen of all partners

1871 partners S' (both starting sides, S itself excluded). Each S family representative placed so that all its faults fall in S cycles of alt [S, S'] (every time shift tried); detector and observable flips computed exactly by stim FlipSimulator in the alt circuit. Score = families still undetected AND logical.

- Score histogram: {'89': 1871}
- Partners with score 0: 0 []
- S^-1 (1307): score 89; S_mirror (676): score 89
- Status counts over all (partner, family) pairs: {'survives': 166519, 'broken': 1871}
- Sanity, alt [S, S] = S: {'survives': 89, 'broken': 1}
- Stage 4 survivors: [0, 208, 417, 624, 832, 1040, 1248, 1455, 1663, 1871]

### Stage 4 — distance search on the survivors

Settings: 300 trials/seed, 5 seeds, Z+X, 4+6 cycles; S rerun in the same batch.

| circuit | ids | Z 4c | Z 6c | X 4c | X 6c | min | min path exactly verified | alt sets in S / S sets in alt (exact) |
|---|---|---|---|---|---|---|---|---|
| S | 212 | 6 | 6 | 6 | 6 | 6 | yes |  |
| S^-1 | 1307 | 6 | 6 | 6 | 6 | 6 | yes |  |
| S_mirror | 676 | 6 | 6 | 6 | 6 | 6 | yes |  |
| alt [S, S^-1] | 212+1307 | 6 | 6 | 6 | 6 | 6 | yes | {'survives': 505, 'broken': 59} / {'survives': 530, 'broken': 1} |
| alt [S, S_mirror] | 212+676 | 6 | 6 | 6 | 6 | 6 | yes | {'survives': 523, 'broken': 56} / {'survives': 530, 'broken': 1} |
| alt [S, S'#0] | 212+0 | 3 | 3 | 3 | 3 | 3 | yes | {'detected': 116} / {'survives': 530, 'broken': 1} |
| alt [S, S'#208] | 212+208 | 3 | 3 | 3 | 3 | 3 | yes | {'detected': 115} / {'survives': 530, 'detected': 1} |
| alt [S, S'#417] | 212+417 | 3 | 3 | 3 | 3 | 3 | yes | {'detected': 177} / {'survives': 530, 'broken': 1} |
| alt [S, S'#624] | 212+624 | 6 | 6 | 6 | 6 | 6 | yes | {'survives': 502, 'broken': 67} / {'survives': 530, 'broken': 1} |
| alt [S, S'#832] | 212+832 | 6 | 6 | 6 | 6 | 6 | yes | {'survives': 469, 'broken': 41} / {'survives': 530, 'broken': 1} |
| alt [S, S'#1040] | 212+1040 | 6 | 6 | 6 | 6 | 6 | yes | {'survives': 494, 'broken': 39} / {'survives': 530, 'broken': 1} |
| alt [S, S'#1248] | 212+1248 | 6 | 6 | 6 | 6 | 6 | yes | {'survives': 499, 'broken': 110} / {'survives': 530, 'broken': 1} |
| alt [S, S'#1455] | 212+1455 | 6 | 6 | 6 | 6 | 6 | yes | {'survives': 525, 'detected': 67, 'broken': 1} / {'survives': 530, 'broken': 1} |
| alt [S, S'#1663] | 212+1663 | 5 | 5 | 5 | 5 | 5 | yes | {'broken': 104} / {'survives': 530, 'broken': 1} |
| alt [S, S'#1871] | 212+1871 | 6 | 6 | 6 | 6 | 6 | yes | {'survives': 490, 'detected': 64} / {'survives': 530, 'broken': 1} |

Circuits that beat S: none.

### Control check: PASS

S gives 6: True. Every alternating circuit <= 6: True {'212+1307': 6, '212+676': 6, '212+0': 3, '212+208': 3, '212+417': 3, '212+624': 6, '212+832': 6, '212+1040': 6, '212+1248': 6, '212+1455': 6, '212+1663': 5, '212+1871': 6}. Agrees with earlier [[72]] runs (S, S^-1, alt [S, S^-1] all 6): True {'S': 6, 'Sinv': 6, 'alt': 6}. Partners that caught all of S's weight-6 families in Stage 3: 0.

## [[90,8,10]]

### Stage 0 — setup and regression: PASS

n = 90, k = 8, H_X H_Z^T = 0: True. S noiseless detectors all zero (both bases) at 2 and 6 cycles: True. S bound: minimum 8 (Bravyi 8), 600 trials/seed, 5 seeds, Z+X, 4+6 cycles.

| basis | cycles | seed 1 | seed 2 | seed 3 | seed 4 | seed 5 |
|---|---|---|---|---|---|---|
| Z | 4 | 8 | 9 | 8 | 8 | 9 |
| Z | 6 | 8 | 8 | 8 | 8 | 8 |
| X | 4 | 10 | 10 | 10 | 10 | 10 |
| X | 6 | 9 | 9 | 10 | 9 | 9 |

### Stage 1 — valid schedules

1872 valid depth-7 schedules (Z-first 936, X-first 936): no same-round collision and all-zero noiseless detectors in both bases (stim, every schedule). ids: S = 212, S^-1 = 1307, S_mirror = 676; time-reverse ids: {'S': 1307, 'Sinv': 212, 'Smirror': 1787}. File: results_partner/90/schedules.jsonl.

### Stage 2 — S's weakest paths (weight 8)

| basis | cycles | distinct sets | families | cycle spans of families |
|---|---|---|---|---|
| Z | 4 | 4 | 3 | {1: 3} |
| Z | 6 | 9 | 6 | {2: 3, 1: 3} |

One representative per family (first DEM column's physical location shown for each fault: Pauli, qubits, cycle):

- Z|4 family 0 (2 sets, span 1 cycle(s)): X@R0 c0; X@L25 c1; X@L2 c0; X@L8 c0; X@R28 c0; X@X9 c1; X@X37 c1; X@L17 c1
- Z|4 family 1 (1 sets, span 1 cycle(s)): X@R3 c1; X@L28 c1; X@R23 c1; X@L0 c2; X@X32 c2; X@X12 c2; X@L37 c2; X@L22 c1
- Z|4 family 2 (1 sets, span 1 cycle(s)): X@R3 c2; X@L28 c2; X@R23 c2; X@L0 c3; X@X32 c3; X@X12 c3; X@L37 c3; X@L22 c2
- Z|6 family 0 (2 sets, span 2 cycle(s)): X@R4 c1; X@L29 c1; X@R21 c1; X@L1 c2; X@X30 c2; X@X13 c2; X@L38 c2; X@L23 c1
- Z|6 family 1 (2 sets, span 1 cycle(s)): X@R0 c1; X@L25 c2; X@L2 c1; X@L8 c1; X@R28 c1; X@X9 c2; X@X37 c2; X@L17 c2
- Z|6 family 2 (2 sets, span 2 cycle(s)): X@R0 c3; X@L25 c3; X@R20 c3; X@L42 c4; X@X29 c4; X@X9 c4; X@L34 c4; X@L19 c3
- Z|6 family 3 (1 sets, span 1 cycle(s)): X@R0 c0; X@L25 c1; X@L2 c0; X@L8 c0; X@R28 c0; X@X9 c1; X@X37 c1; X@L17 c1
- Z|6 family 4 (1 sets, span 2 cycle(s)): X@R4 c2; X@L29 c2; X@R21 c2; X@L1 c3; X@X30 c3; X@X13 c3; X@L38 c3; X@L23 c2
- Z|6 family 5 (1 sets, span 1 cycle(s)): X@L3 c2; X@L42 c2; X@R26 c2; X@X7 c3; X@X35 c3; X@L12 c3; X@R43 c2; X@L23 c3

### Stage 3 — exact screen of all partners

1871 partners S' (both starting sides, S itself excluded). Each S family representative placed so that all its faults fall in S cycles of alt [S, S'] (every time shift tried); detector and observable flips computed exactly by stim FlipSimulator in the alt circuit. Score = families still undetected AND logical.

- Score histogram: {'6': 1871}
- Partners with score 0: 0 []
- S^-1 (1307): score 6; S_mirror (676): score 6
- Status counts over all (partner, family) pairs: {'survives': 11226, 'broken': 5613}
- Sanity, alt [S, S] = S: {'survives': 6, 'broken': 3}
- Stage 4 survivors: [0, 208, 417, 624, 832, 1040, 1248, 1455, 1663, 1871]

Figures: figures_partner/F1_bounds.png, F2_screen.png (F3_ler.png only if Stage 5 ran).
