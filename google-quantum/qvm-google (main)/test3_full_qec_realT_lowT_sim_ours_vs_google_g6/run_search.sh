#!/bin/bash
# Test 3 overnight search (tmux "grafting"). Stage A: the cs02 search size on G6's data.
# Stage B (only if A finds nothing): one step larger. Each stage writes its own report.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
T="qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6"
PY=.venv/bin/python
echo "stage A start $(TZ=Asia/Seoul date '+%b %d %I:%M %p KST')" > "$T/logs/run_search.status"
$PY "$T/search_g6.py" --dmax 5 --nmax 13 --umax 1 --hours 3 --out "$T/results/g6_search" \
    --report "$T/RESULTS_search.md" > "$T/logs/search_g6.log" 2>&1
N=$($PY -c "import json;print(json.load(open('$T/results/g6_search/state.json'))['n_success'])")
echo "stage A done $(TZ=Asia/Seoul date '+%b %d %I:%M %p KST'), successes $N" >> "$T/logs/run_search.status"
if [ "$N" = "0" ]; then
  $PY "$T/search_g6.py" --dmax 6 --nmax 14 --umax 1 --hours 6 --out "$T/results/g6_search_d6n14" \
      --report "$T/RESULTS_search_d6n14.md" > "$T/logs/search_g6_d6n14.log" 2>&1
  echo "stage B done $(TZ=Asia/Seoul date '+%b %d %I:%M %p KST')" >> "$T/logs/run_search.status"
fi
echo DONE >> "$T/logs/run_search.status"
