#!/bin/bash
# Martingale TWEL 0,75 su 2021-11 top 20 (įskaitant vėliau žlugusias LUNA, FTT) – išgyvenusiųjų iškraipymo patikra
cd "$(dirname "$0")"
S=BTC,ETH,BNB,SOL,ADA,XRP,DOT,DOGE,AVAX,LUNA,SHIB,MATIC,LTC,LINK,UNI,ALGO,BCH,ATOM,FTT,TRX
for TW in 0.75; do
docker run --rm --memory 12g --user "$(id -u):$(id -g)" -e HOME=/tmp -e MPLCONFIGDIR=/tmp \
  -v "$PWD/caches:/app/caches" -v "$PWD/backtests:/app/backtests" passivbot:stamped \
  python src/backtest.py configs/examples/default_trailing_martingale_long.json --suite n -e binance -dp all -s $S -ltwel $TW -sd 2021-11-08 -ed 2026-11-08 > out/mart20_2021top_tw$TW.log 2>&1
done
echo PB5_DONE
