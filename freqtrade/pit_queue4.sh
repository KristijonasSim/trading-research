#!/bin/bash
# Išgyvenusiųjų patikra naujoms atrinktoms (2026-11-15)
cd "$(dirname "$0")"
for S in EI3v2_tag_cofi_green_2_4 abbasPublic eddies DS_Green_5m NS4_dca NFI7HO2 BearBull3 BSS2b EI3v2_tag_cofi_green_7; do
  C=config_spot.json; grep -qE "'market'|\"market\"" user_data/strategies/validate50/$S.py && C=config_spot_market.json
  MEM=${MEM:-6g} CFG=$C ./pit_bt.sh $S
done
echo PIT_Q4_DONE >> results/pit/pit.log
