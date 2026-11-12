"""Test 4, step A1: validate Clifft (exact near-Clifford, real T) against Google's qsim
(state vector, real T) on the same noisy double-check circuits, before Clifft is trusted
for the full pipeline (double check + lattice-surgery escape, too large for qsim).

Same circuit for both (clifft_bridge.py): ideal |T_L> in, the double check with real T and
DEPOLARIZE1(p) on every qubit after every moment, ideal decode. Counted with the E4 rule.

    .venv/bin/python "qvm-google (main)/test4_cs02_lattice_surgery_escape_realT_clifft/validate_clifft.py" \
        [--qsim-shots 4000000] [--clifft-shots 200000000] [--workers 12]
    -> results/validation/<design>_p<p>.json (qsim chunks resumable), RESULTS_validation.md
"""
import argparse
import datetime as dt
import json
import math
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

import clifft
from scipy.stats import beta

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clifft_bridge as B  # noqa: E402

QW = B.QW
RES = HERE / "results" / "validation"
DESIGNS = ["G4_G6style", "cont_success02", "g6fit00"]
LABEL = {"G4_G6style": "Google G4 G6-style (FD 2)", "cont_success02": "cs02 (ours, FD 3)",
         "g6fit00": "#0 (ours, G6-fit, FD 3)"}
PS = [0.002, 0.005]


def kst():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d %I:%M %p KST")


def rate(x, n):
    lo = 0.0 if x == 0 else float(beta.ppf(0.025, x, n - x + 1))
    hi = float(beta.ppf(0.975, x + 1, n - x)) if x < n else 1.0
    return dict(events=x, of=n, rate=x / n if n else float("nan"), ci95=[lo, hi])


def _qsim_chunk(args):
    name, p, k, reps, path = args
    d = B.register(name)
    seed = zlib.crc32(f"{name}:{p}:{k}".encode())
    r = QW.qsim(seed=seed).run(B.noisy_circuit(d, p), repetitions=reps)
    c = QW.e4_counts(d, r.measurements)
    c.update(chunk=k, seed=seed)
    Path(path).write_text(json.dumps(c))
    return c


def run_qsim(name, p, shots, chunk, workers, log):
    cdir = RES / "qsim_chunks"
    cdir.mkdir(parents=True, exist_ok=True)
    todo, done = [], []
    for k in range(shots // chunk):
        path = cdir / f"{name}_p{p}_{k:05d}.json"
        if path.exists():
            done.append(json.loads(path.read_text()))
        else:
            todo.append((name, p, k, chunk, str(path)))
    log(f"qsim {name} p={p}: {len(done)} chunks done, {len(todo)} to run")
    t0 = time.time()
    with Pool(workers) as pool:
        for i, c in enumerate(pool.imap_unordered(_qsim_chunk, todo)):
            done.append(c)
            if (i + 1) % 100 == 0:
                log(f"  {i + 1}/{len(todo)} chunks, {time.time() - t0:.0f} s")
    S = {k: sum(c[k] for c in done) for k in ("shots", "kept", "kept_code", "kept_code_logical_error")}
    return dict(shots=S["shots"], acceptance=S["kept"] / S["shots"], kept_code=S["kept_code"],
                error=rate(S["kept_code_logical_error"], S["kept_code"]))


def run_clifft(name, p, shots, threads):
    d = B.register(name)
    txt, nd = B.to_clifft_text(B.noisy_circuit(d, p), d)
    ncode = len(d.data) - 1
    progA = clifft.compile(txt, postselection_mask=[1] * (nd + ncode), expected_observables=[0])
    progK = clifft.compile(txt, postselection_mask=[1] * nd + [0] * ncode)
    t0 = time.time()
    seed = zlib.crc32(f"clifft:{name}:{p}".encode())
    rA = clifft.sample_survivors(progA, shots, seed=seed, threads=threads)
    rK = clifft.sample_survivors(progK, shots, seed=seed + 1, threads=threads)
    return dict(shots=shots, acceptance=rK.passed_shots / rK.total_shots, kept_code=rA.passed_shots,
                error=rate(int(rA.logical_errors), int(rA.passed_shots)), wall_s=round(time.time() - t0, 1))


def agree(a, b):
    """Two-proportion z-score of the error rates and of the acceptances."""
    ea, eb = a["error"], b["error"]
    pa, pb = ea["events"] / ea["of"], eb["events"] / eb["of"]
    pool = (ea["events"] + eb["events"]) / (ea["of"] + eb["of"])
    se = math.sqrt(pool * (1 - pool) * (1 / ea["of"] + 1 / eb["of"]))
    z_err = (pa - pb) / se if se else 0.0
    sa = math.sqrt(a["acceptance"] * (1 - a["acceptance"]) / a["shots"] + b["acceptance"] * (1 - b["acceptance"]) / b["shots"])
    return dict(z_error=z_err, z_acceptance=(a["acceptance"] - b["acceptance"]) / sa)


def one_in(x):
    return f"1 in {1 / x:,.0f}" if x > 0 else "0 events"


def report(rows):
    L = [f"# Test 4, step A1: Clifft vs Google's qsim, real T (written {kst()})", "",
         "Same noisy circuit in both simulators (`clifft_bridge.py`): ideal |T_L> in, the double check with real T "
         "gates and DEPOLARIZE1(p) on every qubit after every moment, ideal decode; counted with the E4 rule "
         "(error per kept T state = wrong logical among kept shots in the code space). Pauli noise because Clifft "
         "supports only Pauli channels: this is a simulator cross-check, not a Willow-noise result.", "",
         "| circuit | p | simulator | shots | acceptance | errors / kept in code | error per kept T state (95 % CI) |",
         "|---|---|---|---|---|---|---|"]
    verdicts = []
    for name, p, q, c in rows:
        for lab, r in (("qsim", q), ("Clifft", c)):
            e = r["error"]
            L.append(f"| {LABEL[name]} | {100 * p:.1f} % | {lab} | {r['shots']:,} | {100 * r['acceptance']:.2f} % | "
                     f"{e['events']} / {e['of']:,} | {one_in(e['rate'])} ({one_in(e['ci95'][1])} to {one_in(e['ci95'][0])}) |")
        a = agree(q, c)
        ok = abs(a["z_error"]) < 3 and abs(a["z_acceptance"]) < 3
        verdicts.append(ok)
        L.append(f"| | | **agreement** | | z = {a['z_acceptance']:+.2f} | | z = {a['z_error']:+.2f} → **{'agree' if ok else 'DISAGREE'}** |")
    L += ["", f"**Verdict: {'Clifft agrees with qsim in every case (|z| < 3)' if all(verdicts) else 'at least one case disagrees; do not use Clifft before finding out why'}.**", "",
          "z = (Clifft − qsim) / combined standard error, for the acceptance and for the error rate.", ""]
    (HERE / "RESULTS_validation.md").write_text("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qsim-shots", type=int, default=4_000_000)
    ap.add_argument("--clifft-shots", type=int, default=200_000_000)
    ap.add_argument("--chunk", type=int, default=5000)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    log = lambda *x: print(f"[{kst()}]", *x, flush=True)
    rows = []
    for name in DESIGNS:
        for p in PS:
            c = run_clifft(name, p, a.clifft_shots, a.workers)
            log(f"clifft {name} p={p}: {c['error']['events']} errors / {c['kept_code']:,}, acceptance {c['acceptance']:.4f}, {c['wall_s']} s")
            q = run_qsim(name, p, a.qsim_shots, a.chunk, a.workers, log)
            log(f"qsim {name} p={p}: {q['error']['events']} errors / {q['kept_code']:,}, acceptance {q['acceptance']:.4f}")
            (RES / f"{name}_p{p}.json").write_text(json.dumps(dict(qsim=q, clifft=c), indent=1))
            rows.append((name, p, q, c))
            report(rows)
    log("done")


if __name__ == "__main__":
    main()
