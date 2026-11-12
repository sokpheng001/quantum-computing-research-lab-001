#!/bin/bash
# Unattended driver: G4 fault distance, live-rule refinement, Option 1 search (first 20 valid).
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
CL=/home/ubuntu/.vscode-server/extensions/anthropic.claude-code-2.1.314-linux-x64/resources/native-binary/claude
kst() { TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST'; }
rm -f logs/OPTION1_DONE
echo "OPTION1 START $(kst)" >> logs/timing.txt
"$CL" -p "$(cat logs/PROMPT_option1.md)" \
  --model claude-opus-5-5 \
  --allowedTools "Bash Read Write Edit Glob Grep WebFetch WebSearch" \
  --output-format stream-json --verbose \
  > logs/option1_stream.jsonl 2> logs/option1_stderr.log
echo "OPTION1 EXIT $? $(kst)" >> logs/timing.txt
git -C cliffordea status --porcelain --ignored > logs/cliffordea_check_option1.txt 2>&1
touch logs/OPTION1_DONE
