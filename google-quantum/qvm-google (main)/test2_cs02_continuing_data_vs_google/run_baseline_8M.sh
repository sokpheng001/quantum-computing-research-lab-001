#!/bin/bash
# Same number of shots for every circuit as cs02 (8,000,000): extend Google's G4 (test 1) and
# G4 G6-style (test 2) from 4 M to 8 M shots. Resumable chunks: the first 4 M are reused, only
# the new 800 chunks per circuit are simulated (seeds CRC32("name:chunk")). Then the test 2
# figure + RESULTS.md and MASTER_RESULTS.md are regenerated; then the 9 G6-fit circuits to 8 M too. tmux "baseline8m".
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
PY=.venv/bin/python; Q="qvm-google (main)"; T2="$Q/test2_cs02_continuing_data_vs_google"; L="$T2/logs"
log() { echo "[$(TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST')] $*" | tee -a "$L/run_baseline_8M.log"; }
log start
$PY "$T2/run_qvm.py" e4 --design G4_G6style=results/g4/G4-G6style --shots 8000000 > "$L/e4_G4_G6style_8M.log" 2>&1 || { log "FAILED G4_G6style"; exit 1; }
log "G4 G6-style 8M done"
$PY "$Q/qvm_willow.py" e4 --chunk 5000 --shots-json '{"success03": 8000000, "success04": 2000000, "success00": 2000000, "G4": 8000000, "d3a6": 2000000}' > "$L/e4_G4_8M.log" 2>&1 || { log "FAILED G4"; exit 1; }
log "G4 8M done"
# our G6-fit circuits to the same 8 M shots: #0 (chosen) first, then the other 8
T3="$Q/test3_full_qec_realT_lowT_sim_ours_vs_google_g6"
for n in 00 02 05 04 03 01 06 07 09; do
  $PY "$T3/qvm_g6fit.py" e4 --design "g6fit$n=$T3/results/g6_search_d6n14/success$n" --shots 8000000 \
      > "$T3/logs/e4_g6fit${n}_8M.log" 2>&1 || log "FAILED g6fit$n"
  log "g6fit$n 8M done"
  $PY "$T3/report_qvm_g6fit.py" >> "$L/run_baseline_8M.log" 2>&1
  $PY "$Q/master_results.py" >> "$L/run_baseline_8M.log" 2>&1
done
$PY "$T2/plots.py" >> "$L/run_baseline_8M.log" 2>&1
$PY "$T2/report.py" >> "$L/run_baseline_8M.log" 2>&1
$PY "$Q/master_results.py" >> "$L/run_baseline_8M.log" 2>&1
log DONE
