#!/bin/bash
# Test 7 part E (mechanism proof). tmux "t7mech". Output: logs/mechanism.log, results/mechanism/mechanism.json
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
ulimit -v 6000000
D="qvm-google (main)/test7_d3_cs02_vs_google_noise_sweep_chip_positions"
.venv/bin/python -u "$D/t7_mechanism.py" > "$D/logs/mechanism.log" 2>&1
echo "[$(TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST')] mechanism finished, exit $?" >> "$D/logs/mechanism.log"
