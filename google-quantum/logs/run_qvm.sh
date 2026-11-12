#!/bin/bash
# Waits for the comparison job (logs/COMPARISON_DONE), then runs the Google QVM experiment.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
CL=/home/ubuntu/.vscode-server/extensions/anthropic.claude-code-2.1.314-linux-x64/resources/native-binary/claude
kst() { TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST'; }
while [ ! -f logs/COMPARISON_DONE ]; do sleep 30; done
mkdir -p qvm-google/logs; rm -f logs/QVM_DONE
echo "QVM START $(kst)" >> logs/timing.txt
"$CL" -p "$(cat logs/PROMPT_qvm.md)" \
  --model claude-opus-5-5 \
  --allowedTools "Bash Read Write Edit Glob Grep" \
  --output-format stream-json --verbose \
  > logs/qvm_stream.jsonl 2> logs/qvm_stderr.log
echo "QVM EXIT $? $(kst)" >> logs/timing.txt
git -C cliffordea status --porcelain --ignored > logs/cliffordea_check_qvm.txt 2>&1
touch logs/QVM_DONE
