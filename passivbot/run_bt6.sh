#!/bin/bash
cd "$(dirname "$0")"
S=BTC,ETH,XRP,BNB,SOL,DOGE,ADA,TRX,LINK,AVAX,LTC,DOT
for C in ema_anchor hsl_npos1; do for P in "2021-11-08 2026-11-08" "2019-12-01 2021-11-08"; do set -- $P
  docker run --rm --memory 12g --user "$(id -u):$(id -g)" -e HOME=/tmp -e MPLCONFIGDIR=/tmp \
    -v "$PWD/caches:/app/caches" -v "$PWD/backtests:/app/backtests" passivbot:stamped \
    python src/backtest.py configs/examples/$C.json --suite n -e binance -dp all -s $S -sd $1 -ed $2 > out/${C}_12_$1.log 2>&1
  echo "$C $1"
done; done
echo PB6_DONE
