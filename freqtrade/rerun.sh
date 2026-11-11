#!/bin/bash
# rerun failed batch tests (missing skopt / out of memory) one by one with a larger memory limit
cd "$(dirname "$0")"
for b in batch50f batch50 batch50b batch50c batch50d batch50e; do
  BATCH=$b MEM=${MEM:-10g} .venv/bin/python run_batch.py -j 1 | grep -v skip
done
echo ALLDONE
