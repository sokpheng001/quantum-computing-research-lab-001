"""Exact low-fault-count verification of a custom double-check circuit.

Reuses cliffordea end to end; nothing of the acceptance algorithm is
reimplemented:
  * The two circuits are written to a temporary directory laid out like
    cliffordea's bundled ``stim_files/<name>/{inner,full}.stim`` and loaded by
    cliffordea's own ``LogicalMeasurement.__init__`` (via a subclass that only
    changes ``_CIRCUIT_PARENT``). So DATA_INDICES, STABILIZER_GENERATORS and
    LOGICAL_S come from ``find_data_indices`` / ``find_stabilizer_generators`` /
    ``find_logical_s_gate`` exactly as for the bundled circuits.
  * Then the README "Complete enumeration workflow": ``uniformly_depolarize``,
    ``CliffordLogicalAnalyzer``, ``FaultCombinator.get_kept_effects``,
    ``summarize_contributions``, ``error_rates_per_kept_shot``.
"""
from pathlib import Path
import tempfile
import time

import stim

from cliffordea import accept, enum
from cliffordea.enum.circuits.main import LogicalMeasurement

STATES = ("T", "S")


def _as_circuit(c) -> stim.Circuit:
    return c if isinstance(c, stim.Circuit) else stim.Circuit.from_file(str(c))


def load_measurement(stim_circuit_full, stim_circuit_inner) -> LogicalMeasurement:
    """Build a cliffordea LogicalMeasurement from in-memory circuits or paths."""
    full, inner = _as_circuit(stim_circuit_full), _as_circuit(stim_circuit_inner)
    with tempfile.TemporaryDirectory(prefix="nnflags_") as tmp:
        # LogicalMeasurement reads <_CIRCUIT_PARENT>/d{distance}a{ancilla_count}/;
        # the numbers are only a directory label here.
        (Path(tmp) / "d0a0").mkdir()
        (Path(tmp) / "d0a0" / "inner.stim").write_text(str(inner))
        (Path(tmp) / "d0a0" / "full.stim").write_text(str(full))

        class _Custom(LogicalMeasurement):
            _CIRCUIT_PARENT = Path(tmp)

        return _Custom(distance=0, ancilla_count=0, flag_count=0)


def verify(
        stim_circuit_full,
        stim_circuit_inner,
        max_fault_count: int = 2,
        noise_level: float = 1e-3,
        states: tuple[str, ...] = STATES,
) -> dict:
    """Enumerate kept fault configurations of a double check.

    :return: {"T": {k: {"benign": n, "malignant": n}}, "S": {...},
        "summary": summarize_contributions DataFrame,
        "error_rate_per_kept_shot": {state: rate at noise_level},
        "malignant_configurations": {state: [(k, fault indices), ...]},
        "fault_count", "signature_count", "runtime_s", "settings"}.
    Malignant/benign counts are the ``configuration_count`` columns of
    cliffordea's ``summarize_contributions``.
    """
    t0 = time.perf_counter()
    m = load_measurement(stim_circuit_full, stim_circuit_inner)
    noisy_circuit = enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=noise_level)
    analyzer = accept.CliffordLogicalAnalyzer(
        data_indices=m.DATA_INDICES,
        stabilizer_generators=m.STABILIZER_GENERATORS,
        logical_s=m.LOGICAL_S,
    )
    combinator = enum.FaultCombinator(noisy_circuit)
    kept = combinator.get_kept_effects(
        logical_analyzer=analyzer,
        max_fault_count=max_fault_count,
        cultivated_states=states,
    )
    summary = combinator.summarize_contributions(kept)
    result: dict = {}
    for state in states:
        result[state] = {
            k: {"benign": int(summary.loc[(state, k), ("configuration_count", "benign")]),
                "malignant": int(summary.loc[(state, k), ("configuration_count", "malignant")])}
            for k in range(max_fault_count + 1)
        }
    result["summary"] = summary
    result["error_rate_per_kept_shot"] = {
        s: float(combinator.error_rates_per_kept_shot(kept[s], noise_levels=[noise_level])[0])
        for s in states}
    result["malignant_configurations"] = {
        s: [(k, cfg) for k, effects in enumerate(kept[s])
            for p, fid, cfgs in effects.values() if p > 0 and fid != 1 for cfg in cfgs]
        for s in states}
    result["fault_count"] = combinator.fault_count
    result["signature_count"] = combinator.signature_count
    result["data_indices"] = m.DATA_INDICES
    result["runtime_s"] = time.perf_counter() - t0
    result["settings"] = dict(max_fault_count=max_fault_count, noise_level=noise_level,
                              noise_model="enum.noise.uniformly_depolarize", states=states)
    return result


def bundled_paths(name: str) -> tuple[Path, Path]:
    """(full, inner) paths of a bundled double check, e.g. "d3a6f2"."""
    d = LogicalMeasurement.__init__.__globals__["_STIM_FILES_DIR"] / "double_checks" / name
    return d / "full.stim", d / "inner.stim"
