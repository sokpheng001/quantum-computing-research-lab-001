"""Task 3 of the continuing-data search round: validate the best continuing-data
success like success03 was validated (RESULTS_comparison.md), against success03,
G4 (as run, CX form) and G4 with q7 unmeasured (G6's double check).

  * uniform p = 0.1 % (enum.noise.uniformly_depolarize), CX form: malignant T / S
    counts (verify, mfc 2 and 3), T error per kept shot (mfc 3), enumerated
    acceptance (comparison.enumerated), stim Monte Carlo acceptance (10,000,000
    shots), attempts per kept shot;
  * realistic Willow noise, native CZ + H (willow_noise.cx_to_native) at each
    circuit's Willow positions: calibration and spec-sheet models
    (willow_noise.model_params / noisy_native), enumeration to mfc 4 (table: mfc 3),
    Monte Carlo acceptance (4,000,000 shots, asymmetric readout);
  * readout checks: constraints.check_circuit strict, and with data_continue=True.

    .venv/bin/python -m nnflags.continuing_validate --new results/continuing/success00 [...]
"""
import argparse
import json
import time
import zlib
from pathlib import Path

import stim

from cliffordea import enum

from nnflags import comparison as CMP
from nnflags import constraints as C
from nnflags import g4
from nnflags import g6_continuing as G6
from nnflags import willow_noise as WN
from nnflags.verify import load_measurement, verify

R = Path("results")


def references():
    out = {}
    for n in ("success03",):
        out[n] = dict(full=stim.Circuit.from_file(str(R / "zz" / f"{n}.full.stim")),
                      inner=stim.Circuit.from_file(str(R / "zz" / f"{n}.inner.stim")),
                      native=None, note="ZZ + X flag, fault distance 3 (previous round's best)")
    out["G4-CX"] = dict(full=stim.Circuit.from_file(str(R / "g4" / "G4-CX.full.stim")),
                        inner=stim.Circuit.from_file(str(R / "g4" / "G4-CX.inner.stim")),
                        native=stim.Circuit.from_file(str(R / "g4" / "G4-native_CZH.inner.stim")),
                        note="Google's as-run double check (Fig. 2), CX form; native = its own CZ + H")
    inner = G6.g4_without_q7()
    out["G4-G6style"] = dict(full=g4.full_for(inner), inner=inner, native=None,
                             note="G4 with q7 unmeasured, as in G6 (Fig. 4 grafting)")
    return out


def emb_of(inner):
    return {q: (int(a), int(b)) for q, (a, b) in C.native_coords(inner).items()}


def validate(name, d, shots_uniform=10_000_000, shots_willow=4_000_000, cal=None):
    t0 = time.perf_counter()
    full, inner = d["full"], d["inner"]
    emb = emb_of(inner)
    r = dict(note=d.get("note", ""), **CMP.structure(inner))
    r["strict"] = C.summarize(C.check_circuit(inner, emb))
    r["continuing"] = len(C.continuing_data_violations(inner, emb))
    for mfc in (2, 3):
        v = verify(full, inner, max_fault_count=mfc)
        r[f"mfc{mfc}"] = dict(T=v["T"], S=v["S"], rate=v["error_rate_per_kept_shot"],
                              fault_count=v["fault_count"])
    en, _ = CMP.enumerated(full, inner, p_list=(CMP.P0,), mfc=3, detectors_mfc=4)
    e = en[CMP.P0]
    m = load_measurement(full, inner)
    mc = CMP.mc_acceptance(enum.noise.uniformly_depolarize(m.INNER_CIRCUIT, noise_level=CMP.P0),
                           shots_uniform, seed=zlib.crc32(f"{name}cont".encode()))
    r["uniform"] = dict(rate_T_mfc3=r["mfc3"]["rate"]["T"], acc_enum_T=e["T"]["acceptance"],
                        acc_enum_detectors=e["detectors"]["acceptance"], mc=mc,
                        attempts=1 / mc["acceptance"],
                        T_error_per_attempt=r["mfc3"]["rate"]["T"] * mc["acceptance"])
    # realistic Willow noise, native CZ + H at the circuit's own Willow positions
    native = d["native"] if d["native"] is not None else WN.cx_to_native(inner)
    r["native_ticks"] = native.num_ticks
    vn = verify(full, native, max_fault_count=3)
    r["native_uniform_counts_equal"] = vn["T"] == r["mfc3"]["T"] and vn["S"] == r["mfc3"]["S"]
    mn = load_measurement(full, native)
    r["willow"] = {}
    for model in ("calibration", "spec"):
        prm = WN.model_params(model, cal, emb)
        noisy_sym, _ = WN.noisy_native(mn.INNER_CIRCUIT, prm, "symmetric")
        noisy_asym, rmap = WN.noisy_native(mn.INNER_CIRCUIT, prm, "asymmetric")
        en, _ = CMP.enumerated(full, native, mfc=WN.MFC_CHECK, noisy=noisy_sym)
        e = en["custom"]
        rate3 = e["T"]["rate_by_mfc"][3]
        mcw = CMP.mc_acceptance(noisy_asym, shots_willow, seed=zlib.crc32(f"{name}{model}".encode()),
                                readout=rmap)
        r["willow"][model] = dict(rate_T=rate3, rate_T_mfc4=e["T"]["rate"], T_counts=e["T"]["counts"],
                                  acc_enum_detectors=e["detectors"]["acceptance"], mc=mcw,
                                  attempts=1 / mcw["acceptance"],
                                  T_error_per_attempt=rate3 * mcw["acceptance"])
        print(name, model, CMP.kst_now(), f"1 in {1 / rate3:,.0f}", f"acc {mcw['acceptance']:.4f}", flush=True)
    r["runtime_s"] = time.perf_counter() - t0
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", nargs="+", required=True, help="path prefixes of new circuits (.full/.inner.stim)")
    ap.add_argument("--out", default="results/continuing_validation.json")
    ap.add_argument("--shots-uniform", type=int, default=10_000_000)
    ap.add_argument("--shots-willow", type=int, default=4_000_000)
    a = ap.parse_args()
    cal = WN.load_calibration()
    ds = {}
    for p in a.new:
        n = Path(p).name
        ds[n] = dict(full=stim.Circuit.from_file(p + ".full.stim"),
                     inner=stim.Circuit.from_file(p + ".inner.stim"), native=None,
                     note=f"continuing-data search ({p})")
    ds.update(references())
    rec = dict(started=CMP.kst_now(), settings=dict(
        uniform="enum.noise.uniformly_depolarize p = 0.001, CX form; MC 10,000,000 shots, kept = no detector",
        willow="willow_noise calibration / spec models, native CZ + H at own Willow positions; enumeration "
               "mfc 4 (table mfc 3); MC 4,000,000 shots, asymmetric readout",
        durations_ns=WN.DUR, reset_error=WN.RESET_ERROR), designs={})
    for n, d in ds.items():
        rec["designs"][n] = validate(n, d, a.shots_uniform, a.shots_willow, cal)
        Path(a.out).write_text(json.dumps(rec, indent=1, default=str))
    rec["finished"] = CMP.kst_now()
    Path(a.out).write_text(json.dumps(rec, indent=1, default=str))


if __name__ == "__main__":
    main()
