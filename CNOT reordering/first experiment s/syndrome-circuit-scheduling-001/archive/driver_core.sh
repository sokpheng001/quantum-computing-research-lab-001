#!/bin/bash
# TASK2.md (TASKS_core) driver.  Stage A here; later stages in core_after_A.sh
# (read only when stage A ends, so it can be written while A runs).
cd /home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-001
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
P=../venv/bin/python
echo "== driver_core start $(date)"
echo "== task A: bounds + n_min + fault sets, [[72]], 4 cycles, Z-first ids 0-935, both bases, 100 trials, 12 workers"
$P bounds_all.py --n 72 --cycles 4 --p 0.001 --trials 100 --nproc 12 --ids 0-935 2>&1
echo "== task A finished $(date)"
bash core_after_A.sh 2>&1
echo "== driver_core end $(date)"
