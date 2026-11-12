#!/bin/bash
# overnight: batchM5..M13 (sources_more2), 2 tests at a time; candidate list after each batch
cd "$(dirname "$0")"
for k in 10 11 12 13; do b=batchM$k
  BATCH=$b .venv/bin/python run_batch.py -j 2 > results/${b}_run.log 2>&1
  .venv/bin/python - "$b" >> results/candidates_M.txt <<'P'
import json,glob,sys
b=sys.argv[1]
for f in glob.glob(f"results/{b}/*/summary.json"):
    s=json.load(open(f))
    if (s['cagr_pct'] or 0)>=14 and (s['max_drawdown_pct'] or 100)<35:
        print(b,s['strategy'],s['group'],s['timeframe'],s['cagr_pct'],s['max_drawdown_pct'],s['trades'],json.dumps(s['yearly_pct']))
print(b,"DONE")
P
done
echo Q2_DONE > results/queue2_done.txt
