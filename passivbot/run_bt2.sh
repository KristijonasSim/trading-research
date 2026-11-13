#!/bin/bash
# Tie patys konfigai, bet užstatas tik USDT (btc_collateral_cap 0) – palyginama su kitais testais.
cd "$(dirname "$0")"
until grep -q PB_DONE out/queue.log; do sleep 30; done
for C in btc_long BTC_ETH_XRP_SOL_ADA_long; do
  for P in "2021-11-08 2026-11-08" "2019-12-01 2021-11-08"; do set -- $P
    docker run --rm --memory 12g --user "$(id -u):$(id -g)" -e HOME=/tmp -e MPLCONFIGDIR=/tmp \
      -v "$PWD/caches:/app/caches" -v "$PWD/backtests:/app/backtests" passivbot:stamped \
      python src/backtest.py configs/examples/$C.json --suite n -e binance -sd $1 -ed $2 -dp all --backtest.btc_collateral_cap 0 > out/${C}_usd_$1.log 2>&1
    echo "$C usd $1 baigta"
  done
done
echo PB2_DONE
