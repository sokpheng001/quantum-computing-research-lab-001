# Non-uniform schedules: different CNOT orders for different ancillas

**Purpose.** The uniform-schedule work showed that on [[90,8,10]] every schedule in which all ancillas use the
same CNOT order has a one-cycle fault path of weight at most 8, the same as Bravyi's schedule S. This folder
tests depth-7 schedules where **ancillas use different orders**, with the same qubits and connectivity.

**Key idea.** S's weight-8 fault paths come in families related by translation on the torus. Changing the order
at one place breaks only one copy, so the change must repeat across the torus. We use **class schedules**: the
ancillas are split into classes by a group homomorphism, and each class gets its own order.

**Results** (`results_nonuniform/`, task in `task.md`):

| Code | Valid class schedules | Above d1(S)? |
|---|---|---|
| [[72,12,6]] | – | none |
| [[90,8,10]] | 50 of about 87,000 candidates | none |
| [[108,8,10]] | 62 of about 89,000 candidates | none |

For [[144,12,12]], d1(S) = 10 was reproduced (100,000 trials). `ours/check_alt_w10.py` placed S's 17 weight-10
paths into alt[S, S⁻¹]: all stay undetected and logical, so the alternation does not beat S either.

**Files.**
- `ours/`: our code.
  - `nu.py`: the stages;
  - `classsched.py`: the class-schedule builder;
  - `bravyi_d1.py`: the distance search;
  - `bravyi_ler.py`: the logical error rate.
- `driver_nu.sh`, `launch.sh`, `stages.txt`: run scripts.
- `results_nonuniform/<code>/`: results per code.

Bravyi's reference code goes in `bravyi_ref/` (not included).
