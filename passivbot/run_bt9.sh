#!/bin/bash
# Martingale ant Bybit duomenų: 12 ir 4 pozicijos (TWEL 0,75) – ar Bybit nuosmukis sisteminis
cd "$(dirname "$0")"
S=BTC,ETH,XRP,BNB,SOL,DOGE,ADA,TRX,LINK,AVAX,LTC,DOT
for NP in 12 4; do
docker run --rm --memory 12g --user "$(id -u):$(id -g)" -e HOME=/tmp -e MPLCONFIGDIR=/tmp \
  -v "$PWD/caches:/app/caches" -v "$PWD/backtests:/app/backtests" passivbot:stamped \
  python src/backtest.py configs/examples/default_trailing_martingale_long.json --suite n -e bybit -dp all -s $S -ltwel 0.75 --bot.long.risk.n_positions $NP -sd 2021-11-08 -ed 2026-11-08 > out/mart_bybit_np$NP.log 2>&1
done
echo PB9_DONE >> out/queue9.log
