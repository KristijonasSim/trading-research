#!/bin/bash
cd "$(dirname "$0")"
./pit_bt.sh EI3v2_tag_cofi_green
./pit_bt.sh NASOSv5_mod3
CFG=config_spot_market.json ./pit_bt.sh E0V1E_DCA3
./pit_bt.sh ckNSJT_morning
echo PIT_Q_DONE >> results/pit/pit.log
