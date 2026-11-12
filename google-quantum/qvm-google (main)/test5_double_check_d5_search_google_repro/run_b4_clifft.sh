#!/bin/bash
# Test 5, B4: Clifft cross-check (SI1000 p = 0.5 %), alone; 3 threads, 30 GB cap (8 GB ran out of memory in the exact count, Nov 5).
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
ulimit -v 30000000
.venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b4_clifft_check.py" --threads 3 \
  >> "qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b4_clifft.log" 2>&1
echo "exit $?" >> "qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b4_clifft.log"
