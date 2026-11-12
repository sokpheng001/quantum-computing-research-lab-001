#!/bin/bash
# Unattended driver: generalised (multi-control) flag search for fault distance 3 on Willow.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
CL=/home/ubuntu/.vscode-server/extensions/anthropic.claude-code-2.1.314-linux-x64/resources/native-binary/claude
kst() { TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST'; }
rm -f logs/ZZ_DONE
echo "ZZ START $(kst)" >> logs/timing.txt
"$CL" -p "$(cat logs/PROMPT_zzflags.md)" \
  --model claude-opus-5-5 \
  --allowedTools "Bash Read Write Edit Glob Grep" \
  --output-format stream-json --verbose \
  > logs/zz_stream.jsonl 2> logs/zz_stderr.log
echo "ZZ EXIT $? $(kst)" >> logs/timing.txt
git -C cliffordea status --porcelain --ignored > logs/cliffordea_check_zz.txt 2>&1
touch logs/ZZ_DONE
