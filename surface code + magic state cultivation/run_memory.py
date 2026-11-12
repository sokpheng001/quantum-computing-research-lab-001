"""
Surface-code memory sweep for figure F2 (Stim + PyMatching, via sinter).

Same circuit family and noise as full_stack_sim.surface_code_memory: rotated memory-Z,
rounds = d, uniform depolarizing p on every location. Writes memory_results.csv with
per-shot and per-cycle logical error rates and 95% Clopper-Pearson intervals.
"""

import csv
import os

import sinter
import stim

from run_validation import clopper_pearson

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "memory_results.csv")
RESUME = os.path.join(HERE, "logs", "memory_stats.csv")

DISTANCES = (3, 5, 7)
PS = (2e-4, 3e-4, 5e-4, 7e-4, 1e-3, 2e-3, 3e-3, 5e-3)
EXTRA = ((9, 1e-3),)  # pipeline point: the Toffoli example needs d = 9 at p = 0.1%
MAX_ERRORS = int(float(os.environ.get("MEM_MAX_ERRORS", 100)))
MAX_SHOTS = int(float(os.environ.get("MEM_MAX_SHOTS", 5e7)))


def memory_circuit(d: int, p: float) -> stim.Circuit:
    return stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=d, rounds=d,
        after_clifford_depolarization=p, before_round_data_depolarization=p,
        before_measure_flip_probability=p, after_reset_flip_probability=p,
    )


def main() -> None:
    os.makedirs(os.path.dirname(RESUME), exist_ok=True)
    tasks = [sinter.Task(circuit=memory_circuit(d, p), json_metadata={"d": d, "p": p, "rounds": d})
             for d, p in [(d, p) for d in DISTANCES for p in PS] + list(EXTRA)]
    stats = sinter.collect(
        num_workers=os.cpu_count(), tasks=tasks, decoders=["pymatching"],
        max_errors=MAX_ERRORS, max_shots=MAX_SHOTS,
        save_resume_filepath=RESUME, print_progress=True,
    )
    rows = []
    for s in sorted(stats, key=lambda s: (s.json_metadata["d"], s.json_metadata["p"])):
        d, p, r = s.json_metadata["d"], s.json_metadata["p"], s.json_metadata["rounds"]
        lo, hi = clopper_pearson(s.errors, s.shots)
        per_cycle = lambda x: 1 - (1 - x) ** (1 / r)
        rows.append({
            "d": d, "p": p, "rounds": r, "shots": s.shots, "errors": s.errors,
            "per_shot": s.errors / s.shots, "per_shot_lo": lo, "per_shot_hi": hi,
            "per_cycle": per_cycle(s.errors / s.shots),
            "per_cycle_lo": per_cycle(lo), "per_cycle_hi": per_cycle(hi),
            "cpu_seconds": s.seconds,
        })
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT} ({len(rows)} points)")


if __name__ == "__main__":
    main()
