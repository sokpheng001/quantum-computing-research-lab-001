"""Three-circuit [[144]] bounds report (verification Steps 1-4) -> appended to RESULTS.md.
Runs the Step 4 circuit checks itself and reads Step 3 outputs results/step3_144_<b>_<id>_w<w>.json."""
import json, glob, datetime, subprocess, os
from bb_code import BBCode, memory_circuit
from sched_ids import table
T = table(); code = BBCode(144)
md = [f'\n## [[144]] three-circuit bounds: S, S^-1, alternating S/S^-1 ({datetime.date.today()})\n',
      'Multi-seed randomised BP-OSD search, 4 cycles, OSD-CS order 20, 10 serial min-sum iterations, random channel',
      'priors; 5 independent seeds per circuit and basis. Values are upper bounds (a found fault path).\n',
      subprocess.run(['../venv/bin/python', 'strong_summary.py'], capture_output=True, text=True).stdout]
md.append('Step 4 checks (noiseless detectors zero; detector count equal to S):\n')
md += ['| circuit | cycles | basis | detectors | nonzero noiseless detectors / observables |', '|---|---|---|---|---|']
ok = True
for nm, sch in (('S', [212]), ('S^-1', [1307]), ('alt', [212, 1307])):
    for cyc in (4, 6):
        for b in 'ZX':
            c = memory_circuit(code, [T[i] for i in sch], cyc, 0.0, b)
            d, o = c.compile_detector_sampler(seed=1).sample(4, separate_observables=True)
            ref = memory_circuit(code, [T[212]], cyc, 0.0, b).num_detectors
            ok &= (d.sum() == 0 and o.sum() == 0 and c.num_detectors == ref)
            md.append(f'| {nm} | {cyc} | {b} | {c.num_detectors} | {int(d.sum())} / {int(o.sum())} |')
md.append(f'\nAll Step 4 circuit checks pass: {ok}\n')
md.append('Step 3, exact mapping of each single schedule\'s lowest-weight fault sets into the alternating circuit')
md.append('(only sets whose faults lie in cycles where alt runs that same schedule are mappable):\n')
md += ['| single | basis | weight | sets | result |', '|---|---|---|---|---|']
for f in sorted(glob.glob('results/step3_144_*_w*.json')):
    d = json.load(open(f)); a = d['args']; n = sum(d['counts'].values())
    md.append(f"| {'S' if a['single'] == '212' else 'S^-1'} | {a['basis']} | {a['weight']} | {n} | " +
              '; '.join(f'{v} {k}' for k, v in sorted(d['counts'].items())) + ' |')
subprocess.run(['../venv/bin/python', 'fig_bounds.py', '--out', 'figures/exp_144_bounds.png'])
md.append('\nFigure: figures/exp_144_bounds.png (lowest weight found vs trials, per seed).')
if '## [[144]] three-circuit bounds' not in open('RESULTS.md').read():   # resume-safe: append once
    open('RESULTS.md', 'a').write('\n'.join(md) + '\n')
open('results/bounds_144_three.md', 'w').write('\n'.join(md) + '\n')
print('\n'.join(md))
