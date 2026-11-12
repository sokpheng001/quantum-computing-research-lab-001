#!/bin/bash
# Test 5, Part B, B4 (tmux "test5"): d = 5 circuits under SI1000 / Willow spec / Willow calibration noise.
# Nov 5: 11 workers ran the machine out of memory at 10:15 am KST. Then 3 workers capped at 10 GB each; at
# 2:12 pm many circuits hit the cap because pool workers grew across tasks -> now a fresh process per circuit
# (maxtasksperchild=1) and capped circuits are re-run (--retry-errors).
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
ulimit -v 12000000
.venv/bin/python "qvm-google (main)/test5_double_check_d5_search_google_repro/b4_real_noise.py" --mfc 4 --mfc2 5 --threads 3 \
  --retry-errors >> "qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b4_real_noise.log" 2>&1
echo "exit $?" >> "qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b4_real_noise.log"
