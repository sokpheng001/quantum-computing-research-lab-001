# summary — figures across all codes

Cross-code view of folders 001–004. The figures are redrawn automatically every 10 minutes
by the README updater, so they always show the latest results. To redraw by hand:

    cd /home/ubuntu/quantum001/summary && ../venv/bin/python make_summary.py

| figure | shows |
|---|---|
| `figures/method_pipeline.png` | how the logical error rate and the circuit-level distance are measured |
| `figures/summary_dcirc.png` | lowest fault-path weight found (upper bound on circuit-level distance) for S, S⁻¹ and alternating, on [[72]], [[90]], [[144]], with the code distance and Bravyi et al.'s value for S |
| `figures/summary_ler.png` | logical error rate per cycle against p for the same three circuits on every code, Z and X memory, 95% error bars |
| `figures/decoder_compare.png` | [[72]]: the same circuits decoded with BP-OSD order 7 (001) and BP-OSD-0 (003) |

Data sources: 001 (`results/ler.csv`, `bounds_exp1.csv`, `strong_144.csv`), 003 (`results/ler.csv`),
004 (`results/strong_90.csv`, `results/ler.csv`). Panels of runs that have not started say "running – no data yet".
