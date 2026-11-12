#!/usr/bin/env bash
# Runs Steps 3-6 unattended (meant for a detached tmux session):
#   validation (capped at 6 h, checkpointed) -> finalize -> memory sweep -> pipeline -> figures -> RESULTS.
# Every stage runs even if an earlier one fails; failures are logged in logs/timing.txt.
cd "$(dirname "$0")"
export PATH="/home/ubuntu/quantum001-PKNU-Lab/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 TZ=Asia/Seoul
mkdir -p logs
stamp() { echo "$(date '+%Y-%m-%d %I:%M:%S %p KST')  $*" | tee -a logs/timing.txt; }

stage() {  # stage <name> <command...>
  local name=$1; shift
  stamp "start  $name"
  "$@" > "logs/$name.log" 2>&1
  local rc=$?
  if [ $rc -eq 0 ]; then stamp "done   $name"
  elif [ $rc -eq 124 ]; then stamp "CAPPED $name (6 h limit reached; results so far are kept)"
  else stamp "FAILED $name (exit $rc) - see logs/$name.log"; fi
}

stamp "run_all.sh started"
stage validation timeout --signal=INT --kill-after=120 6h python run_validation.py collect
stage finalize python run_validation.py finalize
stage memory python run_memory.py
python full_stack_sim.py > logs/pipeline_output.txt 2>&1 && stamp "done   pipeline" || stamp "FAILED pipeline - see logs/pipeline_output.txt"
stage plots python plot_results.py
stage results python write_results.py
stamp "run_all.sh finished"
touch logs/DONE
