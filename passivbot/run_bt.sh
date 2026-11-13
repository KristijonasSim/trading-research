#!/bin/bash
# Passivbot autoriaus pavyzdiniai konfigai, Binance futures, 2 laikotarpiai. Rezultatai: passivbot/out/*.log
cd "$(dirname "$0")"
for C in btc_long BTC_ETH_XRP_SOL_ADA_long default_trailing_martingale_long; do
  for P in "2021-11-08 2026-11-08" "2019-12-01 2021-11-08"; do set -- $P
    docker run --rm --memory 12g --user "$(id -u):$(id -g)" -e HOME=/tmp -e MPLCONFIGDIR=/tmp \
      -v "$PWD/caches:/app/caches" -v "$PWD/backtests:/app/backtests" passivbot:stamped \
      python src/backtest.py configs/examples/$C.json --suite n -e binance -sd $1 -ed $2 -dp all > out/${C}_$1.log 2>&1
    echo "$C $1 baigta: $(tail -1 out/${C}_$1.log)"
  done
done
echo PB_DONE
