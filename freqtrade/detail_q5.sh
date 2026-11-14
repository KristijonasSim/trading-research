#!/bin/bash
# 2026 m. 1m detalumas geriausioms (alts10)
cd "$(dirname "$0")"
for S in EI3v2_tag_cofi_green NASOSv5_mod3 abbas NASMAO; do
  [ -f user_data/strategies/validate50/$S.py ] || cp ../best_strategies/$S.py user_data/strategies/validate50/
  for DT in none 1m; do TAG=_2026 bash detail.sh $S 5m $DT alts10 20260101-20261108 >> results/validate50/detail_q.log; done
done
echo DONE5 >> results/validate50/detail_q.log
