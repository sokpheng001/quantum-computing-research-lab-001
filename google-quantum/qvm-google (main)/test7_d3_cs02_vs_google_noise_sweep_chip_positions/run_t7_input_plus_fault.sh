#!/bin/bash
# Test 7 part F (input error + one check fault). tmux "t7inpf". Output: RESULTS_input_plus_fault.md, logs/input_plus_fault.log
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
ulimit -v 4000000
D="qvm-google (main)/test7_d3_cs02_vs_google_noise_sweep_chip_positions"
.venv/bin/python -u "$D/t7_input_plus_fault.py" --workers 3 > "$D/logs/input_plus_fault.log" 2>&1
echo "[$(TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST')] finished, exit $?" >> "$D/logs/input_plus_fault.log"
