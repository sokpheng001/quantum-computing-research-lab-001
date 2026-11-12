"""Step 0: reproduce the README "Complete enumeration workflow" baselines.

Follows cliffordea/cliffordea/enum/README.md verbatim (noise_level=1e-3,
uniformly_depolarize, CliffordLogicalAnalyzer, FaultCombinator.get_kept_effects,
summarize_contributions, error_rates_per_kept_shot).

Usage: python -m nnflags.step0 [--max-fault-count 2] [--out results]
Each circuit's result is written to disk as soon as it finishes.
"""
import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cliffordea import accept, enum

KST = timezone(timedelta(hours=9))
CIRCUITS = {"d3a6": dict(distance=3, ancilla_count=6, flag_count=0),
            "d3a6f2": dict(distance=3, ancilla_count=6, flag_count=2)}


def kst_now() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %I:%M:%S %p KST")


def run_one(name: str, settings: dict, max_fault_count: int, noise_level: float, out: Path) -> dict:
    started = kst_now()
    t0 = time.perf_counter()
    circuit = enum.circuits.DoubleCheck(**settings)
    noisy_circuit = enum.noise.uniformly_depolarize(
        circuit.INNER_CIRCUIT,
        noise_level=noise_level,
    )
    analyzer = accept.CliffordLogicalAnalyzer(
        data_indices=circuit.DATA_INDICES,
        stabilizer_generators=circuit.STABILIZER_GENERATORS,
        logical_s=circuit.LOGICAL_S,
    )
    combinator = enum.FaultCombinator(noisy_circuit)
    t_build = time.perf_counter() - t0
    kept_effects = combinator.get_kept_effects(
        logical_analyzer=analyzer,
        max_fault_count=max_fault_count,
        cultivated_states=("S", "T"),
    )
    t_enum = time.perf_counter() - t0 - t_build
    summary = combinator.summarize_contributions(kept_effects)
    t_error_rate = float(combinator.error_rates_per_kept_shot(
        kept_effects["T"], noise_levels=[noise_level])[0])
    s_error_rate = float(combinator.error_rates_per_kept_shot(
        kept_effects["S"], noise_levels=[noise_level])[0])
    total = time.perf_counter() - t0

    # Malignant T configurations with the physical error events they stand for
    # (needed later to prioritise flag placement).
    malignant = []
    for fault_count, effects in enumerate(kept_effects["T"]):
        for accept_probability, logical_fidelity, configurations in effects.values():
            if accept_probability > 0 and logical_fidelity != 1:
                for config in configurations:
                    malignant.append({
                        "fault_count": fault_count,
                        "accept_probability": accept_probability,
                        "logical_fidelity": logical_fidelity,
                        "fault_indices": list(config),
                        "events": [sorted(repr(e) for e in combinator.index_to_events[i])
                                   for i in config],
                    })

    summary.to_csv(out / f"step0_{name}_summary.csv")
    record = {
        "circuit": name, **settings,
        "noise_model": f"enum.noise.uniformly_depolarize(INNER_CIRCUIT, noise_level={noise_level})",
        "max_fault_count": max_fault_count, "cultivated_states": ["S", "T"],
        "combinator": str(combinator),
        "summary_text": summary.to_string(),
        "T_error_rate_per_kept_shot": t_error_rate,
        "S_error_rate_per_kept_shot": s_error_rate,
        "malignant_T_configurations": malignant,
        "timing_s": {"build": t_build, "get_kept_effects": t_enum, "total": total},
        "started": started, "finished": kst_now(),
    }
    (out / f"step0_{name}.json").write_text(json.dumps(record, indent=1, default=str))
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-fault-count", type=int, default=2)
    parser.add_argument("--noise-level", type=float, default=1e-3)
    parser.add_argument("--out", default="results")
    parser.add_argument("--only", nargs="*", default=list(CIRCUITS))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in args.only:
        rec = run_one(name, CIRCUITS[name], args.max_fault_count, args.noise_level, out)
        print(f"=== {name} {CIRCUITS[name]} max_fault_count={args.max_fault_count} "
              f"p={args.noise_level} ({rec['started']} -> {rec['finished']})")
        print(rec["combinator"])
        print(rec["summary_text"])
        print("timing_s:", rec["timing_s"])
        print("malignant T configurations:", len(rec["malignant_T_configurations"]), flush=True)


if __name__ == "__main__":
    main()
