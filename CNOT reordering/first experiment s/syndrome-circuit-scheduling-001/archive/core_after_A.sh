#!/bin/bash
# TASK2.md stages after task A.  Every stage is resumable (CSV-checkpointed), so the
# whole driver can simply be relaunched with ./launch.sh driver_core.sh after a stop.
cd /home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-001
P=../venv/bin/python; NP=12
log() { echo "== $* $(date)"; }
run72()  { $P run_ler.py --n 72  --cycles 6 --nproc $NP "$@" 2>&1; }
run144() { $P run_ler.py --n 144 --cycles 6 --nproc $NP "$@" 2>&1; }

log "task B: ranking + symmetry classes"
$P rank_936.py 2>&1 || { echo "task B failed"; exit 1; }
grep -q "## Task B" RESULTS.md || cat results/ranking_936.md >> RESULTS.md
BEST=$(awk -F, 'NR==2{print $2}' results/ranking_936.csv)
MED=$(awk -F, 'NR==469{print $2}' results/ranking_936.csv)
WORST=$(awk -F, 'END{print $2}' results/ranking_936.csv)
echo "best=$BEST median=$MED worst=$WORST"

log "task D: pair selection by fault-set overlap"
$P pairs.py select 2>&1 || { echo "task D select failed"; exit 1; }
SPECS=$(cat results/pair_specs.txt)
log "task D: alternating bounds on [[72]] for $SPECS"
$P bounds_pairs.py --n 72 --cycles 4 --trials 600 --nproc $NP --specs "$SPECS" --out results/pair_bounds.csv --tag _pb 2>&1
$P pairs.py finalist 2>&1 || { echo "task D finalist failed"; exit 1; }
grep -q "## Task D" RESULTS.md || cat results/pairs.md >> RESULTS.md
FIN=$(cat results/pair_finalist.txt)
PA=$(awk -F, '$1=="PA"{print $2}' results/pair_candidates.csv)
echo "finalist=$FIN pairA=$PA"

log "task F: [[144]] 4-cycle bounds for finalist $FIN, pair A $PA, best single $BEST"
[ -f results/exp_144_bounds.csv ] || $P - <<'PY'
import csv
F = ['n','basis','cycles','p','trials','seed','sched','bound','n_min_paths','hist','seconds']
with open('results/exp_144_bounds.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=F); w.writeheader()
    for r in csv.reader(open('results/bounds_exp1.csv')):
        if r and r[0] == '144': w.writerow(dict(zip(F[:10], r[:10]), seconds=''))
print('copied S / S^-1 / alt rows (4000 trials) from bounds_exp1.csv')
PY
$P bounds_pairs.py --n 144 --cycles 4 --trials 4000 --nproc $NP --specs "$FIN,$PA,$BEST" --out results/exp_144_bounds.csv 2>&1

log "task G: verification of bounds > 10"
$P verify_bound.py --trials 2000 --nproc $NP 2>&1 || { echo "task G failed"; exit 1; }
grep -q "## Task G" RESULTS.md || cat results/task_G.md >> RESULTS.md
OVER=$(tr '\n' ' ' < results/task_G_over10.txt)

log "task C: [[72]] LER for best $BEST / median $MED / worst $WORST (S exists), 6 cycles"
for s in $BEST $MED $WORST; do for b in Z X; do
  run72 --sched $s --basis $b --p 0.006 --target-fails 50 --max-shots 2000  --batch 500
  run72 --sched $s --basis $b --p 0.004 --target-fails 50 --max-shots 6000  --batch 1000
  run72 --sched $s --basis $b --p 0.002 --target-fails 50 --max-shots 50000 --batch 5000
done; done
$P fig_ler.py --n 72 --cycles 6 --scheds "212:S (Bravyi),$BEST:best (id $BEST),$MED:median (id $MED),$WORST:worst (id $WORST)" \
   --out figures/single_schedules_ler.png --title "[[72,12,6]] single schedules, 6 cycles" 2>&1

log "task E: [[72]] LER for finalist pair $FIN (and pair A $PA at p >= 0.004)"
for b in Z X; do
  run72 --sched $FIN --basis $b --p 0.006 --target-fails 50 --max-shots 2000  --batch 500
  run72 --sched $FIN --basis $b --p 0.004 --target-fails 50 --max-shots 6000  --batch 1000
  run72 --sched $FIN --basis $b --p 0.002 --target-fails 50 --max-shots 50000 --batch 5000
  run72 --sched $PA  --basis $b --p 0.006 --target-fails 50 --max-shots 2000  --batch 500
  run72 --sched $PA  --basis $b --p 0.004 --target-fails 50 --max-shots 6000  --batch 1000
done
$P fig_ler.py --n 72 --cycles 6 --scheds "212:S (Bravyi),$BEST:best single,$FIN:finalist pair,$PA:best + its reverse,212+1307:S + S^-1" \
   --out figures/exp2_pairs_ler.png --title "[[72,12,6]] pairs vs best single, 6 cycles" 2>&1

log "task H: [[144]] LER, 6 cycles: S, then circuits bounding > 10 [$OVER] else finalist $FIN at p=0.005"
for b in Z X; do
  run144 --sched 212 --basis $b --p 0.005 --target-fails 30 --max-shots 3000  --batch 500
  run144 --sched 212 --basis $b --p 0.004 --target-fails 30 --max-shots 12000 --batch 1000
done
if [ -n "$OVER" ]; then
  for sp in $OVER; do for b in Z X; do
    run144 --sched $sp --basis $b --p 0.005 --target-fails 30 --max-shots 3000  --batch 500
    run144 --sched $sp --basis $b --p 0.004 --target-fails 30 --max-shots 12000 --batch 1000
  done; done
  H_SCHEDS="212:S (Bravyi)$(for sp in $OVER; do printf ',%s:%s' "$sp" "$sp"; done)"
else
  for b in Z X; do run144 --sched $FIN --basis $b --p 0.005 --target-fails 30 --max-shots 3000 --batch 500; done
  H_SCHEDS="212:S (Bravyi),$FIN:finalist pair"
fi
$P fig_ler.py --n 144 --cycles 6 --scheds "$H_SCHEDS" --out figures/exp_144_ler_6cyc.png --title "[[144,12,12]] gross code, 6 cycles" 2>&1
awk -F, 'NR==1 || $1==144' results/ler.csv > results/exp_144.csv

log "task I: [[72]] p=0.002 top-up to 50 failures for S, S^-1, alt"
for s in S Sinv alt; do for b in Z X; do
  run72 --sched $s --basis $b --p 0.002 --target-fails 50 --max-shots 60000 --batch 5000
done; done
$P status.py 2>&1
log "all TASK2 stages finished"
