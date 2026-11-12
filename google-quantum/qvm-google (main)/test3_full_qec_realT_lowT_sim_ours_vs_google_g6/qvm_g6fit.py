"""Test 3, step 2: QVM checks (E1-E4, real T gates, Willow noise) of the G6-fit double checks
on their own (13-15 qubits fit the QVM's state vector), before the splice into G6.

Runs test 2's run_qvm.py unchanged, with its results directory redirected to
results/qvm/ here.

    .venv/bin/python "qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6/qvm_g6fit.py" e1 \
        --design "g6fit04=qvm-google (main)/test3_full_qec_realT_lowT_sim_ours_vs_google_g6/results/g6_search_d6n14/success04"
    #   e2 | e3 | e4 --shots 4000000
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "test2_cs02_continuing_data_vs_google"))
import run_qvm  # noqa: E402

run_qvm.RES = HERE / "results" / "qvm"

if __name__ == "__main__":
    run_qvm.main()
