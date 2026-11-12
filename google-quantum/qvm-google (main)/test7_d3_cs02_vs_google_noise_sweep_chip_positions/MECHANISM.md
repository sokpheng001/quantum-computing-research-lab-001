# Test 7, part E: where the improvement comes from (written 2026-11-11 09:40 PM KST)

Script `t7_mechanism.py`, run in tmux `t7mech` (06:37 PM KST), data `results/mechanism/mechanism.json`, log
`logs/mechanism.log`. Exact Pauli faults are injected into Google's QVM circuits (real T gates, no other
noise, 40,000 shots per configuration, ideal decode); fault lists and verdicts from cliffordea (exact).

## E1. The silent pairs exist only with the real T gate

| circuit | fault locations | silent wrong pairs, real T | silent wrong pairs, S stand-in |
|---|---|---|---|
| Google G4 G6-style | 150 | **7** | 0 |
| cs02 | 162 | **0** | 0 |

## E2. How Google's 7 pairs fool the double check

For every one of the 7 pairs (Google's qubit numbering; data = 0, 2, 3, 5, 8, 10, 11):

- **Each fault alone:** no detector of the double check fires (Pauli signature all zero), and the state
  ends **outside the code space** in all 4,000 shots, so the next stabiliser check would catch it. Harmless.
- **The two together, real T:** still no detector fires (silent in 100 % of shots), and in about **25 %** of
  shots (9,908 to 10,003 of 40,000) the state ends **inside the code space with the wrong logical value**
  (wrong in every one of them). The other 75 % end outside the code space.
- **The two together, S stand-in:** not malignant.

| pair | fault 1 | fault 2 | in code and wrong |
|---|---|---|---|
| 1 | slice 1: X on data 2 | slice 17: Y3 X4 | 9,908 / 40,000 |
| 2 | slice 1: X on data 2 | slice 17: X9 Y10 | 9,908 / 40,000 |
| 3 | slice 5: X on helper 4 | slice 15: X8 X9 | 9,998 / 40,000 |
| 4 | slice 5: X on helper 4 | slice 19: Y2 X6 | 9,908 / 40,000 |
| 5 | slice 5: X on data 5 | slice 15: Y on data 8 | 10,003 / 40,000 |
| 6 | slice 5: X on helper 9 | slice 19: Y2 X6 | 9,908 / 40,000 |
| 7 | slice 15: X on helper 9 | slice 19: Y2 X6 | 9,908 / 40,000 |

Mechanism: an X-type fault inside the fold/unfold tree, which the double check's detectors cannot see,
plus a second fault near the end. As Pauli errors they only push the state out of the code space. The
final layer of physical T gates turns their combination into a coherent, non-Pauli error, and a quarter
of its weight is a logical error inside the code space (Chan et al., arXiv:2609.17706).

## E3. Ablation: the flags remove exactly these pairs

| cs02 variant | detectors | silent wrong pairs (real T) |
|---|---|---|
| as designed (ZZ flag F10 + X flag F11) | 6 | **0** |
| flags present, their 2 detectors ignored | 4 | **6** |
| flag qubits removed (the bare fold tree) | 6 | **5** |

The bare tree's 5 pairs match the search's screen value for this tree (5).

## E4. Which flag catches which pair (cs02 numbering; data = 1, 2, 4, 5, 6, 8, 9)

| fault 1 | fault 2 | flag detector fires | silent if flag alarms ignored; in code and wrong |
|---|---|---|---|
| slice 1: X on data 1 | slice 22: X3 Y5 | ZZ flag F10 and X flag F11, 100 % | 100 %; 10,066 / 40,000 |
| slice 1: X on data 4 | slice 22: X7 Y9 | ZZ flag F10, 100 % | 100 %; 9,976 / 40,000 |
| slice 5: X on root 0 | slice 22: X3 Y5 | ZZ flag F10 and X flag F11, 100 % | 100 %; 10,066 / 40,000 |
| slice 5: X on flag 10 | slice 18: X on data 2 | X flag F11, 100 % | 100 %; 40,000 / 40,000 |
| slice 7: X on helper 3 | slice 24: X0 Y1 | ZZ flag F10, 100 % | 100 %; 10,066 / 40,000 |
| slice 7: X on helper 7 | slice 24: X3 Y4 | ZZ flag F10, 100 % | 100 %; 9,976 / 40,000 |

The pairs have the same form as Google's (an X fault inside the tree plus an X·Y fault near the end). In
cs02 a flag reads a Z parity **during** the check, while the error is still a plain Pauli X. X anticommutes
with Z, so the flag fires with certainty (100 %, deterministic), before the final T layer can turn the
error into a coherent one. Without the flag alarms, cs02 fails exactly like Google's circuit.
