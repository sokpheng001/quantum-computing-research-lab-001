"""Convert a Crumble URL (algassert.com/crumble#circuit=...) into a stim.Circuit.

Crumble's URL encoding: instructions are separated by ';', targets by '_',
'Q(' = QUBIT_COORDS, 'DT' = DETECTOR, 'OI' = OBSERVABLE_INCLUDE,
POLYGON / MARKX / MARKY / MARKZ are Crumble-only drawing marks (kept as
'#!pragma' comments, which stim ignores), and tags are percent-encoded
('H%5Binjection%5D' = 'H[injection]'). Gate names may themselves contain '_'
(S_DAG, H_YZ, SQRT_X_DAG), so the name is matched against stim's gate list,
longest first, instead of splitting blindly.
"""
import re
from urllib.parse import unquote

import stim

_ALIASES = {"Q": "QUBIT_COORDS", "DT": "DETECTOR", "OI": "OBSERVABLE_INCLUDE"}
_MARKS = ("POLYGON", "MARKX", "MARKY", "MARKZ", "MARK")
_GATES = sorted(set(stim.gate_data()) | set(_ALIASES), key=len, reverse=True)


def _split_name(instr: str):
    for name in _MARKS + tuple(_GATES):
        if instr.startswith(name) and (len(instr) == len(name) or instr[len(name)] in "_([ "):
            return name, instr[len(name):]
    raise ValueError(f"Unknown Crumble instruction: {instr!r}")


def crumble_to_stim_text(url: str) -> str:
    """Stim text of a Crumble URL (or of the bare '#circuit=' payload)."""
    payload = url.split("#circuit=", 1)[-1].strip()
    lines = []
    for instr in payload.split(";"):
        instr = unquote(instr)
        if not instr:
            continue
        name, rest = _split_name(instr)
        m = re.match(r"(\[[^\]]*\])?(\([^)]*\))?_?(.*)$", rest)
        tag, args, targets = m.group(1) or "", m.group(2) or "", m.group(3)
        targets = " ".join(t for t in targets.split("_") if t)
        if name in _MARKS:
            lines.append(f"#!pragma {name}{args} {targets}".rstrip())
        else:
            lines.append(f"{_ALIASES.get(name, name)}{tag}{args} {targets}".rstrip())
    return "\n".join(lines) + "\n"


def crumble_to_stim(url: str) -> stim.Circuit:
    return stim.Circuit(crumble_to_stim_text(url))
