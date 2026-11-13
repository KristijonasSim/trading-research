#!/bin/bash
# Martingale TWEL 0,75 ant kitos biržos duomenų (Bybit) – patikra, kad rezultatas nepriklauso nuo Binance kainų ypatumų
cd "$(dirname "$0")"
until grep -q PB7_DONE out/queue7.log; do sleep 30; done
S=BTC,ETH,XRP,BNB,SOL,DOGE,ADA,TRX,LINK,AVAX,LTC,DOT
docker run --rm --memory 12g --user "$(id -u):$(id -g)" -e HOME=/tmp -e MPLCONFIGDIR=/tmp \
  -v "$PWD/caches:/app/caches" -v "$PWD/backtests:/app/backtests" passivbot:stamped \
  python src/backtest.py configs/examples/default_trailing_martingale_long.json --suite n -e bybit -dp all -s $S -ltwel 0.75 -sd 2021-11-08 -ed 2026-11-08 > out/mart12_bybit.log 2>&1
echo PB8_DONE
