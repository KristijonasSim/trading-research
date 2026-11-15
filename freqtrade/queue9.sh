#!/bin/bash
# Futures perleidimas visoms ankstesnėms partijoms, kur strategija norėjo short (spot klaida)
cd "$(dirname "$0")"
while [ ! -f results/queue8b_done.txt ]; do sleep 300; done
for b in $(grep -ls "Short strategies cannot run in spot" results/batch*/*/error.txt | cut -d/ -f2 | sort -u | sort -V); do
  [ -d user_data/strategies/$b ] || continue
  for e in $(grep -ls "Short strategies cannot run in spot" results/$b/*/error.txt); do rm -f "$e"; done
  BATCH=$b .venv/bin/python run_batch.py -j 3 > results/${b}_futrun.log 2>&1
  .venv/bin/python - "$b" >> results/candidates_M.txt <<'P'
import json,glob,sys
b=sys.argv[1]
for f in glob.glob(f"results/{b}/*/summary.json"):
    s=json.load(open(f))
    if s.get('mode')!='futures': continue
    if (s['cagr_pct'] or 0)>=14 and (s['max_drawdown_pct'] or 100)<35:
        print(b,s['strategy'],s['group'],s['timeframe'],s['cagr_pct'],s['max_drawdown_pct'],s['trades'],json.dumps(s['yearly_pct']),"FUTURES")
print(b,"FUT_DONE")
P
done
echo Q9_DONE > results/queue9_done.txt
