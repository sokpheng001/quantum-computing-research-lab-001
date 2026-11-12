#!/bin/bash
# task.md pipeline on [[72]]: Phases 1-4 (search_scheduler_72.py), then LER for the chosen
# schedules, then figures.  2 workers (the other cores run the [[144]] and [[72]] jobs).  Resumable.
cd /home/ubuntu/quantum001-PKNU-Lab/syndrome-circuit-scheduling-002
echo 1000 > /proc/$$/oom_score_adj 2>/dev/null
P=../venv/bin/python; NP=2
echo "== driver_72lr start $(date)"
$P search_scheduler_72.py --nproc $NP --cycles 3 --limit 4 2>&1 || { echo "search failed"; exit 1; }
$P make_figures_72.py 2>&1
# choose: most L/R-like schedule with d_circ = 6, and most L/R-like with d_circ = 3
eval "$($P - <<'PY'
import csv
rows = list(csv.DictReader(open('results/distance_72.csv')))
for r in rows: r['d'] = min(int(r['dZ']), int(r['dX'])); r['sw'] = int(r['switches_x']) + int(r['switches_z'])
for tag, d in (('D6', 6), ('D3', 3)):
    c = sorted((r for r in rows if r['d'] == d), key=lambda r: (r['sw'], r['layout'], r['x_order'], r['z_order']))
    if c: print(f'{tag}_LAY="{c[0]["layout"]}"; {tag}_X="{c[0]["x_order"]}"; {tag}_Z="{c[0]["z_order"]}"')
PY
)"
echo "chosen: d6 $D6_LAY [$D6_X] [$D6_Z]   d3 $D3_LAY [$D3_X] [$D3_Z]"
SX="A2 B2 B1 B3 A1 A3"; SZ="A1 A3 B1 B2 B3 A2"
run() { $P ler_72.py --nproc $NP "$@" 2>&1; }
for b in Z X; do
  for p in 0.006 0.004; do
    [ "$p" = 0.006 ] && M=2000 B=500 || M=6000 B=1000
    run --name S     --layout z_first  --x "$SX"   --z "$SZ"   --basis $b --p $p --max-shots $M --batch $B
    run --name LR_d6 --layout "$D6_LAY" --x "$D6_X" --z "$D6_Z" --basis $b --p $p --max-shots $M --batch $B
    [ -n "$D3_X" ] && run --name LR_d3 --layout "$D3_LAY" --x "$D3_X" --z "$D3_Z" --basis $b --p $p --max-shots $M --batch $B
    $P make_figures_72.py 2>&1 | tail -n 1
  done
done
echo "== driver_72lr end $(date)"
