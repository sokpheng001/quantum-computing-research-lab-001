#!/bin/bash
# Method 2: path-targeted partner search (docs/task.md).  [[72]] (control) -> [[90]] -> [[108]].
# Every stage is resumable; stages already finished are skipped.  Exit code 3 from partner.py = a PASS
# condition failed: the driver stops, rebuilds RESULTS_partner.md and writes its end marker.
# Start only with:  ./launch.sh driver_partner.sh      ([[144]] is NOT run on this server.)
cd "/home/ubuntu/quantum001-PKNU-Lab/method2 for schedule reordering" || exit 1
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
P=../venv/bin/python
unset PARTNER_RES PARTNER_FIG PARTNER_MD PARTNER_CHUNK     # test-mode variables must never reach the real run
echo "== driver_partner start $(date)"
step() {   # step <n> <stage>
  $P partner.py --n "$1" --stage "$2" --nproc 12; rc=$?
  $P report.py >/dev/null 2>&1; $P figs.py >/dev/null 2>&1
  if [ $rc -eq 3 ]; then echo "== STOPPED at [[$1]] stage $2 (PASS condition failed), see RESULTS_partner.md"; echo "== driver_partner end (stopped) $(date)"; exit 0; fi
  if [ $rc -ne 0 ]; then echo "== ERROR rc=$rc at [[$1]] stage $2 $(date)"; exit 1; fi
}
for s in 0 1 2 3 4 control; do step 72 $s; done
for n in 90 108; do for s in 0 1 2 3 4 5; do step $n $s; done; done
$P report.py; $P figs.py
echo "== driver_partner end $(date)"
