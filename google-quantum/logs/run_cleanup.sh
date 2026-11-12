#!/bin/bash
# Waits for the QVM job (logs/QVM_DONE), then tidies the project as agreed with the user on Nov 1.
# Deletes only regenerable caches and the superseded aborted ZZ run; archives/compresses the rest.
cd /home/ubuntu/quantum001-PKNU-Lab/google-quantum
kst() { TZ=Asia/Seoul date '+%Y-%m-%d %I:%M %p KST'; }
while [ ! -f logs/QVM_DONE ]; do sleep 30; done
sleep 60   # let the QVM agent's last file writes settle
R=logs/CLEANUP_REPORT.txt
{
echo "CLEANUP START $(kst)"
echo "size before: $(du -sh . | cut -f1)"

echo "1. caches"
rm -rf .pycache .pytest_cache qvm-google/.pytest_cache
find nnflags qvm-google -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null

echo "2. aborted ZZ run (superseded by the canonical run)"
rm -rf results/zz_aborted logs/search_zzflags_lenient_aborted.log
sed -i 's#in `results/zz_aborted/`#(removed in the Nov 1 cleanup; superseded by the canonical run)#; s#its files are kept in `results/zz_aborted/`, and the canonical run supersedes them#its files were removed in the Nov 1 cleanup; the canonical run supersedes them#; s#, `logs/search_zzflags_lenient_aborted.log`##' RESULTS_zzflags.md

echo "3. figures -> figures/archive/ (already done by hand at 5:00 pm; this step is a no-op if so)"
mkdir -p figures/archive
for f in embedding_d3a6.png embedding_d3a6f2.png step3_candidates.png; do
  [ -f figures/$f ] && mv figures/$f figures/archive/$f
done
sed -i 's#figures/embedding_d3a6#figures/archive/embedding_d3a6#g; s#figures/step3_candidates#figures/archive/step3_candidates#g' RESULTS_steps0-2.md RESULTS_step3.md
# figures/archive/README.txt already written by hand (Nov 1); keep it

echo "4. compress transcripts and the Step 3 candidate table"
gzip -f logs/*.jsonl
[ -f results/step3_candidates.csv ] && gzip -f results/step3_candidates.csv
sed -i 's#results/step3_candidates.csv#results/step3_candidates.csv.gz#g' RESULTS_step3.md

echo "5. full test suite after cleanup"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q nnflags/tests qvm-google/tests 2>&1 | tail -3
echo "cliffordea status (must be empty):"; git -C cliffordea status --porcelain --ignored
echo "test..py left untouched (user's file)"
echo "size after: $(du -sh . | cut -f1)"
echo "CLEANUP DONE $(kst)"
} > $R 2>&1
echo "CLEANUP DONE $(kst)" >> logs/timing.txt
touch logs/CLEANUP_DONE
