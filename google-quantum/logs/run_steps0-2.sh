#!/bin/bash
# Unattended driver: Steps 0-2 of first-ex.md via headless Claude Code.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
CL=/home/ubuntu/.vscode-server/extensions/anthropic.claude-code-2.1.314-linux-x64/resources/native-binary/claude
kst() { TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST'; }
echo "START $(kst)" > logs/timing.txt
"$CL" -p "$(cat logs/PROMPT_steps0-2.md)" \
  --model claude-opus-5-5 \
  --allowedTools "Bash Read Write Edit Glob Grep WebFetch WebSearch" \
  --output-format stream-json --verbose \
  > logs/agent_stream.jsonl 2> logs/agent_stderr.log
echo "AGENT EXIT $? $(kst)" >> logs/timing.txt
{ echo "--- cliffordea status (must be empty) ---"; git -C cliffordea status --porcelain 2>&1; git -C cliffordea rev-parse HEAD 2>&1; } > logs/cliffordea_check.txt
echo "DONE $(kst)" >> logs/timing.txt
touch logs/DONE
