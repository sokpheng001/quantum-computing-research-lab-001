#!/bin/bash
# Test 7 (tmux "test7"): d = 3 benchmarks A-C. Small circuits; 4 workers, 6 GB cap each (Nov 5 OOM lesson).
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
ulimit -v 6000000
.venv/bin/python "qvm-google (main)/test7_d3_cs02_vs_google_noise_sweep_chip_positions/t7_d3_benchmarks.py" --workers 4 \
  >> "qvm-google (main)/test7_d3_cs02_vs_google_noise_sweep_chip_positions/logs/t7.log" 2>&1
echo "exit $?" >> "qvm-google (main)/test7_d3_cs02_vs_google_noise_sweep_chip_positions/logs/t7.log"
