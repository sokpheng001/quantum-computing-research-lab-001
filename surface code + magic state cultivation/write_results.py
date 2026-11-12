"""Write RESULTS_cultivation.md from saved results (cultivation_results.json, memory_results.csv,
pipeline_results.json, logs/). Safe to rerun at any time."""

import csv
import json
import os
import sys
from importlib.metadata import version

import cultivation_plugin as cp

HERE = cp.HERE
LOGS = os.path.join(HERE, "logs")


def read(path: str, default: str = "") -> str:
    path = os.path.join(HERE, path)
    return open(path).read() if os.path.exists(path) else default


CODE_MAP = """\
## 1. Map of the paper's code (read before writing any adapter)

Archive: `Magic state cultivation/` (Gidney, Shutty & Jones 2024, arXiv:2409.17595, Zenodo 10.5281/zenodo.13777072). **Never edited.**

| Path | What it is |
|---|---|
| `code/README.md`, `code/requirements.txt` | usage; pins `stim~=1.14`, `sinter~=1.14`, `chromobius~=1.1.0`, pymatching, numpy, scipy, networkx, pygltflib, matplotlib, pytest |
| `code/step1_make_circuits` | calls `tools/make_circuits` (GNU parallel) for every circuit family below |
| `code/step2_collect` | `sinter collect --custom_decoders cultiv:sinter_samplers` per family (weeks of CPU) |
| `code/step3_plot` | `tools/sinter_plot_echo.py` plots; end-to-end x-axis = `(shots+1)/(shots-discards+2)` |
| `code/tools/make_circuits` | CLI → `cultiv.make_*` builder, then `gen.NoiseModel.uniform_depolarizing(p).noisy_circuit_skipping_mpp_boundaries(circuit)` (`--gateset css` → noise `uniform`) |
| `code/tools/write_historical_data_csv.py` | builds the paper's "This Work" points: `DOUBLING_S_GIVES_T_ASSUMPTION = 2` (×2 on errors), gap cut via `cultiv.stat_to_gap_stats(..., rounding=1)`, cost via `select_rep_stats` |
| `code/src/cultiv/_construction/_integration.py` | **circuit builders** (below) |
| `code/src/cultiv/_construction/_cultivation_stage.py` | `make_inject_and_cultivate_chunks_d3/_d5(style)` — double-checking uses `S`/`S_DAG` (the S-for-T stand-in) |
| `code/src/cultiv/_construction/_escape_stage.py` | `make_color_code_to_big_matchable_code_escape_chunks(dcolor, dsurface, basis, r_growing, r_end)` |
| `code/src/cultiv/_decoding/_perfectionist_sampler.py` | `PerfectionistSampler`: discard on **any** detection event, predict "no flip" |
| `code/src/cultiv/_decoding/_desaturation_sampler.py` | `DesaturationSampler`: postselects detectors with coord[4] == -9 / missing annotation and the ablatable color-code detectors (r-X, g-Z), decodes the rest with PyMatching twice (obs forced on / off) → prediction + complementary gap (dB), stored as `custom_counts` keys `C<gap>` / `E<gap>` |
| `code/src/cultiv/_decoding/_mux_sampler.py` | `sinter_samplers()` dict: highlander, vec/twirl_intercept_{t,s,z}, notouch, chromobius-continue, chromobius-gap, desaturation, pymatching-gap (**no `perfectionist` entry**) |
| `code/src/cultiv/_stats_util.py` | `stat_to_gap_stats`, `split_by_gap_threshold`, `split_by_gap`, `compute_expected_injection_growth_volume(circuit, discard_rate)` |

**Circuit builders (signatures):**
- `cultiv.make_inject_and_cultivate_circuit(*, dcolor: int, inject_style: 'degenerate'|'bell'|'unitary', basis: 'X'|'Y')` — injection + cultivation ("ungrown"); d1 ∈ {3, 5}.
- `cultiv.make_end2end_cultivation_circuit(*, dcolor, dsurface, basis, r_growing, r_end, inject_style)` — injection + cultivation + escape into the grafted matchable code ("end-to-end"). Paper: `dsurface=15, r_growing=d1, r_end=5`.
- also: `make_escape_to_big_matchable_code_circuit`, `make_idle_matchable_code_circuit`, `make_surface_code_memory_circuit`, `make_escape_to_big_color_code_circuit`, `make_surface_code_cnot`.
- Noise strength is not a builder argument; it is applied afterwards by `gen.NoiseModel.uniform_depolarizing(p)`.

**Answers to Step 1:**
1. Builders: above. Parameters: `dcolor` (= d1), `dsurface` (= d2, final distance), `r_growing` (r1), `r_end` (r2), `inject_style`, `basis`; noise p via `gen.NoiseModel`.
2. S-for-T variant: `basis='Y'` (all paper circuits use `b=Y`); the cultivation check circuits contain `S`/`S_DAG`, so the cultivated state is S|+⟩ (Y eigenstate), simulable by Stim. The ×2 to get T is applied only in `write_historical_data_csv.py`, **not** in the samplers → our `simulate()` keeps the ×2.
3. Sampling/postselection: `sinter collect` with a custom sampler. Ungrown: `PerfectionistSampler` (discard if any detector fires). End-to-end: `DesaturationSampler` (discard if any postselected detector fires: all injection/cultivation detectors and the color-code detectors removed by the escape).
4. Escape decoding + gap cut: `DesaturationSampler` builds a matchable DEM (`clipped_matchable_dem`, virtual pair nodes for color-code triplets), adds an observable detector, decodes with PyMatching with that detector on and off; gap = |w_on − w_off| in dB. The cut is applied afterwards: `stat_to_gap_stats(..., rounding=1, func=at_least)` keeps shots with gap ≥ threshold.
5. Rates: logical error = errors / (shots − discards) per kept shot, then ×2 for T; discard = discards / shots; cost axis = `compute_expected_injection_growth_volume(noisy_circuit, discard_rate=0) / keep_rate` (qubit·rounds per kept state).

**`circuits/` (57 .stim files, noisy, b=Y unless noted):** `for_perfectionist_decoding` (inject[bell|teleport|unitary]+cultivate, p ∈ {0.05%, 0.1%, 0.2%}, d1=3; unitary also d1=5) · `for_desaturated_decoding_3` / `_5` (end2end, d1=3 / 5, d2=15, r1=d1, r2=5, p ∈ {0.05%, 0.1%, 0.2%}) · `for_intercept_sampling` (inject[unitary]+cultivate d1=3, p from 0.1% to 1%) · `for_matching` (idle-matchable-code and surface-code-memory, d2 ∈ {11, 15}) · `for_color_gap_decoding` (escape-to-big-color-code d1 ∈ {3,5,7}) · `for_correlated_matching` (surface-code-cnot, d2 = 3…25, b ∈ {X, Z}).

**`stats.csv` (95 rows; identical to `code/assets/stats.csv`):** columns `shots, errors, discards, seconds, decoder, strong_id, json_metadata, custom_counts`; metadata keys `b, c, d1, d2, g, noise, p, q, r, r1, r2`. Decoders present: perfectionist (12 rows), desaturation (6, with gap histograms in custom_counts), twirl/vec_intercept_{t,s,z} (36), pymatching-gap (14), chromobius-gap (3), sparse_blossom_correlated (24). **No cost column**: cost is derived (see 5.) — F3 uses the paper's own volume function. `seconds` is summed worker time (end-to-end d1=3 p=0.1%: 504 s per 10⁶ shots).
"""


def fmt(x: float) -> str:
    """Rates as '1 in N' (3 significant figures) or %, never e-notation."""
    if x <= 0:
        return "0"
    if x >= 0.01:
        return f"{100 * x:.3g}%"
    n = float(f"{1 / x:.3g}")
    return f"1 in {n:,.0f}"


def main() -> None:
    cache = cp.load_cache()
    out = ["# RESULTS — cultivation plugin (Gidney, Shutty & Jones 2024 inside full_stack_sim.py)", "",
           f"_Generated by `write_results.py`. Folder: `{HERE}`._", "", CODE_MAP]

    # ---------------- validation table
    out += ["## 2. Validation at p = 0.1 %, d1 = 3 (Step 3 / Step 5)", "",
            "| setting | stage | shots | kept | failures | error (95% CI) | discard (95% CI) | paper value | paper stats.csv (same cut) | ratio | PASS? |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, stage in (("1e-03,3,ungrown", "ungrown"), ("1e-03,3", "end_to_end")):
        r = cache.get(key)
        if not r or r.get("source") != "simulated":
            out.append(f"| p=0.1%, d1=3 | {stage} | — | — | — | not simulated | — | — | — | — | NOT RUN |")
            continue
        lo, hi = r["error_ci95"]
        dlo, dhi = r["discard_ci95"]
        ps = r["paper_stats_csv"]
        cut = f", gap ≥ {r['gap_cutoff_db']} dB" if r.get("gap_cutoff_db") else ""
        err = f"{fmt(r['error'])} [{fmt(lo)}, {fmt(hi)}]" if r["failures"] else f"< {fmt(hi)} (0 failures)"
        ratio = f"{r['ratio_to_paper']:.2f}" if r["ratio_to_paper"] else "—"
        verdict = "**PASS**" if r["pass"] else "**FAIL**"
        if not r.get("complete"):
            verdict += " (capped)"
        out.append(f"| p=0.1%, d1=3{cut} | {stage} | {r['shots']:,} | {r['kept']:,} | {r['failures']} | {err} | "
                   f"{100 * r['discard']:.2f}% [{100 * dlo:.2f}, {100 * dhi:.2f}] | {fmt(r['paper_value']['error'])}, "
                   f"{100 * r['paper_value']['discard']:.0f}% | {fmt(ps['error'])}, {100 * ps['discard']:.1f}% "
                   f"({ps['failures']} fails / {ps['kept']:,} kept) | {ratio} | {verdict} |")
    out += ["",
            "- error = T-state error = 2 × (S-state failures / kept) (Assumption 3.1). CI: exact Clopper-Pearson 95 % on the S rate, ×2.",
            "- PASS = our error and discard both within a factor 2 of the paper value (task rule). Ratio = ours / paper value.",
            "- Ungrown = `inject[unitary]+cultivate` + `PerfectionistSampler`; end-to-end = `end2end-inplace-distillation` (d2=15, r1=3, r2=5) + `DesaturationSampler`, "
            f"gap cut fixed at {cp.GAP_CUTOFF_DB} dB **before** sampling (the largest gap the decoder reports; the paper's stats give 1 in 377,000 at 77.5 % there).",
            "- d1 = 5 was **not** simulated (errors ~1 in 10⁹ need ~10¹² shots); the pipeline uses the published values for d1 = 5.", ""]

    # ---------------- run times
    timing = read("logs/timing.txt", "(no timing log)")
    out += ["## 3. Run times", "",
            "Measured before the long run (one core, paper samplers called directly):",
            "- ungrown (15 qubits, perfectionist): **0.2 s per 10⁶ shots**",
            "- end-to-end (454 qubits, desaturation, 2 matchings per kept shot): **379 s per 10⁶ shots** "
            "(paper's own stats.csv: 504 s per 10⁶ shots)",
            "- estimate: ~20 end-to-end failures ≈ 6.7·10⁷ shots ≈ 35 min on 12 cores; target 3.5·10⁸ shots (~105 failures) ≈ 3 h; hard cap 6 h.", "",
            "CPU time recorded by sinter (sum over workers):"]
    for key in ("1e-03,3,ungrown", "1e-03,3"):
        r = cache.get(key)
        if r and r.get("cpu_seconds") is not None:
            out.append(f"- {r['stage']}: {r['cpu_seconds'] / 3600:.2f} CPU-hours for {r['shots']:,} shots")
    out += ["", "Wall-clock log (`logs/timing.txt`, KST):", "", "```", timing.strip(), "```", ""]

    # ---------------- pipeline
    pipe_txt = read("logs/pipeline_output.txt", "(pipeline not run yet)")
    out += ["## 4. Pipeline output (Step 4: `python full_stack_sim.py`)", "",
            "Each factory line is tagged `[simulated]` (from `cultivation_results.json`) or `[published]` (paper Fig. 2 fallback).", "",
            "```", pipe_txt.strip(), "```", ""]

    # ---------------- memory
    if os.path.exists(os.path.join(HERE, "memory_results.csv")):
        with open(os.path.join(HERE, "memory_results.csv")) as f:
            rows = list(csv.DictReader(f))
        out += ["## 5. Surface-code memory sweep (F2 data, `memory_results.csv`)", "",
                "| d | p | shots | failures | per-cycle error (95% CI) |", "|---|---|---|---|---|"]
        for r in rows:
            e = (f"{fmt(float(r['per_cycle']))} [{fmt(float(r['per_cycle_lo']))}, {fmt(float(r['per_cycle_hi']))}]"
                 if int(r["errors"]) else f"< {fmt(float(r['per_cycle_hi']))}")
            out.append(f"| {r['d']} | {float(r['p']) * 100:g}% | {int(r['shots']):,} | {r['errors']} | {e} |")
        out.append("")

    # ---------------- figures
    out += ["## 6. Figures (`figures/`, PNG + PDF; rebuild with `python plot_results.py`)", ""]
    for n, d in (("F1_validation", "validation vs paper"), ("F2_memory", "surface-code memory"),
                 ("F3_cost", "cultivation error vs cost (stats.csv + ours)"), ("F4_pipeline", "pipeline outcome counts"),
                 ("F5_resources", "physical-qubit breakdown")):
        out.append(f"- {d}: `{os.path.join(HERE, 'figures', n + '.png')}` (+ `.pdf`)")
    out.append("")

    # ---------------- environment
    pkgs = ["stim", "sinter", "pymatching", "chromobius", "numpy", "scipy", "networkx", "pygltflib",
            "matplotlib", "qiskit", "qiskit-qasm3-import", "pytest"]
    vers = ", ".join(f"{p} {version(p)}" for p in pkgs)
    py = "Python " + sys.version.split()[0]
    out += ["## 7. Environment", "",
            f"- venv: `/home/ubuntu/quantum001-PKNU-Lab/venv` (the existing one; {py}). Added: chromobius, pygltflib, networkx, pytest, qiskit-qasm3-import.",
            f"- versions: {vers}",
            "- 12 CPU cores, 47 GB RAM, Ubuntu (kernel 6.8).", ""]

    # ---------------- paper functions used
    out += ["## 8. Paper functions used by our code", "",
            "- `cultiv.make_inject_and_cultivate_circuit(dcolor=d1, inject_style='unitary', basis='Y')`",
            "- `cultiv.make_end2end_cultivation_circuit(dcolor=d1, dsurface=15, basis='Y', r_growing=d1, r_end=5, inject_style='unitary')`",
            "- `gen.NoiseModel.uniform_depolarizing(p).noisy_circuit_skipping_mpp_boundaries(circuit)`",
            "- `cultiv._decoding._perfectionist_sampler.PerfectionistSampler`, `cultiv.sinter_samplers()['desaturation']` (via `sinter.collect`)",
            "- `cultiv.stat_to_gap_stats(stats, rounding=1, func=...)` (same lambda as `write_historical_data_csv.py`)",
            "- `cultiv.compute_expected_injection_growth_volume(circuit, discard_rate=0)` (F3 cost axis)", ""]

    # ---------------- deviations / problems
    out += ["## 9. Problems and deviations (none worked around silently)", "",
            "1. **Missing venv.** The cultivation `.venv` set up on Oct 23 no longer exists. As instructed, the existing `~/quantum001/venv` was used; "
            "stim/sinter are **1.16.0**, not the `~=1.14` pinned by `requirements.txt` (not downgraded: that venv is shared).",
            "2. **Paper unit tests (`pytest src`, unchanged): 432 passed, 27 failed** (`logs/step0_pytest.log`). "
            "24 = `_twirl_intercept_sampler` calls `FlipSimulator.reset()`, which stim does not have (not used here). "
            "3 = `gen` gate-table / layer-squash tests (`KeyError: 'X*C_ZYX'`, two circuit-equality asserts) — newer stim gate set; not on our path.",
            "3. **Generated circuits = shipped circuits.** Our wrapper's circuits (ungrown d1=3, d1=5; end-to-end d1=3) are identical to the files in `circuits/` "
            "after a text round-trip; the only difference is detector-coordinate rounding in the saved files (2.142857… vs 2.14286), which has no physical effect. "
            "This also shows the 3 failing `gen` tests do not change these circuits.",
            "4. **`perfectionist` is not registered** in `cultiv.sinter_samplers()`, although `step2_collect` asks for it. We import `PerfectionistSampler` from its module directly (no copy, no edit).",
            "5. **Paper code applies T = 2×S only in post-processing** (`DOUBLING_S_GIVES_T_ASSUMPTION` in `write_historical_data_csv.py`), not in the samplers, so `simulate()` keeps its ×2 — no double counting.",
            "6. **End-to-end gap threshold.** The paper reports a curve over gap cut-offs; one point is needed here. We fixed 69 dB (largest gap; ≈ the task's 1 in 333,000 / 80 %) before sampling.",
            "7. **Paper value vs task value for ungrown discard.** Task says ≈35 %; stats.csv gives 31.3 % for the same circuit. Both are listed.",
            "8. **Pipeline's own QEC model** (`qec_error_model`, 20 000 shots) sees only ~1 failure at d = 5, so its λ extrapolation is noisy. Left unchanged (not in scope); F2 shows the properly sampled curves.",
            "9. Cache keys: end-to-end keeps the existing key format `\"1e-03,3\"` (read by the pipeline); ungrown is stored as `\"1e-03,3,ungrown\"`. Published fallback unchanged.", ""]

    with open(os.path.join(HERE, "RESULTS_cultivation.md"), "w") as f:
        f.write("\n".join(out))
    print("wrote RESULTS_cultivation.md")


if __name__ == "__main__":
    main()
