#!/bin/bash
# Gross code [[144,12,12]]: (1) d_circ bounds for S, S^-1, alternating (4 cycles, 12 workers),
# (2) LER vs p at 12 cycles (8 workers: each decoder needs ~4.3 GB RAM).
cd /home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-001
# first to be killed if RAM ever saturates (protects SSH / Tailscale sessions); inherited by all workers
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
P=../venv/bin/python
echo "== driver_144 start $(date)"
# ---- stage 1: bounds ----
$P run_experiment1.py --n 144 --cycles 4 --bound-trials 4000 --bound-p 0.001 --skip-ler --nproc 12 \
   --out results/exp1_144_bounds.json 2>&1
$P - <<'PY'
import json, csv, os
from sched_ids import named
d = json.load(open('results/exp1_144_bounds.json')); ids = named()
lab = {'S': str(ids['S']), 'Sinv': str(ids['Sinv']), 'alt': f"{ids['S']}+{ids['Sinv']}"}
with open('results/bounds_exp1.csv', 'a', newline='') as f:
    w = csv.writer(f)
    for key, g in d['bounds'].items():
        cfg, basis = key.split('/')
        w.writerow([144, basis, d['args']['cycles'], d['args']['bound_p'], g['trials'], '0-11', lab[cfg], f"<= {g['min_weight']}", g['n_min_paths_found'], json.dumps(g['hist'])])
print('bounds appended to results/bounds_exp1.csv')
PY
echo "== stage 1 (bounds) finished $(date)"
# ---- stage 2: LER, 12 cycles, 8 workers ----
run() { $P run_ler.py --n 144 --cycles 12 --nproc 8 "$@" 2>&1; }
for s in S alt; do for b in Z X; do
  run --sched $s --basis $b --p 0.006 --target-fails 30 --max-shots 1000 --batch 200
  run --sched $s --basis $b --p 0.005 --target-fails 30 --max-shots 1500 --batch 300
  run --sched $s --basis $b --p 0.004 --target-fails 30 --max-shots 3000 --batch 500
done; done
for s in S alt; do for b in Z X; do
  run --sched $s --basis $b --p 0.003 --target-fails 30 --max-shots 8000 --batch 1000
done; done
for b in Z X; do
  run --sched Sinv --basis $b --p 0.006 --target-fails 30 --max-shots 1000 --batch 200
  run --sched Sinv --basis $b --p 0.005 --target-fails 30 --max-shots 1500 --batch 300
  run --sched Sinv --basis $b --p 0.004 --target-fails 30 --max-shots 3000 --batch 500
  run --sched Sinv --basis $b --p 0.003 --target-fails 30 --max-shots 8000 --batch 1000
done
$P status.py 2>&1
echo "== driver_144 end $(date)"
