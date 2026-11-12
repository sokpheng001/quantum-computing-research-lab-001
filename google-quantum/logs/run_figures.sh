#!/bin/bash
# Waits for the Steps 0-2 run (logs/DONE), then makes figures via headless Claude Code.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
CL=/home/ubuntu/.vscode-server/extensions/anthropic.claude-code-2.1.314-linux-x64/resources/native-binary/claude
kst() { TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST'; }
while [ ! -f logs/DONE ]; do sleep 30; done
echo "FIGURES START $(kst)" >> logs/timing.txt
"$CL" -p "$(cat logs/PROMPT_figures.md)" \
  --model claude-opus-5-5 \
  --allowedTools "Bash Read Write Edit Glob Grep" \
  --output-format stream-json --verbose \
  > logs/figures_stream.jsonl 2> logs/figures_stderr.log
echo "FIGURES EXIT $? $(kst)" >> logs/timing.txt
git -C cliffordea status --porcelain > logs/cliffordea_check_after_figures.txt 2>&1
touch logs/FIGURES_DONE
