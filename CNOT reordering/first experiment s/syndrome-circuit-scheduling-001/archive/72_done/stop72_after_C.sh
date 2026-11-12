#!/bin/bash
# Watcher: stop the [[72]] job as soon as task C (incl. its figure) is done, i.e. when the
# driver prints the task E header.  Tasks E and I are skipped by the user's change of plan.
LOG=/home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-001/results/driver_72rest.log
until grep -q "== task E" "$LOG"; do sleep 20; done
for u in $(systemctl --user list-units --type=scope --no-legend | awk '{print $1}' | grep '^qec-driver_72rest'); do systemctl --user stop "$u"; done
echo "== stopped after task C by user's change of plan (tasks E and I skipped) $(date)" >> "$LOG"
