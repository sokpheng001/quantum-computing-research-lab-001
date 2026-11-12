# CNOT-layer reordering for BB codes at the syndrome-extraction level: summary statement

We tested whether reordering the CNOT layers of the depth-7 syndrome-extraction circuit of Bravyi et al.,
or alternating a schedule with its time reverse from cycle to cycle, can improve bivariate bicycle (BB)
codes (open question 4 of Bravyi et al., Nature 627, 778, 2024). Circuits were simulated in stim under
uniform circuit-level depolarising noise. The circuit-level distance was estimated with Bravyi et al.'s
randomised BP-OSD search, which returns upper bounds, and selected fault paths were checked exactly by
propagating them through the circuit. Logical error rates were obtained with a BP-OSD decoder (min-sum BP,
OSD-CS order 7) over 6 syndrome cycles.

All 1872 valid depth-7 CNOT orders were examined on [[72,12,6]] and [[90,8,10]]. No order reaches a larger
circuit-level distance than Bravyi's schedule S (6 and 8, respectively). A fraction of the orders lowers it:
288 of 1872 on [[72,12,6]], down to 3, and 92 of 1872 on [[90,8,10]], down to 6. The loss is visible in the
logical error rate: at p = 0.2% the distance-3 order on [[72,12,6]] fails about 3.8 times more often per cycle
than S (0.072% versus 0.019%), while the best-ranked and median orders perform like S. Alternating S with its
time reverse leaves the circuit-level distance unchanged on all three codes (6, 8 and 10 for [[72,12,6]],
[[90,8,10]] and [[144,12,12]]); on [[144,12,12]], all 17 weight-10 fault paths of S found by the search remain
undetected logical errors when placed in the alternating circuit. The reason is that the minimum-weight fault
paths of S fit inside a single syndrome cycle, and alternation only removes paths that need two consecutive
cycles of the same schedule. Consistently, the logical error rates of S, its time reverse and the alternating
circuit agree within their 95% intervals at p = 0.4% and 0.5% on [[90,8,10]] and [[144,12,12]]. Non-uniform
schedules, in which different classes of checks use different orders, did not beat S on [[72,12,6]],
[[90,8,10]] or [[108,8,10]] either.

Within the depth-7 circuit family considered here, CNOT reordering and time-reverse alternation therefore do
not improve on Bravyi's schedule; the schedule choice matters mainly to avoid orders that lose distance.
Limitations: the distances are upper bounds from a randomised search; the full scan of single orders was not
run on [[144,12,12]], and the scan on [[108,8,10]] was not completed.

## Figure caption

Figure X. CNOT-layer reordering of the depth-7 syndrome-extraction circuit of Bravyi et al.
(a) One-cycle circuit-level distance d1 of all 1872 valid depth-7 CNOT orders on [[72,12,6]] and [[90,8,10]],
relative to Bravyi's schedule S (d1(S) = 6 and 8). No order exceeds S. (b) Best circuit-level distance reached
by Bravyi's schedule S, the best reordered single schedule, and alternation of S with its time reverse S^-1,
with the code distance d shown as a dashed line. The full scan of single orders was not run on [[144,12,12]].
All distances are upper bounds from a randomised BP-OSD search; the [[144,12,12]] value for the alternating
circuit is confirmed by an exact check of S's weight-10 fault paths.
