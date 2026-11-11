#!/bin/bash
# after queue.sh: rerun batchM tests that failed on missing modules (finished tests are skipped)
cd "$(dirname "$0")"
while [ ! -f results/queue_done.txt ]; do sleep 120; done
for b in batchM1 batchM2 batchM3 batchM4; do
  for f in results/$b/*/error.txt; do grep -qE "No module named '(custom_indicators|utils|pywt)'" "$f" 2>/dev/null && rm -rf "$(dirname "$f")"; done
  BATCH=$b .venv/bin/python run_batch.py -j 2 > results/${b}_rerun.log 2>&1
done
echo REQUEUE_DONE > results/requeue_done.txt
