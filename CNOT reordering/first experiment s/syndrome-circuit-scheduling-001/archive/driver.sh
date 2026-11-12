#!/bin/bash
# Phase 1.2 + Phase 2 LER points, then PASS check, then Phase 3.1/3.2.
cd /home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-001
# first to be killed if RAM ever saturates (protects SSH / Tailscale sessions); inherited by all workers
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
P=../venv/bin/python
run() { $P run_ler.py "$@" 2>&1; }
echo "== driver start $(date)"
# Phase 1.2 (S only) high-p points first
for b in Z X; do run --sched S --basis $b --p 0.005 --target-fails 50 --max-shots 3000 --batch 500; done
for b in Z X; do run --sched S --basis $b --p 0.003 --target-fails 50 --max-shots 12000 --batch 2000; done
# Phase 2: p = 0.008 for all six
for s in S Sinv alt; do for b in Z X; do run --sched $s --basis $b --p 0.008 --target-fails 30 --max-shots 2000 --batch 500; done; done
# Phase 1.2 / Phase 2: p = 0.002 (needs ~30k shots per config)
for b in Z X; do run --sched S --basis $b --p 0.002 --target-fails 50 --max-shots 40000 --batch 4000; done
for s in Sinv alt; do for b in Z X; do run --sched $s --basis $b --p 0.002 --target-fails 30 --max-shots 40000 --batch 4000; done; done
# Phase 1.2: p = 0.001, capped (expected LER ~4e-4 per 6 cycles -> ~8 failures in 20k)
for b in Z X; do run --sched S --basis $b --p 0.001 --target-fails 50 --max-shots 20000 --batch 5000; done
echo "== LER jobs finished $(date)"
$P fig_bravyi.py 2>&1
if $P phase2_check.py 2>&1; then
  echo "== Phase 2 PASS recorded; starting Phase 3.1 $(date)"
  $P bounds_all.py --cycles 4 --trials 60 2>&1
else
  echo "== Phase 2 PASS condition NOT met; Phase 3 not started $(date)"
fi
echo "== driver end $(date)"
