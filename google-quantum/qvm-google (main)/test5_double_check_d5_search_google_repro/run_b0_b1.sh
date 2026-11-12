#!/bin/bash
# Test 5, Part B, B0-B1 (tmux "test5"): d = 5 baselines up to 4 faults + Willow placements.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
.venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b0_b1_d5_baselines.py" --max-faults 4 \
  > "qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b0_b1.log" 2>&1
echo "exit $?" >> "qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b0_b1.log"
