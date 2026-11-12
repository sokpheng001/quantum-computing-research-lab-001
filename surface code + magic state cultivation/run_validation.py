"""
Step 3: validate cultivation_plugin against the paper at p = 1e-3, d1 = 3.

Runs the paper's samplers through cultivation_plugin.keep_and_check, checkpointing every
sinter batch to logs/validation_<stage>.csv (sinter resume files), so a run that is killed
(e.g. by the 6-hour cap in run_all.sh) can be finalized or resumed later.

    python run_validation.py collect     # sample (resumes from the CSVs if present)
    python run_validation.py finalize    # read the CSVs -> cultivation_results.json
"""

import json
import os
import sys

import sinter
from scipy.stats import beta

import cultivation_plugin as cp

HERE = cp.HERE
LOGS = os.path.join(HERE, "logs")
P, D1 = 1e-3, 3

# Shot budgets (overridable for quick tests). Measured cost per core: ungrown 0.2 s / 1e6 shots,
# end-to-end 379 s / 1e6 shots. Expected failures: ungrown ~ 4e9 * 0.687 * 3.4e-7 ~ 900,
# end-to-end ~ 3.5e8 * 0.225 * 1.33e-6 ~ 105 (about 3 h on 12 cores).
SHOTS = {
    "ungrown": int(float(os.environ.get("VAL_SHOTS_UNGROWN", 4e9))),
    "end_to_end": int(float(os.environ.get("VAL_SHOTS_E2E", 3.5e8))),
}

# Values the task asks us to match, and the exact values recomputed from the paper's stats.csv.
PAPER = {
    "ungrown": {"error": 6e-7, "discard": 0.35},
    "end_to_end": {"error": 3e-6, "discard": 0.80},
}


def resume_csv(stage: str) -> str:
    return os.path.join(LOGS, f"validation_{stage}.csv")


def clopper_pearson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    a = (1 - conf) / 2
    lo = 0.0 if k == 0 else beta.ppf(a, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a, k + 1, n - k)
    return float(lo), float(hi)


def stats_csv_value(stage: str) -> dict:
    """The paper's own number for this setting, recomputed from stats.csv with the same cut."""
    stats = sinter.read_stats_from_csv_files(cp.STATS_CSV)
    dec = cp._decoder_name(stage)
    c = "inject[unitary]+cultivate" if stage == "ungrown" else "end2end-inplace-distillation"
    stat, = [s for s in stats if s.decoder == dec and s.json_metadata.get("c") == c
             and s.json_metadata.get("p") == P and s.json_metadata.get("d1") == D1]
    kept, fails = cp.kept_and_failures(stat, stage)
    return {"shots": stat.shots, "kept": kept, "failures": fails,
            "error": cp.T_OVER_S * fails / kept, "discard": 1 - kept / stat.shots}


def collect() -> None:
    os.makedirs(LOGS, exist_ok=True)
    for stage in ("ungrown", "end_to_end"):
        print(f"[validation] {stage}: up to {SHOTS[stage]:,} shots", flush=True)
        circuit = cp.build_cultivation_circuit(P, D1, stage)
        kept, fails = cp.keep_and_check(circuit, SHOTS[stage], stage,
                                        resume_csv=resume_csv(stage), print_progress=True)
        print(f"[validation] {stage}: kept {kept:,}, failures {fails}", flush=True)


def finalize() -> None:
    cache = cp.load_cache()
    for stage in ("ungrown", "end_to_end"):
        path = resume_csv(stage)
        if not os.path.exists(path):
            print(f"[finalize] {stage}: no data ({path} missing)")
            continue
        merged = sinter.stats_from_csv_files(path)
        if not merged:
            print(f"[finalize] {stage}: resume file is empty")
            continue
        stat, = merged
        kept, fails = cp.kept_and_failures(stat, stage)
        s_lo, s_hi = clopper_pearson(fails, kept) if kept else (0.0, 1.0)
        d_lo, d_hi = clopper_pearson(stat.shots - kept, stat.shots)
        err = cp.T_OVER_S * fails / max(kept, 1)
        ref = PAPER[stage]
        ratio = err / ref["error"] if fails else None
        passed = bool(fails) and 0.5 <= ratio <= 2 and 0.5 <= (1 - kept / stat.shots) / ref["discard"] <= 2
        result = {
            "error": err, "error_ci95": [cp.T_OVER_S * s_lo, cp.T_OVER_S * s_hi],
            "discard": 1 - kept / stat.shots, "discard_ci95": [d_lo, d_hi],
            "kept": kept, "failures": fails, "shots": stat.shots,
            "stage": stage, "p": P, "d1": D1,
            "gap_cutoff_db": cp.GAP_CUTOFF_DB if stage == "end_to_end" else None,
            "cpu_seconds": stat.seconds,
            "target_shots": SHOTS[stage],
            "complete": stat.shots >= SHOTS[stage],
            "paper_value": ref, "paper_stats_csv": stats_csv_value(stage),
            "ratio_to_paper": ratio, "pass": passed,
            "source": "simulated",
        }
        if fails == 0:
            result["note"] = "0 failures: error is only an upper bound; run more shots"
        if not result["complete"]:
            result["note"] = (result.get("note", "") + " stopped at the 6 h cap before the target shots").strip()
        cache[cp._key(P, D1, stage)] = result
        print(f"[finalize] {stage}: {json.dumps(result)}")
    cp.save_cache(cache)


if __name__ == "__main__":
    {"collect": collect, "finalize": finalize}[sys.argv[1]]()
