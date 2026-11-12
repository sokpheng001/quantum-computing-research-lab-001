# Test 7, part F: one input error + one fault in the double check (written 2026-11-12 10:38 AM KST)

Each of 24 input errors (logical X, Y, Z before encoding; X, Y, Z on each data qubit after encoding) combined with no fault and with every distinct single fault of the check; Google's QVM circuit, real T, no other noise, ideal decode, 400 shots per pair. 'Silent wrong' = no detector fired, in the code space, wrong logical value. Script `t7_input_plus_fault.py`.

| circuit | check faults | pairs tested | input alone: silent wrong | input + 1 fault: silent wrong pairs |
|---|---|---|---|---|
| Google G4 G6-style | 150 | 3,624 | 0 | 4 |
| cs02 (ours) | 162 | 3,912 | 0 | 0 |

## Google G4 G6-style: silent wrong (input, fault) pairs

| input error | pairs | largest silent-wrong probability |
|---|---|---|
| data X on q2 | 2 | 0.125 |
| data Y on q2 | 2 | 0.120 |

| input error | check fault | silent | silent wrong |
|---|---|---|---|
| X on data q2 | slice 17: Y3 X4 | 0.532 | 0.125 |
| X on data q2 | slice 17: X9 Y10 | 0.435 | 0.120 |
| Y on data q2 | slice 17: Y3 X4 | 0.540 | 0.120 |
| Y on data q2 | slice 17: X9 Y10 | 0.490 | 0.113 |

## cs02 (ours): silent wrong (input, fault) pairs

None.
