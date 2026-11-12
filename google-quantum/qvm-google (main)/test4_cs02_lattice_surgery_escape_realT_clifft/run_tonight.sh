#!/bin/bash
# Test 4 tonight (tmux "test4"): A2 analysis + A1 Clifft-vs-qsim validation, each writes its own report.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
PY=.venv/bin/python; T="qvm-google (main)/test4_cs02_lattice_surgery_escape_realT_clifft"; L="$T/logs"
log() { echo "[$(TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST')] $*" | tee -a "$L/run_tonight.log"; }
log start
$PY "$T/analyze_hirano_escape.py" >> "$L/run_tonight.log" 2>&1 && log "A2 done"
$PY "$T/validate_clifft.py" --qsim-shots 4000000 --clifft-shots 200000000 > "$L/validate_clifft.log" 2>&1 || { log "A1 FAILED"; exit 1; }
log "A1 done"
log DONE
