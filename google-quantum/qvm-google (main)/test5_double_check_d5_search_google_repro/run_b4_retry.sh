#!/bin/bash
# Test 5, B4 retry (tmux "test5", window "retry"): after run_b4.sh ends, the circuits that still ran out of
# memory at 12 GB are re-run ONE at a time with a 36 GB cap, best first by the uniform-noise rate (B2),
# at most 6 of them. Second pass and Clifft are not repeated.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
D="qvm-google (main)/test5_double_check_d5_search_google_repro"
L="$D/logs/b4_real_noise.log"
until grep -q "^exit" "$L"; do sleep 60; done
NAMES=$(.venv/bin/python - <<PY
import json
r = json.load(open("$D/results/b4/b4.json"))
rows = {f"seed{x['seed']}": x for x in map(json.loads, open("$D/results/b2_search/trees.jsonl")) if x["stage"] == "SUCCESS"}
capped = [k for k, v in r.items() if k in rows and not v["models"]]
capped.sort(key=lambda k: rows[k]["rate_mfc4"])
print(",".join(capped[:6]))
PY
)
echo "[retry $(TZ=Asia/Seoul date +'%I:%M %p') KST, one at a time, 36 GB: $NAMES]" >> "$L"
ulimit -v 36000000
.venv/bin/python "$D/b4_real_noise.py" --mfc 4 --threads 1 --retry-errors --skip-second-pass --names "$NAMES" >> "$L" 2>&1
echo "retry exit $?" >> "$L"
