#!/bin/bash
# Verification STEP 2 on [[144]] (8 workers).  Resumable: relaunch with ./launch.sh driver_strong.sh
cd /home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-001
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
echo "== driver_strong start $(date)"; free -g | sed -n 2p
../venv/bin/python strong_search.py --nproc 8 --seeds 5 --chunk 200 --max-chunks 60 2>&1
../venv/bin/python strong_summary.py 2>&1
echo "== driver_strong end $(date)"
