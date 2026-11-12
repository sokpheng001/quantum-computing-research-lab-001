#!/bin/bash
# Extra stage (user request 2026-10-18, not in task.md): LER and circuit-level distance for S, alt[S,S^-1], A*,
# alt[A*,A*^-1].  Order (user asked for the LER first):
#   1. [[90]] LER now, with the main run (the [[108]] d1 screen) PAUSED (SIGSTOP) so the LER gets all cores;
#      the main run is resumed (SIGCONT) as soon as this step ends, also on error (trap).
#   2. [[90]] circuit-level distance (shares the CPUs with the main run).
#   3. [[108]] LER + distance after the main run has finished.
# Start only with ./launch.sh driver_method3_extra.sh   (resumable; finished work is never repeated)
cd "/home/ubuntu/quantum001-PKNU-Lab/bb code/CNOT reordering/bb-code-reordering-cnot-running/ours" || exit 1
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
unset M3_TEST M3_RES M3_FIG M3_MD
P=/home/ubuntu/quantum001-PKNU-Lab/venv/bin/python
MAIN=$(systemctl --user list-units --type=scope --no-legend | awk '{print $1}' | grep '^qecm3-driver_method3-[0-9]')
resume_main() { [ -n "$MAIN" ] && systemctl --user kill -s SIGCONT "$MAIN" 2>/dev/null && echo "== main run resumed $(date)"; MAIN=; }
trap resume_main EXIT
echo "== driver_method3_extra start $(date)"
step() {  # step <n> <stage>
  $P m3.py --n $1 --stage $2 --nproc 12; rc=$?
  $P report_m3.py >/dev/null 2>&1
  if [ $rc -ne 0 ]; then echo "== ERROR rc=$rc at [[$1]] $2 $(date)"; exit 1; fi
}
grep -q "\[\[90\]\] screen done" ../results_method3/driver_method3.log || { echo "== [[90]] screen not finished"; exit 1; }
if [ ! -f ../results_method3/90/ler.json ] && [ -n "$MAIN" ]; then systemctl --user kill -s SIGSTOP "$MAIN" && echo "== main run paused for the [[90]] LER $(date)"; fi
step 90 ler
resume_main
step 90 extra
until grep -q "driver_method3 end" ../results_method3/driver_method3.log 2>/dev/null; do sleep 300; done
if grep -q "driver_method3 end (stopped)" ../results_method3/driver_method3.log; then echo "== main run stopped on a PASS failure: [[108]] extra not run"; echo "== driver_method3_extra end (partial) $(date)"; exit 0; fi
step 108 ler
step 108 extra
$P report_m3.py
echo "== driver_method3_extra end $(date)"
