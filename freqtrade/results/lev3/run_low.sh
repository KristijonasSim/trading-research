#!/bin/bash
# Mažesnis svertas 2020-01-01 – 2026-11-08, 10 altcoin'ų (perpaleista po kompiuterio perkrovimo)
cd "$(dirname "$0")/../.."
A="XRP/USDT:USDT BNB/USDT:USDT SOL/USDT:USDT DOGE/USDT:USDT ADA/USDT:USDT TRX/USDT:USDT LINK/USDT:USDT AVAX/USDT:USDT LTC/USDT:USDT DOT/USDT:USDT"
for SL in EI3v2_tag_cofi_green:1 EI3v2_tag_cofi_green:2 NASOSv5_mod3:1 NASOSv5_mod3:2 NASOSv5_mod3:3; do S=${SL%%:*}; L=${SL#*:}
  LEV=$L .venv/bin/freqtrade backtesting -c config_futures_market.json -s ${S}_Lev --strategy-path user_data/strategies/lev \
    --timerange 20200101-20261108 -p $A --max-open-trades 10 --breakdown year > results/lev3/alts10_${S}_${L}x.log 2>&1 &
done
wait; echo LOW_DONE
