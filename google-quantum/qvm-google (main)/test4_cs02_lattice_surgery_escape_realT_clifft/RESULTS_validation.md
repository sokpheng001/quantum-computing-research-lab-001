# Test 4, step A1: Clifft vs Google's qsim, real T (written 2026-11-03 10:55 PM KST)

Same noisy circuit in both simulators (`clifft_bridge.py`): ideal |T_L> in, the double check with real T gates and DEPOLARIZE1(p) on every qubit after every moment, ideal decode; counted with the E4 rule (error per kept T state = wrong logical among kept shots in the code space). Pauli noise because Clifft supports only Pauli channels: this is a simulator cross-check, not a Willow-noise result.

| circuit | p | simulator | shots | acceptance | errors / kept in code | error per kept T state (95 % CI) |
|---|---|---|---|---|---|---|
| Google G4 G6-style (FD 2) | 0.2 % | qsim | 4,000,000 | 74.07 % | 55 / 2,409,978 | 1 in 43,818 (1 in 33,664 to 1 in 58,165) |
| Google G4 G6-style (FD 2) | 0.2 % | Clifft | 200,000,000 | 74.08 % | 2940 / 120,522,075 | 1 in 40,994 (1 in 39,538 to 1 in 42,517) |
| | | **agreement** | | z = -0.75 | | z = -0.49 → **agree** |
| Google G4 G6-style (FD 2) | 0.5 % | qsim | 4,000,000 | 48.27 % | 336 / 1,138,058 | 1 in 3,387 (1 in 3,044 to 1 in 3,780) |
| Google G4 G6-style (FD 2) | 0.5 % | Clifft | 200,000,000 | 48.26 % | 16902 / 56,908,945 | 1 in 3,367 (1 in 3,317 to 1 in 3,418) |
| | | **agreement** | | z = +0.36 | | z = -0.11 → **agree** |
| cs02 (ours, FD 3) | 0.2 % | qsim | 4,000,000 | 61.87 % | 43 / 2,016,109 | 1 in 46,886 (1 in 34,808 to 1 in 64,786) |
| cs02 (ours, FD 3) | 0.2 % | Clifft | 200,000,000 | 61.92 % | 2172 / 100,861,843 | 1 in 46,437 (1 in 44,525 to 1 in 48,454) |
| | | **agreement** | | z = -1.82 | | z = -0.06 → **agree** |
| cs02 (ours, FD 3) | 0.5 % | qsim | 4,000,000 | 31.81 % | 339 / 733,959 | 1 in 2,165 (1 in 1,946 to 1 in 2,415) |
| cs02 (ours, FD 3) | 0.5 % | Clifft | 200,000,000 | 31.79 % | 14966 / 36,639,918 | 1 in 2,448 (1 in 2,409 to 1 in 2,488) |
| | | **agreement** | | z = +0.90 | | z = +2.24 → **agree** |
| #0 (ours, G6-fit, FD 3) | 0.2 % | qsim | 4,000,000 | 53.99 % | 47 / 1,680,998 | 1 in 35,766 (1 in 26,896 to 1 in 48,677) |
| #0 (ours, G6-fit, FD 3) | 0.2 % | Clifft | 200,000,000 | 53.98 % | 2647 / 84,030,408 | 1 in 31,746 (1 in 30,559 to 1 in 32,990) |
| | | **agreement** | | z = +0.18 | | z = -0.81 → **agree** |
| #0 (ours, G6-fit, FD 3) | 0.5 % | qsim | 4,000,000 | 23.10 % | 322 / 469,911 | 1 in 1,459 (1 in 1,308 to 1 in 1,633) |
| #0 (ours, G6-fit, FD 3) | 0.5 % | Clifft | 200,000,000 | 23.08 % | 14855 / 23,484,826 | 1 in 1,581 (1 in 1,556 to 1 in 1,607) |
| | | **agreement** | | z = +1.03 | | z = +1.42 → **agree** |

**Verdict: Clifft agrees with qsim in every case (|z| < 3).**

z = (Clifft − qsim) / combined standard error, for the acceptance and for the error rate.
