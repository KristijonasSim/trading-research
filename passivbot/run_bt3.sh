#!/bin/bash
# Martingale: be išgyvenusiųjų iškraipymo (BTC, ETH + alts10, kaip kituose testuose) ir mažesnė ekspozicija.
cd "$(dirname "$0")"
S=BTC,ETH,XRP,BNB,SOL,DOGE,ADA,TRX,LINK,AVAX,LTC,DOT
for TW in 1.5 0.75 0.4; do for P in "2021-11-08 2026-11-08" "2019-12-01 2021-11-08"; do set -- $P
  docker run --rm --memory 12g --user "$(id -u):$(id -g)" -e HOME=/tmp -e MPLCONFIGDIR=/tmp \
    -v "$PWD/caches:/app/caches" -v "$PWD/backtests:/app/backtests" passivbot:stamped \
    python src/backtest.py configs/examples/default_trailing_martingale_long.json --suite n -e binance -sd $1 -ed $2 -dp all -s $S -ltwel $TW > out/mart12_tw${TW}_$1.log 2>&1
  echo "tw $TW $1 baigta"
done; done
echo PB3_DONE
