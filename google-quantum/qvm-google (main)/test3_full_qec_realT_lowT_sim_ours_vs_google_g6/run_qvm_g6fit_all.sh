#!/bin/bash
# Test 3 step 2b (tmux "qvmg6all"): QVM E1-E4 (real T, Willow noise) of the other 7 distinct
# G6-fit circuits (#2 and #4 done by run_qvm_g6fit.sh), report updated after each.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
PY=.venv/bin/python; T="qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6"; L="$T/logs"
log() { echo "[$(TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST')] $*" | tee -a "$L/run_qvm_g6fit_all.log"; }
log start
for n in 00 01 03 05 06 07 09; do
  D="g6fit$n=$T/results/g6_search_d6n14/success$n"
  ok=1
  for e in e1 e2 e3; do
    $PY "$T/qvm_g6fit.py" $e --design "$D" > "$L/${e}_g6fit$n.log" 2>&1 || { log "FAILED $e g6fit$n"; ok=0; break; }
  done
  [ $ok = 1 ] && { $PY "$T/qvm_g6fit.py" e4 --design "$D" --shots 4000000 > "$L/e4_g6fit$n.log" 2>&1 || log "FAILED e4 g6fit$n"; }
  log "g6fit$n done"
  $PY "$T/report_qvm_g6fit.py" >> "$L/run_qvm_g6fit_all.log" 2>&1
done
log DONE
