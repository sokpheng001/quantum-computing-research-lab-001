# Test 5, B2: randomised d = 5 search, our method (written Nov 04, 07:33 PM KST)

Settings: {"max_anc": 14, "max_depth": 8, "evals": 120, "max_flags": 6}. Trees tried: **41** in 0.0 h.

| outcome | trees |
|---|---|
| SUCCESS | 41 |

- fewest malignant 3-fault T configurations left after flags: 0 (seed 1000, 0 flags, 29 qubits)

## Successes: fault distance >= 4 with real T, nearest-neighbour, strict readout rule, on Willow

| seed | qubits | flags | TICKs | max partners | malignant at 4 faults | T error per kept shot, p = 0.1 % (to 4 faults) |
|---|---|---|---|---|---|---|
| 1035 | 33 | 0 | 18 | 4 | 1705 | 1 in 7,587,187,214 |
| 1036 | 29 | 0 | 16 | 4 | 4257 | 1 in 7,380,639,739 |
| 1021 | 25 | 0 | 16 | 4 | 2859 | 1 in 4,903,605,602 |
| 1033 | 33 | 0 | 18 | 4 | 995 | 1 in 4,387,920,123 |
| 1029 | 32 | 0 | 18 | 4 | 1601 | 1 in 4,063,688,034 |
| 1031 | 32 | 0 | 18 | 4 | 1191 | 1 in 3,977,649,107 |
| 1004 | 29 | 0 | 18 | 4 | 1622 | 1 in 3,872,676,688 |
| 1038 | 24 | 0 | 16 | 4 | 4044 | 1 in 3,612,970,210 |
| 1019 | 23 | 0 | 16 | 4 | 4321 | 1 in 3,511,381,665 |
| 1006 | 28 | 0 | 18 | 4 | 1861 | 1 in 3,154,103,736 |
| 1037 | 24 | 0 | 18 | 4 | 4273 | 1 in 3,115,470,008 |
| 1000 | 29 | 0 | 18 | 4 | 2988 | 1 in 3,085,008,416 |
| 1039 | 33 | 0 | 18 | 4 | 2036 | 1 in 3,007,748,915 |
| 1018 | 29 | 0 | 18 | 4 | 2422 | 1 in 2,945,717,899 |
| 1013 | 30 | 0 | 18 | 4 | 2037 | 1 in 2,922,570,093 |
| 1007 | 26 | 0 | 16 | 4 | 2646 | 1 in 2,752,508,738 |
| 1005 | 30 | 0 | 18 | 4 | 2556 | 1 in 2,676,080,854 |
| 1025 | 26 | 0 | 18 | 4 | 3299 | 1 in 2,670,036,566 |
| 1028 | 30 | 0 | 18 | 4 | 1942 | 1 in 2,659,710,044 |
| 1011 | 28 | 0 | 20 | 4 | 2551 | 1 in 2,562,448,384 |
| 1008 | 31 | 0 | 18 | 3 | 2203 | 1 in 2,476,181,767 |
| 1017 | 30 | 0 | 20 | 4 | 1564 | 1 in 2,320,232,083 |
| 1034 | 23 | 0 | 16 | 4 | 4205 | 1 in 2,300,996,080 |
| 1002 | 31 | 0 | 20 | 4 | 1312 | 1 in 2,296,093,278 |
| 1014 | 31 | 0 | 20 | 4 | 2216 | 1 in 2,129,712,221 |
| 1024 | 25 | 2 | 18 | 4 | 4547 | 1 in 2,007,277,678 |
| 1015 | 24 | 0 | 20 | 4 | 3577 | 1 in 1,900,195,574 |
| 1023 | 30 | 0 | 20 | 4 | 2316 | 1 in 1,849,539,717 |
| 1022 | 25 | 0 | 18 | 4 | 3137 | 1 in 1,825,935,904 |
| 1016 | 28 | 0 | 20 | 4 | 3430 | 1 in 1,793,876,211 |
| 1010 | 33 | 0 | 20 | 4 | 2101 | 1 in 1,723,510,660 |
| 1026 | 23 | 0 | 18 | 4 | 2590 | 1 in 1,547,675,328 |
| 1012 | 25 | 2 | 18 | 4 | 3360 | 1 in 1,532,273,758 |
| 1001 | 23 | 0 | 18 | 4 | 4169 | 1 in 1,474,807,179 |
| 1003 | 30 | 0 | 20 | 4 | 2935 | 1 in 1,295,122,524 |
| 1030 | 24 | 1 | 18 | 4 | 5003 | 1 in 1,293,723,506 |
| 1032 | 29 | 0 | 20 | 4 | 3265 | 1 in 1,256,783,656 |
| 1009 | 25 | 0 | 18 | 4 | 4445 | 1 in 1,215,472,508 |
| 1027 | 24 | 1 | 20 | 4 | 4098 | 1 in 1,050,659,269 |
| 1040 | 27 | 0 | 20 | 4 | 3084 | 1 in 1,013,085,876 |
| 1020 | 25 | 1 | 22 | 4 | 3554 | 1 in 621,510,529 |

Reference (B0, same counting): Gidney d5a19 (FD 3) 1 in 974,523,423; Chan d5a19f3 (FD 4, not nearest-neighbour) 1 in 3,487,408,846.

## Validation notes (Nov 4, about 8 pm KST)

- Equivalence checks (nnflags/equivalence.py) on the first 6 results: (ii) logical action, (iii) unfold = exact
  time reverse of the fold, (iv) all detectors deterministic: **all pass**.
- Check (i) (same code as a reference) brute-forces all permutations of the data (19! at d = 5) and could not
  run (killed). The code is Gidney's d = 5 colour code by construction (d5_method.CODE, relabelled from
  cliffordea's d5a19); checked separately: 9 independent plaquettes, smallest logical weight 5.
- Discrimination: random labellings of the same trees have 47-273 malignant 3-fault T configurations; the
  labelling search brings them to 0, so the count is not trivially zero.
- Every result has malignant 4-fault T configurations (about 1,000-5,000): fault distance exactly 4, not 5.
- Still to do before claiming it: an independent real-T check by sampling (Clifft, noise sweep, slope), and
  the continuing-data readout rule.
