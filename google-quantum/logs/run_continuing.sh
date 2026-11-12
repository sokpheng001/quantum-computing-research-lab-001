#!/bin/bash
# Unattended driver: continuing-data readout rule -> G6 study, new search, validation.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
CL=/home/ubuntu/.vscode-server/extensions/anthropic.claude-code-2.1.314-linux-x64/resources/native-binary/claude
kst() { TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST'; }
rm -f logs/CONTINUING_DONE
echo "CONTINUING START $(kst)" >> logs/timing.txt
"$CL" -p "$(cat logs/PROMPT_continuing.md)" \
  --model claude-opus-5-5 \
  --allowedTools "Bash Read Write Edit Glob Grep" \
  --output-format stream-json --verbose \
  > logs/continuing_stream.jsonl 2> logs/continuing_stderr.log
echo "CONTINUING EXIT $? $(kst)" >> logs/timing.txt
git -C cliffordea status --porcelain --ignored > logs/cliffordea_check_continuing.txt 2>&1
touch logs/CONTINUING_DONE
