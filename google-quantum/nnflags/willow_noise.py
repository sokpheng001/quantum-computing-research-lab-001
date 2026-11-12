"""Task 4 of the comparison round: the designs under realistic Willow noise.

Calibration: cirq_google's bundled
``cirq_google/devices/calibrations/willow_pink_d7v1-2024_08_16_calibration.json``
(the same Willow snapshot as nnflags/data's device spec), loaded with
``cirq_google.Calibration`` from a ``v2.metrics_pb2.MetricsSnapshot``.

Models (all channels Pauli, placed after the operations of each TICK as in
cliffordea's ``uniformly_depolarize``: first and last TICK noiseless, data
noisy from the MPP marker on, a qubit measured without reset is dropped):

* "calibration" (primary), per qubit / per coupler at the circuit's Willow
  positions:
    - CZ: DEPOLARIZE2(e2), e2 = two_qubit_parallel_cz_gate_xeb_pauli_error_per_cycle
      minus the single_qubit_rb_pauli_error_per_gate of both qubits (an XEB
      cycle is one random single-qubit gate on each qubit plus the CZ; the H
      gates of our circuits get their own noise, so not subtracting would
      count them twice). Floored at 0. Pairs without a coupler (only in the
      "what if" placement of d3a6f2): the median e2 over the 182 couplers.
      cirq_google's own converter does not subtract
      (engine/calibration_to_noise_properties.py:164-176).
    - H: DEPOLARIZE1(single_qubit_rb_pauli_error_per_gate).
    - Readout: p00 = P(read 1 | 0) = single_qubit_p00_error,
      p11 = P(read 0 | 1) = single_qubit_p11_error. Monte Carlo: exact,
      asymmetric by the actual outcome. Enumeration (cliffordea needs a flip
      probability per measurement): symmetric (p00 + p11) / 2.
    - Reset: X_ERROR(RESET_ERROR) after R / MR (assumption, not in the file).
    - Idle: amplitude + phase damping for the idle time of each qubit in a
      TICK, Pauli-twirled: px = py = (1 - exp(-t/T1)) / 4,
      pz = (1 - exp(-t/T2)) / 2 - px, as independent X_ERROR, Y_ERROR, Z_ERROR.
      T1 = single_qubit_idle_t1_micros. T2 is not in the file: 1/T2 = 1/(2 T1)
      + 1/Tphi with Tphi from single_qubit_rb_incoherent_error_per_gate exactly
      as cirq_google derives it (calibration_to_noise_properties.py:142-152,
      microwave gate time = the 1q duration below).
* "spec" (secondary), Willow spec-sheet averages, uniform: CZ 0.33 %,
  1q 0.035 %, readout 0.77 % (symmetric), T1 = 68 us, T2 = T1 (assumption),
  same durations and reset error.

Durations (ns): 1q 25, CZ 42, measurement 600 (Google proposal guidance),
reset 200 (assumption); MR = measurement + reset. A TICK lasts as long as
its longest operation; a qubit idles for (TICK duration - its own operation).

The circuits are in native CZ + H form (``cx_to_native``) at their Willow
positions. cliffordea's FaultCombinator takes any noisy stim circuit built
from X/Y/Z_ERROR, DEPOLARIZE1/2 and measurement flips
(cultivation_circuit.py:296-335, combinators/_base.py:141-162; other channel
names are skipped silently), but it ignores the channel strengths: its rates
use one global noise level (fault_combinator.py:164-225, 558-605). So the
configurations and their accept/fidelity values come from cliffordea, and
the weights from ``comparison.odds_from_circuit`` (per-location strengths,
cliffordea's own decomposition).

Usage: python -m nnflags.willow_noise [--out results]
"""
import argparse
import json
import math
import time
import zlib
from pathlib import Path

import numpy as np
import stim

from cliffordea import enum
from cliffordea.enum.circuit_tools import split_by_ticks

from nnflags import comparison as CMP
from nnflags import equivalence as Q
from nnflags.verify import load_measurement, verify
from nnflags.willow import WILLOW, edges

CAL_FILE = (Path(__file__).resolve().parents[1] / ".venv" / "lib" / "python3.12" / "site-packages"
            / "cirq_google" / "devices" / "calibrations"
            / "willow_pink_d7v1-2024_08_16_calibration.json")
DUR = dict(q1=25.0, cz=42.0, meas=600.0, reset=200.0)
RESET_ERROR = 0.001
MFC_CHECK = 4  # enumerate to 4 faults; the table uses the mfc-3 truncation, mfc 4 = convergence check
SPEC = dict(cz=0.0033, q1=0.00035, meas=0.0077, t1_us=68.0)
R = Path("results")


# ---- calibration ----------------------------------------------------------------

def load_calibration(path=CAL_FILE) -> dict:
    import cirq_google as cg
    from cirq_google.api import v2
    from google.protobuf import json_format
    d = json.loads(Path(path).read_text())
    snap = json_format.ParseDict(d["metrics"], v2.metrics_pb2.MetricsSnapshot())
    cal = cg.Calibration(snap)
    q1 = lambda key: {(q.row, q.col): v[0] for (q,), v in cal[key].items()}
    cal_d = dict(
        t1_us=q1("single_qubit_idle_t1_micros"), e1=q1("single_qubit_rb_pauli_error_per_gate"),
        incoh=q1("single_qubit_rb_incoherent_error_per_gate"),
        p00=q1("single_qubit_p00_error"), p11=q1("single_qubit_p11_error"),
        xeb={tuple(sorted(((a.row, a.col), (b.row, b.col)))): v[0] for (a, b), v in
             cal["two_qubit_parallel_cz_gate_xeb_pauli_error_per_cycle"].items()})
    assert len(cal_d["t1_us"]) == 105 and len(cal_d["xeb"]) == 182
    assert set(cal_d["t1_us"]) == set(WILLOW) and set(cal_d["xeb"]) == edges(WILLOW)
    e2, floored = {}, 0
    for (a, b), x in cal_d["xeb"].items():
        v = x - cal_d["e1"][a] - cal_d["e1"][b]
        floored += v < 0
        e2[(a, b)] = max(v, 0.0)
    cal_d["e2"], cal_d["e2_floored"] = e2, floored
    cal_d["e2_median"] = float(np.median(list(e2.values())))
    t2 = {}
    for q, t1 in cal_d["t1_us"].items():
        t1_ns = t1 * 1000
        tphi_err = cal_d["incoh"][q] - DUR["q1"] / (3 * t1_ns)
        tphi_ns = 1e10 if tphi_err <= 0 else DUR["q1"] / (3 * tphi_err)
        t2[q] = 1 / (1 / (2 * t1_ns) + 1 / tphi_ns) / 1000
    cal_d["t2_us"] = t2
    return cal_d


def calibration_summary(cal) -> dict:
    def st(v):
        v = np.array(list(v.values()))
        return dict(n=len(v), mean=float(v.mean()), median=float(np.median(v)),
                    min=float(v.min()), max=float(v.max()))
    return {k: st(cal[k]) for k in ("t1_us", "t2_us", "e1", "incoh", "p00", "p11", "xeb", "e2")} | dict(
        e2_floored=cal["e2_floored"])


# ---- CX form -> native CZ + H ----------------------------------------------------

def cx_to_native(inner: stim.Circuit) -> stim.Circuit:
    """Native CZ + H form of a cliffordea CX-form inner circuit.

    Frame bit f[q] (actual state = H^f |state of the CX form>): CX c->t needs
    f[c] = 0, f[t] = 1 at the CZ (H_t CZ H_t = CX); M / MR need f = 0, MX / MRX
    need f = 1; R sets f = 0, RX = R with f = 1 (|+> = H|0>), MR -> f = 0,
    MRX -> MR with f = 1. Hadamards are emitted lazily, as one H-only TICK
    before a TICK whose requirements differ from the current frames; data
    qubits must be back at f = 0 before the last measurement TICK. The last
    TICK (cliffordea's noiseless trailing reset) maps RX -> R. Measurement order,
    detectors, QUBIT_COORDS and the MPP marker are unchanged.
    """
    layers = split_by_ticks(inner)
    data = set(CMP_data(inner))
    f: dict[int, int] = {}
    last_meas = max(t for t, L in enumerate(layers) if any(
        stim.gate_data(op.name).produces_measurements and op.name != "MPP"
        for op in L if isinstance(op, stim.CircuitInstruction)))
    out = []
    for t, L in enumerate(layers):
        if t == 0 or t == len(layers) - 1:
            new = stim.Circuit()
            for op in L:
                if op.name == "RX":
                    new.append("R", op.targets_copy())
                elif t > 0 and op.name not in ("R", "DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS"):
                    raise ValueError(f"unexpected op in trailing TICK: {op}")
                else:
                    new.append(op)
            out.append(new)
            continue
        need = {}
        for op in L:
            if not isinstance(op, stim.CircuitInstruction):
                raise ValueError("REPEAT not supported")
            n, ts = op.name, [x.value for x in op.targets_copy()]
            if n == "CX":
                for c, tg in zip(ts[::2], ts[1::2]):
                    need[c], need[tg] = 0, 1
            elif n in ("M", "MR"):
                need.update({q: 0 for q in ts})
            elif n in ("MX", "MRX"):
                need.update({q: 1 for q in ts})
        if t == last_meas:
            need.update({q: 0 for q in data})
        flip = sorted(q for q, v in need.items() if f.get(q, 0) != v)
        if flip:
            h = stim.Circuit()
            h.append("H", flip)
            out.append(h)
            for q in flip:
                f[q] = 1 - f.get(q, 0)
        new = stim.Circuit()
        for op in L:
            n, ts, args = op.name, op.targets_copy(), op.gate_args_copy()
            qs = [x.value for x in ts]
            if n == "CX":
                new.append("CZ", ts)
            elif n in ("R", "RX"):
                new.append("R", ts)
                f.update({q: int(n == "RX") for q in qs})
            elif n in ("M", "MX"):
                new.append("M", ts, args)
            elif n in ("MR", "MRX"):
                new.append("MR", ts, args)
                f.update({q: int(n == "MRX") for q in qs})
            elif n in ("DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS", "MPP"):
                new.append(op)
            else:
                raise ValueError(f"unsupported op {n}")
        out.append(new)
    assert all(f.get(q, 0) == 0 for q in data)
    c = stim.Circuit()
    for k, L in enumerate(out):
        if k:
            c.append("TICK")
        c += L
    return c


def CMP_data(inner):
    for op in inner:
        if op.name == "MPP":
            return [t.qubit_value for t in op.targets_copy() if t.qubit_value is not None]
    raise ValueError("no MPP")


# ---- placements -----------------------------------------------------------------

def placement(name: str, inner_cx: stim.Circuit) -> tuple[dict, str]:
    """Willow (row, col) of every qubit, and where it comes from."""
    if name == "d3a6":
        e = json.loads((R / "embed_search_d3a6.json").read_text())["example_min_embedding"]["exempt"]
        return ({int(k): tuple(v) for k, v in e.items()},
                "results/embed_search_d3a6.json example_min_embedding['exempt'] (1 strict "
                "readout conflict, the minimum over all 182,968 embeddings); NOT Willow-compatible")
    if name == "d3a6f2":
        e = json.loads((R / "step1.json").read_text())["d3a6f2_willow"]["embedding"]
        return ({int(k): tuple(v) for k, v in e.items()},
                "results/step1.json d3a6f2_willow (d3a6 placement + best free flag spots; "
                "3 couplers missing, qubit 6 has 6 partners); NOT Willow-compatible")
    coords = inner_cx.get_final_qubit_coordinates()
    return {q: tuple(int(x) for x in c) for q, c in coords.items()}, "own QUBIT_COORDS (Willow)"


# ---- noise ----------------------------------------------------------------------

def _twirl(t_ns, t1_us, t2_us):
    if t_ns <= 0:
        return 0.0, 0.0, 0.0
    a = 1 - math.exp(-t_ns / (t1_us * 1000))
    px = a / 4
    pz = (1 - math.exp(-t_ns / (t2_us * 1000))) / 2 - px
    return px, px, max(pz, 0.0)


def _xor(p, q):
    return p * (1 - q) + q * (1 - p)


def model_params(model: str, cal: dict, emb: dict):
    """Per-qubit / per-pair parameters for the qubits of ``emb``."""
    if model == "spec":
        u = lambda v: {q: v for q in emb}
        return dict(e1=u(SPEC["q1"]), p00=u(SPEC["meas"]), p11=u(SPEC["meas"]),
                    t1=u(SPEC["t1_us"]), t2=u(SPEC["t1_us"]), e2=lambda a, b: SPEC["cz"])
    assert model == "calibration"
    pos = lambda q: emb[q]

    def e2(a, b):
        k = tuple(sorted((pos(a), pos(b))))
        return cal["e2"].get(k, cal["e2_median"])
    return dict(e1={q: cal["e1"][pos(q)] for q in emb}, p00={q: cal["p00"][pos(q)] for q in emb},
                p11={q: cal["p11"][pos(q)] for q in emb}, t1={q: cal["t1_us"][pos(q)] for q in emb},
                t2={q: cal["t2_us"][pos(q)] for q in emb}, e2=e2)


def _op_duration(name):
    return {"H": DUR["q1"], "CZ": DUR["cz"], "M": DUR["meas"], "MR": DUR["meas"] + DUR["reset"],
            "R": DUR["reset"]}[name]


def noisy_native(inner: stim.Circuit, prm: dict, readout="symmetric"):
    """(noisy circuit, readout map). ``readout="symmetric"``: flips (p00+p11)/2 on
    the noisy measurements (enumeration); ``"asymmetric"``: no flip in the
    circuit, map {measurement index: (p00, p11)} for ``mc_acceptance``."""
    layers = split_by_ticks(inner)
    data = set(CMP_data(inner))
    system = set()
    for op in inner:
        if isinstance(op, stim.CircuitInstruction) and op.name not in (
                "QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "MPP"):
            system |= {t.value for t in op.targets_copy() if t.qubit_value is not None}
    system -= data
    out = stim.Circuit()
    rmap = {}
    mi = 0
    for t, L in enumerate(layers):
        if t:
            out.append("TICK")
        noisy_tick = 0 < t < len(layers) - 1
        busy, after, pauli = {}, stim.Circuit(), {}
        for op in L:
            n, ts = op.name, op.targets_copy()
            qs = [x.value for x in ts if x.qubit_value is not None]
            if n == "MPP":
                out.append(op)
                mi += op.num_measurements
                continue
            if n in ("QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE"):
                out.append(op)
                continue
            if n in ("M", "MR"):
                for q in qs:
                    if noisy_tick and readout == "symmetric":
                        out.append(n, [q], [(prm["p00"][q] + prm["p11"][q]) / 2])
                    else:
                        out.append(n, [q])
                        if noisy_tick:
                            rmap[mi] = (prm["p00"][q], prm["p11"][q])
                    mi += 1
            else:
                out.append(op)
            if not noisy_tick:
                continue
            for q in qs:
                busy[q] = _op_duration(n)
            if n == "CZ":
                for a, b in zip(qs[::2], qs[1::2]):
                    after.append("DEPOLARIZE2", [a, b], [prm["e2"](a, b)])
            elif n == "H":
                for q in qs:
                    after.append("DEPOLARIZE1", [q], [prm["e1"][q]])
            if n in ("R", "MR"):
                for q in qs:
                    pauli[(q, "X")] = _xor(pauli.get((q, "X"), 0.0), RESET_ERROR)
        if noisy_tick:
            dur = max(busy.values(), default=0.0)
            for q in sorted(system | (data if t > 0 else set())):
                px, py, pz = _twirl(dur - busy.get(q, 0.0), prm["t1"][q], prm["t2"][q])
                for b, p in (("X", px), ("Y", py), ("Z", pz)):
                    if p > 0:
                        pauli[(q, b)] = _xor(pauli.get((q, b), 0.0), p)
            out += after
            for (q, b), p in sorted(pauli.items()):
                out.append(f"{b}_ERROR", [q], [p])
        for op in L:  # measured without reset: no further noise (cliffordea convention)
            if op.name == "M":
                system -= {x.value for x in op.targets_copy()}
                data -= {x.value for x in op.targets_copy()}
    return out, rmap


# ---- driver ---------------------------------------------------------------------

def designs_for_task4() -> dict:
    ds = CMP.designs()
    zz = {n: ds[n] for n in ds if n.startswith("success")}
    best3 = sorted(zz, key=lambda n: _rate_from_csv(n))[:3]
    names = list(dict.fromkeys(["success03", *best3, "d3a6f2", "G4", "d3a6"]))
    out = {}
    for n in names:
        if n == "G4":
            out[n] = dict(cx=ds["G4-CX"], native_from=ds["G4-native"])
        else:
            out[n] = dict(cx=ds[n])
    return out


def _rate_from_csv(name):
    import csv
    for r in csv.DictReader(open(R / "zz_candidates.csv")):
        if r.get("stim_file", "").endswith(f"{name}.inner.stim"):
            return float(r["ler_T_mfc3"])
    return 1.0


def run(out: Path, shots_cap=None):
    t0 = time.perf_counter()
    cal = load_calibration()
    rec = dict(started=CMP.kst_now(), calibration_file=str(CAL_FILE.relative_to(Path.cwd().resolve()))
               if CAL_FILE.is_relative_to(Path.cwd().resolve()) else str(CAL_FILE),
               calibration=calibration_summary(cal), durations_ns=DUR, reset_error=RESET_ERROR,
               spec=SPEC, designs={})
    (out / "willow_noise").mkdir(parents=True, exist_ok=True)
    for name, d in designs_for_task4().items():
        full_cx, inner_cx = CMP.load(d["cx"])
        if "native_from" in d:
            native = CMP.load(d["native_from"])[1]
            conv = "G4's own native CZ + H extraction (results/g4/G4-native_CZH.inner.stim)"
        else:
            native = cx_to_native(inner_cx)
            conv = "nnflags.willow_noise.cx_to_native (lazy H frames)"
        (out / "willow_noise" / f"{name}.native.inner.stim").write_text(str(native))
        back, info = Q.absorb_hadamards(native, CMP_data(native))
        emb, emb_src = placement(name, inner_cx)
        r = dict(conversion=conv, placement_source=emb_src,
                 placement={str(k): v for k, v in sorted(emb.items())},
                 deterministic_native=Q.is_deterministic(native),
                 absorb_back_non_cx=info["non_cx"], native_ticks=native.num_ticks,
                 cx_ticks=inner_cx.num_ticks,
                 n_cz=sum(len(op.targets_copy()) // 2 for op in native if op.name == "CZ"),
                 n_h=sum(len(op.targets_copy()) for op in native if op.name == "H"))
        # conversion keeps the malignant counts (uniform noise, p = 0.001, mfc 3)
        vc = verify(full_cx, inner_cx, max_fault_count=3)
        vn = verify(full_cx, native, max_fault_count=3)
        r["uniform_check"] = dict(cx=dict(T=vc["T"], S=vc["S"], rate=vc["error_rate_per_kept_shot"]),
                                  native=dict(T=vn["T"], S=vn["S"], rate=vn["error_rate_per_kept_shot"]),
                                  counts_equal=(vc["T"] == vn["T"] and vc["S"] == vn["S"]))
        m = load_measurement(full_cx, native)
        mc_u = CMP.mc_acceptance(enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=CMP.P0),
                                 10_000_000 if shots_cap is None else min(shots_cap, 10_000_000),
                                 seed=zlib.crc32(f"{name}uniform".encode()))
        r["uniform_native_p001"] = dict(rate_T=vn["error_rate_per_kept_shot"]["T"], acc=mc_u["acceptance"],
                                        mc=mc_u)
        r["models"] = {}
        for model in ("calibration", "spec"):
            prm = model_params(model, cal, emb)
            noisy_sym, _ = noisy_native(m.INNER_CIRCUIT, prm, "symmetric")
            noisy_asym, rmap = noisy_native(m.INNER_CIRCUIT, prm, "asymmetric")
            (out / "willow_noise" / f"{name}.{model}.noisy.stim").write_text(str(noisy_sym))
            en, comb = CMP.enumerated(full_cx, native, mfc=MFC_CHECK, noisy=noisy_sym)
            e = en["custom"]
            rate3 = e["T"]["rate_by_mfc"][3]
            shots = 4_000_000 if shots_cap is None else min(shots_cap, 4_000_000)
            seed = zlib.crc32(f"{name}{model}".encode())
            mc = CMP.mc_acceptance(noisy_asym, shots, seed=seed, readout=rmap)
            mc_sym = CMP.mc_acceptance(noisy_sym, shots, seed=seed + 1)
            r["models"][model] = dict(
                T_counts=e["T"]["counts"], S_counts=e["S"]["counts"],
                rate_T=rate3, rate_T_mfc4=e["T"]["rate"], rate_S=e["S"]["rate_by_mfc"][3],
                rate_S_mfc4=e["S"]["rate"], malignant_weight_T_by_k=e["T"]["malignant_weight_by_k"],
                acc_enum_T=e["T"]["acceptance"], acc_enum_detectors=e["detectors"]["acceptance"],
                acc_enum_detectors_by_k=e["detectors"]["acceptance_by_k"],
                mean_faults=e["mean_faults"], mc=mc, mc_symmetric_readout=mc_sym,
                attempts=1 / mc["acceptance"], T_error_per_attempt=rate3 * mc["acceptance"])
            print(name, model, CMP.kst_now(), f"rate 1 in {1 / rate3:,.0f} (mfc4 {1 / e['T']['rate']:,.0f})",
                  f"acc {mc['acceptance']:.5f}±{mc['se']:.5f}", f"sym {mc_sym['acceptance']:.5f}",
                  f"enum-det {e['detectors']['acceptance']:.5f}", e["T"]["counts"], flush=True)
        rec["designs"][name] = r
        (out / "willow_noise.json").write_text(json.dumps(rec, indent=1, default=str))
    rec["finished"] = CMP.kst_now()
    rec["runtime_s"] = time.perf_counter() - t0
    (out / "willow_noise.json").write_text(json.dumps(rec, indent=1, default=str))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--max-shots", type=int, default=None)
    a = ap.parse_args()
    run(Path(a.out), a.max_shots)


if __name__ == "__main__":
    main()
