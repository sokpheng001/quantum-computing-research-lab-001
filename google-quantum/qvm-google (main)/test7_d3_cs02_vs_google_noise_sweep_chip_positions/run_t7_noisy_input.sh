#!/bin/bash
# Test 7 part D: noisy input to the double check, Google G4 G6-style vs cs02. tmux "t7noisy".
# P1 Bloch circle (QVM, 24 angles x X/Y, 20k shots each), P2 T angle QVM 8M, P3 T angle QVM stronger input 4M,
# P4 T angle SI1000 p = 0.36 % 4M. 3 workers, 4 GB virtual memory per process. Resumable (chunks).
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
ulimit -v 4000000
PY=.venv/bin/python
D="qvm-google (main)/test7_d3_cs02_vs_google_noise_sweep_chip_positions"
L="$D/logs/noisy_input.log"
log() { echo "[$(TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST')] $*" | tee -a "$L"; }
log "start"
for P in P1 P2 P3 P4; do
  $PY -u "$D/t7_noisy_input.py" run --part $P --workers 3 >> "$D/logs/noisy_input_$P.out" 2>&1 || { log "FAILED $P"; exit 1; }
  $PY -I "$D/t7_noisy_input_report.py" > /dev/null 2>> "$L" || log "report failed after $P"
  log "$P done, report updated"
done
log "DONE"
