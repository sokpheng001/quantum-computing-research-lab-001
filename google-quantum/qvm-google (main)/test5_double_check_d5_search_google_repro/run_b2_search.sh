#!/bin/bash
# Test 5, Part B, B2 (tmux "test5"): randomised d = 5 search, fault distance >= 4, nearest-neighbour, on Willow.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
.venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b2_search_d5.py" --workers 11 --hours 8 \
  > "qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b2_search.log" 2>&1
echo "exit $?" >> "qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b2_search.log"
