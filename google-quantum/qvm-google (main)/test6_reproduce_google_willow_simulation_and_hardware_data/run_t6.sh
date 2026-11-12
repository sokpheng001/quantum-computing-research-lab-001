#!/usr/bin/env bash
# Test 6 (steps 1-4) in the background: tmux new -d -s test6 "bash run_t6.sh"
# Step 1 (data, 1 process) runs beside steps 2-3 (simulation, 3 workers); memory capped.
set -u
cd "$(dirname "$0")"
PY="$(cd ../.. && pwd)/.venv/bin/python"   # google-quantum/.venv, independent of the parent folder name
ulimit -v 30000000   # 30 GB virtual memory cap for this job
echo "[$(TZ=Asia/Seoul date '+%b %d, %I:%M %p KST')] run_t6.sh start" >> logs/t6.log
$PY -I t6_step4_circuits.py >> logs/step4.out 2>&1
$PY -I t6_step1_data.py > logs/step1.out 2>&1 &
S1=$!
$PY -I t6_sim.py --workers 3 > logs/sim.out 2>&1
wait $S1
$PY -I t6_report.py >> logs/report.out 2>&1
echo "[$(TZ=Asia/Seoul date '+%b %d, %I:%M %p KST')] run_t6.sh finished" >> logs/t6.log
