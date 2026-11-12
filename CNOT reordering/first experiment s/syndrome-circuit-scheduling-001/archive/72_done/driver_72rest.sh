#!/bin/bash
# Remaining [[72]] work from TASK2 (tasks C, E, I) on 4 workers while [[144]] verification runs.
# Task H is intentionally NOT here (paused until verification steps 1-4 pass).  Resumable.
cd /home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-001
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
P=../venv/bin/python; NP=4
BEST=744; MED=131; WORST=52; FIN=497+303; PA=744+1517
run72() { $P run_ler.py --n 72 --cycles 6 --nproc $NP "$@" 2>&1; }
echo "== driver_72rest start $(date)"
echo "== task C: best $BEST / median $MED / worst $WORST"
for s in $BEST $MED $WORST; do for b in Z X; do
  run72 --sched $s --basis $b --p 0.006 --target-fails 50 --max-shots 2000  --batch 500
  run72 --sched $s --basis $b --p 0.004 --target-fails 50 --max-shots 6000  --batch 1000
  run72 --sched $s --basis $b --p 0.002 --target-fails 50 --max-shots 50000 --batch 5000
done; done
$P fig_ler.py --n 72 --cycles 6 --scheds "212:S (Bravyi),$BEST:best (id $BEST),$MED:median (id $MED),$WORST:worst (id $WORST)" \
   --out figures/single_schedules_ler.png --title "[[72,12,6]] single schedules, 6 cycles" 2>&1
echo "== task E: finalist pair $FIN, pair A $PA $(date)"
for b in Z X; do
  run72 --sched $FIN --basis $b --p 0.006 --target-fails 50 --max-shots 2000  --batch 500
  run72 --sched $FIN --basis $b --p 0.004 --target-fails 50 --max-shots 6000  --batch 1000
  run72 --sched $FIN --basis $b --p 0.002 --target-fails 50 --max-shots 50000 --batch 5000
  run72 --sched $PA  --basis $b --p 0.006 --target-fails 50 --max-shots 2000  --batch 500
  run72 --sched $PA  --basis $b --p 0.004 --target-fails 50 --max-shots 6000  --batch 1000
done
$P fig_ler.py --n 72 --cycles 6 --scheds "212:S (Bravyi),$BEST:best single,$FIN:finalist pair,$PA:best + its reverse,212+1307:S + S^-1" \
   --out figures/exp2_pairs_ler.png --title "[[72,12,6]] pairs vs best single, 6 cycles" 2>&1
echo "== task I: p=0.002 top-up for S, S^-1, alt $(date)"
for s in S Sinv alt; do for b in Z X; do
  run72 --sched $s --basis $b --p 0.002 --target-fails 50 --max-shots 60000 --batch 5000
done; done
$P status.py 2>&1
echo "== driver_72rest end $(date)"
