#!/bin/bash
# Martingale jautrumas: TWEL 1.0, n_positions 4 ir 12 (autoriaus 7), TWEL 0.75
cd "$(dirname "$0")"
until grep -q PB6_DONE out/queue6.log; do sleep 30; done
S=BTC,ETH,XRP,BNB,SOL,DOGE,ADA,TRX,LINK,AVAX,LTC,DOT
run() { docker run --rm --memory 12g --user "$(id -u):$(id -g)" -e HOME=/tmp -e MPLCONFIGDIR=/tmp \
    -v "$PWD/caches:/app/caches" -v "$PWD/backtests:/app/backtests" passivbot:stamped \
    python src/backtest.py configs/examples/default_trailing_martingale_long.json --suite n -e binance -dp all -s $S "$@"; }
run -sd 2021-11-08 -ed 2026-11-08 -ltwel 1.0 > out/mart12_tw1.0.log 2>&1; echo tw1.0
for NP in 4 12; do run -sd 2021-11-08 -ed 2026-11-08 -ltwel 0.75 --bot.long.risk.n_positions $NP > out/mart12_np$NP.log 2>&1; echo np$NP; done
for NP in 4 12; do run -sd 2019-12-01 -ed 2021-04-20 -ltwel 0.75 --bot.long.risk.n_positions $NP > out/mart12_oos_np$NP.log 2>&1; echo oos np$NP; done
echo PB7_DONE
