#!/bin/bash
# Test 6: download Google's data release (Rosenfeld et al., arXiv:2512.13908; Zenodo 10.5281/zenodo.17872003,
# CC BY 4.0) into references/zenodo_17872003/. Waits until test 5's main d = 5 run has finished (user, Nov 5).
# Data only: the files are read, never executed (Example_usage.ipynb is not run).
B="/home/ubuntu/quantum001-PKNU-Lab/google-quantum/qvm-google (main)/test6_reproduce_google_willow_simulation_and_hardware_data"
L5="/home/ubuntu/quantum001-PKNU-Lab/google-quantum/qvm-google (main)/test5_double_check_d5_search_google_repro/logs/b4_real_noise.log"
Z="$B/references/zenodo_17872003"
until grep -q "^exit" "$L5"; do sleep 60; done
echo "[$(TZ=Asia/Seoul date +'%b %d %I:%M %p KST')] test 5 main run finished; downloading" >> "$B/logs/download.log"
cd "$Z"
declare -A MD5=([fig2.zip]=cc084df72b3a0326478de9f179c8f780 [fig3.zip]=e2494c176ecd7c3cc5ed4380cb5ff7d5 \
                [fig4.zip]=592a1a9c553b56be6adc4a95a2a6e349 [Example_usage.ipynb]=9e68254638484a62012a126dab36b566)
for f in fig2.zip fig3.zip fig4.zip Example_usage.ipynb; do
  curl -sL --retry 5 -A "research-script" -o "$f" "https://zenodo.org/api/records/17872003/files/$f/content"
  got=$(md5sum "$f" | cut -d' ' -f1)
  echo "[$(TZ=Asia/Seoul date +'%I:%M %p')] $f $(du -h "$f" | cut -f1) md5 $([ "$got" == "${MD5[$f]}" ] && echo OK || echo "MISMATCH $got")" >> "$B/logs/download.log"
done
for f in fig2.zip fig3.zip fig4.zip; do mkdir -p "${f%.zip}" && unzip -q -o "$f" -d "${f%.zip}"; done
echo "[$(TZ=Asia/Seoul date +'%I:%M %p')] unzipped; done" >> "$B/logs/download.log"
