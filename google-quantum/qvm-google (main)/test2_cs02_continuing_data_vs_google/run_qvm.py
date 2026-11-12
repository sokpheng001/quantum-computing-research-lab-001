"""QVM checks (E1-E4 of RESULTS_qvm.md) for circuits of the continuing-data search round.

Reuses qvm_willow.py unchanged: the new design is registered in qvm_willow.DESIGNS
and the results directory is redirected to this test's results/.

    .venv/bin/python "qvm-google (main)/test2_cs02_continuing_data_vs_google/run_qvm.py" e1 --design NAME=results/continuing/success00
    .venv/bin/python "qvm-google (main)/test2_cs02_continuing_data_vs_google/run_qvm.py" e2 --design ...
    .venv/bin/python "qvm-google (main)/test2_cs02_continuing_data_vs_google/run_qvm.py" e3 --design ... [--workers 12]
    .venv/bin/python "qvm-google (main)/test2_cs02_continuing_data_vs_google/run_qvm.py" e4 --design ... --shots 2000000
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # google-quantum/
sys.path.insert(0, str(HERE.parent))  # qvm_willow.py, the shared engine
import qvm_willow as QW  # noqa: E402

RES = HERE / "results"


def register(spec: str) -> str:
    name, prefix = spec.split("=")
    QW.DESIGNS[name] = (ROOT / f"{prefix}.full.stim", ROOT / f"{prefix}.inner.stim", "CX",
                        "continuing-data search: fault distance 3, data lines disjoint from measured lines")
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exp", choices=["e1", "e2", "e3", "e4"])
    ap.add_argument("--design", required=True, help="NAME=path prefix of .full/.inner.stim")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--random-pairs", type=int, default=2000)
    ap.add_argument("--shots", type=int, default=2_000_000)
    ap.add_argument("--chunk", type=int, default=5000)
    a = ap.parse_args()
    os.chdir(ROOT)
    RES.mkdir(parents=True, exist_ok=True)
    QW.RES = RES
    name = register(a.design)
    if a.exp == "e1":
        dev = QW.device()
        out = dict(started=QW.kst_now(), processor=QW.PROCESSOR, designs={name: QW.e1_design(name, dev)})
        from nnflags import constraints as C
        d = QW.load_design(name)
        out["designs"][name]["continuing_data_violations"] = len(
            C.continuing_data_violations(d.inner_src, d.pos, d.data))
        QW._dump(out, RES / f"e1_{name}.json")
    elif a.exp == "e2":
        QW._dump(dict(started=QW.kst_now(), designs={name: QW.e2_design(name)}), RES / f"e2_{name}.json")
    elif a.exp == "e3":
        QW._dump(QW.run_e3(a.random_pairs, a.workers, designs=[name]), RES / f"e3_{name}.json")
    elif a.exp == "e4":
        res = QW.run_e4({name: a.shots}, a.chunk, a.workers, outdir=RES / "e4_chunks")
        QW._dump(dict(updated=QW.kst_now(), chunk=a.chunk, results=res), RES / f"e4_{name}.json")
        for n, s in res.items():
            print(n, s["shots"], f"{100 * s['acceptance']:.3f} %", s["logical_error_given_code"])


if __name__ == "__main__":
    main()
