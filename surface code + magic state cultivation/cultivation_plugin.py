"""
Cultivation plugin: run the magic-state cultivation code from
Gidney, Shutty & Jones (2024), arXiv:2409.17595, Zenodo doi:10.5281/zenodo.13777072,
and turn its output into the numbers full_stack_sim.py needs:
    (p, d1) -> (logical error of a kept T state, discard rate, attempts per kept state)

The paper's archive lives (unmodified) in "Magic state cultivation/" (circuits/, code/, stats.csv).
This file only wraps the paper's own functions (see RESULTS_cultivation.md for the map):
  circuits : cultiv.make_inject_and_cultivate_circuit   (stage="ungrown")
             cultiv.make_end2end_cultivation_circuit    (stage="end_to_end")
             gen.NoiseModel.uniform_depolarizing(p).noisy_circuit_skipping_mpp_boundaries
             -- same calls and arguments as the paper's tools/make_circuits + step1_make_circuits
  sampling : sinter.collect with the paper's samplers
             PerfectionistSampler (discard on ANY detection event)          for "ungrown"
             DesaturationSampler  (postselect color-code dets, then matching
                                   with a complementary-gap readout)        for "end_to_end"
  gap cut  : cultiv.stat_to_gap_stats with the same rule as tools/write_historical_data_csv.py

Design:
  * results are cached in cultivation_results.json, so the slow simulation runs once
  * if a setting has not been simulated, fall back to the paper's published Fig. 2 values
  * the T gate is simulated as S (the paper's Assumption 3.1: T error ~ 2 x S error).
    The paper's samplers return S-state counts; the paper applies the x2 only in
    tools/write_historical_data_csv.py (DOUBLING_S_GIVES_T_ASSUMPTION = 2), so simulate() keeps it.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Folder that holds the paper's archive (circuits/, code/, stats.csv).
# Order: env var CULTIVATION_REF, then "./Magic state cultivation/", then this script's folder.
def _find_ref_dir() -> str:
    if os.environ.get("CULTIVATION_REF"):
        return os.environ["CULTIVATION_REF"]
    for cand in (os.path.join(HERE, "Magic state cultivation"), HERE):
        if os.path.isdir(os.path.join(cand, "circuits")):
            return cand
    return os.path.join(HERE, "Magic state cultivation")


REF_DIR = _find_ref_dir()
CIRCUITS_DIR = os.path.join(REF_DIR, "circuits")
CODE_DIR = os.path.join(REF_DIR, "code")
STATS_CSV = os.path.join(REF_DIR, "stats.csv")

CACHE = os.path.join(HERE, "cultivation_results.json")

PUBLISHED = {                        # end-to-end values, Fig. 2 of the paper
    "1e-03,3": {"error": 3e-6, "discard": 0.80, "source": "published"},
    "1e-03,5": {"error": 2e-9, "discard": 0.99, "source": "published"},
    "5e-04,5": {"error": 4e-11, "discard": 0.90, "source": "published"},
}

# Settings of the paper's end-to-end circuits (step1_make_circuits: --d2 15 --r1 "d1" --r2 "5").
END2END_D2 = 15
END2END_R2 = 5
# Complementary-gap cut for the end-to-end stage (dB). 69 dB is the largest gap the
# desaturation decoder reports for d1=3; keeping only those shots gives the paper's
# ~3e-6 / ~80% point (stats.csv: 2.65e-6 at 77.5% discard). Fixed before simulating.
GAP_CUTOFF_DB = 69

T_OVER_S = 2                         # Assumption 3.1 (DOUBLING_S_GIVES_T_ASSUMPTION in the paper)


def _key(p: float, d1: int, stage: str = "end_to_end") -> str:
    key = f"{p:.0e},{d1}"
    return key if stage == "end_to_end" else f"{key},{stage}"


def _paper_modules():
    """Import the paper's packages (cultiv, gen) from CODE_DIR/src without copying them."""
    src = os.path.join(CODE_DIR, "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    import cultiv
    import gen
    from cultiv._decoding._perfectionist_sampler import PerfectionistSampler
    return cultiv, gen, PerfectionistSampler


def _decoder_name(stage: str) -> str:
    return {"ungrown": "perfectionist", "end_to_end": "desaturation"}[stage]


def _custom_decoders(stage: str) -> dict:
    cultiv, _, PerfectionistSampler = _paper_modules()
    if stage == "ungrown":
        # 'perfectionist' is used by step2_collect but missing from cultiv.sinter_samplers().
        return {"perfectionist": PerfectionistSampler()}
    return {"desaturation": cultiv.sinter_samplers()["desaturation"]}


# ----------------------------------------------------------------- paper wrappers
def build_cultivation_circuit(p: float, d1: int, stage: str = "end_to_end"):
    """Return the noisy stim.Circuit for one cultivation attempt at uniform noise p and
    target fault distance d1, S-gate (basis='Y') variant, built by the paper's generator.
    stage="ungrown":     injection + cultivation (c=inject[unitary]+cultivate)
    stage="end_to_end":  injection + cultivation + escape into the d2=15 grafted code
                         (c=end2end-inplace-distillation, r1=d1, r2=5)"""
    cultiv, gen, _ = _paper_modules()
    if stage == "ungrown":
        circuit = cultiv.make_inject_and_cultivate_circuit(dcolor=d1, inject_style="unitary", basis="Y")
    elif stage == "end_to_end":
        circuit = cultiv.make_end2end_cultivation_circuit(
            dcolor=d1, dsurface=END2END_D2, basis="Y",
            r_growing=d1, r_end=END2END_R2, inject_style="unitary",
        )
    else:
        raise ValueError(f"stage must be 'ungrown' or 'end_to_end', got {stage!r}")
    noise = gen.NoiseModel.uniform_depolarizing(p)
    return noise.noisy_circuit_skipping_mpp_boundaries(circuit)


def kept_and_failures(stat, stage: str, gap_cutoff: int = GAP_CUTOFF_DB) -> tuple[int, int]:
    """(kept, failures) from one sinter.TaskStats of the paper's samplers.
    end_to_end: apply the complementary-gap cut with the paper's cultiv.stat_to_gap_stats."""
    if stage == "ungrown":
        return stat.shots - stat.discards, stat.errors
    cultiv, _, _ = _paper_modules()
    import sinter
    rows = cultiv.stat_to_gap_stats([stat], rounding=1, func=lambda arg: sinter.AnonTaskStats(
        shots=arg.source.shots,
        discards=arg.at_least.discards + arg.less.shots,
        errors=arg.at_least.errors,
    ))
    above = [r for r in rows if r.json_metadata.get("gap", 0) >= gap_cutoff]
    if not above:
        return 0, 0
    r = min(above, key=lambda r: r.json_metadata["gap"])
    return r.shots - r.discards, r.errors


def keep_and_check(circuit, shots: int, stage: str = "end_to_end", *,
                   num_workers: int | None = None, resume_csv: str | None = None,
                   gap_cutoff: int = GAP_CUTOFF_DB, print_progress: bool = False) -> tuple[int, int]:
    """Sample `shots` attempts with the paper's sampler for `stage` (via sinter.collect,
    as in the paper's step2_collect) and return (kept_shots, logical_failures_among_kept).
    resume_csv: sinter resume file, so an interrupted run continues where it stopped."""
    import sinter
    stats = sinter.collect(
        num_workers=num_workers or os.cpu_count(),
        tasks=[sinter.Task(circuit=circuit, json_metadata={"stage": stage})],
        decoders=[_decoder_name(stage)],
        custom_decoders=_custom_decoders(stage),
        max_shots=shots,
        save_resume_filepath=resume_csv,
        print_progress=print_progress,
    )
    stat, = stats
    return kept_and_failures(stat, stage, gap_cutoff)
# --------------------------------------------------------------------------------


def simulate(p: float, d1: int, shots: int, stage: str = "end_to_end") -> dict:
    circ = build_cultivation_circuit(p, d1, stage)
    kept, fails = keep_and_check(circ, shots, stage)
    discard = 1 - kept / shots
    s_error = fails / max(kept, 1)
    return {
        "error": T_OVER_S * s_error,       # Assumption 3.1: T error ~ 2 x S error
        "discard": discard,
        "kept": kept, "failures": fails, "shots": shots,
        "stage": stage, "p": p, "d1": d1,
        "source": "simulated",
    }


def load_cache() -> dict:
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE, "w") as f:
        json.dump(cache, f, indent=2)


def cultivation_numbers(p: float, d1: int, shots: int | None = None, stage: str = "end_to_end") -> dict:
    """Main entry point used by the pipeline.
    shots=None -> never simulate, use cache or published values.
    shots=N    -> simulate if not cached (can take a long time)."""
    cache, key = load_cache(), _key(p, d1, stage)
    if key in cache:
        return cache[key]
    if shots:
        try:
            result = simulate(p, d1, shots, stage)
            if result["failures"] == 0:
                result["note"] = "0 failures: error is only an upper bound; run more shots"
            cache[key] = result
            save_cache(cache)
            return result
        except NotImplementedError:
            pass
    if key in PUBLISHED:
        return PUBLISHED[key]
    raise KeyError(f"no data for p={p}, d1={d1}: simulate it or add published values")


if __name__ == "__main__":
    # Example: validate the plugin against the paper at the cheapest setting first.
    print(cultivation_numbers(1e-3, 3))            # cache, else published fallback
