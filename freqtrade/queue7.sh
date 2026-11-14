#!/bin/bash
# sources_more7 (2761 strategija, pirma 480 ne remiotore): batchM36..M91, Docker be interneto, po 2 testus
cd "$(dirname "$0")"
for k in $(seq 36 91); do b=batchM$k
  [ -d user_data/strategies/$b ] || continue
  BATCH=$b .venv/bin/python run_batch.py -j 3 > results/${b}_run.log 2>&1
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
echo Q7_DONE > results/queue7_done.txt
