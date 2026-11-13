#!/bin/bash
# EI3v2, NASOSv5_mod3, ckNSJT_morning su svertu, Binance futures, 10 altcoin'ų, 2021-11-08 – 2026-11-08, mokestis 0,05 %
cd "$(dirname "$0")/../.."
P="XRP/USDT:USDT BNB/USDT:USDT SOL/USDT:USDT DOGE/USDT:USDT ADA/USDT:USDT TRX/USDT:USDT LINK/USDT:USDT AVAX/USDT:USDT LTC/USDT:USDT DOT/USDT:USDT"
for S in EI3v2_tag_cofi_green NASOSv5_mod3 ckNSJT_morning; do for L in ${@:-2 3 5}; do
  LEV=$L /home/kris/trading/ft-venv/bin/freqtrade backtesting -c config_futures_market.json -s ${S}_Lev \
    --strategy-path user_data/strategies/lev --timerange 20211108-20261108 -p $P \
    --breakdown year --export trades --backtest-filename results/lev2/${S}_${L}x.json > results/lev2/${S}_${L}x.log 2>&1 &
done; done
wait
