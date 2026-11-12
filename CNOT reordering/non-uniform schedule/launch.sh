#!/bin/bash
# Launch a driver safely:  ./launch.sh driver_method3.sh
#  - detached from the terminal / VS Code (survives logout), systemd user scope with a RAM cap, no swap
#  - driver marks itself first-to-kill (oom_score_adj 1000)
# Log: results_nonuniform/<driver>.log      Stop: ./launch.sh stop      Status: ./launch.sh status
cd "/home/ubuntu/quantum001-PKNU-Lab/CNOT reordering/non-uniform schedule" || exit 1
CAP=${CAP:-16G}; PFX=qecm4-
if [ "$1" = "stop" ]; then
  for u in $(systemctl --user list-units --type=scope --no-legend | awk '{print $1}' | grep "^$PFX"); do
    systemctl --user stop "$u"; echo "stopped $u"
    j=$(echo "$u" | sed -E "s/^$PFX//; s/-[0-9]{6}\.scope$//")
    touch "results_nonuniform/.no_resume_$j"
    echo "== stopped by user (./launch.sh stop) $(date)" >> "results_nonuniform/$j.log"
  done
  sleep 2; pgrep -fa 'nu.py' | grep -v pgrep || echo "all stopped"; exit 0
fi
if [ "$1" = "status" ]; then
  U=$(systemctl --user list-units --type=scope --no-legend | awk '{print $1}' | grep "^$PFX"); [ -z "$U" ] && echo "nothing running"
  for u in $U; do echo "$u  memory $(systemctl --user show $u -p MemoryCurrent --value | numfmt --to=iec) of cap $(systemctl --user show $u -p MemoryMax --value | numfmt --to=iec)"; done
  tail -3 results_nonuniform/driver_nu.log 2>/dev/null; exit 0
fi
[ -z "$1" ] && { echo "usage: ./launch.sh <driver.sh> | status | stop"; ls driver_*.sh; exit 1; }
D=$1; LOG="results_nonuniform/${D%.sh}.log"; mkdir -p results_nonuniform
rm -f "results_nonuniform/.no_resume_${D%.sh}"
loginctl enable-linger "$USER" 2>/dev/null || true
setsid nohup systemd-run --user --scope -q --unit=$PFX${D%.sh}-$(date +%H%M%S) -p MemoryMax=$CAP -p MemorySwapMax=0 bash "$D" >> "$LOG" 2>&1 < /dev/null &
sleep 3; echo "launched $D under a $CAP RAM cap; log: $LOG"; pgrep -fa "bash $D" | grep -v pgrep
