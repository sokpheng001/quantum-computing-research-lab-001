#!/usr/bin/env bash
# Test 6, part 2: after run_t6.sh ends, SI1000 at p = 0.36 % (the p at which our SI1000 matches Google's
# released simulation, see t6_gap_check.py), then the report.  tmux new -d -s test6b "bash run_t6_part2.sh"
set -u
cd "$(dirname "$0")"
PY="$(cd ../.. && pwd)/.venv/bin/python"
ulimit -v 30000000
while tmux has-session -t =test6 2>/dev/null; do read -t 30 < /dev/zero 2>/dev/null || true; done
echo "[$(TZ=Asia/Seoul date '+%b %d, %I:%M %p KST')] part 2 start: SI1000 at p = 0.36 %" >> logs/t6.log
$PY -I t6_sim.py --models si1000@0.0036 --workers 3 > logs/sim_036.out 2>&1
# re-summarise all models into step23_sim.json (no new chunks to run)
$PY -I t6_sim.py --models ideal si1000 qvm si1000@0.0036 --workers 3 >> logs/sim_036.out 2>&1
$PY -I t6_report.py >> logs/report.out 2>&1
echo "[$(TZ=Asia/Seoul date '+%b %d, %I:%M %p KST')] part 2 finished" >> logs/t6.log
