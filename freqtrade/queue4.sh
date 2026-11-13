#!/bin/bash
# sources_more4 (353 strategijos): batchM16..M23, Docker be interneto, po 2 testus
cd "$(dirname "$0")"
for k in 16 17 18 19 20 21 22 23; do b=batchM$k
  [ -d user_data/strategies/$b ] || continue
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
echo Q4_DONE > results/queue4_done.txt
