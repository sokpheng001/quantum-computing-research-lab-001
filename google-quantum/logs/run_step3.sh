#!/bin/bash
# Unattended driver: readout-rule update, cross-checks, figure fix, Step 3.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
CL=/home/ubuntu/.vscode-server/extensions/anthropic.claude-code-2.1.314-linux-x64/resources/native-binary/claude
kst() { TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST'; }
rm -f logs/STEP3_DONE
echo "STEP3 START $(kst)" >> logs/timing.txt
"$CL" -p "$(cat logs/PROMPT_step3.md)" \
  --model claude-opus-5-5 \
  --allowedTools "Bash Read Write Edit Glob Grep WebFetch WebSearch" \
  --output-format stream-json --verbose \
  > logs/step3_stream.jsonl 2> logs/step3_stderr.log
echo "STEP3 EXIT $? $(kst)" >> logs/timing.txt
git -C cliffordea status --porcelain --ignored > logs/cliffordea_check_step3.txt 2>&1
touch logs/STEP3_DONE
