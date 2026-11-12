"""The 105-qubit Willow grid as a set of (row, col).

SOURCE: Google's published device specification shipped with Cirq,
``cirq_google/devices/specifications/willow_pink_d7v1-2024_08_16_device_spec_for_grid_device.proto.txt``
from the ``cirq-google==1.7.0`` wheel (copy kept in ``nnflags/data/``,
sha256 a9013ac5f78e5514d1c7349c077eee49264aa80ccd2b8b3b49190898297cee5c).
Qubit ids there are "row_col". The file lists 105 valid qubits and 182
two-qubit targets, and the targets are exactly the pairs with
|r-r'| + |c-c'| == 1 (checked in tests/test_willow.py).

Cross-checked (RESULTS_step3.md, task C): the list is identical, row by row
and with the same (row, col) labels, to the "Qubit grid" on p. 2 of Google's
Willow spec sheet (Dec 9 2024), and matches the 105 qubits of Fig. 1a of
"Quantum error correction below the surface code threshold" (arXiv:2408.13687)
up to the figure's 45-degree rotation. Everything else in nnflags only needs a
set of (row, col) tuples, so another list can be swapped in via ``grid=``.

Readout line = r + c: Google's Hardware Experiment Proposal Guidance (March
2026): "Readout lines run diagonally across the chip (i.e., such that in the
diagram on page 2 of the spec sheet, row+col = const)."
"""
from pathlib import Path
import re

Qubit = tuple[int, int]

_ROWS = {
    0: range(6, 9),
    1: range(5, 9),
    2: range(4, 11),
    3: range(3, 11),
    4: range(2, 13),
    5: range(1, 13),
    6: range(0, 15),
    7: range(2, 14),
    8: range(2, 13),
    9: range(4, 12),
    10: range(4, 11),
    11: range(6, 10),
    12: range(6, 9),
}

WILLOW: frozenset[Qubit] = frozenset((r, c) for r, cols in _ROWS.items() for c in cols)
"""The 105 Willow qubits as (row, col)."""

SPEC_FILE = Path(__file__).with_name("data") / \
    "willow_pink_d7v1-2024_08_16_device_spec_for_grid_device.proto.txt"


def neighbours(q: Qubit, grid: frozenset[Qubit] = WILLOW) -> list[Qubit]:
    """Qubits of ``grid`` at Manhattan distance 1 from ``q``."""
    r, c = q
    return [n for n in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)) if n in grid]


def is_unit_step(a, b) -> bool:
    """Axis-aligned distance 1. Equals |r-r'|+|c-c'| == 1 on integer points,
    and also rejects half-integer diagonal steps such as (1,1)-(1.5,0.5)."""
    return sorted((abs(a[0] - b[0]), abs(a[1] - b[1]))) == [0, 1]


def is_edge(a: Qubit, b: Qubit, grid: frozenset[Qubit] | None = WILLOW) -> bool:
    """Whether (a, b) is an edge of the hardware graph G (grid=None: any points)."""
    return (grid is None or (a in grid and b in grid)) and is_unit_step(a, b)


def edges(grid: frozenset[Qubit] = WILLOW) -> set[tuple[Qubit, Qubit]]:
    """All edges of G as sorted pairs."""
    return {tuple(sorted((q, n))) for q in grid for n in neighbours(q, grid)}


def readout_line(q: Qubit) -> int:
    """Readout line of (r, c) = r + c (first-ex.md; Google's proposal guidance)."""
    return q[0] + q[1]


def load_spec_file(path: Path = SPEC_FILE) -> tuple[set[Qubit], set[tuple[Qubit, Qubit]]]:
    """Parse qubits and two-qubit targets from the Cirq device-spec text proto."""
    text = path.read_text()
    to_q = lambda s: tuple(map(int, s.split("_")))
    qubits = {to_q(s) for s in re.findall(r'valid_qubits: "(\d+_\d+)"', text)}
    pairs = re.findall(r'ids: "(\d+_\d+)"\s*ids: "(\d+_\d+)"', text)
    return qubits, {tuple(sorted((to_q(a), to_q(b)))) for a, b in pairs}


def ascii_map(grid: frozenset[Qubit] = WILLOW, marks: dict[Qubit, str] | None = None) -> str:
    """Text picture of the grid; ``marks`` overrides the '#' for given qubits."""
    marks = marks or {}
    rows = range(min(r for r, _ in grid), max(r for r, _ in grid) + 1)
    cols = range(min(c for _, c in grid), max(c for _, c in grid) + 1)
    return "\n".join(
        f"{r:2d} " + "".join(marks.get((r, c), "#") if (r, c) in grid else "." for c in cols)
        for r in rows)
