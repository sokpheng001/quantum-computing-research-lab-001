#!/bin/bash
# Waits for the ZZ-flag run (logs/ZZ_DONE), then completes the design comparison.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
CL=/home/ubuntu/.vscode-server/extensions/anthropic.claude-code-2.1.314-linux-x64/resources/native-binary/claude
kst() { TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST'; }
while [ ! -f logs/ZZ_DONE ]; do sleep 30; done
rm -f logs/COMPARISON_DONE
echo "COMPARISON START $(kst)" >> logs/timing.txt
"$CL" -p "$(cat logs/PROMPT_comparison.md)" \
  --model claude-opus-5-5 \
  --allowedTools "Bash Read Write Edit Glob Grep" \
  --output-format stream-json --verbose \
  > logs/comparison_stream.jsonl 2> logs/comparison_stderr.log
echo "COMPARISON EXIT $? $(kst)" >> logs/timing.txt
git -C cliffordea status --porcelain --ignored > logs/cliffordea_check_comparison.txt 2>&1
touch logs/COMPARISON_DONE
