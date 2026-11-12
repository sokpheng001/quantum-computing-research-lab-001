#!/bin/bash
# [[144]] three-circuit experiment: S, S^-1, alt S/S^-1.  <= 8 workers.  Resumable:
# relaunch with ./launch.sh driver_144three.sh (finished chunks / batches are skipped).
cd /home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-001
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
P=../venv/bin/python; NP=8
echo "== driver_144three start $(date)"; free -g | sed -n 2p
echo "== bounds: multi-seed search, 5 seeds x 12 chunks x 200 trials (2400/seed, 12000 per circuit and basis)"
$P strong_search.py --nproc $NP --seeds 5 --chunk 200 --max-chunks 12 2>&1
echo "== step 3: exact mapping into the alternating circuit $(date)"
for single in 212 1307; do for b in Z X; do
  W=$($P - <<PY
import csv
print(min(int(r['min_weight']) for r in csv.DictReader(open('results/strong_144.csv')) if r['circuit']=='$single' and r['basis']=='$b'))
PY
)
  for w in $(seq $W 11); do $P step3_exact.py --single $single --alt 212+1307 --basis $b --weight $w 2>&1; done
done; done
echo "== bounds report (written to RESULTS.md before any LER run) $(date)"
$P bounds_report.py 2>&1
echo "== LER: S, S^-1, alt, both bases, 6 cycles, >= 30 failures, raw samples $(date)"
free -g | sed -n 2p
run() { $P run_ler.py --n 144 --cycles 6 --nproc $NP --target-fails 30 "$@" 2>&1; }
for s in S Sinv alt; do for b in Z X; do run --sched $s --basis $b --p 0.005 --max-shots 8000  --batch 500;  done; done
for s in S Sinv alt; do for b in Z X; do run --sched $s --basis $b --p 0.004 --max-shots 30000 --batch 1000; done; done
$P fig_ler.py --n 144 --cycles 6 --scheds "212:S (Bravyi),1307:S^-1,212+1307:alt S/S^-1" \
   --out figures/exp_144_three_ler.png --title "[[144,12,12]] gross code, 6 cycles: S vs S^-1 vs alternating" 2>&1
awk -F, 'NR==1 || $1==144' results/ler.csv > results/exp_144.csv
echo "== driver_144three end $(date)"
