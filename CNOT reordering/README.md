# CNOT reordering for bivariate bicycle (BB) codes

**Question.** Bravyi et al., *Nature* 627, 778 (2024), open question 4: can a different order of the CNOT gates
in the syndrome-measurement circuit of a BB code, or alternating two orders from cycle to cycle, give a higher
circuit-level distance than their schedule **S**?

**Answer from this work: no.** No schedule we found beats S.

| Code | Bravyi's S | Our search | Result |
|---|---|---|---|
| [[72,12,6]] | 6 | all 1,872 uniform depth-7 schedules, and alternations | none above 6 |
| [[90,8,10]] | 8 | all uniform schedules; non-uniform "class" schedules (50 valid of about 87,000) | none above 8 |
| [[108,8,10]] | 8 | non-uniform class schedules (62 valid of about 89,000); the uniform scan was not finished | none above 8 found |
| [[144,12,12]] | 10 | S's 17 weight-10 fault paths placed inside alt[S, S⁻¹] | all 17 still undetected and logical, so alt[S, S⁻¹] ≤ 10 = S |

All distances are upper bounds from Bravyi's randomised BP-OSD search, reproduced exactly on S before every
run. The project was closed in October 2026.

## Folders

| Folder | What it is |
|---|---|
| [`first experiment s/`](first%20experiment%20s/) | experiments 001–004, method 2 and a cross-code summary (each has its own README) |
| [`bb-code-reordering-cnot-running/`](bb-code-reordering-cnot-running/) | uniform-schedule work: one-cycle distance of every uniform depth-7 schedule, with Bravyi's reference setup |
| [`non-uniform schedule/`](non-uniform%20schedule/) | non-uniform work: schedules where groups of ancillas use different CNOT orders |
| [`first found/`](first%20found/) | early side experiments (a BB84 key-distribution demo) |

**Not included:** Bravyi's reference code ([github.com/sbravyi/BivariateBicycleCodes](https://github.com/sbravyi/BivariateBicycleCodes),
Apache 2.0) is cloned into each `bravyi_ref/` folder and never modified. Python environments and result files over
50 MB (`sets.jsonl` of the [[72]] and [[108]] runs) are left out. Scripts contain absolute paths from the author's
server.
