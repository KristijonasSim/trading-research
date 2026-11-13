#!/bin/bash
# 1m detalumo patikra atrinktoms strategijoms, metai po vienus (RAM)
cd "$(dirname "$0")"
for S in NASOSv5_mod3 ckNSJT_morning; do
  for Y in 2022 2023 2024 2025; do
    for DT in none 1m; do
      TAG=_$Y bash detail.sh $S 5m $DT alts10 ${Y}0101-$((Y+1))0101 >> results/validate50/detail_q.log
    done
  done
done
echo DONE >> results/validate50/detail_q.log
