#!/bin/bash
# abbas, NASMAO, SMAO 1m detalumas 2022–2025 po metus (alts10)
cd "$(dirname "$0")"
for S in abbas NASMAO SMAO; do
  [ -f user_data/strategies/validate50/$S.py ] || cp ../best_strategies/$S.py user_data/strategies/validate50/
  for Y in 2022 2023 2024 2025; do for DT in none 1m; do
    TAG=_$Y bash detail.sh $S 5m $DT alts10 ${Y}0101-$((Y+1))0101 >> results/validate50/detail_q.log
  done; done
done
echo DONE6 >> results/validate50/detail_q.log
