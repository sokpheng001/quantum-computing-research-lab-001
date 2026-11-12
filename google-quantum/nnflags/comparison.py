"""Design comparison: malignant counts, T error per kept shot, acceptance.

Tasks 1-3 of the comparison round (RESULTS_comparison.md).

Everything goes through cliffordea's own code paths (nothing of the
enumeration is reimplemented; cliffordea is not modified):
  * ``verify.verify`` (README workflow: ``uniformly_depolarize``,
    ``CliffordLogicalAnalyzer``, ``FaultCombinator.get_kept_effects``,
    ``summarize_contributions``, ``error_rates_per_kept_shot``) for the
    malignant counts and the T / S error per kept shot.
  * Acceptance from the enumeration. cliffordea has no acceptance output.
    ``error_rates_per_kept_shot`` (fault_combinator.py:164-225) returns
    malignant_odds / (benign_odds + malignant_odds), where every kept
    configuration contributes accept_probability * prod(odds of its faults)
    (``_compile_odds_terms``, :722-758; odds per fault ``_bag_to_odds``,
    :558-580). The normalisation prod_i (1 - q_i) over all faults cancels in
    that ratio. Multiplying it back gives the probability of a kept shot,
    truncated at max_fault_count:
        P(kept) = prod_i (1 - q_i) * sum_{k <= mfc} sum_{kept cfg} a(cfg) prod_{i in cfg} odds_i
    with q_i = odds_i / (1 + odds_i). This is what ``enumerated_acceptance``
    computes, from the same kept effects and the same per-fault odds.
    Two meanings, by analyzer:
      - ``analyzer="T"`` / ``"S"``: kept = no inner detector fires AND the
        noiseless final stabiliser postselection of ``CliffordLogicalAnalyzer``
        (a(cfg) = its accept_probability, accept/logical_analyzers.py:370-403).
        This is the denominator of cliffordea's "per kept shot".
      - ``analyzer="detectors"``: an accept-everything analyzer
        (``AcceptAll``), so kept = no inner detector fires. This is the
        same event as the stim Monte Carlo below.
  * Monte Carlo: the same noisy inner circuit (``uniformly_depolarize``),
    stim's detector sampler, kept = no detector fired.
  * ``odds_from_circuit``: per-fault odds for a noisy circuit whose channel
    strengths differ from location to location (used by willow_noise). It
    reads the same error locations as ``FaultCombinator.__init__``
    (``CultivationCircuit.group_error_events_by_location``,
    enum/cultivation_circuit.py:296-335) in the same order, so it lines up
    with ``combinator._event_fault_indices`` (fault_combinator.py:113-124,
    as ``index_to_events`` does, :374-388), and decomposes each channel into
    independent events with cliffordea's ``_decomposed_probability``
    (:584-605) evaluated at that location's own strength.

Usage: python -m nnflags.comparison [--out results] [--max-shots N]
"""
import argparse
import json
import math
import time
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import stim

from cliffordea import accept, enum
from cliffordea.accept.logical_analyzers import LogicalAnalyzer
from cliffordea.enum.combinators._base import classify
from cliffordea.enum.combinators.fault_combinator import FaultCombinator

from nnflags import constraints as C
from nnflags.verify import bundled_paths, load_measurement, verify

KST = timezone(timedelta(hours=9))
P_LIST = (0.0005, 0.001, 0.002, 0.003)
P0 = 0.001
R = Path("results")


def kst_now() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %I:%M:%S %p KST")


def _paths(prefix):
    return Path(f"{prefix}.full.stim"), Path(f"{prefix}.inner.stim")


# name -> (full, inner, Willow-compatible?, flags, note)
def designs() -> dict:
    out = {}
    for n, flags in (("d3a6", 0), ("d3a6f2", 2), ("d3a4", 0)):
        out[n] = dict(paths=bundled_paths(n), willow=False, flags=flags, form="CX",
                      note="cliffordea bundled; not Willow-compatible (strict readout"
                           + ("; flags need diagonal couplers, degree 6" if flags else "") + ")")
    out["G4-CX"] = dict(paths=_paths(R / "g4" / "G4-CX"), willow=True, flags=0, form="CX",
                        note="Google as-run double check, CX form")
    out["G4-native"] = dict(paths=_paths(R / "g4" / "G4-native_CZH"), willow=True, flags=0,
                            form="CZ+H", note="Google as-run double check, native CZ + H TICKs")
    out["cand03"] = dict(paths=_paths(R / "option1" / "cand03"), willow=True, flags=1, form="CX",
                         note="best Option-1 candidate (same-control Z flag)")
    for f in sorted((R / "zz").glob("success*.inner.stim")):
        n = f.name.split(".")[0]
        out[n] = dict(paths=_paths(R / "zz" / n), willow=True, flags=2, form="CX",
                      note="ZZ flag + X flag, fault distance 3")
    return out


def load(d):
    full, inner = d["paths"]
    return stim.Circuit.from_file(str(full)), stim.Circuit.from_file(str(inner))


def structure(inner: stim.Circuit) -> dict:
    gates = C.two_qubit_gates(inner)
    used = {t.qubit_value for op in inner if isinstance(op, stim.CircuitInstruction)
            and op.name not in ("QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE")
            for t in op.targets_copy() if t.qubit_value is not None}
    return dict(qubits=len(used),
                ticks=inner.num_ticks, n_2q=len(gates),
                gate_names=sorted({g for _, g, _, _ in gates}))


# ---- enumeration-based quantities ---------------------------------------------

class AcceptAll(LogicalAnalyzer):
    """Keeps every data effect with fidelity 1: kept = no inner detector fired."""

    def analyze(self, cultivated_state, before_transversal):
        return 1.0, 1.0


def combinator_and_analyzer(full, inner, noisy=None, noise_level=P0):
    """The objects ``verify`` builds (verify.py:65-72); ``noisy`` overrides the
    noisy inner circuit (willow_noise)."""
    m = load_measurement(full, inner)
    if noisy is None:
        noisy = enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=noise_level)
    analyzer = accept.CliffordLogicalAnalyzer(
        data_indices=m.DATA_INDICES, stabilizer_generators=m.STABILIZER_GENERATORS,
        logical_s=m.LOGICAL_S)
    return m, noisy, FaultCombinator(noisy), analyzer


def uniform_odds(comb: FaultCombinator, p: float) -> np.ndarray:
    """cliffordea's per-fault odds at uniform noise level p (fault_combinator.py:228-233)."""
    o = comb.get_index_to_odds(p)
    return np.array([o[i] for i in range(comb.fault_count)])


def odds_from_circuit(comb: FaultCombinator) -> np.ndarray:
    """Per-fault odds for location-dependent channel strengths (see module doc).

    Each location's probability is the gate argument of its instruction in
    ``comb.circuit.noisy_circuit``; the elementary events of a location are
    independent with probability ``_decomposed_probability(class, p_loc)``.
    The odd-parity probability of a fault index is (1 - prod(1 - 2 q_e)) / 2.
    """
    from cliffordea.enum.circuit_tools import split_by_ticks
    probs: dict = {}
    for ts, layer in enumerate(split_by_ticks(comb.circuit.noisy_circuit)):
        for ins in layer:
            name = ins.name
            args = ins.gate_args_copy()
            p = args[0] if args else 0.0
            if name == "DEPOLARIZE2":
                for g in ins.target_groups():
                    a, b = sorted(t.value for t in g)
                    probs.setdefault((ts, name, (a, b)), []).append(p)
            elif name == "DEPOLARIZE1" or name in _ONE_Q:
                for t in ins.targets_copy():
                    probs.setdefault((ts, name, (t.value,)), []).append(p)
    decay = np.ones(comb.fault_count)
    groups = comb.circuit.group_error_events_by_location()
    fault_iter = iter(comb._event_fault_indices)
    for (ts, name, targets), group in groups.items():
        cls = classify(name)
        per = {0: 1, 1: 3, 2: 15}[cls]
        ps = probs[(ts, name, tuple(t.value for t in targets))]
        assert len(ps) * per == len(group), (ts, name, targets, ps, len(group))
        for p in ps:
            q = FaultCombinator._decomposed_probability(cls, p) if p > 0 else 0.0
            for _ in range(per):
                decay[next(fault_iter)] *= 1 - 2 * q
    assert next(fault_iter, None) is None
    prob = (1 - decay) / 2
    return prob / (1 - prob)


from cliffordea.enum.constants import ONE_QUBIT_ERROR_EVENTS as _ONE_Q  # noqa: E402


def weighted_sums(kept_state, odds: np.ndarray):
    """Per fault count k: (benign, malignant) sums of a * fid * prod(odds),
    a * (1 - fid) * prod(odds), and the malignant / benign configuration counts."""
    rows = []
    for effects in kept_state:
        ben = mal = 0.0
        nb = nm = 0
        for a, fid, cfgs in effects.values():
            w = sum(math.prod(odds[i] for i in cfg) for cfg in cfgs)
            ben += a * fid * w
            mal += a * (1 - fid) * w
            if a > 0:
                if fid == 1:
                    nb += len(cfgs)
                else:
                    nm += len(cfgs)
        rows.append(dict(benign=ben, malignant=mal, n_benign=nb, n_malignant=nm))
    return rows


def rate_and_acceptance(kept_state, odds):
    rows = weighted_sums(kept_state, odds)
    ben = sum(r["benign"] for r in rows)
    mal = sum(r["malignant"] for r in rows)
    norm = float(np.prod(1 / (1 + odds)))
    cb = np.cumsum([r["benign"] for r in rows])
    cm = np.cumsum([r["malignant"] for r in rows])
    return dict(rate=mal / (ben + mal), acceptance=norm * (ben + mal),
                rate_by_mfc=[float(m / (b + m)) for b, m in zip(cb, cm)],
                malignant_weight_by_k=[r["malignant"] * norm for r in rows],
                acceptance_by_k=[norm * (r["benign"] + r["malignant"]) for r in rows],
                counts=[(r["n_benign"], r["n_malignant"]) for r in rows])


def enumerated(full, inner, p_list=P_LIST, mfc=3, states=("T", "S"), noisy=None,
               detectors_mfc=None):
    """Enumeration at the noise levels of ``p_list`` (uniform), or for the
    given ``noisy`` circuit (p_list ignored): T/S rate, T/S acceptance, and
    the detectors-only acceptance (``AcceptAll``)."""
    m, noisy_c, comb, analyzer = combinator_and_analyzer(full, inner, noisy=noisy)
    kept = comb.get_kept_effects(logical_analyzer=analyzer, max_fault_count=mfc,
                                 cultivated_states=states)
    kept_all = comb.get_kept_effects(logical_analyzer=AcceptAll(m.DATA_INDICES, m.LOGICAL_S),
                                     max_fault_count=detectors_mfc or mfc,
                                     cultivated_states=("T",))["T"]
    out = {}
    levels = [None] if noisy is not None else list(p_list)
    for p in levels:
        odds = odds_from_circuit(comb) if p is None else uniform_odds(comb, p)
        rec = {s: rate_and_acceptance(kept[s], odds) for s in states}
        if p is not None:  # cross-check against cliffordea's own rate
            for s in states:
                ref = float(comb.error_rates_per_kept_shot(kept[s], noise_levels=[p])[0])
                rec[s]["cliffordea_rate"] = ref
                assert abs(rec[s]["rate"] - ref) <= 1e-9 * max(ref, 1e-30) + 1e-18, (s, p, ref)
        rec["detectors"] = rate_and_acceptance(kept_all, odds)
        rec["mean_faults"] = float(np.sum(odds / (1 + odds)))
        out["custom" if p is None else p] = rec
    return out, comb


# ---- stim Monte Carlo ---------------------------------------------------------

def mc_acceptance(noisy: stim.Circuit, shots: int, seed: int = 2026, batch: int = 1_000_000,
                  readout=None) -> dict:
    """Fraction of shots with no detector event.

    ``readout``: optional {measurement index: (p_flip_if_0, p_flip_if_1)};
    then measurements are sampled raw (``noisy`` must carry no flip on those
    measurements), flipped asymmetrically by their actual outcome, and turned
    into detection events with stim's m2d converter.
    """
    kept = 0
    rng = np.random.default_rng(seed)
    if readout is None:
        sampler = noisy.compile_detector_sampler(seed=seed)
    else:
        sampler = noisy.compile_sampler(seed=seed)
        conv = noisy.compile_m2d_converter()
        idx = np.array(sorted(readout))
        p0 = np.array([readout[i][0] for i in idx])
        p1 = np.array([readout[i][1] for i in idx])
    done = 0
    while done < shots:
        n = min(batch, shots - done)
        if readout is None:
            det = sampler.sample(n, bit_packed=True)
        else:
            meas = sampler.sample(n)
            sub = meas[:, idx]
            u = rng.random(sub.shape)
            flip = np.where(sub, u < p1, u < p0)
            meas[:, idx] = sub ^ flip
            det = conv.convert(measurements=meas, append_observables=False)
            det = np.packbits(det, axis=1, bitorder="little")
        kept += int(np.count_nonzero(~det.any(axis=1)))
        done += n
    a = kept / shots
    se = math.sqrt(a * (1 - a) / shots)
    return dict(acceptance=a, se=se, rel_se=se / a if a else float("inf"), shots=shots,
                kept=kept, seed=seed)


# ---- driver -------------------------------------------------------------------

def run(out: Path, max_shots=None):
    t0 = time.perf_counter()
    rec = {"started": kst_now(), "settings": dict(
        noise="enum.noise.uniformly_depolarize (cliffordea enum/noise/main.py:9)",
        p_list=P_LIST, p_table=P0, max_fault_count=[2, 3], states=["T", "S"],
        acceptance_mc="stim detector sampler on the same noisy inner circuit; kept = no detector "
                      "fired; 10,000,000 shots at p = 0.001 and 4,000,000 at the other p",
        acceptance_enum="prod(1-q_i) * sum of kept accept-weighted odds products, truncated at "
                        "max_fault_count 3 (T/S) and 4 (detectors only)"),
        "designs": {}}
    for name, d in designs().items():
        full, inner = load(d)
        r = dict(willow=d["willow"], flags=d["flags"], form=d["form"], note=d["note"],
                 files=[str(x) for x in d["paths"]], **structure(inner))
        for mfc in (2, 3):
            v = verify(full, inner, max_fault_count=mfc, noise_level=P0)
            r[f"mfc{mfc}"] = dict(T=v["T"], S=v["S"], rate=v["error_rate_per_kept_shot"],
                                  fault_count=v["fault_count"], runtime_s=v["runtime_s"])
        en, _ = enumerated(full, inner, mfc=3, detectors_mfc=4)
        r["enum"] = {str(p): v for p, v in en.items()}
        m = load_measurement(full, inner)
        r["mc"] = {}
        for p in P_LIST:
            noisy = enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=p)
            shots = 10_000_000 if p == P0 else 4_000_000
            if max_shots is not None:
                shots = min(shots, max_shots)
            r["mc"][str(p)] = mc_acceptance(noisy, shots, seed=zlib.crc32(f"{name}{p}".encode()))
        a = r["mc"][str(P0)]
        r["table"] = dict(
            rate_T_mfc3=r["mfc3"]["rate"]["T"], acceptance=a["acceptance"], acceptance_se=a["se"],
            attempts=1 / a["acceptance"],
            T_error_per_attempt=r["mfc3"]["rate"]["T"] * a["acceptance"])
        rec["designs"][name] = r
        print(name, kst_now(), r["mfc3"]["T"], f"acc {a['acceptance']:.5f}±{a['se']:.5f}",
              f"enum-det {en[P0]['detectors']['acceptance']:.5f}",
              f"enum-T {en[P0]['T']['acceptance']:.5f}", flush=True)
        (out / "comparison.json").write_text(json.dumps(rec, indent=1, default=str))
    rec["finished"] = kst_now()
    rec["runtime_s"] = time.perf_counter() - t0
    (out / "comparison.json").write_text(json.dumps(rec, indent=1, default=str))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--max-shots", type=int, default=None)
    a = ap.parse_args()
    run(Path(a.out), a.max_shots)


if __name__ == "__main__":
    main()
