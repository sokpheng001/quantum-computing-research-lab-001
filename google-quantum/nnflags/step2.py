"""Step 2: verify() on the bundled d3a6 / d3a6f2 files vs the Step 0 results.

Usage: python -m nnflags.step2 [--out results]
"""
import argparse
import json
from pathlib import Path

from nnflags.verify import bundled_paths, verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results")
    out = Path(parser.parse_args().out)
    record = {}
    for name in ("d3a6", "d3a6f2"):
        r = verify(*bundled_paths(name), max_fault_count=2, states=("S", "T"))  # README order
        step0 = json.loads((out / f"step0_{name}.json").read_text())
        same = r["summary"].to_string() == step0["summary_text"]
        record[name] = {"T": r["T"], "S": r["S"], "settings": r["settings"],
                        "error_rate_per_kept_shot": r["error_rate_per_kept_shot"],
                        "malignant_T": r["malignant_configurations"]["T"],
                        "fault_count": r["fault_count"], "runtime_s": r["runtime_s"],
                        "summary_text": r["summary"].to_string(),
                        "identical_to_step0_summary": same,
                        "same_malignant_T_fault_indices": sorted(list(c) for _, c in r["malignant_configurations"]["T"])
                        == sorted(m["fault_indices"] for m in step0["malignant_T_configurations"]),
                        "same_T_rate_as_step0": r["error_rate_per_kept_shot"]["T"]
                        == step0["T_error_rate_per_kept_shot"]}
        print(f"== {name}: identical summary to Step 0: {same}; "
              f"same malignant T fault indices: {record[name]['same_malignant_T_fault_indices']}; "
              f"same T rate: {record[name]['same_T_rate_as_step0']}; runtime {r['runtime_s']:.3f} s")
        print(r["summary"].to_string())
        print("T malignant configs:", r["malignant_configurations"]["T"])
    (out / "step2.json").write_text(json.dumps(record, indent=1, default=str))


if __name__ == "__main__":
    main()
