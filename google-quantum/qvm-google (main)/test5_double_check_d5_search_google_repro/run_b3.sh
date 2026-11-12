#!/bin/bash
# Test 5, Part B, B3 (tmux "test5"): independent real-T sampling check (Clifft) of the d = 5 circuits.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
.venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b3_clifft_check.py" --threads 11 --mfc 5 \
  > "qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b3_clifft.log" 2>&1
echo "exit $?" >> "qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b3_clifft.log"
