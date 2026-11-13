#!/bin/bash
# Martingale 12 monetų: tikrai nematytas 2019-12 – 2021-04-20 ir mokesčių stresas (maker 0,1 %, taker 0,1 %)
cd "$(dirname "$0")"
S=BTC,ETH,XRP,BNB,SOL,DOGE,ADA,TRX,LINK,AVAX,LTC,DOT
run() { docker run --rm --memory 12g --user "$(id -u):$(id -g)" -e HOME=/tmp -e MPLCONFIGDIR=/tmp \
    -v "$PWD/caches:/app/caches" -v "$PWD/backtests:/app/backtests" passivbot:stamped \
    python src/backtest.py configs/examples/default_trailing_martingale_long.json --suite n -e binance -dp all -s $S "$@"; }
for TW in 0.75 1.5; do run -sd 2019-12-01 -ed 2021-04-20 -ltwel $TW > out/mart12_oos_tw$TW.log 2>&1; echo "oos $TW"; done
for TW in 0.75; do run -sd 2021-11-08 -ed 2026-11-08 -ltwel $TW --backtest.maker_fee_override 0.001 --backtest.taker_fee_override 0.001 > out/mart12_fee_tw$TW.log 2>&1; echo "fee $TW"; done
echo PB4_DONE
