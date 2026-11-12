#!/bin/bash
# Folder 004: the three-circuit experiment (S, S^-1, alternating S/S^-1) on the [[90,8,10]] BB code
# (l=15, m=3, A = x^9 + y + y^2, B = 1 + x^2 + x^7), decoder = the project's fixed BP-OSD
# (serial min-sum, scaling 1.0, 100 iterations, OSD-CS order 7, DEM priors).
# Stage 1: d_circ bounds, multi-seed randomised BP-OSD search, 4 cycles, 5 seeds x 600 trials.
# Stage 2: logical error rate, 6 cycles, both bases, p = 0.006, 0.005, 0.004, >= 30 failures.
# Workers adapt to free cores (2..8) at every step.  Resumable: ./launch.sh driver_004.sh
cd /home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-004
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
P=../venv/bin/python; export BB_N=90 BB_REF=8
np_free() { local busy n; busy=$(ps -eo pcpu=,args= | awk '$1>50 && /python/' | wc -l); n=$((12 - busy)); [ $n -lt 2 ] && n=2; [ $n -gt 8 ] && n=8; echo $n; }
echo "== driver_004 start $(date)"
echo "== stage 1: d_circ bounds on [[90,8,10]], 4 cycles, 5 seeds x 6 chunks x 100 trials"
for k in 1 2 3 4 5 6; do
  NP=$(np_free); echo "-- round $k, $NP workers $(date)"
  $P strong_search.py --n 90 --cycles 4 --nproc $NP --seeds 5 --chunk 100 --max-chunks $k 2>&1 | grep -v "^ *$"
done
$P strong_summary.py 2>&1 | tee results/bounds_90_three.md
$P fig_bounds.py --out figures/exp_90_bounds.png 2>&1
grep -q "three-circuit d_circ bounds" RESULTS.md || { echo; echo "## [[90,8,10]] three-circuit d_circ bounds ($(date -u +%F))"; echo; cat results/bounds_90_three.md; echo; echo "Figure: figures/exp_90_bounds.png"; } >> RESULTS.md
echo "== stage 2: LER, 6 cycles, both bases $(date)"
for p in 0.006 0.005 0.004; do
  case $p in 0.006) M=3000;  B=300;;  0.005) M=8000;  B=500;;  0.004) M=20000; B=1000;; esac
  for s in S Sinv alt; do for b in Z X; do
    NP=$(np_free); $P run_ler.py --n 90 --cycles 6 --nproc $NP --sched $s --basis $b --p $p --target-fails 30 --max-shots $M --batch $B 2>&1
  done; done
  $P fig_ler.py --n 90 --cycles 6 --scheds "212:S (Bravyi),1307:S^-1,212+1307:alt S/S^-1" \
     --out figures/exp_90_three_ler.png --title "[[90,8,10]] BB code, 6 cycles, BP-OSD: S vs S^-1 vs alternating" 2>&1 | tee results/ler_90_table.md
done
grep -q "three-circuit logical error rate" RESULTS.md || { echo; echo "## [[90,8,10]] three-circuit logical error rate, 6 cycles ($(date -u +%F))"; echo; cat results/ler_90_table.md; echo; echo "Figure: figures/exp_90_three_ler.png"; } >> RESULTS.md
echo "== driver_004 end $(date)"
