# RESULTS.md — folder 003: the 001 experiments with BP-OSD-0

Folder 003 repeats the logical-error-rate experiments of folder 001 with one change: the
decoder for logical error rates is **BP-OSD-0** (ldpc 2.4.1 BpOsdDecoder, osd_method 'OSD_0',
order 0). Everything else is as in 001: serial min-sum BP, scaling 1.0, 100 iterations,
DEM priors, same circuits, same noise model, same schedules.

Not changed: the circuit-level distance search (randomised BP-OSD, OSD-CS order 20) is a
fault-path search, not a decoder, so all d_circ bounds are decoder-independent. They are
copied from 001 into results/from_001/ (bounds_936.csv, ranking_936.*, faultsets/, exp_144_bounds.csv,
pair_*) and summarised in docs/RESULTS_001_reference.md.

Experiments (driver_003.sh):
1. [[72]], 6 cycles: S, S^-1, alternating; best (744), median (131), worst (52) schedules;
   p = 0.006 and 0.004; both bases; >= 50 failures per point. DONE. The p = 0.002 stage was dropped
   on Oct 15 by the user's decision: the BP-OSD order-7 baseline in 001 is sufficient for [[72]].
   Figures: figures/exp_72_ler_osd0.png, figures/single_schedules_ler_osd0.png
2. [[144]], 6 cycles: S, S^-1, alternating; p = 0.005, 0.004. CANCELLED on Oct 15 by the user's decision
   (not needed). Folder 003 is closed.
