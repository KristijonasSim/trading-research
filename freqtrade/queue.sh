#!/bin/bash
# runs the remaining batches one after another (resumable)
cd "$(dirname "$0")"
# (batch50i included below)
[ -d user_data/strategies/batch50j ] || .venv/bin/python make_batch.py batch50j
for b in batch50i batch50j batchM1 batchM2 batchM3 batchM4; do
  BATCH=$b .venv/bin/python run_batch.py -j 2 > results/${b}_run.log 2>&1
done
echo QUEUE_DONE > results/queue_done.txt
