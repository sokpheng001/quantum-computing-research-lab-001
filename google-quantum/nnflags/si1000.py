"""SI1000 noise comparison (the model Google used, Rosenfeld et al. arXiv:2512.13908).

SI1000 (Gidney, Newman, Fowler, Broughton, Quantum 5, 605 (2021)), at strength p:
    CZ                         DEPOLARIZE2(p)
    single-qubit gate (H)      DEPOLARIZE1(p / 10)
    idle in a gate TICK        DEPOLARIZE1(p / 10)
    idle in a TICK with a
      measurement or reset     DEPOLARIZE1(2 p)      ("resonator idle")
    measurement                flip with 5 p
    reset (R, MR)              X_ERROR(2 p)
Google matched its experiment with p = 0.23 % (Figs. 3, 4, S19-S22).

Applied to the native CZ + H circuits with cliffordea's conventions, exactly as
willow_noise.noisy_native: the first (MPP) and last (trailing reset) TICKs are
noiseless, data qubits are noisy from the MPP marker on, and a qubit measured
without reset gets no further noise.

    .venv/bin/python -m nnflags.si1000
"""

import json
import time
import zlib
from pathlib import Path

import stim

from cliffordea.enum.circuit_tools import split_by_ticks

from nnflags import comparison as CMP
from nnflags import continuing_validate as CV
from nnflags import willow_noise as WN
from nnflags.verify import load_measurement

P_LIST = (0.0023, 0.001)
SHOTS = 4_000_000


def si1000(inner: stim.Circuit, p: float) -> stim.Circuit:
    layers = split_by_ticks(inner)
    data = set(WN.CMP_data(inner))
    system = set()
    for op in inner:
        if isinstance(op, stim.CircuitInstruction) and op.name not in (
                "QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "MPP"):
            system |= {t.value for t in op.targets_copy() if t.qubit_value is not None}
    system -= data
    out = stim.Circuit()
    for t, L in enumerate(layers):
        if t:
            out.append("TICK")
        noisy_tick = 0 < t < len(layers) - 1
        busy, after = set(), stim.Circuit()
        resonator = any(op.name in ("M", "MR", "R") for op in L)
        for op in L:
            n = op.name
            qs = [x.value for x in op.targets_copy() if x.qubit_value is not None]
            if n in ("M", "MR") and noisy_tick:
                for q in qs:
                    out.append(n, [q], [5 * p])
            else:
                out.append(op)
            if not noisy_tick or n in ("MPP", "QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE"):
                continue
            busy |= set(qs)
            if n == "CZ":
                for a, b in zip(qs[::2], qs[1::2]):
                    after.append("DEPOLARIZE2", [a, b], [p])
            elif n == "H":
                after.append("DEPOLARIZE1", qs, [p / 10])
            if n in ("R", "MR"):
                after.append("X_ERROR", qs, [2 * p])
        if noisy_tick:
            idle = sorted((system | (data if t > 0 else set())) - busy)
            if idle:
                after.append("DEPOLARIZE1", idle, [2 * p if resonator else p / 10])
            out += after
        for op in L:  # measured without reset: no further noise (cliffordea convention)
            if op.name == "M":
                system -= {x.value for x in op.targets_copy()}
                data -= {x.value for x in op.targets_copy()}
    return out


def designs():
    ref = CV.references()
    out = {k: ref[k] for k in ("G4-CX", "G4-G6style", "success03")}
    for n in ("success02", "success07", "success06"):
        out[f"cs{n[-2:]}"] = dict(full=stim.Circuit.from_file(f"results/continuing/{n}.full.stim"),
                                  inner=stim.Circuit.from_file(f"results/continuing/{n}.inner.stim"),
                                  native=None)
    return out


def main():
    res = {}
    for name, d in designs().items():
        t0 = time.perf_counter()
        full = d["full"]
        native = d["native"] if d["native"] is not None else WN.cx_to_native(d["inner"])
        m = load_measurement(full, native)
        r = {}
        for p in P_LIST:
            noisy = si1000(m.INNER_CIRCUIT, p)
            en, _ = CMP.enumerated(full, native, mfc=4, noisy=noisy)
            e = en["custom"]
            mc = CMP.mc_acceptance(noisy, SHOTS, seed=zlib.crc32(f"{name}si{p}".encode()))
            r[str(p)] = dict(rate_T_mfc3=e["T"]["rate_by_mfc"][3], rate_T_mfc4=e["T"]["rate"],
                             T_counts=e["T"]["counts"], acceptance=mc["acceptance"], mc=mc,
                             attempts=1 / mc["acceptance"],
                             T_error_per_attempt=e["T"]["rate"] * mc["acceptance"])
            print(f"{name:11s} SI1000 p={p*100:.2f}%  1 in {1 / e['T']['rate_by_mfc'][3]:,.0f} (mfc 3), "
                  f"1 in {1 / e['T']['rate']:,.0f} (mfc 4)  acceptance {mc['acceptance']*100:.2f}%", flush=True)
        r["native_ticks"] = native.num_ticks
        r["runtime_s"] = time.perf_counter() - t0
        res[name] = r
    Path("results/si1000.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
