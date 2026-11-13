#!/bin/bash
# po detail_q2: E0V1E_DCA3 ir EI3v2 1m detalumas 2022–2025 po metus
cd "$(dirname "$0")"
until grep -q DONE2 results/validate50/detail_q.log; do sleep 60; done
for S in E0V1E_DCA3 EI3v2_tag_cofi_green; do for Y in 2022 2023 2024 2025; do for DT in none 1m; do
  TAG=_$Y bash detail.sh $S 5m $DT alts10 ${Y}0101-$((Y+1))0101 >> results/validate50/detail_q.log
done; done; done
echo DONE3 >> results/validate50/detail_q.log
