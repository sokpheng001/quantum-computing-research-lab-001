#!/bin/bash
# QVM runs for the cs02 figure: G4 G6-style E3 + E4 (4 M shots), cs02 E4 extended to 8 M shots,
# then the figure and RESULTS.md. Run from google-quantum/ in tmux "qvmcs02".
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
PY=.venv/bin/python; Q="qvm-google (main)/test2_cs02_continuing_data_vs_google"; L="$Q/logs"
set -o pipefail
echo "[$(TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST')] start" | tee "$L/run_cs02_qvm.log"
$PY "$Q/run_qvm.py" e3 --design G4_G6style=results/g4/G4-G6style 2>&1 | tee "$L/e3_G4_G6style.log" || exit 1
$PY "$Q/run_qvm.py" e4 --design G4_G6style=results/g4/G4-G6style --shots 4000000 2>&1 | tee "$L/e4_G4_G6style.log" || exit 1
$PY "$Q/run_qvm.py" e4 --design cont_success02=results/continuing/success02 --shots 8000000 2>&1 | tee "$L/e4_continuing_8M.log" || exit 1
$PY "$Q/plots.py" 2>&1 | tee -a "$L/run_cs02_qvm.log" || exit 1
$PY "$Q/report.py" 2>&1 | tee -a "$L/run_cs02_qvm.log"
echo "[$(TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST')] done" | tee -a "$L/run_cs02_qvm.log"
