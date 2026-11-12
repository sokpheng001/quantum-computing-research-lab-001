#!/bin/bash
# Test 3 step 2 (tmux "qvmg6fit"): QVM E1-E4 (real T, Willow noise) of G6-fit #4 and #2,
# then RESULTS_qvm_g6fit.md + figures/qvm_g6fit_vs_google.png.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
PY=.venv/bin/python; T="qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6"; L="$T/logs"
set -o pipefail
log() { echo "[$(TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST')] $*" | tee -a "$L/run_qvm_g6fit.log"; }
log start
for n in 04 02; do
  D="g6fit$n=$T/results/g6_search_d6n14/success$n"
  for e in e1 e2 e3; do
    $PY "$T/qvm_g6fit.py" $e --design "$D" > "$L/${e}_g6fit$n.log" 2>&1 || { log "FAILED $e g6fit$n"; exit 1; }
    log "$e g6fit$n done"
  done
  $PY "$T/qvm_g6fit.py" e4 --design "$D" --shots 4000000 > "$L/e4_g6fit$n.log" 2>&1 || { log "FAILED e4 g6fit$n"; exit 1; }
  log "e4 g6fit$n done"
  $PY "$T/report_qvm_g6fit.py" >> "$L/run_qvm_g6fit.log" 2>&1
done
log DONE
