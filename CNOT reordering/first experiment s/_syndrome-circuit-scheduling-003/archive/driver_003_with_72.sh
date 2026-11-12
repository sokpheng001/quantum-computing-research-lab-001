#!/bin/bash
# Folder 003 = the 001 experiments with the logical-error-rate decoder changed to BP-OSD-0.
# Distance bounds are decoder-independent and copied from 001 (not recomputed).
# Stage 1 [[72]] now (2 workers); stage 2 [[144]] only after the 001 gross-code job has
# finished (never two [[144]] jobs at once, 8 workers).  Resumable: ./launch.sh driver_003.sh
cd /home/ubuntu/quantum001-PKNU-Lab/_syndrome-circuit-scheduling-003
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
P=../venv/bin/python
np_free() { local busy n; busy=$(ps -eo pcpu=,args= | awk '$1>50 && /python/' | wc -l); n=$((12 - busy)); [ $n -lt 2 ] && n=2; [ $n -gt 8 ] && n=8; echo $n; }
echo "== driver_003 start $(date)  decoder: $($P -c 'import dcirc; print(dcirc.LER_OSD_METHOD, dcirc.LER_OSD_ORDER)')"
r72()  { $P run_ler.py --n 72 --cycles 6 --nproc $(np_free) --target-fails 50 "$@" 2>&1; }
echo "== stage 1a: [[72]] S, S^-1, alt and best/median/worst at p = 0.006, 0.004 $(date)"
for p in 0.006 0.004; do
  [ "$p" = 0.006 ] && M=2000 B=500 || M=8000 B=1000
  for s in S Sinv alt 744 131 52; do for b in Z X; do r72 --sched $s --basis $b --p $p --max-shots $M --batch $B; done; done
done
figs72() {
  $P fig_ler.py --n 72 --cycles 6 --scheds "212:S (Bravyi),1307:S^-1,212+1307:alt S/S^-1" \
     --out figures/exp_72_ler_osd0.png --title "[[72,12,6]], 6 cycles, BP-OSD-0: S vs S^-1 vs alternating" 2>&1 | tail -n 1
  $P fig_ler.py --n 72 --cycles 6 --scheds "212:S (Bravyi),744:best (id 744),131:median (id 131),52:worst (id 52)" \
     --out figures/single_schedules_ler_osd0.png --title "[[72,12,6]], 6 cycles, BP-OSD-0: single schedules" 2>&1 | tail -n 1
}
figs72
echo "== stage 1b: [[72]] p = 0.002 $(date)"
for s in S Sinv alt 744 131 52; do for b in Z X; do r72 --sched $s --basis $b --p 0.002 --max-shots 60000 --batch 5000; done; done
figs72
echo "== stage 2: waiting for the 001 gross-code job to finish $(date)"
while systemctl --user list-units --type=scope --no-legend | awk '{print $1}' | grep -q '^qec-driver_144three\|^qec001-driver_144three'; do sleep 300; done
echo "== stage 2: [[144]] S, S^-1, alt, both bases, 6 cycles, >= 30 failures, 8 workers $(date)"; free -g | sed -n 2p
r144() { $P run_ler.py --n 144 --cycles 6 --nproc 8 --target-fails 30 "$@" 2>&1; }
for s in S Sinv alt; do for b in Z X; do r144 --sched $s --basis $b --p 0.005 --max-shots 8000  --batch 500;  done; done
for s in S Sinv alt; do for b in Z X; do r144 --sched $s --basis $b --p 0.004 --max-shots 30000 --batch 1000; done; done
$P fig_ler.py --n 144 --cycles 6 --scheds "212:S (Bravyi),1307:S^-1,212+1307:alt S/S^-1" \
   --out figures/exp_144_three_ler_osd0.png --title "[[144,12,12]], 6 cycles, BP-OSD-0: S vs S^-1 vs alternating" 2>&1
cp -f ../syndrome-circuit-scheduling-001/results/bounds_144_three.md results/ 2>/dev/null && echo "copied 001 bounds report (decoder-independent)"
awk -F, 'NR==1 || $1==144' results/ler.csv > results/exp_144.csv
echo "== driver_003 end $(date)"
