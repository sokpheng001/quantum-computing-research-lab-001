#!/bin/bash
# Launch a driver safely:  ./launch.sh driver_144.sh
#  - detached from the terminal / VS Code (survives logout)
#  - hard RAM ceiling via a systemd user scope (MemoryMax), no swap
#  - driver marks itself first-to-kill (oom_score_adj 1000)
# Log: results/<driver>.log      Stop: ./launch.sh stop      Status: ./launch.sh status
cd /home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-004
CAP=${CAP:-38G}
if [ "$1" = "stop" ]; then
  # stop every launched scope (driver + all its workers) as a unit
  for u in $(systemctl --user list-units --type=scope --no-legend | awk '{print $1}' | grep '^qec004-'); do
    systemctl --user stop "$u"; echo "stopped $u"
    j=$(echo "$u" | sed -E 's/^qec[0-9]*-//; s/-[0-9]{6}\.scope$//')      # unit name -> driver name
    touch "results/.no_resume_$j"                                            # stopped on purpose: never auto-resume
    echo "== stopped by user (./launch.sh stop) $(date)" >> "results/$j.log"
  done
  sleep 2; pgrep -fa 'syndrome-circuit-scheduling-004' | grep -v pgrep || echo "all stopped"; exit 0
fi
if [ "$1" = "status" ]; then
  U=$(systemctl --user list-units --type=scope --no-legend | awk '{print $1}' | grep '^qec004-'); [ -z "$U" ] && echo "nothing running"
  for u in $U; do echo "$u  memory $(systemctl --user show $u -p MemoryCurrent --value | numfmt --to=iec) of cap $(systemctl --user show $u -p MemoryMax --value | numfmt --to=iec)"; done; exit 0
fi
[ -z "$1" ] && { echo "usage: ./launch.sh <driver.sh> | status | stop"; ls driver_*.sh 2>/dev/null; exit 1; }
D=$1; LOG=results/${D%.sh}.log
rm -f "results/.no_resume_${D%.sh}"      # started on purpose: protected by auto-resume again
loginctl enable-linger "$USER" 2>/dev/null || true
setsid nohup systemd-run --user --scope -q --unit=qec004-${D%.sh}-$(date +%H%M%S) -p MemoryMax=$CAP -p MemorySwapMax=0 bash "$D" >> "$LOG" 2>&1 < /dev/null &
sleep 3; echo "launched $D under a $CAP RAM cap; log: $LOG"; pgrep -fa "bash $D" | grep -v pgrep
