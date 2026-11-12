"""Test 4 side check: the toy noise of the validation (DEPOLARIZE1(p) on every qubit after
every moment, real T) at lower p, Clifft only, Google G6-style vs cs02. Shows where fault
distance 3 starts to pay off in that model. Writes results/toy_p_sweep.json.

    .venv/bin/python "qvm-google (main)/test4_cs02_lattice_surgery_escape_realT_clifft/toy_noise_p_sweep.py"
"""
import json, sys, zlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate_clifft as V  # noqa: E402

out = {}
for p in (0.0002, 0.0005, 0.001, 0.002):
    shots = 2_000_000_000 if p < 0.001 else 400_000_000
    for name in ("G4_G6style", "cont_success02"):
        r = V.run_clifft(name, p, shots, 12)
        out[f"{name}_p{p}"] = r
        e = r["error"]
        print(f"p={100*p:.2f}% {name:15s} acc {100*r['acceptance']:.2f}%  errors {e['events']:6d} / {e['of']:,}  "
              f"{V.one_in(e['rate'])}  ({r['wall_s']} s)", flush=True)
(HERE / "results" / "toy_p_sweep.json").write_text(json.dumps(out, indent=1))
