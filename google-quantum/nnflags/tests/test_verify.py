"""verify() on the bundled files must reproduce Step 0 (DoubleCheck path) exactly."""
import pytest

from cliffordea import accept, enum
from nnflags.verify import bundled_paths, load_measurement, verify


def step0(flag_count):
    """README "Complete enumeration workflow", verbatim."""
    circuit = enum.circuits.DoubleCheck(distance=3, ancilla_count=6, flag_count=flag_count)
    noisy_circuit = enum.noise.uniformly_depolarize(circuit.INNER_CIRCUIT, noise_level=1e-3)
    analyzer = accept.CliffordLogicalAnalyzer(
        data_indices=circuit.DATA_INDICES,
        stabilizer_generators=circuit.STABILIZER_GENERATORS,
        logical_s=circuit.LOGICAL_S,
    )
    combinator = enum.FaultCombinator(noisy_circuit)
    kept = combinator.get_kept_effects(
        logical_analyzer=analyzer, max_fault_count=2, cultivated_states=("S", "T"))
    return circuit, combinator, kept, combinator.summarize_contributions(kept)


@pytest.mark.parametrize("name,flag_count,malignant_t2", [("d3a6", 0, 4), ("d3a6f2", 2, 0)])
def test_verify_reproduces_step0(name, flag_count, malignant_t2):
    circuit, combinator, kept, summary = step0(flag_count)
    full, inner = bundled_paths(name)
    r = verify(full, inner, max_fault_count=2)

    # Same derived code properties as DoubleCheck.
    m = load_measurement(full, inner)
    assert m.DATA_INDICES == circuit.DATA_INDICES
    assert m.STABILIZER_GENERATORS == circuit.STABILIZER_GENERATORS
    assert m.LOGICAL_S == circuit.LOGICAL_S
    assert m.INNER_CIRCUIT == circuit.INNER_CIRCUIT

    # Identical summary table (counts and weights) and fault basis.
    assert r["summary"].sort_index().equals(summary.sort_index())
    assert r["fault_count"] == combinator.fault_count
    assert r["signature_count"] == combinator.signature_count

    # Expected baseline numbers.
    assert r["T"][2]["malignant"] == malignant_t2
    assert all(r["S"][k]["malignant"] == 0 for k in range(3))
    assert all(r["T"][k]["malignant"] == 0 for k in range(2))
    assert len(r["malignant_configurations"]["T"]) == malignant_t2


def test_verify_accepts_in_memory_circuits():
    full, inner = bundled_paths("d3a6")
    import stim
    r = verify(stim.Circuit.from_file(str(full)), stim.Circuit.from_file(str(inner)))
    assert r["T"][2]["malignant"] == 4
