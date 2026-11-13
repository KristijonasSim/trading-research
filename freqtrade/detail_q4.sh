#!/bin/bash
# E0V1E_DCA3 1m detalumas 2022–2025 (market orderiai -> config_spot_market.json)
cd "$(dirname "$0")"
for Y in 2022 2023 2024 2025; do for DT in none 1m; do
  CFG=config_spot_market.json TAG=_$Y bash detail.sh E0V1E_DCA3 5m $DT alts10 ${Y}0101-$((Y+1))0101 >> results/validate50/detail_q.log
done; done
echo DONE4 >> results/validate50/detail_q.log
