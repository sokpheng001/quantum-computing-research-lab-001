#!/bin/bash
# Method 4 driver.  Stages are read from stages.txt one at a time ("<stage> <n>" per line), so new parts can be
# appended while it runs; a line "END" finishes the driver.  Finished stages are skipped (their json exists).
# Exit code 3 from nu.py = a PASS condition failed: stop and report.  Start only with ./launch.sh driver_nu.sh
cd "/home/ubuntu/quantum001-PKNU-Lab/CNOT reordering/non-uniform schedule/ours" || exit 1
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
unset NU_RES
P=../../../venv/bin/python
echo "== driver_nu start $(date)"
i=0
while true; do
  line=$(sed -n "$((i+1))p" ../stages.txt)
  if [ -z "$line" ]; then sleep 60; continue; fi                 # waiting for the next part to be added
  [ "$line" = "END" ] && break
  set -- $line
  if [ -f "../results_nonuniform/$2/$1.json" ] && ! grep -q '"PASS": false' "../results_nonuniform/$2/$1.json"; then i=$((i+1)); continue; fi
  $P nu.py --stage "$1" --n "$2"; rc=$?
  [ -f report_nu.py ] && $P report_nu.py >/dev/null 2>&1
  if [ $rc -eq 3 ]; then echo "== STOPPED at $line (PASS condition failed)"; echo "== driver_nu end (stopped) $(date)"; exit 0; fi
  if [ $rc -ne 0 ]; then echo "== ERROR rc=$rc at $line $(date)"; exit 1; fi
  i=$((i+1))
done
[ -f report_nu.py ] && $P report_nu.py
echo "== driver_nu end $(date)"
