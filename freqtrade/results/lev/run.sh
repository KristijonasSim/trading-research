#!/bin/bash
# E0V1E_DCA3 su svertu 1x/3x/5x/10x, Binance futures, 10 altcoin'ų, 2021-11-08 – 2026-11-08, mokestis 0,05 %
cd "$(dirname "$0")/../.."
P="XRP/USDT:USDT BNB/USDT:USDT SOL/USDT:USDT DOGE/USDT:USDT ADA/USDT:USDT TRX/USDT:USDT LINK/USDT:USDT AVAX/USDT:USDT LTC/USDT:USDT DOT/USDT:USDT"
for L in ${@:-1 3 5 10}; do
  LEV=$L /home/kris/trading/ft-venv/bin/freqtrade backtesting -c config_futures_market.json -s E0V1E_DCA3_Lev \
    --strategy-path user_data/strategies/lev --timerange 20211108-20261108 -p $P \
    --breakdown year --export trades --backtest-filename results/lev/bt_${L}x.json > results/lev/E0V1E_${L}x.log 2>&1 &
done
wait
