#!/bin/bash
# laukia queue9, tada paleidžia batchM95 (sources_more9)
cd "$(dirname "$0")"
until [ -f results/queue9_done.txt ]; do sleep 120; done
BATCH=batchM95 .venv/bin/python run_batch.py -j 3 > results/batchM95_run.log 2>&1
.venv/bin/python - <<'P' >> results/candidates_M.txt
import json, glob
for f in glob.glob("results/batchM95/*/summary.json"):
    s = json.load(open(f))
    try:
        if s.get("cagr_pct", 0) >= 14 and s.get("max_drawdown_pct", 100) < 35: print("batchM95", f.split("/")[2], s.get("cagr_pct"), s.get("max_drawdown_pct"))
    except Exception: pass
P
echo "batchM95 DONE" >> results/candidates_M.txt; date > results/queue10_done.txt
