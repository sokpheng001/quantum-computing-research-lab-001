#!/bin/bash
# Method 3, Track B (docs/task.md): one-cycle distance ranking, Bravyi setup.  [[72]] control -> [[90]] -> [[108]].
# Resumable: finished stages are skipped, finished work units are never repeated.  Exit code 3 from m3.py =
# a PASS condition failed: the driver stops, rebuilds RESULTS_method3.md and writes its end marker.
# Start only with ./launch.sh driver_method3.sh
cd "/home/ubuntu/quantum001-PKNU-Lab/bb code/CNOT reordering/bb-code-reordering-cnot-running/ours" || exit 1
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
unset M3_TEST M3_RES M3_FIG M3_MD                       # test-mode variables must never reach the real run
P=/home/ubuntu/quantum001-PKNU-Lab/venv/bin/python
echo "== driver_method3 start $(date)"
step() {
  $P m3.py --n "$1" --stage "$2" --nproc 12; rc=$?
  $P report_m3.py >/dev/null 2>&1
  if [ $rc -eq 3 ]; then echo "== STOPPED at [[$1]] $2 (PASS condition failed), see RESULTS_method3.md"; echo "== driver_method3 end (stopped) $(date)"; exit 0; fi
  if [ $rc -ne 0 ]; then echo "== ERROR rc=$rc at [[$1]] $2 $(date)"; exit 1; fi
}
step 72 b0; step 72 screen          # B0 + B1 (control: STOP if any schedule has d1 > 6)
for n in 90 108; do step $n b0; step $n screen; step $n b3; done
$P report_m3.py
echo "== driver_method3 end $(date)"
